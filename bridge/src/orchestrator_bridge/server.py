"""Single MCP server-construction path (Sections 10.11 single entry, 19.6; MT-2.1-04).

Every run mode builds its server here — one implementation, no per-mode drift,
official MCP Python SDK (Section 6.6 technology decisions). WP-2.4 onward wires
the ``orchestrator_bridge.tools`` registry into this function; until then the
server advertises the **empty tool set** of the WP-2.1 acceptance
(Section 19.1).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from mcp.server import MCPServer

from .config import Settings

__all__ = ["create_server"]


def _package_version() -> str:
    try:
        return package_version("orchestrator-bridge")
    except PackageNotFoundError:  # pragma: no cover - only outside an install
        return "0.0.0"


def create_server(settings: Settings) -> MCPServer[Any]:
    """Build the MCP server from *settings* — the shared path of all run modes.

    ``settings.log_level`` is mirrored into the SDK so its internal logging
    agrees with the bridge's structured logs; no tools are registered here yet
    (empty tool set is the WP-2.1 acceptance, Section 19.1).
    """
    return MCPServer(
        name="orchestrator-bridge",
        description="AI Agent Task Orchestrator MCP bridge (parent plan Section 10)",
        version=_package_version(),
        log_level=settings.log_level,
    )
