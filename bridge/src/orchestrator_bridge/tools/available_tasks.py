"""``get_available_tasks`` (parent plan Sections 9.2, 10.5; MT-2.4-02).

Discovery tool: calls the backend's ``GET /api/v1/projects/{pid}/work`` with
the role and filters, project resolved from the bound session (never from
arguments — Section 10.3). Responses are the Section 10.5 **compact
descriptors** — id, title, priority, state, dependency status — plus
attachment *descriptors* when the backend row carries them, and never
attachment content (that is ``read_task_attachment``'s job, WP-2.5).

Pagination note (MT out-of-scope): ``limit`` caps at the backend page size of
100 and one page is fetched; tasks beyond that need a paging input decision
(recorded as an OQ in the WP changelog — no extra inputs are invented here).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any
from urllib.parse import urlencode

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["list_available_tasks", "make_handler", "task_descriptor"]

#: Descriptor fields — Section 10.5 compactness (no criteria, no checkpoint
#: history, no project data; MT-2.4-02 risk note on descriptor bloat).
_DESCRIPTOR_FIELDS: tuple[str, ...] = (
    "id",
    "title",
    "priority",
    "state",
    "depends_on",
)


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def task_descriptor(row: Mapping[str, Any]) -> dict[str, Any]:
    """One compact descriptor; attachment descriptors pass through verbatim.

    The current Task row carries no attachment list (the attachment API is
    backend WP-1.11); when a row *does* carry ``attachments``/``attachment_
    count``, the descriptor keeps them — descriptors only, never content.
    """
    descriptor = {key: row.get(key) for key in _DESCRIPTOR_FIELDS}
    for attachment_key in ("attachments", "attachment_count"):
        if attachment_key in row:
            descriptor[attachment_key] = row[attachment_key]
    return descriptor


def list_available_tasks(
    runtime: ToolRuntime,
    *,
    role: str = "coder",
    priority_filter: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    """One work-list call against the bound project; errors pass through."""
    query: dict[str, str] = {"role": role, "page_size": str(limit)}
    if priority_filter is not None:
        query["priority"] = priority_filter
    path = f"{endpoint('work_list').path.format(pid=runtime.project_id)}?{urlencode(query)}"
    try:
        envelope = runtime.client.request("GET", path)
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(envelope, Mapping) or not isinstance(envelope.get("results"), list):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="work list response is not the documented envelope",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "work_list"},
            )
        )
    tasks = [task_descriptor(row) for row in envelope["results"] if isinstance(row, Mapping)]
    result: dict[str, Any] = {"role": role, "count": len(tasks), "tasks": tasks}
    cursor = envelope.get("next_cursor")
    if cursor is not None:
        result["next_cursor"] = cursor
    return result


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def get_available_tasks(
        priority_filter: str | None = None,
        limit: int = 25,
        role: str = "coder",
    ) -> dict[str, Any]:
        """List the bound project's offerable tasks (Section 10.5)."""
        return list_available_tasks(
            runtime,
            role=role,
            priority_filter=priority_filter,
            limit=limit,
        )

    return get_available_tasks
