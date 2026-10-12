"""``get_task_details`` (parent plan Sections 9.2, 10.5; MT-2.4-03).

Full payload for one task of the bound project via
``GET /api/v1/tasks/{id}``: the Section 7.2 field set the backend returns —
description, acceptance criteria, target scope, test command, priority,
state, dependency and lease status, ``latest_feedback`` — nothing invented or
re-derived locally (Section 19.3). Resolution info appears when the backend
includes it (MT-2.4-03 scope: "when the backend returns it"; role gating of
that exposure is the backend's Section 12.2 authority, not the bridge's —
the tool takes no role input).

Attachment *content* never rides this payload (WP-2.5 boundary); attachment
descriptors the backend attaches to the row pass through untouched.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["get_task_details", "make_handler"]


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def get_task_details(runtime: ToolRuntime, *, task_id: str) -> dict[str, Any]:
    """Fetch the full task payload; backend errors pass through translated."""
    path = endpoint("task_details").path.format(id=task_id)
    try:
        row = runtime.client.request("GET", path)
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(row, Mapping):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="task details response is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "task_details"},
            )
        )
    return {"task": dict(row)}


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def get_task_details_tool(task_id: str) -> dict[str, Any]:
        """Full payload for one task of the bound project (Section 10.5)."""
        return get_task_details(runtime, task_id=task_id)

    return get_task_details_tool
