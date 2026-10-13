"""Connection admission, lookup, idle sweep and close-out (MT-2.9-03).

The registry is the **single capacity and idle authority** for the HTTP
service (the per-connection session manager's own caps are disabled):

* *admission* — a documented maximum concurrent-connections default
  (:data:`~orchestrator_bridge.config.DEFAULT_HTTP_MAX_CONNECTIONS`); the
  reservation counter is incremented synchronously before the backend session
  opens, so interleaved opening handshakes cannot overshoot the cap on one
  event loop;
* *lookup* — established connections are keyed by their MCP session id, which
  is also what makes routing per-connection (an id not in the registry is
  answered 404 before any handler runs);
* *idle sweep* — a connection with no request and **no open SSE stream** for
  ``http_idle_timeout_seconds`` is finalized with reason ``idle_timeout``;
  the background sweeper in :mod:`app` calls :meth:`sweep` on a fixed tick
  (tests drive it directly with an injected clock — no wall-clock sleeps);
* *close-out* — every exit path funnels through
  :meth:`Connection.finalize`, so cleanup cannot diverge between the sweeper,
  a client ``DELETE`` and process shutdown.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Final

from ..logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .connection import Connection

__all__ = ["ConnectionRegistry"]

_LOGGER_COMPONENT = "http.registry"
#: One sweep per this interval (seconds) — the tick, not the timeout; the
#: effective close granularity is tick + timeout. Not a config key: it only
#: bounds how late a close may run, never whether it runs.
SWEEP_TICK_SECONDS: Final = 30.0


class ConnectionRegistry:
    """Established connections plus the admission reservation counter."""

    def __init__(
        self,
        *,
        max_connections: int,
        idle_timeout_seconds: float,
        time_func: Callable[[], float],
    ) -> None:
        self.max_connections = max_connections
        self.idle_timeout_seconds = idle_timeout_seconds
        self._time_func = time_func
        self._connections: dict[str, Connection] = {}
        self._reserved = 0

    # --- capacity / admission -------------------------------------------------

    @property
    def size(self) -> int:
        """Established connections (what ``/health`` reports)."""
        return len(self._connections)

    @property
    def admitted_or_reserved(self) -> int:
        """Established plus in-flight handshakes — the capacity numerator."""
        return len(self._connections) + self._reserved

    def has_capacity(self) -> bool:
        """Whether one more connection may open (synchronous check+reserve)."""
        if self.admitted_or_reserved >= self.max_connections:
            return False
        self._reserved += 1
        return True

    def cancel_reservation(self) -> None:
        """Undo a reservation whose handshake never completed."""
        if self._reserved == 0:  # pragma: no cover - programming error guard
            raise RuntimeError("cancel_reservation without a live reservation")
        self._reserved -= 1

    def register(self, session_id: str, connection: Connection) -> None:
        """File a bound connection under its MCP session id."""
        self.cancel_reservation()
        self._connections[session_id] = connection

    # --- lookup ---------------------------------------------------------------

    def get(self, session_id: str) -> Connection | None:
        return self._connections.get(session_id)

    # --- close-out ------------------------------------------------------------

    async def close(self, session_id: str, reason: str) -> bool:
        """Finalize and forget one connection; ``False`` when already gone."""
        connection = self._connections.pop(session_id, None)
        if connection is None:
            return False
        await connection.finalize(reason)
        return True

    async def sweep(self) -> list[str]:
        """Close idle connections; returns the session ids finalized here.

        A connection holding an open SSE stream is never idle (its client is
        connected but quiet); one whose stream has dropped starts counting
        from the last request.
        """
        now = self._time_func()
        closed: list[str] = []
        for session_id, connection in list(self._connections.items()):
            if connection.open_streams > 0:
                continue
            if now - connection.last_activity >= self.idle_timeout_seconds:
                if await self.close(session_id, "idle_timeout"):
                    closed.append(session_id)
        if closed:
            get_logger(_LOGGER_COMPONENT).info(
                "idle connections closed",
                extra={"event": "idle_sweep", "count": len(closed)},
            )
        return closed

    async def close_all(self, reason: str) -> int:
        """Finalize every established connection (process shutdown path)."""
        session_ids = list(self._connections)
        closed = 0
        for session_id in session_ids:
            if await self.close(session_id, reason):
                closed += 1
        return closed
