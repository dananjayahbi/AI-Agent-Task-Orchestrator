"""Strict input validation against the MT-2.4-01 schemas (FR-MCP-03).

The bridge validates tool arguments itself, with ``jsonschema`` against the
tool's declared input schema, *before* the MCP SDK's looser signature-derived
model runs. Two reasons this layer exists (MT-2.4-01):

* **Unknown properties are rejected** (``additionalProperties: false``) —
  the SDK's pydantic argument model ignores extra keys, which would silently
  accept a smuggled ``project_id`` and weaken the Section 10.3 binding model.
* **Errors are structured**: a failure raises :class:`ToolFailure` carrying
  a :class:`~orchestrator_bridge.error_translation.TranslatedError` — the
  Section 9.2 canonical ``VALIDATION_ERROR`` code plus the hint and next
  action of Section 10.5's tool design rules — instead of the SDK's prose.

Messages run through ``scrub_text`` (FR-SEC-04) and echo only the offending
values back to the model (they came from the model's own call).
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..error_translation import translate_error
from ..scrub import scrub_text
from .errors import ToolFailure
from .schemas import ToolSpec

__all__ = ["ToolFailure", "validate_tool_input"]

_VALIDATOR_CACHE: dict[str, Draft202012Validator] = {}


def _validator(spec: ToolSpec) -> Draft202012Validator:
    """One compiled validator per tool (schemas are static per process)."""
    validator = _VALIDATOR_CACHE.get(spec.name)
    if validator is None:
        validator = Draft202012Validator(dict(spec.input_schema))
        _VALIDATOR_CACHE[spec.name] = validator
    return validator


def _input_error(spec: ToolSpec, reasons: list[str]) -> ToolFailure:
    """Shape one VALIDATION_ERROR failure with hint and next action (FR-MCP-03)."""
    detail = "; ".join(reasons[:5])
    error = ApiError(
        code=ErrorCode.VALIDATION_ERROR,
        message=f"invalid arguments for {spec.name}: {scrub_text(detail)}",
        retryable=False,
        kind=ErrorKind.ENVELOPE,
        details={"tool": spec.name},
        correlation_id=None,
    )
    return ToolFailure(translate_error(error))


def validate_tool_input(spec: ToolSpec, arguments: Any) -> dict[str, Any]:
    """Validate *arguments* against the tool's schema; return them typed.

    ``None`` normalizes to ``{}`` (MCP clients send omitted arguments as
    absent or null interchangeably). Anything that is not an object, an
    unknown property, an out-of-enum value, a bound violation or a missing
    required key raises :class:`~orchestrator_bridge.tools.errors.ToolFailure`
    with a ``VALIDATION_ERROR`` payload naming the failing location.
    """
    payload: Any = {} if arguments is None else arguments
    reasons = [
        f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: {error.message}"
        for error in sorted(
            _validator(spec).iter_errors(payload), key=lambda item: list(item.absolute_path)
        )
    ]
    if reasons:
        raise _input_error(spec, reasons)
    if not isinstance(payload, dict):
        raise _input_error(spec, ["<root>: not an object"])
    return dict(payload)
