"""``claim_task`` (parent plan Sections 9.2, 9.3, 10.5, 10.6; MT-2.4-04, MT-2.7-03).

The atomicity-critical tool. The backend owns the claim algorithm
(select-for-update skip-locked, re-validation inside the lock — Section 9.3);
the bridge's job is the honest wire call and the response assembly:

* body = the ``ClaimRequest`` contract — ``session_id`` (the bridge-issued
  ``agent_session_id``, the lease's identity half), ``worker_agent_id``
  (the tool's ``agent_identifier`` label) and ``role`` (WP-3.3 added the
  optional ``role`` field so the backend can gate the claim: coder claims
  only ``pending`` (T4), auditor only ``to_be_audited`` (T11), and the
  token's scopes still gate first — Section 12.2). The tool-level ``role``
  input is validated for the model and selects the rules template
  (MT-2.7-03); it now travels on the wire so an auditor claim reaches the
  backend's auditor half (MT-3.5-03, consuming WP-3.3).
* idempotency: the POST carries an ``Idempotency-Key`` minted by the WP-2.3
  transport (NFR-12, ADR-012) — one logical claim, replayed safely.
* response = the three Section 10.5 artifacts — **lease, rules block,
  branch name** — plus the task row. The ``rules`` block is the bridge's own
  Section 10.6 render (MT-2.7-03 resolves this module's forward note): the
  coder/auditor template from :mod:`orchestrator_bridge.rules` with the
  claim's real parameters — the G-09 branch name, the task's test command,
  the checkpoint interval derived from *this* lease — and the session's
  cached ``system_prompt_rules`` appended (MT-2.7-02). One render path serves
  every channel, so the text cannot diverge (G-08). The backend still returns
  its own ``rules_block`` on the wire (Section 9.3 step 6, the OpenAPI
  contract) and its presence is shape-checked, but the bridge's templates are
  the delivery source of truth per Section 10.6's bridge-owned block.
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
from ..rules import (
    DEFAULT_LEASE_MINUTES,
    checkpoint_interval_minutes,
    lease_minutes,
    render_rules,
)
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


def _policy_lease_fallback(policy_summary: Mapping[str, Any]) -> int:
    """The policy summary's ``lease_duration_minutes`` when it is sane."""
    raw = policy_summary.get("lease_duration_minutes")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return DEFAULT_LEASE_MINUTES  # Section 7.2 default


def claim_task(
    runtime: ToolRuntime,
    *,
    task_id: str,
    agent_identifier: str,
    role: str = "coder",
) -> dict[str, Any]:
    """One atomic claim; returns lease + rules block + branch (Section 10.5)."""
    role_key = role if role in ("coder", "auditor") else "coder"
    body = {
        "session_id": runtime.agent_session_id,
        "worker_agent_id": agent_identifier,
        # WP-3.3's ClaimRequest role field (Section 10.5): the backend gates
        # coder → pending (T4) / auditor → to_be_audited (T11) on it.
        "role": role_key,
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
    branch = branch_name_for(runtime.binding, task_id)
    # MT-2.7-03: the delivered block is the bridge's Section 10.6 render for
    # the claiming role, parameterized by this claim — the G-09 branch, the
    # task's own test command, and the checkpoint interval derived from this
    # lease (RISK-02). Project rules come from the session cache (single
    # render path, G-08); a cache miss fetches through the client and a
    # failure surfaces translated, never as a crash.
    try:
        context = runtime.project_context()
    except ApiError as exc:
        raise _failure(exc) from None
    test_command = task.get("test_command")
    rendered_rules = render_rules(
        role_key,
        branch=branch,
        test_command=test_command if isinstance(test_command, str) and test_command else None,
        checkpoint_minutes=checkpoint_interval_minutes(
            lease_minutes(lease, fallback=_policy_lease_fallback(context.policy_summary))
        ),
        project_rules=context.rules,
    )
    return {
        "task_id": claimed_task_id if isinstance(claimed_task_id, str) else task_id,
        "branch": branch,
        "lease": _lease_block(lease),
        "rules": {"role": role_key, "text": rendered_rules},
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
