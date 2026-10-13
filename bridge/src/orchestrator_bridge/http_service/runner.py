"""Uvicorn runner for the HTTP/SSE run mode (Sections 10.2, 9.10, 12.4;
MT-2.9-01).

One build path (:func:`build_server`) shared by the production entry
(:func:`run`) and the tests, so what tests exercise is what serves: layered
settings decide the listen address (documented defaults, loopback-only unless
explicitly reconfigured — Section 12.4), the bound address is logged as one
clean startup line, and uvicorn's own lifecycle drives the ASGI lifespan that
starts the sweeper and finalizes every connection on shutdown (Section 10.10).

Exit codes follow the entry-point contract: ``0`` after a clean shutdown,
``1`` when the address cannot be bound (fail fast, one scrubbed line, no
traceback — NFR-10). ``on_server`` is the test seam: it receives the
:class:`uvicorn.Server` before serving starts so a test can wait for
readiness and then request a graceful exit.
"""

from __future__ import annotations

import asyncio
import sys
import time
from collections.abc import Callable
from typing import Any, Final

import uvicorn

from ..config import RunMode, Settings, validate_for_mode
from ..entrypoints import EXIT_CONFIG_ERROR, EXIT_OK
from ..logging import get_logger
from ..transport import SendFn
from .app import HttpBridgeApp, create_http_app
from .registry import SWEEP_TICK_SECONDS

__all__ = ["build_server", "run"]

_LOGGER_COMPONENT = "http.runner"

#: Uvicorn's own chatter is noise next to the bridge's structured lines: keep
#: its warnings/errors visible on the standard logging pipeline, mute the
#: INFO-level startup/access repeats (our startup line carries the address).
_UVICORN_LOG_CONFIG: Final[dict[str, Any]] = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "uvicorn": {"level": "WARNING"},
        "uvicorn.error": {"level": "WARNING"},
        "uvicorn.access": {"level": "WARNING"},
    },
}


def build_server(settings: Settings, app: HttpBridgeApp) -> uvicorn.Server:
    """One uvicorn server for *app* — the single construction path."""
    config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_config=_UVICORN_LOG_CONFIG,
        log_level="warning",
        access_log=False,
        # Bounded graceful stop: a client holding an idle keep-alive socket or
        # a server->client SSE stream gets a short drain window, then the
        # connections are closed so shutdown always completes (the lifespan
        # still finalizes every connection's backend session afterwards —
        # Section 10.10).
        timeout_graceful_shutdown=5,
    )
    return uvicorn.Server(config)


def _bound_address(server: uvicorn.Server) -> tuple[str, int] | None:
    """The real (host, port) after startup — how port 0 tests learn the port."""
    try:
        listeners = server.servers[0].sockets
    except (AttributeError, IndexError):  # pragma: no cover - defensive
        return None
    if not listeners:  # pragma: no cover - defensive
        return None
    host, port, *_ = listeners[0].getsockname()
    return str(host), int(port)


async def _serve(server: uvicorn.Server, settings: Settings) -> bool:
    """Serve until shutdown; log the bound address; ``False`` = never bound."""
    logger = get_logger(_LOGGER_COMPONENT)
    serve_task = asyncio.create_task(server.serve())
    while not server.started and not serve_task.done():
        await asyncio.sleep(0.01)
    if server.started:
        host, port = _bound_address(server) or (settings.http_host, settings.http_port)
        logger.info(
            f"bridge starting on http://{host}:{port}",
            extra={"event": "startup", "mode": "http", "host": host, "port": port},
        )
    await serve_task  # clean shutdown: lifespan finalized every connection
    return bool(server.started)


def run(
    settings: Settings,
    *,
    on_server: Callable[[uvicorn.Server], None] | None = None,
    send: SendFn | None = None,
    time_func: Callable[[], float] = time.monotonic,
    sweep_tick_seconds: float = SWEEP_TICK_SECONDS,
) -> int:
    """Serve the HTTP/SSE run mode until interrupted; return the exit code.

    No manifest is consulted (Section 10.2: HTTP binds per connection, from
    the URL and the presented token) — configuration that fails validation
    still exits ``1`` at :func:`validate_for_mode` before any socket opens.
    """
    validate_for_mode(settings, RunMode.HTTP)
    logger = get_logger(_LOGGER_COMPONENT)
    app = create_http_app(
        settings,
        send=send,
        time_func=time_func,
        sweep_tick_seconds=sweep_tick_seconds,
    )
    server = build_server(settings, app)
    if on_server is not None:
        on_server(server)
    try:
        started = asyncio.run(_serve(server, settings))
    except OSError as exc:
        print(
            f"bridge startup error: cannot listen on {settings.http_host}:"
            f"{settings.http_port} ({exc.strerror or exc})",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    except SystemExit as exc:
        # uvicorn aborts a failed bind with sys.exit(STARTUP_FAILURE) — the
        # entry contract still wins: one scrubbed line, exit 1, no traceback.
        if exc.code in (0, None):
            return EXIT_OK
        print(
            f"bridge startup error: cannot listen on {settings.http_host}:"
            f"{settings.http_port} (address in use or not permitted)",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    if not started:
        print(
            f"bridge startup error: cannot listen on {settings.http_host}:"
            f"{settings.http_port} (address in use or not permitted)",
            file=sys.stderr,
        )
        return EXIT_CONFIG_ERROR
    logger.info("bridge stopped", extra={"event": "shutdown", "mode": "http"})
    return EXIT_OK
