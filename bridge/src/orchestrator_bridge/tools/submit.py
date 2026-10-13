"""``submit_task_resolution`` (parent plan Sections 8.2, 9.2, 10.5, 10.10,
11.1; FR-MCP-07, ADR-012; MT-2.6-04, MT-2.6-05).

The coder's finish line, in four steps the plan sequences:

1. **verify** (MT-2.6-02, :mod:`submit_verify`): repository identity, the
   assigned branch, a real commit reachable on it — host-side only (ADR-007).
2. **capture** (MT-2.6-03, :mod:`submit_capture`): the merge-base patch at
   that verified sha, plus provisional stats/file list, re-verifying the tip
   so evidence can never straddle two commits.
3. **retain** (MT-2.6-05, :mod:`~orchestrator_bridge.submission_spool`): the
   assembled payload — patch, summary, flags and the minted
   ``Idempotency-Key`` — is persisted **before** any network attempt
   (Section 10.10; the WP-2.6 "outage loses nothing" acceptance is pinned by
   test against this ordering).
4. **upload**: ``POST /tasks/{id}/resolution`` with that key. Acknowledged →
   the spool entry is cleared (only acknowledgments complete a submission).
   Retryable failure → the entry is kept and the error tells the agent the
   payload is retained (restart resumes the retry with the same key).
   Definitive rejection → the entry is dropped and the catalog error with
   hint/next action surfaces; ``LEASE_EXPIRED``/``TASK_STATE_CONFLICT`` are
   the Section 11.1 step 7 stop-and-orient answers — never a blind retry
   (the transport does not retry non-retryable envelopes either).

The outcome the agent is told is the backend's actual task state (Section
10.5): ``to_be_audited`` (T7) or ``in_human_review`` with its
``review_reason`` (T8 — self-flag or scope violation; escalations are never
hidden, MT-2.6-04 risk note). ``trigger`` names which Section 8.2 row fired
and ``scope_violations`` carries the offending paths, so the agent sees *why*
review happened. The wire body sends the bridge's captured file list and
stats as the provisional claims WP-3.2's serializer documents — the server's
patch parse replaces them authoritatively (Section 9.7), and the response
echoes what the server stored.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from typing import Any

from ..api_errors import ApiError, ErrorCode
from ..endpoints import endpoint
from ..error_translation import TranslatedError, translate_error
from ..idempotency import new_key
from ..submission_spool import SubmissionSpool
from .errors import ToolFailure
from .runtime import ToolRuntime
from .submit_capture import capture_patch
from .submit_verify import verify_submission

__all__ = ["submit_task_resolution", "make_handler"]

_OUTCOME_STATES = frozenset({"to_be_audited", "in_human_review"})


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def _malformed(message: str) -> ToolFailure:
    """One SERVER_ERROR-tagged failure for a response that broke the contract."""
    return ToolFailure(
        TranslatedError(
            code=ErrorCode.SERVER_ERROR,
            message=message,
            hint=(
                "the backend answered with a body that is not the documented "
                "submission response (Section 9.2 row)."
            ),
            next_action=(
                "Check the task with get_task_details — an acknowledged submission "
                "still landed and replays safely with its idempotency key; report "
                "the malformed response with the correlation id."
            ),
            retryable=False,
            details={"endpoint": "resolution_submit"},
            correlation_id=None,
        )
    )


def _no_spool_failure() -> ToolFailure:
    """The runtime has no spool bound — a wiring bug, not an agent mistake."""
    return ToolFailure(
        TranslatedError(
            code=ErrorCode.SERVER_ERROR,
            message="the bridge runtime has no submission spool configured",
            hint=(
                "submissions are persisted locally before upload (Section 10.10); "
                "this bridge was built without that seam, which is a bridge bug."
            ),
            next_action=(
                "Report this bridge build/runtime problem to the operator; do not "
                "retry submission until the bridge is restarted through its entrypoint."
            ),
            retryable=False,
            details=None,
            correlation_id=None,
        )
    )


def _retention_note(translated: TranslatedError) -> TranslatedError:
    """Append the retained-payload note to a retryable failure's guidance."""
    return dataclasses.replace(
        translated,
        next_action=(
            f"{translated.next_action} The submission payload is retained locally in "
            "the submission spool and will be retried on the next bridge start with "
            "the same idempotency key — nothing was lost."
        ),
    )


