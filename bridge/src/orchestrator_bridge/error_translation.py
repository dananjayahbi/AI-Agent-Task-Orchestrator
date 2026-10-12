"""Error translation: canonical code + hint + next action (parent plan Sections
9.2, 10.5; MT-2.3-04).

Section 10.5's tool design rule — *every error carries a stable code, a
human-readable hint and a "next action" suggestion for the model* — applied to
the backend's Section 9.2 failures. The bridge translates; it does not extend:

* **Passthrough verbatim:** ``code``, ``message``, ``details`` and
  ``correlation_id`` come straight from the typed
  :class:`~orchestrator_bridge.api_errors.ApiError` (retryable included);
  only ``hint``/``next_action`` are added locally — nothing is rewritten,
  renamed or dropped (Section 20.5 traceability).
* **Closed catalog:** entries key only on :class:`~orchestrator_bridge.api_errors.ErrorCode`
  (the 19 Section 9.2 codes); :func:`translate_error` rejects anything else
  outright — this module can never become a second catalog
  (Section 20.4 item 5).
* **Default branch:** a catalog code without a specific entry still produces
  guidance that *names the canonical code*, so missing coverage is visible in
  what the model sees instead of silently generic (MT-2.3-04 risk note).
  ``HINTS`` currently covers all 19; the branch exists for the day a code is
  added to Section 9.2 before its wording lands here.

Wording is agent-facing behaviour: vague advice degrades recovery, so the
claim/lease entries carry the RISK-02 mitigation explicitly (stop, checkpoint,
re-claim) and every ``next_action`` names a concrete step or tool call. The
MCP tool handlers that will call :func:`translate_error` arrive with WP-2.4.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from .api_errors import ApiError, ErrorCode

__all__ = ["HINTS", "TranslatedError", "translate_error"]


@dataclass(frozen=True, slots=True)
class TranslatedError:
    """What a tool handler shows the model: the error, plus how to recover."""

    code: ErrorCode
    message: str
    hint: str
    next_action: str
    retryable: bool
    details: Mapping[str, Any] | None
    correlation_id: str | None


#: ``code -> (hint, next_action)``. Keys are exactly catalog codes; values are
#: non-empty sentences (tested). Order follows the published catalog. Typed as
#: a dict (not Mapping) so tests can monkeypatch an entry for the default branch.
HINTS: Final[dict[ErrorCode, tuple[str, str]]] = {
    ErrorCode.AUTH_REQUIRED: (
        "The bridge's agent token is missing, expired or was revoked for this backend.",
        "Stop and tell the user the agent token must be reconfigured "
        "(ORCHESTRATOR_AGENT_TOKEN or 'orchestrator init'); do not retry until it is fixed.",
    ),
    ErrorCode.AUTH_FORBIDDEN_PROJECT: (
        "The token is valid but belongs to a different project than this session.",
        "Re-orient with get_project_context and work only inside the bound project; "
        "never attempt cross-project access.",
    ),
    ErrorCode.VALIDATION_ERROR: (
        "The request was malformed or failed server-side validation.",
        "Fix the input named in details and call again; do not repeat the same payload.",
    ),
    ErrorCode.TASK_NOT_FOUND: (
        "No task with that id exists in this project.",
        "Call get_available_tasks to refresh the list and pick an existing task.",
    ),
    ErrorCode.TASK_STATE_CONFLICT: (
        "The task's current state does not allow this operation.",
        "Call get_task_details to re-read the state, then adapt — never force a "
        "transition the backend refused.",
    ),
    ErrorCode.TASK_ALREADY_CLAIMED: (
        "Another worker already holds this task's lease.",
        "Do not retry this claim — call get_available_tasks again and claim a different task.",
    ),
    ErrorCode.LEASE_EXPIRED: (
        "The lease on this task expired — work must stop immediately.",
        "Stop editing now; preserve progress with log_task_checkpoint if useful, "
        "then call claim_task again to re-acquire the lease if the task is still needed.",
    ),
    ErrorCode.LEASE_NOT_OWNED: (
        "This session does not hold the task's current lease.",
        "Stop mutating the task; re-read it with get_task_details and claim it again "
        "only if it is free.",
    ),
    ErrorCode.DEPENDENCY_UNMET: (
        "A task this one depends on has not completed yet.",
        "Choose other work from get_available_tasks and try again once the dependencies finish.",
    ),
    ErrorCode.CONCURRENCY_LIMIT_REACHED: (
        "The project's concurrency limit is reached — no further tasks may be held.",
        "Release a held task with release_task, or wait and retry the call later.",
    ),
    ErrorCode.SCOPE_VIOLATION: (
        "The change touches paths outside the task's target_scope.",
        "Stay inside target_scope, or release_task and flag the task for human "
        "attention instead of expanding scope.",
    ),
    ErrorCode.ROLE_NOT_PERMITTED: (
        "This session's role may not perform the operation.",
        "Use only the tools your role allows (coder vs auditor) and do not retry "
        "with the same role.",
    ),
    ErrorCode.AUDITOR_SAME_AS_CODER: (
        "The same agent may not audit its own work.",
        "Leave the task for a different auditor; do not submit a verdict on work you authored.",
    ),
    ErrorCode.ATTACHMENT_NOT_READY: (
        "The attachment is still being processed.",
        "Wait briefly, then call read_task_attachment again; details carry the processing status.",
    ),
    ErrorCode.ATTACHMENT_UNSUPPORTED_FORMAT: (
        "The requested attachment format is outside the allowlist.",
        "Ask for a supported format (or text/markdown) instead; do not repeat the same format.",
    ),
    ErrorCode.POLICY_VIOLATION: (
        "The Policy Engine rejected the submission against a project rule.",
        "Read the rule results in details, fix the flagged issue, then submit again.",
    ),
    ErrorCode.RATE_LIMITED: (
        "The backend rate limit was reached; a retry can succeed.",
        "Wait for the advised delay, then retry the call; slow the pace of subsequent calls.",
    ),
    ErrorCode.VERSION_CONFLICT: (
        "The task changed since it was last read (stale version).",
        "Re-read with get_task_details and re-apply the change against the new version.",
    ),
    ErrorCode.SERVER_ERROR: (
        "The backend failed unexpectedly or was unreachable; a retry can succeed.",
        "Wait and retry the call; if it persists, report it with the correlation "
        "id and check backend health.",
    ),
}


def translate_error(error: ApiError) -> TranslatedError:
    """Add hint + next action to a typed error; passthrough everything else.

    Raises :class:`ValueError` for a code outside the Section 9.2 catalog —
    the translator consumes the canonical codes and invents none.
    """
    code = ErrorCode(str(error.code))  # ValueError → out-of-catalog, rejected
    entry = HINTS.get(code)
    if entry is None:
        # Default branch: still names the canonical code, never invents one.
        correlation = error.correlation_id or "unavailable"
        hint = f"The backend reported {code}."
        next_action = (
            f"Read the error details and quote correlation id {correlation} when "
            "reporting it; retry only if the failure looks transient."
        )
    else:
        hint, next_action = entry
    return TranslatedError(
        code=code,
        message=error.message,
        hint=hint,
        next_action=next_action,
        retryable=error.retryable,
        details=error.details,
        correlation_id=error.correlation_id,
    )
