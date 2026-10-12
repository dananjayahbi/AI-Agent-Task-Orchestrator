"""STDIO run mode (parent plan Section 10.2; FR-MCP-01; MT-2.1-04, MT-2.2-01…03).

Spawned by the agent CLI inside the repository directory (Claude Code, OpenCode,
Aider and other CLIs); binds the session by working directory. Builds the shared
server (``server.create_server``) and serves MCP over stdin/stdout, with the
bridge's structured diagnostics on **stderr** so they can never corrupt the
JSON-RPC framing (verified against the MCP Python SDK — see the logging module).

Startup order (Section 10.3 steps 1–3, WP-2.2): discover the manifest upward to
the Git root, validate it against the published schema and version, then prove
the token is configured — all before the server is built. A binding failure is
logged as ``event=binding_failed`` (correlation id included), printed as one
scrubbed stderr line, and exits :data:`EXIT_CONFIG_ERROR`: the bridge never
serves unbound (FR-MCP-02; MT-2.2-01 "no silent fallback"). Session open and
the mismatch abort (steps 4–5) join with MT-2.2-04/05.
"""

from __future__ import annotations

import sys

from ..config import RunMode, Settings, validate_for_mode
from ..errors import BindingError
from ..logging import get_logger
from ..manifest import bind_startup
from ..scrub import scrub_text
from ..server import create_server
from . import EXIT_CONFIG_ERROR, cli

__all__ = ["main", "run"]


def run(settings: Settings) -> int:
    """Bind the manifest (Section 10.3 steps 1–3), then serve MCP on stdio.

    Returns after a clean shutdown (stdin close); returns
    :data:`EXIT_CONFIG_ERROR` when binding fails — logged, one scrubbed stderr
    line, no traceback, no secret.
    """
    validate_for_mode(settings, RunMode.STDIO)
    logger = get_logger("stdio")
    try:
        binding = bind_startup(settings)
    except BindingError as exc:
        logger.error(
            str(exc),
            extra={
                "event": "binding_failed",
                "mode": RunMode.STDIO.value,
                "error_type": type(exc).__name__,
            },
        )
        print(f"bridge startup error: {scrub_text(str(exc))}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    server = create_server(settings)
    logger.info(
        "bridge starting",
        extra={
            "event": "startup",
            "mode": RunMode.STDIO.value,
            "manifest_path": str(binding.manifest_path),
            "project_id": binding.project_id,
        },
    )
    server.run(transport="stdio")
    logger.info("bridge stopped", extra={"event": "shutdown", "mode": RunMode.STDIO.value})
    return 0


def main() -> int:
    """Console-script entry (``orchestrator-bridge-stdio``): explicit STDIO."""
    return cli(explicit_mode=RunMode.STDIO)