def submit_task_resolution(
    runtime: ToolRuntime,
    *,
    task_id: str,
    git_branch: str,
    commit_sha: str,
    execution_summary: str,
    requires_human_attention: bool = False,
    risk_justification: str = "",
) -> dict[str, Any]:
    """Verify, capture, retain and upload one task resolution (Section 10.5)."""
    verified = verify_submission(
        runtime.binding,
        task_id=task_id,
        git_branch=git_branch,
        commit_sha=commit_sha,
    )
    default_branch = str(runtime.binding.manifest["default_branch"])
    captured = capture_patch(
        verified.root,
        branch=verified.branch,
        default_branch=default_branch,
        expected_head_sha=verified.commit_sha,
    )
    spool: SubmissionSpool | None = runtime.spool
    if spool is None:
        raise _no_spool_failure()
    body: dict[str, Any] = {
        "session_id": runtime.agent_session_id,
        # ADR-012 fencing pair; 0 when this process never claimed the task —
        # the backend answers LEASE_EXPIRED/LEASE_NOT_OWNED authoritatively.
        "lease_generation": runtime.lease_generation(task_id) or 0,
        "git_branch": verified.branch,
        "commit_sha": verified.commit_sha,
        "execution_summary": execution_summary,
        "requires_human_attention": requires_human_attention,
        "risk_justification": risk_justification,
        # The patch rides in full: the backend parses the *received* bytes for
        # authoritative stats and applies the Section 9.7 storage cap itself
        # (WP-3.2 "bridge prepares, backend stores" — never truncate here).
        "patch": captured.patch,
        # Provisional claims (Section 9.7; the server's parse replaces them).
        "changed_files": list(captured.changed_files),
        "diff_summary": dict(captured.stats),
    }
    path = endpoint("resolution_submit").path.format(id=task_id)
    key = new_key("POST", target=path)
    try:
        # Persist-before-send (MT-2.6-05): no network attempt happens before
        # this returns; an unwritable spool surfaces as a failure instead.
        entry = spool.hold(
            project_id=runtime.project_id,
            task_id=task_id,
            path=path,
            body=body,
            idempotency_key=key,
        )
    except OSError as exc:
        raise ToolFailure(
            TranslatedError(
                code=ErrorCode.SERVER_ERROR,
                message=(
                    f"the submission payload could not be persisted locally ({type(exc).__name__})"
                ),
                hint=(
                    "submissions must be durable on this host before upload "
                    "(Section 10.10); the upload was NOT attempted."
                ),
                next_action=(
                    "Check free disk space and permissions on the submission spool, "
                    "then submit again — your committed work is still on the branch."
                ),
                retryable=False,
                details={"endpoint": "resolution_submit"},
                correlation_id=None,
            )
        ) from None
    try:
        payload = runtime.client.request("POST", path, body=body, idempotency_key=key)
    except ApiError as exc:
        translated = translate_error(exc)
        if exc.retryable:
            spool.mark_failed(entry.id, error_code=str(exc.code))
            raise ToolFailure(_retention_note(translated)) from None
        # Definitive rejection: the payload can never succeed as-is (the agent
        # must fix and resubmit) — drop it rather than loop on a dead outcome.
        spool.resolve(entry.id)
        raise ToolFailure(translated) from None
    spool.resolve(entry.id)  # acknowledged — the only state that completes
    if not isinstance(payload, Mapping):
        raise _malformed("resolution response is not the documented object")
    resolution = payload.get("resolution")
    task = payload.get("task")
    if not isinstance(resolution, Mapping) or not isinstance(task, Mapping):
        raise _malformed("resolution response is missing resolution/task (Section 9.2 row)")
    state = task.get("state")
    if not isinstance(state, str) or state not in _OUTCOME_STATES:
        raise _malformed("resolution response carries an unknown task state")
    trigger = payload.get("trigger")
    violations = payload.get("scope_violations")
    review_reason = task.get("review_reason")
    if state == "in_human_review":
        reason_text = (
            review_reason if isinstance(review_reason, str) and review_reason else "requested"
        )
        next_action = (
            f"Human review required ({reason_text}): wait for the owner's decision — "
            "do not resubmit and do not keep editing this task."
        )
    else:
        next_action = (
            "The submission is queued for audit (T7); pick new work from "
            "get_available_tasks while you wait for the verdict."
        )
    return {
        "task_id": task_id,
        "outcome": state,
        "review_reason": review_reason if isinstance(review_reason, str) else None,
        "trigger": trigger if isinstance(trigger, str) else None,
        "resolution_id": resolution.get("id"),
        "branch": verified.branch,
        "commit_sha": verified.commit_sha,
        # What the server stored (authoritative per Section 9.7).
        "changed_files": list(resolution.get("changed_files") or []),
        "diff_summary": dict(resolution.get("diff_summary") or {}),
        "scope_violations": list(violations) if isinstance(violations, list) else [],
        "requires_human_attention": requires_human_attention,
        "patch_size_bytes": captured.patch_size_bytes,
        "diff_too_large": captured.diff_too_large,
        "working_tree": verified.working_tree,
        "next_action": next_action,
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def submit_task_resolution_tool(
        task_id: str,
        git_branch: str,
        commit_sha: str,
        execution_summary: str,
        requires_human_attention: bool = False,
        risk_justification: str = "",
    ) -> dict[str, Any]:
        """Verify, capture and upload the task's resolution; reports the outcome."""
        return submit_task_resolution(
            runtime,
            task_id=task_id,
            git_branch=git_branch,
            commit_sha=commit_sha,
            execution_summary=execution_summary,
            requires_human_attention=requires_human_attention,
            risk_justification=risk_justification,
        )

    return submit_task_resolution_tool
