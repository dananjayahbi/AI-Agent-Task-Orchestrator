"""``release_task`` (parent plan Sections 9.2, 10.5, 10.10; MT-2.4-05).

Voluntarily return a held task to ``pending`` — the Section 10.5 behavior
"No failure increment" (FR-LEA-06): the wire body carries only the ADR-012
fencing pair (``session_id`` + ``lease_generation`` from the runtime's claim
record) and the optional ``reason``; there is **no attempt/failure field the
bridge could populate** — the no-increment semantics are the backend's
contract, and the request/response shapes are pinned by the guard tests.

Without a recorded generation (e.g. the task was never claimed in this
process) the call still goes out with the session id alone: the backend's
service enforces presence for agent callers and answers
``LEASE_NOT_OWNED``/``LEASE_EXPIRED`` authoritatively — the bridge never
guesses lease state locally (Section 19.3), so the MT's shutdown-race path
stays a clean, structured next action rather than a crash.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["release_task", "release_request_body", "make_handler"]

_RELEASE_NEXT_ACTION = (
    "The task is offerable again — call get_available_tasks when you are ready for different work."
)


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def release_request_body(runtime: ToolRuntime, *, task_id: str, reason: str) -> dict[str, Any]:
    """The exact ``ReleaseRequest`` body the bridge sends (guard-test seam).

    Keys are exactly ``session_id``, ``reason`` and — when this process holds
    a recorded claim — ``lease_generation``; never a failure/attempt field
    (MT-2.4-05 acceptance: release consumes no attempt).
    """
    body: dict[str, Any] = {"session_id": runtime.agent_session_id, "reason": reason}
    generation = runtime.lease_generation(task_id)
    if generation is not None:
        body["lease_generation"] = generation
    return body


def release_task(runtime: ToolRuntime, *, task_id: str, reason: str = "") -> dict[str, Any]:
    """One voluntary release; returns the task's new state (Section 10.5)."""
    path = endpoint("release").path.format(id=task_id)
    try:
        row = runtime.client.request(
            "POST", path, body=release_request_body(runtime, task_id=task_id, reason=reason)
        )
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(row, Mapping):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="release response is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "release"},
            )
        )
    return {
        "task_id": row.get("id") if isinstance(row.get("id"), str) else task_id,
        "state": row.get("state"),
        "released": True,
        "next_action": _RELEASE_NEXT_ACTION,
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def release_task_tool(task_id: str, reason: str = "") -> dict[str, Any]:
        """Voluntarily release a held task; no failure attempt consumed."""
        return release_task(runtime, task_id=task_id, reason=reason)

    return release_task_tool
