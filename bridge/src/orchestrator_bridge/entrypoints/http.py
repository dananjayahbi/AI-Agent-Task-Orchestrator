"""HTTP/SSE run mode (parent plan Section 10.2; FR-MCP-01; WP-2.9).

The long-running local service: one process, one listen address, MCP over
HTTP with SSE for server-to-client messages, every connection bound to a
project from its URL path plus a project-scoped token (Section 10.2's
per-connection binding source — the reason this mode consults **no**
manifest). The mode replaced WP-2.1's exit-2 stub at MT-2.9-01; the shared
bootstrap (config layering, structured logging, correlation scope, mode
precedence) still runs in :func:`orchestrator_bridge.entrypoints.cli`.

Lifecycle: uvicorn binds the configured address (documented defaults in
``bridge/.env.example``; loopback-only unless explicitly reconfigured —
Section 12.4), the runner logs one clean startup line with the **bound**
address, and a clean shutdown finalizes every connection best-effort
(Section 10.10) before the process exits ``0``. A bind failure exits ``1``
with one scrubbed line and no traceback (NFR-10).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..config import RunMode, Settings
from ..http_service.registry import SWEEP_TICK_SECONDS
from ..http_service.runner import run as run_server
from ..transport import SendFn
from . import cli

__all__ = ["main", "run"]


def run(
    settings: Settings,
    *,
    on_server: Callable[[Any], None] | None = None,
    send: SendFn | None = None,
    time_func: Callable[[], float] | None = None,
    sweep_tick_seconds: float = SWEEP_TICK_SECONDS,
) -> int:
    """Serve until interrupted; returns the process exit code.

    The keyword seams (``on_server``/``send``/``time_func``/
    ``sweep_tick_seconds``) forward to the runner — the production path adds
    nothing of its own, so tests that drive them exercise the real entry.
    """
    kwargs: dict[str, Any] = {"sweep_tick_seconds": sweep_tick_seconds}
    if on_server is not None:
        kwargs["on_server"] = on_server
    if send is not None:
        kwargs["send"] = send
    if time_func is not None:
        kwargs["time_func"] = time_func
    return run_server(settings, **kwargs)


def main() -> int:
    """Console-script entry (``orchestrator-bridge-http``): explicit HTTP mode."""
    return cli(explicit_mode=RunMode.HTTP)
