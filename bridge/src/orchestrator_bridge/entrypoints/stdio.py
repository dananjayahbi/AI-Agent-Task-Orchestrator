"""STDIO run mode (parent plan Section 10.2; FR-MCP-01; MT-2.1-04).

Spawned by the agent CLI inside the repository directory (Claude Code, OpenCode,
Aider and other CLIs); binds the session by working directory. Builds the shared
server (``server.create_server``) and serves MCP over stdin/stdout, with the
bridge's structured diagnostics on **stderr** so they can never corrupt the
JSON-RPC framing (verified against the MCP Python SDK — see the logging module).
"""

from __future__ import annotations

from ..config import RunMode, Settings, validate_for_mode
from ..logging import get_logger
from ..server import create_server
from . import cli

__all__ = ["main", "run"]


def run(settings: Settings) -> int:
    """Start the MCP server on stdio; returns after a clean shutdown (stdin close)."""
    validate_for_mode(settings, RunMode.STDIO)
    logger = get_logger("stdio")
    server = create_server(settings)
    logger.info("bridge starting", extra={"event": "startup", "mode": RunMode.STDIO.value})
    server.run(transport="stdio")
    logger.info("bridge stopped", extra={"event": "shutdown", "mode": RunMode.STDIO.value})
    return 0


def main() -> int:
    """Console-script entry (``orchestrator-bridge-stdio``): explicit STDIO."""
    return cli(explicit_mode=RunMode.STDIO)
