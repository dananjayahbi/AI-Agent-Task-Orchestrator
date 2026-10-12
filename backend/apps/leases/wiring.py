"""WP-1.6 wiring of the Section 8.2 T4/T6 rows — via the registry's public API.

MT-1.5-04 registered T4 (claim) and T6 (voluntary release) as stubs and
fixed the extension point: ``DEFAULT_REGISTRY.register(spec, replace=True)``
— "the dispatcher never names a concrete row". This module is WP-1.6's
side of that contract: it rebuilds the two rows with their **guard and
side-effect columns implemented** (verbatim Section 8.2 text) and
replaces them on the process registry. The dispatcher, registry,
loader, and hooks files are never edited (concurrent-agent territory;
MT-1.5-01's extension point is the sanctioned seam).

Idempotence without a module flag (:func:`ensure_wired` asks the
*registry*, not a global): test fixtures snapshot and restore
``DEFAULT_REGISTRY`` around suites, so a cached "already wired" boolean
would skip re-wiring after a restore and dispatch the stub again. The
row's own ``wired`` bit is the state.

Guard-column transcription (Section 8.2 T4, in order):

* **token scope matches** — the service already answered
  ``AUTH_FORBIDDEN_PROJECT`` after the row lock; the guard repeats it so
  a future direct dispatcher caller cannot skip it (ADR-004 defense in
  depth; the extra carries ``caller_project_id``).
* **Project active** — FR-PRJ-04: a paused/archived project offers no
  work. The catalog has no project-state code; this is a Section 8.2
  guard refusal, answered in the ``TASK_STATE_CONFLICT`` family (409,
  recorded reading — same family the dispatcher uses for its own
  invariant refusals).
* **archived tasks accept no claims** — T19's "hidden from boards by
  default" plus WP-1.4-06's archived-write refusal, applied to claim
  (recorded reading; ``TASK_STATE_CONFLICT``).
* **dependencies completed** — ``guards.require_completed_dependencies``
  (catalog ``DEPENDENCY_UNMET``), exactly the predicate
  ``services.dependencies.all_dependencies_completed`` defines.
* **``max_concurrent_tasks`` not exceeded** (MT-1.6-06; FR-LEA-08) —
  counted *after* locking the project row, so two claims of *different*
  tasks in one project serialize on that row and cannot both pass the
  count (the per-task lock alone would leave the count racy —
  MT-1.6-06's TOCTOU risk note). Refusal: ``CONCURRENCY_LIMIT_REACHED``.
* **row lock won** — owned by ``claim.claim_task``: the skip-locked task
  row is already exclusive when the dispatcher runs (Section 9.3 step 3).

Side-effects (Section 8.2 T4): "Set worker, session, lease,
``attempt_number``+1; emit ``task.claimed``" — the event rides the
dispatcher's single hook; the lease fields follow Section 8.6 Acquire
with the policy's ``lease_duration_minutes`` (default 45, Section 7.2).
T6: "Clear worker; no failure increment" via ``guards.clear_coder_lease``
— ``failure_retry_count`` untouched (FR-LEA-06), ``attempt_number``
preserved (Section 8.2 T16 comparison).

Clock (MT-1.6-03 risk note): ``django.utils.timezone.now()`` — one
documented app-server clock for claim, extension and fencing comparisons
within a request; never a per-call mix of DB and Python time.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.accounts.exceptions import AuthForbiddenProject
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import ClaimedRole, Task, TaskState
from apps.tasks.state_machine.guards import clear_coder_lease, require_completed_dependencies
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

from .exceptions import ConcurrencyLimitReached
from .fencing import require_current_lease


def _extra_str(context: TransitionContext, key: str) -> str:
    """One non-blank string input of the claim/release contract.

    Missing wiring inputs are programming errors (the API serializers
    require both fields before dispatch), so they raise ``ValueError`` —
    never a silent default and never a wire response.
    """
    value = context.extra.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"transition context requires a non-blank {key!r} (WP-1.6 contract)")
    return value


def _guard_claim(task: Task, context: TransitionContext) -> None:
    """T4 guards — Section 8.2 verbatim, evaluated inside the row lock."""
    # "token scope matches" — from the token, never the body (Section 9.3
    # step 1; ADR-004; G-07). The service answers first; this repeat keeps
    # direct dispatch callers honest.
    caller_project = context.extra.get("caller_project_id")
    if not isinstance(caller_project, str) or caller_project != task.project_id:
        raise AuthForbiddenProject(
            f"Token is scoped to {caller_project!r}, not {task.project_id!r}."
        )
    # "Project active" — FR-PRJ-04.
    if task.project.active_status != "active":
        raise TaskStateConflict(
            task.pk,
            reason=(
                f"project {task.project_id} is {task.project.active_status} (T4: Project active)"
            ),
        )
    # Archived tasks accept no claims (T19 default visibility; MT-1.4-06 family).
    if task.archived_at is not None:
        raise TaskStateConflict(task.pk, reason="is archived")
    # "dependencies completed" — the single FR-TSK-07 predicate.
    require_completed_dependencies(task)
    # "max_concurrent_tasks not exceeded" — MT-1.6-06 / FR-LEA-08. Lock the
    # project row first: it is the cross-task mutex that makes the count
    # race-free for claims of different tasks in the same project.
    project = Project.objects.select_for_update().get(pk=task.project_id)
    limit = project.agent_policy.max_concurrent_tasks
    held = Task.objects.filter(
        project_id=task.project_id,
        state=TaskState.IN_PROGRESS,
        claimed_role=ClaimedRole.CODER,
    ).count()
    if held >= limit:
        raise ConcurrencyLimitReached(task.pk, limit=limit)


def _side_effect_claim(task: Task, context: TransitionContext) -> Task | None:
    """T4 side effects — Section 8.2 verbatim; Section 8.6 Acquire.

    Mutates in memory; the dispatcher's single ``version`` bump + save
    persists the row with the state change, history, and event together.
    """
    session_id = _extra_str(context, "session_id")
    worker_agent_id = _extra_str(context, "worker_agent_id")
    policy = task.project.agent_policy
    now = timezone.now()
    task.worker_agent_id = worker_agent_id
    task.worker_session_id = session_id
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = now
    task.lease_expires_at = now + timedelta(minutes=policy.lease_duration_minutes)
    task.lease_generation += 1  # Section 8.6 fencing: every claim increments
    task.attempt_number += 1  # Section 8.2 T4 side effects
    return None


def _guard_release(task: Task, context: TransitionContext) -> None:
    """T6 guard — Section 8.2 verbatim: "Caller owns lease (or Owner override)"."""
    if context.actor_type == "owner" and bool(context.extra.get("owner_override")):
        return  # the documented Owner override (Section 8.2 T6 Actor C, O)
    require_current_lease(
        task,
        session_id=context.extra.get("session_id"),
        lease_generation=context.extra.get("lease_generation"),
    )


def _side_effect_release(task: Task, context: TransitionContext) -> Task | None:
    """T6 side effects — Section 8.2 verbatim: "Clear worker; no failure increment"."""
    clear_coder_lease(task)  # keeps failure_retry_count and attempt_number (FR-LEA-06)
    return None


def _wired_claim_spec() -> TransitionSpec:
    """The T4 row with its WP-1.6 behavior filled in (shape from MT-1.5-04)."""
    return TransitionSpec(
        transition_id="T4",
        trigger="claim",
        from_states=frozenset({TaskState.PENDING}),
        to_state=TaskState.IN_PROGRESS,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor C
        guard=_guard_claim,
        side_effect=_side_effect_claim,
        event_type="task.claimed",
        reason_code="claim",
        wired=True,
    )


def _wired_release_spec() -> TransitionSpec:
    """The T6 row with its WP-1.6 behavior filled in (shape from MT-1.5-04)."""
    return TransitionSpec(
        transition_id="T6",
        trigger="voluntary_release",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.PENDING,
        actor_types=frozenset({"agent", "owner"}),  # Section 8.2 actors C, O
        guard=_guard_release,
        side_effect=_side_effect_release,
        event_type="task.released",
        reason_code="voluntary_release",
        wired=True,
    )


def ensure_wired() -> None:
    """Put the wired T4/T6 rows on the process registry (idempotent).

    Registration intentionally **not** import-time or ``AppConfig.ready``:
    the WP-1.5 suites assert the stub rows and snapshot/restore the
    registry per test, so wiring happens lazily on the first claim or
    release call — production gets it on the first lease operation, tests
    get it inside their own restore guards.
    """
    ensure_registered()
    claim_row = DEFAULT_REGISTRY.get("claim")
    if claim_row is None or not claim_row.wired:
        DEFAULT_REGISTRY.register(_wired_claim_spec(), replace=True)
    release_row = DEFAULT_REGISTRY.get("voluntary_release")
    if release_row is None or not release_row.wired:
        DEFAULT_REGISTRY.register(_wired_release_spec(), replace=True)


def claim_extra(
    *,
    caller_project_id: str | None,
    session_id: str,
    worker_agent_id: str,
) -> Mapping[str, Any]:
    """The T4 dispatch inputs (Section 9.3: project from the token)."""
    return {
        "caller_project_id": caller_project_id,
        "session_id": session_id,
        "worker_agent_id": worker_agent_id,
    }


def release_extra(
    *,
    session_id: str | None,
    lease_generation: int | None,
    owner_override: bool,
) -> Mapping[str, Any]:
    """The T6 dispatch inputs (fencing pair + override flag)."""
    return {
        "session_id": session_id,
        "lease_generation": lease_generation,
        "owner_override": owner_override,
    }
