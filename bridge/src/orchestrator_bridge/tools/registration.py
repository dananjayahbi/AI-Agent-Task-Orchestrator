"""Register the Section 10.5 tools on the MCP server (Sections 10.5, 18;
MT-2.4-01, MT-2.6-01/04).

The bridge publishes its **own deterministic schemas** (``schemas.py``) on the
wire, not the MCP SDK's signature-derived ones. Two SDK seams make that exact
(researched against the pinned ``mcp`` SDK; MT-2.4-01):

* ``MCPServer.list_tools`` reads each registered tool's ``parameters`` field —
  assigning the declared input schema there makes the advertised contract the
  MT-2.4-01 dict, byte for byte.
* Dispatch validates against the *function*-derived pydantic model first
  (which ignores extra keys — pydantic default), so strictness lives in
  :class:`BridgeTool`: it re-validates the raw arguments against the declared
  schema (:mod:`validation`) **before** delegating, and converts every
  deliberate failure into an MCP ``ToolError`` whose message is the
  Section 9.2 code + hint + next-action JSON payload (Section 10.5 error
  rule; ``errors.payload_text``).

Handlers are thin closures over the shared :class:`ToolRuntime`; one module
per tool owns its shaping logic.
"""

from __future__ import annotations

from typing import Any, cast

from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError
from mcp.server.mcpserver.tools import Tool

from ..api_errors import ApiError
from ..error_translation import translate_error
from . import (
    attachment,
    audit_verdict,
    available_tasks,
    checkpoint,
    claim,
    context,
    create_draft_task,
    release,
    submit,
    task_details,
)
from .errors import ToolFailure, payload_text
from .runtime import ToolRuntime
from .schemas import TOOL_SPECS, ToolSpec
from .validation import validate_tool_input

__all__ = ["BridgeTool", "build_tools"]

#: One handler factory per tool — the registry of MT-2.4-01's wiring layer
#: (WP-2.6 appends the checkpoint/submission pair; WP-2.5 the attachment
#: reader).
_HANDLER_FACTORIES = {
    "get_available_tasks": available_tasks.make_handler,
    "get_task_details": task_details.make_handler,
    "claim_task": claim.make_handler,
    "read_task_attachment": attachment.make_handler,
    "log_task_checkpoint": checkpoint.make_handler,
    "submit_task_resolution": submit.make_handler,
    "release_task": release.make_handler,
    "submit_audit_verdict": audit_verdict.make_handler,
    "create_draft_task": create_draft_task.make_handler,
    "get_project_context": context.make_handler,
}


class BridgeTool(Tool):
    """One registered tool: strict schema validation plus failure shaping.

    ``spec`` carries the declared contract used by the ``run`` override; it
    is excluded from the pydantic serialization the SDK never reads.
    """

    model_config = {"arbitrary_types_allowed": True, "extra": "forbid"}

    spec: ToolSpec | None = None

    async def run(
        self, arguments: dict[str, Any], context: Any, convert_result: bool = False
    ) -> Any:
        """Validate against the declared schema, then run the handler.

        Failures all reach the model as ``ToolError`` messages of
        ``Error executing tool <name>: {json}`` — the JSON carrying ``code``,
        ``hint`` and ``next_action`` (FR-MCP-03). Unexpected crashes keep the
        SDK's hiding behaviour (nothing unexpected reaches the model).
        """
        if self.spec is None:  # pragma: no cover - registration guarantees it
            raise RuntimeError(f"tool {self.name!r} was registered without a spec")
        try:
            validated = validate_tool_input(self.spec, arguments)
        except ToolFailure as exc:
            raise ToolError(payload_text(self.name, exc.translated)) from None
        try:
            return await super().run(validated, context, convert_result=convert_result)
        except UnexpectedToolError as exc:
            # A "crash" wrapper whose cause may still be a deliberate bridge
            # failure (the SDK wraps anything raised by the handler body).
            cause = exc.__cause__
            if isinstance(cause, ToolFailure):
                raise ToolError(payload_text(self.name, cause.translated)) from None
            if isinstance(cause, ApiError):
                raise ToolError(payload_text(self.name, translate_error(cause))) from None
            raise
        except ToolError:
            raise  # the SDK's own validation prose or a deliberate ToolError
        except ToolFailure as exc:
            raise ToolError(payload_text(self.name, exc.translated)) from None
        except ApiError as exc:
            raise ToolError(payload_text(self.name, translate_error(exc))) from None


def build_tools(runtime: ToolRuntime) -> list[Tool]:
    """Instantiate every registered tool against *runtime* (Section 10.5 catalog)."""
    tools: list[Tool] = []
    for spec in TOOL_SPECS:
        factory = _HANDLER_FACTORIES[spec.name]
        tool = cast(
            BridgeTool,
            BridgeTool.from_function(
                factory(runtime),
                name=spec.name,
                description=spec.description,
            ),
        )
        tool.spec = spec
        # The declared schema is the wire contract; the SDK-derived one is
        # only the dispatch model (registration.py docstring).
        tool.parameters = dict(spec.input_schema)
        tools.append(tool)
    return tools
