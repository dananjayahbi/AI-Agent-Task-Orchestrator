"""``claim_task`` (parent plan Sections 9.2, 9.3, 10.5, 10.6; MT-2.4-04).

The atomicity-critical tool. The backend owns the claim algorithm
(select-for-update skip-locked, re-validation inside the lock — Section 9.3);
the bridge's job is the honest wire call and the response assembly:

* body = the ``ClaimRequest`` contract — ``session_id`` (the bridge-issued
  ``agent_session_id``, the lease's identity half) and ``worker_agent_id``
  (the tool's ``agent_identifier`` label). **The wire body carries no
  ``role``**: the backend derives claimable work from the token's scopes
  (Section 12.2); the tool-level ``role`` input is validated for the model
  and travels again when the claim contract grows a role field (auditor
  claims land with backend WP-3.3 — recorded in the WP changelog).
* idempotency: the POST carries an ``Idempotency-Key`` minted by the WP-2.3
  transport (NFR-12, ADR-012) — one logical claim, replayed safely.
* response = the three Section 10.5 artifacts — **lease, rules block,
  branch name** — plus the task row. The rules block comes verbatim from the
  backend (Section 10.6; WP-2.7 merges project rules into it later — the
  bridge renders what the backend returns, MT-2.7-03 is a forward consumer
  note, not a blocker). The branch name is derived per G-09 from the
  manifest's ``auto_branch_prefix`` + the task index
  (``feat/PID00007-`` + ``T004`` → ``feat/PID00007-T004``); WP-2.10's helper
  will own and extend the derivation — this is the same rule, kept minimal.
* the returned ``lease_generation`` is recorded for the release fencing pair
  (ADR-012; MT-2.4-05 consumes it).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from ..manifest import StartupBinding
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["branch_name_for", "claim_task", "make_handler"]


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def branch_name_for(binding: StartupBinding, task_id: str) -> str:
    """G-09 canonical branch: manifest prefix + the task's index part.

    ``feat/PID00007-`` + ``PID00007-T004`` → ``feat/PID00007-T004``. A
    malformed id (no ``-``) yields the prefix plus the raw id rather than
    fabricating structure — the backend's Section 7.3 validation is the
    authority on task ids; this derivation only names a local branch.
    """
    prefix = str(binding.manifest["auto_branch_prefix"])
    index = task_id.split("-", 1)[1] if "-" in task_id else task_id
    return f"{prefix}{index}"


def _lease_block(lease: Mapping[str, Any]) -> dict[str, Any]:
    """The Section 8.6 lease record, compact and verbatim (no derivation)."""
    return {
        "assigned_agent": lease.get("assigned_agent"),
        "session_id": lease.get("session_id"),
        "role": lease.get("role"),
        "generation": lease.get("lease_generation"),
        "acquired_at": lease.get("lease_acquired_at"),
        "expires_at": lease.get("lease_expires_at"),
        "hard_cap_at": lease.get("lease_hard_cap_at"),
        "last_checkpoint": lease.get("last_checkpoint"),
        "failure_retry_count": lease.get("failure_retry_count"),
    }


def claim_task(
    runtime: ToolRuntime,
    *,
    task_id: str,
    agent_identifier: str,
    role: str = "coder",
) -> dict[str, Any]:
    """One atomic claim; returns lease + rules block + branch (Section 10.5)."""
    del role  # validated input; the token scopes decide server-side (12.2).
    body = {
        "session_id": runtime.agent_session_id,
        "worker_agent_id": agent_identifier,
    }
    try:
        payload = runtime.client.request(
            "POST", endpoint("claim").path.format(id=task_id), body=body
        )
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(payload, Mapping):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="claim response is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "claim"},
            )
        )
    task = payload.get("task")
    lease = payload.get("lease")
    rules = payload.get("rules_block")
    if (
        not isinstance(task, Mapping)
        or not isinstance(lease, Mapping)
        or not isinstance(rules, Mapping)
    ):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="claim response is missing task/lease/rules_block (Section 9.3 step 6)",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "claim"},
            )
        )
    generation = lease.get("lease_generation")
    if isinstance(generation, int):
        runtime.record_lease(task_id, generation)
    claimed_task_id = task.get("id")
    return {
        "task_id": claimed_task_id if isinstance(claimed_task_id, str) else task_id,
        "branch": branch_name_for(runtime.binding, task_id),
        "lease": _lease_block(lease),
        "rules": {
            "standard_rules": list(rules.get("standard_rules") or []),
            "project_rules": rules.get("project_rules") or "",
        },
        "task": dict(task),
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def claim_task_tool(
        task_id: str,
        agent_identifier: str,
        role: str = "coder",
    ) -> dict[str, Any]:
        """Atomically claim one task; returns lease, rules block, branch."""
        return claim_task(runtime, task_id=task_id, agent_identifier=agent_identifier, role=role)

    return claim_task_tool
