"""The local HTTP/SSE ASGI application (Sections 10.1, 10.2, 10.3; FR-MCP-01,
FR-MCP-06; MT-2.9-01…03).

Routes (the whole surface; anything else is a catalog-coded 404):

* ``GET /health`` — liveness for operators and tests (Section 9.2 ops
  discipline, local-only): status, mode and the established-connection count.
* ``GET|POST|DELETE /projects/{project_id}/mcp`` — the MCP endpoint. MCP
  transport rules are the SDK's streamable-HTTP implementation: POST carries
  client→server messages, an ``mcp-session-id`` header routes subsequent
  requests to **one connection**, and a GET holds the server→client SSE
  stream.

The dispatch order is the two-barrier contract of FR-MCP-06:

1. URL project id validated (:mod:`binding`) — malformed never reaches a
   backend call or the filesystem;
2. bearer token required (:mod:`binding`);
3. capacity admission (:mod:`registry`);
4. per-connection session open — the backend verifies the token's project
   (second barrier);
5. established requests are routed by session id and re-checked against the
   connection's URL project **and** its own token — a cross-project request is
   refused here, locally, before any tool runs.

State lives on :class:`~orchestrator_bridge.http_service.connection.Connection`
objects only; the app holds the registry, the layered settings and the
injected seams (``send``, clock, sweep tick). Startup/shutdown ride the ASGI
lifespan: the sweeper starts with the server and **every** connection is
finalized on shutdown (Section 10.10 best-effort session end).
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Callable
from typing import Any, Final, cast

from ..api_errors import ErrorCode
from ..config import Settings
from ..correlation import (
    CORRELATION_HEADER,
    reset_correlation_id,
    resolve_incoming_id,
    set_correlation_id,
)
from ..logging import get_logger
from ..transport import SendFn
from .binding import (
    ConnectionRejection,
    bearer_token_from_headers,
    open_connection,
    parse_project_id,
)
from .connection import ConnectionState, create_connection, mcp_path
from .registry import SWEEP_TICK_SECONDS, ConnectionRegistry
from .responses import send_error, send_json

__all__ = ["HttpBridgeApp", "create_http_app"]

_LOGGER_COMPONENT = "http.app"

#: ``/projects/<id>/mcp`` — the id is validated separately so a malformed id
#: gets ``VALIDATION_ERROR`` (400) rather than a generic 404.
_MCP_PATH_PATTERN: Final = re.compile(r"\A/projects/(?P<project_id>[^/]+)/mcp\Z")

_SESSION_ID_HEADER: Final = "mcp-session-id"
_AUTHORIZATION_HEADER: Final = "authorization"


def _header(scope: Any, name: str) -> str | None:
    """Read one request header from an ASGI scope (latin-1 per the spec)."""
    for header_name, value in scope.get("headers", ()):
        if header_name.lower() == name.encode("ascii"):
            return cast(str, value.decode("latin-1"))
    return None


class HttpBridgeApp:
    """The service: routing, binding barriers, lifecycle — no global state."""

    def __init__(
        self,
        settings: Settings,
        *,
        send: SendFn | None = None,
        time_func: Callable[[], float] = time.monotonic,
        sweep_tick_seconds: float = SWEEP_TICK_SECONDS,
    ) -> None:
        self.settings = settings
        self.send = send
        self.time_func = time_func
        self.sweep_tick_seconds = sweep_tick_seconds
        self.registry = ConnectionRegistry(
            max_connections=settings.http_max_connections,
            idle_timeout_seconds=settings.http_idle_timeout_seconds,
            time_func=time_func,
        )
        self._sweeper_stop: asyncio.Event | None = None
        self._sweeper_task: asyncio.Task[None] | None = None

    # --- ASGI entry -----------------------------------------------------------

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self._lifespan(receive, send)
        elif scope["type"] == "http":
            await self._handle_http(scope, receive, send)

    async def _lifespan(self, receive: Any, send: Any) -> None:
        """Serve the ASGI lifespan: sweeper up, everything finalized on exit."""
        while True:
            message = await receive()
            kind = message["type"]
            if kind == "lifespan.startup":
                try:
                    self._sweeper_stop = asyncio.Event()
                    self._sweeper_task = asyncio.create_task(self._sweeper_main())
                except BaseException as exc:
                    await send(
                        {"type": "lifespan.startup.failed", "message": f"{type(exc).__name__}"}
                    )
                    raise
                await send({"type": "lifespan.startup.complete"})
            elif kind == "lifespan.shutdown":
                try:
                    if self._sweeper_stop is not None:
                        self._sweeper_stop.set()
                    if self._sweeper_task is not None:
                        await self._sweeper_task
                    closed = await self.registry.close_all("server_shutdown")
                    get_logger(_LOGGER_COMPONENT).info(
                        "bridge stopped",
                        extra={
                            "event": "shutdown",
                            "mode": "http",
                            "connections_closed": closed,
                        },
                    )
                except BaseException as exc:
                    await send(
                        {"type": "lifespan.shutdown.failed", "message": f"{type(exc).__name__}"}
                    )
                    raise
                await send({"type": "lifespan.shutdown.complete"})
                return

    async def _sweeper_main(self) -> None:
        """Fixed tick calling the registry sweep; never dies on one bad pass."""
        assert self._sweeper_stop is not None
        while True:
            try:
                await asyncio.wait_for(self._sweeper_stop.wait(), timeout=self.sweep_tick_seconds)
                return
            except TimeoutError:
                pass
            try:
                await self.registry.sweep()
            except Exception:  # one failing sweep must not kill the sweeper
                get_logger(_LOGGER_COMPONENT).warning(
                    "connection sweep failed", extra={"event": "sweep_failed"}
                )

    # --- routing --------------------------------------------------------------

    async def _handle_http(self, scope: Any, receive: Any, send: Any) -> None:
        # Per-request correlation scope (correlation.py WP-2.9 note): honor a
        # well-formed incoming id, else mint one — every envelope this request
        # writes and every log it emits shares it (headers.md).
        incoming = _header(scope, CORRELATION_HEADER.lower()) or ""
        token = set_correlation_id(resolve_incoming_id(incoming))
        try:
            path = str(scope["path"])
            if path == "/health":
                await self._handle_health(scope, send)
            elif path.startswith("/projects/"):
                await self._handle_mcp(scope, receive, send, path)
            else:
                await send_error(
                    send,
                    404,
                    ErrorCode.VALIDATION_ERROR,
                    f"no bridge endpoint at {path!r}.",
                    details={
                        "hint": "the local service exposes /health and /projects/<project id>/mcp.",
                        "next_action": "Point the MCP client at one of those paths.",
                    },
                )
        except ConnectionRejection as rejection:
            await send_error(
                send,
                rejection.status,
                rejection.code,
                rejection.message,
                retryable=rejection.retryable,
                details=rejection.details,
            )
        finally:
            reset_correlation_id(token)

    async def _handle_health(self, scope: Any, send: Any) -> None:
        """Liveness: 200 while the event loop serves (no auth, loopback)."""
        if str(scope.get("method", "GET")).upper() != "GET":
            await send_error(
                send,
                405,
                ErrorCode.VALIDATION_ERROR,
                "/health answers GET only.",
                details={"hint": "liveness probes use GET.", "next_action": "Retry as GET."},
            )
            return
        await send_json(
            send,
            200,
            {
                "status": "ok",
                "mode": "http",
                "connections": self.registry.size,
                "max_connections": self.settings.http_max_connections,
            },
        )

    # --- MCP endpoint ---------------------------------------------------------

    async def _handle_mcp(self, scope: Any, receive: Any, send: Any, path: str) -> None:
        match = _MCP_PATH_PATTERN.match(path)
        if match is None:
            await send_error(
                send,
                404,
                ErrorCode.VALIDATION_ERROR,
                f"no bridge endpoint at {path!r}.",
                details={
                    "hint": "the MCP endpoint is /projects/<project id>/mcp "
                    "(no trailing segments).",
                    "next_action": f"Point the MCP client at {mcp_path('<project id>')}.",
                },
            )
            return
        project_id = parse_project_id(match.group("project_id"))  # barrier 1 (local)
        token = bearer_token_from_headers(scope.get("headers", []))  # local auth
        session_id = _header(scope, _SESSION_ID_HEADER)
        if session_id is None:
            await self._open_connection(scope, receive, send, project_id, token)
        else:
            await self._route_established(scope, receive, send, project_id, token, session_id)

    async def _open_connection(
        self, scope: Any, receive: Any, send: Any, project_id: str, token: str
    ) -> None:
        """Serve an opening request: admit, bind, handshake, register."""
        logger = get_logger(_LOGGER_COMPONENT)
        if not self.registry.has_capacity():
            raise ConnectionRejection(
                503,
                ErrorCode.CONCURRENCY_LIMIT_REACHED,
                f"The bridge already serves its maximum of "
                f"{self.settings.http_max_connections} connections.",
                retryable=True,
                details={
                    "hint": "connections are bounded so one client cannot grow "
                    "the process without limit (MT-2.9-03).",
                    "next_action": "Close idle MCP sessions, or raise "
                    "http_max_connections (ORCHESTRATOR_BRIDGE_HTTP_MAX_CONNECTIONS).",
                    "reason": "connection_limit",
                },
            )
        connection = None
        bound: dict[str, str | None] = {"session_id": None}

        def _on_session(session_id: str, status: int) -> None:
            """File the connection before the client can read the response."""
            if bound["session_id"] is not None or connection is None:
                return
            bound["session_id"] = session_id
            self.registry.register(session_id, connection)
            connection.transition(ConnectionState.BOUND)
            logger.info(
                "connection bound",
                extra={
                    "event": "connection_bound",
                    "project_id": project_id,
                    "agent_session_id": connection.session.agent_session_id,
                },
            )

        try:
            opened = open_connection(project_id, token, self.settings, send=self.send)
            connection = create_connection(
                opened,
                self.settings,
                token=token,
                send=self.send,
                time_func=self.time_func,
            )
            await connection.start()
            outcome = await connection.serve(scope, receive, send, on_session=_on_session)
        except ConnectionRejection:
            await self._discard_unbound(bound, connection)
            raise
        except Exception as exc:
            await self._discard_unbound(bound, connection)
            logger.error(
                "connection setup failed",
                extra={
                    "event": "connection_setup_failed",
                    "project_id": project_id,
                    "error_type": type(exc).__name__,
                },
            )
            await send_error(
                send,
                500,
                ErrorCode.SERVER_ERROR,
                "The bridge could not serve this connection request.",
                details={
                    "hint": "an unexpected failure while starting the MCP "
                    "session; details are in the bridge log.",
                    "next_action": "Retry; if it persists, check the bridge log correlation id.",
                },
            )
            return
        if bound["session_id"] is not None:
            return
        # Handshake refused (or answered without a session id): no state may
        # survive a failed open (MT-2.9-02) — the reservation is free again.
        await self._discard_unbound(bound, connection)
        logger.warning(
            "MCP handshake not established",
            extra={
                "event": "handshake_rejected",
                "project_id": project_id,
                "status": outcome.status,
            },
        )
        if outcome.status is None:
            await send_error(
                send,
                500,
                ErrorCode.SERVER_ERROR,
                "The MCP handshake produced no response.",
                details={
                    "hint": "the per-connection session manager did not answer.",
                    "next_action": "Retry the connection.",
                },
            )

    async def _discard_unbound(self, bound: dict[str, str | None], connection: Any) -> None:
        """Release the admission slot and any half-built connection state.

        A connection registered by ``_on_session`` is closed through the
        registry (it is filed and must be popped); an unregistered one just
        gives the reservation back before finalizing.
        """
        session_id = bound.get("session_id")
        if session_id is not None:
            await self.registry.close(session_id, "setup_failed")
            return
        self.registry.cancel_reservation()
        if connection is not None:
            await connection.finalize("startup_failed")

    async def _route_established(
        self, scope: Any, receive: Any, send: Any, project_id: str, token: str, session_id: str
    ) -> None:
        """Route a request to its connection — local cross-project barrier."""
        connection = self.registry.get(session_id)
        if connection is None:
            await send_error(
                send,
                404,
                ErrorCode.VALIDATION_ERROR,
                "Unknown or expired MCP session.",
                details={
                    "hint": "the connection was closed (client DELETE, idle "
                    "timeout or bridge shutdown).",
                    "next_action": "Reconnect: a fresh initialize opens a new "
                    "connection binding (NFR-04).",
                    "reason": "unknown_session",
                },
            )
            return
        if connection.project_id != project_id:
            # FR-MCP-06 first barrier: refused locally, no tool runs, no
            # backend call is made for the requested project.
            await send_error(
                send,
                403,
                ErrorCode.AUTH_FORBIDDEN_PROJECT,
                f"This connection is bound to project {connection.project_id}; "
                f"{project_id} is a different project.",
                details={
                    "hint": "one connection serves one project (Section 10.2); "
                    "cross-project requests are rejected locally.",
                    "next_action": f"Open a separate connection to "
                    f"/projects/{project_id}/mcp with that project's token.",
                    "reason": "cross_project_request",
                },
            )
            return
        if token != connection.token:
            await send_error(
                send,
                403,
                ErrorCode.AUTH_FORBIDDEN_PROJECT,
                "The presented token is not the credential this connection was bound with.",
                details={
                    "hint": "reusing a session id under another token would "
                    "bypass the per-connection binding.",
                    "next_action": "Present the original connection token, or "
                    "open a new connection with this token.",
                    "reason": "credential_mismatch",
                },
            )
            return
        logger = get_logger(_LOGGER_COMPONENT)
        try:
            outcome = await connection.serve(scope, receive, send)
        except Exception as exc:
            logger.error(
                "request to an established connection failed",
                extra={
                    "event": "connection_request_failed",
                    "project_id": project_id,
                    "error_type": type(exc).__name__,
                },
            )
            await connection.finalize("request_failed")
            await send_error(
                send,
                500,
                ErrorCode.SERVER_ERROR,
                "The connection could not serve this request.",
                details={
                    "hint": "the MCP session manager failed; the connection was closed cleanly.",
                    "next_action": "Reconnect to open a fresh binding.",
                },
            )
            return
        if outcome.method == "DELETE" and outcome.status is not None and outcome.status < 400:
            await self.registry.close(session_id, "client_terminated")


def create_http_app(
    settings: Settings,
    *,
    send: SendFn | None = None,
    time_func: Callable[[], float] = time.monotonic,
    sweep_tick_seconds: float = SWEEP_TICK_SECONDS,
) -> HttpBridgeApp:
    """Build the service app from layered settings (the test seams live here).

    ``send`` is the WP-2.3 transport seam (backend calls answer in-process in
    tests), ``time_func`` the lifecycle clock (idle sweep with no
    wall-clock waits) and ``sweep_tick_seconds`` how often the sweeper runs.
    """
    return HttpBridgeApp(
        settings,
        send=send,
        time_func=time_func,
        sweep_tick_seconds=sweep_tick_seconds,
    )
