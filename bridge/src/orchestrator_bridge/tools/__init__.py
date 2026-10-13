"""The bridge's tool registry (parent plan Sections 10.5, 18; WP-2.1 seam;
WP-2.4/MT-2.4-01).

Seeded empty by MT-2.1-01 (the WP-2.1 "empty tool set" acceptance);
MT-2.4-01 replaced the placeholder with the **core tools** of Section
10.5 as their public :class:`ToolSpec` contracts — names, input schemas and
the Section 9.2 error codes each may surface — and WP-2.6/MT-2.6-01/04
appended ``log_task_checkpoint`` and ``submit_task_resolution``.
``tests/test_tool_schemas.py`` pins the catalog against the plan table
(exact names, no ``project_id`` parameter, closed error vocabulary).

Execution wiring is one layer over: ``registration.build_tools`` turns each
spec into a runtime-bound MCP tool, and ``server.create_server`` registers
them when a bound session exists.
"""

from __future__ import annotations

from typing import Final

from .schemas import CORE_TOOL_NAMES, TOOL_SPECS, ToolSpec

__all__ = ["CORE_TOOL_NAMES", "TOOLS", "ToolSpec"]

#: name -> declared contract, in Section 10.5 catalog order.
TOOLS: Final[dict[str, ToolSpec]] = {spec.name: spec for spec in TOOL_SPECS}
