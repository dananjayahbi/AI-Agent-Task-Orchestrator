"""One HTTP/SSE connection: state machine, MCP session, teardown (Sections 10.2,
10.10; MT-2.9-03).

A *connection* is one MCP session on the local service: its own
:class:`~orchestrator_bridge.tools.runtime.ToolRuntime`, its own backend
agent session, its own MCP server instance and its own
``StreamableHTTPSessionManager`` — nothing a connection accrues lives in
process-global state (MT-2.9-02's isolation precondition; two connections for
different projects cannot observe each other by construction).

Lifecycle (deterministic transitions, MT-2.9-03):

``open → bound → active → closing → closed``

* ``open`` — constructed and backed by a real backend session, handshake not
  yet answered;
* ``bound`` — the initialize handshake succeeded and the registry filed the
  connection under its ``Mcp-Session-Id``;
* ``active`` — at least one post-handshake request has been served;
* ``closing``/``closed`` — :meth:`Connection.finalize` runs the **one**
  cleanup path every exit route shares: stop the session manager (ends the
  SSE stream, terminates the MCP transport), then best-effort
  ``POST /agent-sessions/{id}/end`` (Section 10.10 — logged, never blocking),
  then ``closed``.

An open SSE ``GET`` stream is *not* idle traffic: the registry's sweeper
skips connections with ``open_streams > 0`` (a silent but healthy stream is
only reclaimed after it drops and the idle interval elapses).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, MutableMapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

from ..logging import get_logger
from ..server import create_server
from ..session import AgentSession, close_session
from ..submission_spool import SubmissionSpool
from ..tools.runtime import ToolRuntime
from .binding import OpenedConnection, connection_settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from mcp.server.mcpserver import MCPServer
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    from ..config import Settings
    from ..manifest import StartupBinding
    from ..transport import SendFn

__all__ = [
    "Connection",
    "ConnectionState",
    "ServeOutcome",
    "create_connection",
    "mcp_path",
]

_LOGGER_COMPONENT = "http.connection"

#: Budget for stopping a connection's session manager (Section 10.10 — a
#: teardown may log and give up, never hang the process).
_MANAGER_STOP_TIMEOUT_SECONDS: Final = 5.0


class ConnectionState(StrEnum):
    """The MT-2.9-03 connection lifecycle states."""

    OPEN = "open"
    BOUND = "bound"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"


_ALLOWED_TRANSITIONS: Final[dict[ConnectionState, frozenset[ConnectionState]]] = {
    ConnectionState.OPEN: frozenset({ConnectionState.BOUND, ConnectionState.CLOSING}),
    ConnectionState.BOUND: frozenset({ConnectionState.ACTIVE, ConnectionState.CLOSING}),
    ConnectionState.ACTIVE: frozenset({ConnectionState.CLOSING}),
    ConnectionState.CLOSING: frozenset({ConnectionState.CLOSED}),
    ConnectionState.CLOSED: frozenset(),
}


def mcp_path(project_id: str) -> str:
    """The per-project MCP endpoint path (Section 10.2 binding source)."""
    return f"/projects/{project_id}/mcp"


@dataclass(frozen=True, slots=True)
class ServeOutcome:
    """What one delegated request answered (captured at the ASGI seam)."""

    method: str
    status: int | None
    session_id: str | None


def create_connection(
    opened: OpenedConnection,
    settings: Settings,
    *,
    token: str,
    send: SendFn | None = None,
    time_func: Callable[[], float],
) -> Connection:
    """Build the connection's own runtime, MCP server and session manager.

    The MCP server is built through the shared :func:`create_server` path
    (FR-MCP-01: identical tool registry, schemas and rules instructions as
    stdio); ``streamable_http_app`` is called only to *construct* the
    per-connection session manager — requests are delegated to
    ``manager.handle_request`` directly by :mod:`app`, and the manager's own
    idle/session caps are disabled because the registry owns the documented
    bounds (MT-2.9-03: one capacity authority, one idle authority).
    """
    conn_settings = connection_settings(settings, token)
    # MT-2.6-05 in HTTP mode: submissions still persist before upload (the
    # spool is bound; hold/ack work identically). The startup *resume sweep*
    # is stdio-wired only for now — a per-connection sweep needs a
    # project-level cadence decision (recorded follow-up, WP-2.6 changelog);
    # entries simply wait on disk until a stdio bridge for the project runs.
    runtime = ToolRuntime.from_session(
        opened.binding,
        opened.client,
        opened.session,
        spool=SubmissionSpool.default(),
        session_capability=settings.session_capability,
    )
    server = create_server(settings, runtime=runtime)
    project_id = opened.binding.project_id
    server.streamable_http_app(
        streamable_http_path=mcp_path(project_id),
        host=settings.http_host,
        session_idle_timeout=None,  # registry sweep is the single idle authority
        max_sessions=None,  # registry admission is the single capacity authority
    )
    return Connection(
        project_id=project_id,
        token=token,
        binding=opened.binding,
        session=opened.session,
        conn_settings=conn_settings,
        runtime=runtime,
        server=server,
        manager=server.session_manager,
        send=send,
        time_func=time_func,
    )


@dataclass(slots=True)
class Connection:
    """One bound connection: identity, state, and the single cleanup path."""

    project_id: str
    token: str
    binding: StartupBinding
    session: AgentSession
    conn_settings: Settings
    runtime: ToolRuntime
    server: MCPServer[Any]
    manager: StreamableHTTPSessionManager
    send: SendFn | None
    time_func: Callable[[], float]

    state: ConnectionState = ConnectionState.OPEN
    created_at: float = 0.0
    last_activity: float = 0.0
    open_streams: int = 0

    _closing: bool = field(default=False, repr=False)
    _manager_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _manager_ready: asyncio.Event = field(default_factory=asyncio.Event, repr=False)
    _manager_stop: asyncio.Event = field(default_factory=asyncio.Event, repr=False)

    def __post_init__(self) -> None:
        now = self.time_func()
        self.created_at = now
        self.last_activity = now

    # --- state machine --------------------------------------------------------

    def transition(self, target: ConnectionState) -> None:
        """Apply one deterministic transition; refuse anything else."""
        if target not in _ALLOWED_TRANSITIONS[self.state]:
            raise RuntimeError(
                f"illegal connection transition {self.state.value} -> {target.value}"
            )
        previous = self.state
        self.state = target
        get_logger(_LOGGER_COMPONENT).debug(
            "connection transition",
            extra={
                "event": "connection_state",
                "project_id": self.project_id,
                "from_state": previous.value,
                "to_state": target.value,
            },
        )

    def touch(self) -> None:
        """Record traffic; the first routed request activates the connection."""
        self.last_activity = self.time_func()
        if self.state is ConnectionState.BOUND:
            self.transition(ConnectionState.ACTIVE)

    # --- serving --------------------------------------------------------------

    async def start(self) -> None:
        """Start the per-connection session manager and wait until it serves."""
        self._manager_task = asyncio.get_running_loop().create_task(self._manager_main())
        waiter = asyncio.ensure_future(self._manager_ready.wait())
        try:
            await asyncio.wait(
                {waiter, self._manager_task},
                return_when=asyncio.FIRST_COMPLETED,
                timeout=_MANAGER_STOP_TIMEOUT_SECONDS,
            )
        finally:
            waiter.cancel()
        if not self._manager_ready.is_set():
            reason = "session manager failed to start"
            if self._manager_task.done() and not self._manager_task.cancelled():
                exc = self._manager_task.exception()
                if exc is not None:
                    reason = f"session manager failed to start: {type(exc).__name__}"
            raise RuntimeError(reason)

    async def _manager_main(self) -> None:
        async with self.manager.run():
            self._manager_ready.set()
            await self._manager_stop.wait()

    async def serve(
        self,
        scope: Any,
        receive: Any,
        send: Any,
        *,
        on_session: Callable[[str, int], None] | None = None,
    ) -> ServeOutcome:
        """Delegate one request to the connection's session manager.

        Wraps ``send`` to capture the assigned ``Mcp-Session-Id`` and the
        response status, and keeps the open-stream count so the sweeper never
        closes a live SSE stream.

        ``on_session`` (opening requests only) fires **before** the response
        start is forwarded — the registration the app performs there
        strictly precedes any byte the client can read, so a fast client's
        follow-up request can never observe the brief gap between "response
        sent" and "connection filed" (the notification-after-initialize race).
        """
        method = str(scope.get("method", "GET"))
        self.touch()
        captured: dict[str, Any] = {"status": None, "session_id": None}
        counting_stream = method == "GET"
        if counting_stream:
            self.open_streams += 1

        async def _send(message: MutableMapping[str, Any]) -> None:
            if message.get("type") == "http.response.start":
                captured["status"] = message.get("status")
                for name, value in message.get("headers", ()):
                    if name.lower() == b"mcp-session-id":
                        captured["session_id"] = value.decode("latin-1")
                if (
                    on_session is not None
                    and captured["session_id"] is not None
                    and captured["status"] is not None
                    and captured["status"] < 400
                ):
                    on_session(str(captured["session_id"]), int(captured["status"]))
            await send(message)

        try:
            await self.manager.handle_request(scope, receive, _send)
        finally:
            if counting_stream:
                self.open_streams -= 1
        return ServeOutcome(
            method=method,
            status=captured["status"],
            session_id=captured["session_id"],
        )

    # --- teardown -------------------------------------------------------------

    async def finalize(self, reason: str) -> None:
        """The one cleanup path: stop the manager, end the backend session.

        Idempotent and non-blocking for callers: a second call (a sweeper
        racing a client ``DELETE``) is a no-op, and the backend end attempt is
        Section 10.10 best-effort — failure logs and proceeds so shutdown can
        never be held open by a dead backend.
        """
        if self._closing:
            return
        self._closing = True
        logger = get_logger(_LOGGER_COMPONENT)
        from_state = self.state
        self.transition(ConnectionState.CLOSING)
        logger.info(
            "connection closing",
            extra={
                "event": "connection_closing",
                "reason": reason,
                "project_id": self.project_id,
                "agent_session_id": self.session.agent_session_id,
                "from_state": from_state.value,
            },
        )
        await self._stop_manager()
        try:
            close_session(
                self.binding,
                self.conn_settings,
                self.session,
                send=self.send,
            )
        except Exception as exc:  # teardown never raises (Section 10.10)
            logger.warning(
                "agent session end raised unexpectedly (best-effort; skipped)",
                extra={
                    "event": "session_end_failed",
                    "project_id": self.project_id,
                    "agent_session_id": self.session.agent_session_id,
                    "error_type": type(exc).__name__,
                },
            )
        self.transition(ConnectionState.CLOSED)
        logger.info(
            "connection closed",
            extra={
                "event": "connection_closed",
                "reason": reason,
                "project_id": self.project_id,
                "agent_session_id": self.session.agent_session_id,
            },
        )

    async def _stop_manager(self) -> None:
        self._manager_stop.set()
        task = self._manager_task
        if task is None:
            return
        try:
            await asyncio.wait_for(task, timeout=_MANAGER_STOP_TIMEOUT_SECONDS)
        except TimeoutError:
            pass  # wait_for already cancelled the manager task
        except asyncio.CancelledError:
            raise  # the finalizer itself was cancelled — propagate
        except Exception:  # a crashed manager logs its own cause on the way out
            pass
