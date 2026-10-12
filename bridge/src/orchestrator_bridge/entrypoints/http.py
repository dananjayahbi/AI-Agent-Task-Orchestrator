"""HTTP/SSE run mode stub (parent plan Section 10.2; MT-2.1-04).

The real mode is a long-running local service with per-connection binding
(project id in the URL path plus a project-scoped token) — implemented by
WP-2.9 (HTTP/SSE transport with per-connection binding). This stub loads the
layered config, confirms the mode selection, logs the attempt with MT-2.1-03
structured logging, and exits non-zero with a clear message: no half-built
server may look healthy (MT-2.1-04 risk note).

Note: MT-2.1-04's context text cites "WP-2.10" for HTTP mode; the parent plan
(Section 19.1) and plan-doc-series/overview.md make HTTP transport WP-2.9 and
WP-2.10 the Local Git helper — the plan wins, so this stub names WP-2.9.
"""

from __future__ import annotations

import sys

from ..config import RunMode, Settings, validate_for_mode
from ..logging import get_logger
from . import EXIT_NOT_IMPLEMENTED, cli

__all__ = ["main", "run", "NOT_IMPLEMENTED_MESSAGE"]

NOT_IMPLEMENTED_MESSAGE = (
    "HTTP/SSE run mode is not yet implemented (tracked by WP-2.9 — HTTP/SSE "
    "transport with per-connection binding); no server was started."
)


def run(settings: Settings) -> int:
    """Confirm config and mode selection, then fail fast at the WP-2.9 boundary."""
    validate_for_mode(settings, RunMode.HTTP)
    get_logger("http").info(
        "run mode requested before implementation",
        extra={"event": "mode_not_implemented", "mode": RunMode.HTTP.value},
    )
    print(NOT_IMPLEMENTED_MESSAGE, file=sys.stderr)
    return EXIT_NOT_IMPLEMENTED


def main() -> int:
    """Console-script entry (``orchestrator-bridge-http``): explicit HTTP mode."""
    return cli(explicit_mode=RunMode.HTTP)
