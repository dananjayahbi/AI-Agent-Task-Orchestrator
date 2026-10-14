"""``create_draft_task`` (parent plan Sections 10.5, 11.3, 7.2, 7.3, 8.2 T1;
UC-10, G-19; MT-3.8-02).

The decomposer's one write. The tool is a thin, honest wire call onto the
existing task-creation endpoint (``POST /api/v1/projects/{pid}/tasks`` —
WP-1.4's service, Section 7.3 id allocation under the project row lock
included) — **never** a parallel creation path. Three invariants shape it:

* **Draft-only is structural** (Section 19 WP-3.8 acceptance; MT-3.8-02
  risk note): the input schema has no ``state`` field and this module never
  sends one, so T1 (``* -> draft``) is the only transition the tool can
  cause. Publishing (T2) stays with the Owner (Section 11.3) — the bridge
  has no publish capability to misuse.
* **Role restriction is the backend's** (Section 12.2 matrix; MT-3.8-01):
  the endpoint answers ``ROLE_NOT_PERMITTED`` for tokens without the
  ``decomposer`` role (or owner/device credentials), and the tool surfaces
  that catalog code verbatim through the shared error translation — the
  bridge never re-implements authorization (Section 19.3).
* **``depends_on`` rides the documented wire**: the backend service
  validates same-project existence, self-references and cycles, refusing
  the whole create with ``VALIDATION_ERROR`` (MT-1.4-05); the bridge
  forwards the list and translates the refusal rather than guessing
  locally — completion gating at claim time remains FR-TSK-07's job.

Field mapping is the Section 7.2 names the wire expects: the tool-level
``criteria``/``scope`` inputs map to ``acceptance_criteria``/
``target_scope`` (the same deliberate rename the Section 10.5 catalog
table uses); everything else matches the endpoint 1:1.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["create_draft_task", "make_handler"]


def _malformed(endpoint_id: str) -> ToolFailure:
    """One SERVER_ERROR failure for a non-object create response."""
    return ToolFailure(
        translate_error(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="create response is not the documented task object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": endpoint_id},
            )
        )
    )


def create_draft_task(
    runtime: ToolRuntime,
    *,
    title: str,
    description: str = "",
    criteria: list[str] | None = None,
    scope: list[str] | None = None,
    test_command: str = "",
    priority: str = "medium",
    depends_on: list[str] | None = None,
) -> dict[str, Any]:
    """Create one ``draft`` task in the bound project; return the stored row.

    The body is the WP-1.4 ``TaskCreateSerializer`` contract — no
    ``session_id``/``lease_generation`` pair (this is not a lease
    operation), no ``state`` (draft-only, above), no ``project_id`` (the
    path carries the bound project — Section 10.3). ``Idempotency-Key``
    rides the transport for this mutating POST (NFR-12, ADR-012), so a
    retried create replays instead of duplicating tasks.
    """
    body: dict[str, Any] = {
        "title": title,
        "description": description,
        "acceptance_criteria": list(criteria or []),
        "target_scope": list(scope or []),
        "test_command": test_command,
        "priority": priority,
    }
    if depends_on is not None:
        body["depends_on"] = list(depends_on)
    try:
        payload = runtime.client.request(
            "POST",
            endpoint("task_create_draft").path.format(pid=runtime.project_id),
            body=body,
        )
    except ApiError as exc:
        raise ToolFailure(translate_error(exc)) from None
    if not isinstance(payload, Mapping):
        raise _malformed("task_create_draft")
    task_id = payload.get("id")
    if not isinstance(task_id, str) or not task_id:
        raise _malformed("task_create_draft")
    stored_dependencies = payload.get("depends_on")
    depends_on_list = list(stored_dependencies) if isinstance(stored_dependencies, list) else []
    return {
        "task_id": task_id,
        "state": payload.get("state"),
        "title": payload.get("title"),
        "priority": payload.get("priority"),
        "depends_on": depends_on_list,
        "version": payload.get("version"),
        "next_action": (
            "Draft created (T1). It stays hidden from coder/auditor listings "
            "until the Owner publishes it (T2) — Section 11.3: the decomposer "
            "stops here."
        ),
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def create_draft_task_tool(
        title: str,
        description: str = "",
        criteria: list[str] | None = None,
        scope: list[str] | None = None,
        test_command: str = "",
        priority: str = "medium",
        depends_on: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create one draft task (always `draft`) in the bound project."""
        return create_draft_task(
            runtime,
            title=title,
            description=description,
            criteria=criteria,
            scope=scope,
            test_command=test_command,
            priority=priority,
            depends_on=depends_on,
        )

    return create_draft_task_tool
