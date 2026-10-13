"""Structured tool failures (parent plan Sections 9.2, 10.5; MT-2.3-04 consumer).

Section 10.5's tool design rule — every error carries a stable code, a
human-readable hint and a "next action" suggestion for the model — reaches
the wire through :class:`ToolFailure`: a deliberate exception carrying a
ready-translated
:class:`~orchestrator_bridge.error_translation.TranslatedError`.

Handlers raise :class:`ToolFailure` for local, deliberate failures (and let
:class:`~orchestrator_bridge.api_errors.ApiError` propagate from the client);
``registration.BridgeTool.run`` converts either into an MCP ``ToolError``
whose message is the JSON payload below, so the model always sees the same
structure. Codes come from the translator — this module invents none
(Section 20.4 item 5).
"""

from __future__ import annotations

import json
from typing import Any

from ..api_errors import ApiError, ErrorCode
from ..error_translation import TranslatedError, translate_error
from ..git_helper.errors import GitHelperError

__all__ = ["ToolFailure", "failure_from_api_error", "failure_from_git_error", "payload_text"]


class ToolFailure(Exception):
    """One deliberate, catalog-coded tool failure destined for the model."""

    def __init__(self, translated: TranslatedError) -> None:
        super().__init__(translated.message)
        self.translated = translated


def failure_from_api_error(error: ApiError) -> ToolFailure:
    """Translate a typed backend error into a tool failure (MT-2.3-04)."""
    return ToolFailure(translate_error(error))


def failure_from_git_error(error: GitHelperError) -> ToolFailure:
    """Wrap a WP-2.10 Git-helper failure as the tool layer's structured failure.

    The helper speaks the same Section 9.2 catalog and the same
    hint/next-action contract (its own docstring pins the mirroring), so the
    conversion is a structural copy: code, message, hint, next action,
    retryable flag and details — with no backend correlation id, since no
    HTTP call was involved (MT-2.6-02 consumes this).
    """
    return ToolFailure(
        TranslatedError(
            code=ErrorCode(str(error.code)),
            message=error.message,
            hint=error.hint,
            next_action=error.next_action,
            retryable=error.retryable,
            details=error.details,
            correlation_id=None,
        )
    )


def payload_text(tool_name: str, translated: TranslatedError) -> str:
    """The wire text for one failure: the SDK's prefix plus the JSON payload.

    The prefix keeps the message recognizable to MCP clients that show only
    the first line; the JSON body carries the Section 9.2 envelope fields plus
    ``hint``/``next_action`` for the model to act on.
    """
    payload: dict[str, Any] = {
        "code": str(translated.code),
        "message": translated.message,
        "hint": translated.hint,
        "next_action": translated.next_action,
        "retryable": translated.retryable,
        "details": dict(translated.details) if translated.details is not None else None,
        "correlation_id": translated.correlation_id,
    }
    return f"Error executing tool {tool_name}: {json.dumps(payload, sort_keys=True)}"
