"""Single MCP server-construction path (Sections 10.11 single entry, 19.6; MT-2.1-04).

Every run mode builds its server here — one implementation, no per-mode drift,
official MCP Python SDK (Section 6.6 technology decisions).

With a bound session ``runtime`` (Section 10.3 steps 4–5, MT-2.2-04) the
server advertises the WP-2.4 **five core tools** (MT-2.4-01; registration is
the only seam that adds tools, so the inspector check stays honest). Without
one — the WP-2.1 skeleton acceptance and pure unit tests — the tool set is
empty, exactly as before.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from mcp.server import MCPServer

from .config import Settings
from .tools.registration import build_tools
from .tools.runtime import ToolRuntime

__all__ = ["create_server"]


def _package_version() -> str:
    try:
        return package_version("orchestrator-bridge")
    except PackageNotFoundError:  # pragma: no cover - only outside an install
        return "0.0.0"


def create_server(settings: Settings, *, runtime: ToolRuntime | None = None) -> MCPServer[Any]:
    """Build the MCP server from *settings* — the shared path of all run modes.

    ``settings.log_level`` is mirrored into the SDK so its internal logging
    agrees with the bridge's structured logs. ``runtime`` is the bound
    session: present in the stdio run mode after Section 10.3's five startup
    steps, so the five core tools are registered against it; ``None`` keeps
    the pre-WP-2.4 empty tool set.
    """
    tools = build_tools(runtime) if runtime is not None else None
    return MCPServer(
        name="orchestrator-bridge",
        description="AI Agent Task Orchestrator MCP bridge (parent plan Section 10)",
        version=_package_version(),
        log_level=settings.log_level,
        tools=tools,
    )
