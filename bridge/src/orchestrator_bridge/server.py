"""Single MCP server-construction path (Sections 10.11 single entry, 19.6; MT-2.1-04).

Every run mode builds its server here — one implementation, no per-mode drift,
official MCP Python SDK (Section 6.6 technology decisions).

With a bound session ``runtime`` (Section 10.3 steps 4–5, MT-2.2-04) the
server advertises the Section 10.5 tool catalog (WP-2.4's core tools plus
WP-2.6's ``log_task_checkpoint``/``submit_task_resolution``; registration is
the only seam that adds tools, so the inspector check stays honest), the
Section 10.7 prompt set (WP-2.8 — the four ``orchestrator:*`` prompts, pure
enhancement per ADR-011; ``build_prompts`` is the only seam that adds
prompts), and carries the Section 10.6 **rules block as the initialize-time
server instructions** (MT-2.7-03; gap G-08 channel one) — rendered from the
same :mod:`~orchestrator_bridge.rules` path the claim response and
``get_project_context`` use, with the coder template (role is only chosen at
claim time, so connect delivers the standard block — MT-2.7-03 risk note) and
the session's cached ``system_prompt_rules`` appended. Without a bound
runtime — the WP-2.1 skeleton acceptance and pure unit tests — the tool and
prompt sets are empty and no instructions are advertised, exactly as before.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version
from typing import Any

from mcp.server import MCPServer

from .config import Settings
from .prompts import build_prompts
from .rules import render_session_rules
from .tools.registration import build_tools
from .tools.runtime import ToolRuntime

__all__ = ["create_server"]


def _package_version() -> str:
    try:
        return package_version("orchestrator-bridge")
    except PackageNotFoundError:  # pragma: no cover - only outside an install
        return "0.0.0"


def _initialize_instructions(runtime: ToolRuntime) -> str:
    """The connect-time rules block (G-08 channel one; MT-2.7-03).

    Coder template, generic slot phrasings (no task exists yet), checkpoint
    interval derived from the cached policy summary's lease, project rules
    appended — :func:`render_session_rules` is the single render path shared
    with ``get_project_context`` and the claim response.
    """
    context = runtime.context
    if context is None:  # a resumed runtime self-heals through the client
        context = runtime.project_context()
    return render_session_rules(
        "coder",
        project_rules=context.rules,
        policy_summary=context.policy_summary,
    )


def create_server(settings: Settings, *, runtime: ToolRuntime | None = None) -> MCPServer[Any]:
    """Build the MCP server from *settings* — the shared path of all run modes.

    ``settings.log_level`` is mirrored into the SDK so its internal logging
    agrees with the bridge's structured logs. ``runtime`` is the bound
    session: present in the stdio run mode after Section 10.3's five startup
    steps, so the registered tools are bound against it, the Section 10.7
    prompts are advertised (WP-2.8; ADR-011 keeps them optional
    enhancements — the tool surface is identical either way) and the
    initialize response carries the Section 10.6 rules; ``None`` keeps the
    pre-WP-2.4 empty tool/prompt sets and no instructions.
    """
    tools = None
    instructions = None
    if runtime is not None:
        tools = build_tools(runtime)
        instructions = _initialize_instructions(runtime)
    server = MCPServer(
        name="orchestrator-bridge",
        description="AI Agent Task Orchestrator MCP bridge (parent plan Section 10)",
        instructions=instructions,
        version=_package_version(),
        log_level=settings.log_level,
        tools=tools,
    )
    if runtime is not None:
        for prompt in build_prompts():
            server.add_prompt(prompt)
    return server
