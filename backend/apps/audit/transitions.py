"""WP-3.3 wiring of the audit rows T11–T14 — the sanctioned seam.

MT-1.5-04 fixed the extension point: ``DEFAULT_REGISTRY.register(spec,
replace=True)`` — "the dispatcher never names a concrete row". This
module is WP-3.3's side of that contract (same discipline as
``apps.leases.wiring`` and ``tasks.state_machine.transitions_submission``;
neither file, nor the dispatcher/registry/loader/hooks, is edited here):
it *adds* **T11** (auditor claim), **T12** (audit lease expiry), and the
two verdict-outcome rows **T13**/**T14** on the process registry, with
their Section 8.2 Guard / Side-effects columns implemented.

Idempotence without a module flag (:func:`ensure_audit_wired` asks the
*registry*, not a global — the WP-1.6/WP-3.2 reason recorded again):
test fixtures snapshot and restore ``DEFAULT_REGISTRY`` around suites,
so the rows' own ``wired`` bits are the state. Registration is lazy
(first auditor claim, verdict, or audit sweep) — the WP-1.5 suites'
import-time enumeration (``tests/test_transition_matrix.py``) keeps
seeing the loader's nine stub rows.

**Row shapes — recorded readings (Section 20.1 item 5):**

* **T11** ``audit_claim`` — From ``to_be_audited``, To *"(audit lease)"*
  is not one of the six G-01 states, so the row is flag-only
  (``to_state=None`` — the registry's "state unchanged" shape): the
  lease columns change, the state does not. Guard = the two Section 8.2
  clauses verbatim (*auditor session differs from coder* — the shared
  :func:`apps.audit.independence.assert_auditor_independent`, running
  inside the claim transaction; *audit lease available* — any lease on
  the row, expired-but-unswept included, answers the catalog
  ``TASK_ALREADY_CLAIMED``, mirroring Section 8.6's "T5 is what
  reclaims, never a second claimant"). Side effects set the Section 8.6
  acquire shape for the auditor (policy duration, ``lease_generation``
  + 1) with ``claimed_role = auditor``; ``attempt_number`` is **not**
  bumped (Section 7.2: it increments on each new claim *by a coder*).
* **T12** ``audit_lease_expired`` — From/To ``to_be_audited`` (Section
  8.2 verbatim: the task never leaves the state). Guard: the row must
  sit on an *expired auditor* lease (the sweeper's selection re-checked
  under the lock — a defensive refusal, never a normal path). Side
  effects: release the audit lease (the shared worker/lease clear of
  ``guards.clear_coder_lease``, whose five columns are role-agnostic in
  effect) and increment ``audit_retry_count`` — **only** that counter:
  the coder retry budget, worker history and the resolution are
  untouched (Section 8.3 invariant 1; MT-3.3-03 acceptance). Event:
  ``task.lease_expired`` — the Section 9.6 catalog's existing member
  (no ``audit.*expiry`` string exists; never an uncataloged event,
  Section 20.4 item 6).
* **T13** ``audit_verdict_pass`` — flag-only (To: *"merge-pending (still
  ``to_be_audited`` until merge)"* — the ``merge_status = pending``
  sub-status of Section 8.1, never a seventh state; the same reading
  WP-3.2 recorded for T10's approve branch). Guard asserts the stored
  report/resolution ride the dispatch; the side effect **re-consults
  the decision seam** and refuses a branch the engine did not choose
  (invariant 8.3.4 structural — without MT-3.4-07's hook the fail-closed
  default escalates and this row is unreachable). On approval it sets
  ``merge_status = pending``, emits ``audit.passed``, and releases the
  audit lease (the verdict concludes the claim — the same "clear
  worker" the submission rows apply, so no dead lease lingers to be
  swept by T12 *after* a pass).
* **T14** ``audit_verdict_escalated`` — To ``in_human_review``; the
  same structural guard, and the side effect re-consults the seam: an
  engine that *approved* refuses this branch, an escalation writes the
  enumerated Section 8.4 reason on ``review_reason``, releases the
  audit lease, and lets the dispatcher's ``in_human_review``-entry rule
  fire the Section 9.8 push. Event: ``audit.escalated`` (§9.6).

Transitions/Events are written only by the dispatcher (Section 8.2
rule 2); this module never touches ``state``.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.leases.exceptions import TaskAlreadyClaimed
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import (
    ClaimedRole,
    MergeStatus,
    Task,
    TaskResolution,
    TaskState,
)
from apps.tasks.state_machine.guards import clear_coder_lease
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

from .decision import resolve_audit_decision
from .independence import assert_auditor_independent
from .models import AuditReport

# The worker/lease columns of Section 7.2 — cleared by the shared helper
# (named for T5's coder path; the five columns hold the auditor's identity
# on an audit lease, and Section 8.3 invariant 1 reads them the same way).
clear_worker_lease = clear_coder_lease


def _extra_str(context: TransitionContext, key: str) -> str:
    """One non-blank string input of the claim/verdict contract.

    Missing wiring inputs are programming errors (the API serializers
    require the field before dispatch), so they raise ``ValueError`` —
    never a silent default and never a wire response (the WP-1.6
    ``wiring._extra_str`` contract, restated for this app).
    """
    value = context.extra.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"transition context requires a non-blank {key!r} (WP-3.3 contract)")
    return value


def _extra_resolution(context: TransitionContext, task: Task) -> TaskResolution:
    """The stored resolution riding the dispatch (the service's contract)."""
    resolution = context.extra.get("resolution")
    if not isinstance(resolution, TaskResolution):
        raise ValueError("transition context requires the stored TaskResolution")
    if resolution.task_id != task.pk:  # pragma: no cover - service contract
        raise ValueError("resolution belongs to a different task")
    return resolution


def _extra_report(context: TransitionContext, task: Task) -> AuditReport:
    """The stored Audit Report riding the verdict dispatch (contract)."""
    report = context.extra.get("report")
    if not isinstance(report, AuditReport):
        raise ValueError("transition context requires the stored AuditReport")
    if report.task_id != task.pk:  # pragma: no cover - service contract
        raise ValueError("audit report belongs to a different task")
    return report


def _require_valid_attempt(resolution: TaskResolution, task: Task) -> None:
    """Section 7.2 cardinality: the resolution answers this attempt."""
    if resolution.attempt_number != task.attempt_number:
        raise TaskStateConflict(
            task.pk,
            reason=(
                f"resolution is for attempt {resolution.attempt_number}, "
                f"task is at attempt {task.attempt_number}"
            ),
        )


# --- T11: auditor claim (Section 8.2 row T11) --------------------------------


def _guard_audit_claim(task: Task, context: TransitionContext) -> None:
    """T11 guards — Section 8.2 verbatim: the two clauses, in order.

    "*Auditor session differs from coder*" is the shared independence
    function (G-20; attempt-scoped — see ``apps.audit.independence``);
    "*audit lease available*" refuses any lease already on the row,
    including one expired but not yet swept (Section 8.6: the sweeper
    reclaims, never a second claimant — the auditor-side twin of T4's
    ``in_progress`` check in ``claim.claim_task``).
    """
    session_id = _extra_str(context, "session_id")
    worker_agent_id = _extra_str(context, "worker_agent_id")
    if task.lease_expires_at is not None or task.claimed_role is not None:
        raise TaskAlreadyClaimed(task.pk, holder=task.worker_agent_id)
    assert_auditor_independent(
        task,
        auditor_session_id=session_id,
        auditor_label=worker_agent_id,
    )


def _side_effect_audit_claim(task: Task, context: TransitionContext) -> Task | None:
    """T11 side effects — Section 8.2: "Set auditor lease (same lease rules)".

    Section 8.6 Acquire with the policy's ``lease_duration_minutes``
    (defaults 45/240, Section 7.2) and the fencing increment — exactly
    the T4 shape with ``claimed_role = auditor``. ``attempt_number``
    stays put (Section 7.2: coder claims only), and the dispatcher's
    version bump + Transition row + ``audit.claimed`` event land with
    the lock held.
    """
    session_id = _extra_str(context, "session_id")
    worker_agent_id = _extra_str(context, "worker_agent_id")
    policy = task.project.agent_policy
    now = timezone.now()
    task.worker_agent_id = worker_agent_id
    task.worker_session_id = session_id
    task.claimed_role = ClaimedRole.AUDITOR
    task.lease_acquired_at = now
    task.lease_expires_at = now + timedelta(minutes=policy.lease_duration_minutes)
    task.lease_generation += 1  # Section 8.6: every claim increments
    return None


# --- T12: audit lease expiry (Section 8.2 row T12) ---------------------------


def _guard_audit_lease_expired(task: Task, context: TransitionContext) -> None:
    """T12 guard — Section 8.2: "Auditor lease expired".

    The sweeper's selection already filtered on this predicate under the
    row lock; the re-check keeps a direct dispatcher caller honest and
    answers the Section 8.2 illegal-pair family (``TASK_STATE_CONFLICT``).
    """
    now = timezone.now()
    if (
        task.claimed_role != ClaimedRole.AUDITOR
        or task.lease_expires_at is None
        or task.lease_expires_at > now
    ):
        raise TaskStateConflict(
            task.pk,
            reason="has no expired auditor lease to release (T12's guard)",
        )


def _side_effect_audit_lease_expired(task: Task, context: TransitionContext) -> Task | None:
    """T12 side effects — Section 8.2: release lease; increment audit retry.

    Only the audit side moves: the five worker/lease columns clear, the
    new ``audit_retry_count`` + 1, and ``failure_retry_count``,
    ``attempt_number``, ``review_reason`` and the Task Resolution (and
    its patch artifact) stay untouched — *"expiry releases the audit
    claim without losing the resolution"* (Section 19 WP-3.3
    acceptance; Section 8.3 invariant 1).
    """
    clear_worker_lease(task)
    task.audit_retry_count += 1
    return None


# --- T13 / T14: the verdict outcome (Section 8.2 rows T13, T14) --------------


def _guard_verdict_outcome(task: Task, context: TransitionContext) -> None:
    """The shared structural gate both outcome rows assert.

    The service stored the report and resolved the attempt *before*
    dispatch (same transaction — Section 8.2 rule 2); the rows repeat
    the structural half so a direct dispatcher caller cannot dispatch an
    outcome without them. The engine's own clause ("all rules pass" /
    "any rule fails") lives in the side effects' seam re-consult, the
    way T10's branches made it structural (WP-3.2's recorded pattern).
    """
    resolution = _extra_resolution(context, task)
    _require_valid_attempt(resolution, task)
    report = _extra_report(context, task)
    if report.resolution_id != resolution.pk:  # pragma: no cover - service contract
        raise TaskStateConflict(task.pk, reason="audit report answers a different resolution")


def _side_effect_verdict_pass(task: Task, context: TransitionContext) -> Task | None:
    """T13 side effects — Section 8.2: merge-pending + ``audit.passed``.

    Re-consults the decision seam (pure evaluator — same answer the
    service's trigger choice saw): an engine that did *not* approve
    refuses this branch (``TASK_STATE_CONFLICT``), so approval is
    reachable only through WP-3.4's hook (invariant 8.3.4). Then the
    merge-pending sub-status lands and the audit lease releases — the
    verdict concludes the claim (recorded reading: without the clear a
    dead lease would later fire T12 *after* a pass, bumping the audit
    retry counter for no work).
    """
    resolution = _extra_resolution(context, task)
    report = _extra_report(context, task)
    decision = resolve_audit_decision(task, resolution, report)
    if not decision.approve:
        raise TaskStateConflict(
            task.pk,
            reason="policy engine has not approved (auto-approve is forbidden)",
        )
    task.merge_status = MergeStatus.PENDING
    clear_worker_lease(task)
    return None


def _side_effect_verdict_escalated(task: Task, context: TransitionContext) -> Task | None:
    """T14 side effects — Section 8.2: enumerated ``review_reason`` + push.

    The seam re-consult mirrors T10's escalation branch: an approving
    engine refuses this row, and an escalation writes the validated
    Section 8.4 reason on the task before it lands in
    ``in_human_review`` (the dispatcher's §9.8 push fires on entry). The
    audit lease releases with the row — the task no longer answers to
    any agent lease.
    """
    resolution = _extra_resolution(context, task)
    report = _extra_report(context, task)
    decision = resolve_audit_decision(task, resolution, report)
    if decision.approve:
        raise TaskStateConflict(
            task.pk,
            reason="policy engine approved — the T13 merge-pending row applies",
        )
    task.review_reason = decision.reason  # validated as a Section 8.4 member
    clear_worker_lease(task)
    return None


# --- registration ------------------------------------------------------------


def _wired_audit_claim_spec() -> TransitionSpec:
    """The T11 row with its WP-3.3 behavior filled in (shape MT-1.5-04)."""
    return TransitionSpec(
        transition_id="T11",
        trigger="audit_claim",
        from_states=frozenset({TaskState.TO_BE_AUDITED}),
        to_state=None,  # Section 8.2 To "(audit lease)" — state unchanged
        actor_types=frozenset({"agent"}),  # Section 8.2 actor A
        guard=_guard_audit_claim,
        side_effect=_side_effect_audit_claim,
        event_type="audit.claimed",
        reason_code="audit_claimed",
        wired=True,
    )


def _wired_audit_lease_expired_spec() -> TransitionSpec:
    """The T12 row — From/To ``to_be_audited`` verbatim (Section 8.2)."""
    return TransitionSpec(
        transition_id="T12",
        trigger="audit_lease_expired",
        from_states=frozenset({TaskState.TO_BE_AUDITED}),
        to_state=TaskState.TO_BE_AUDITED,
        actor_types=frozenset({"system"}),  # Section 8.2 actor S
        guard=_guard_audit_lease_expired,
        side_effect=_side_effect_audit_lease_expired,
        event_type="task.lease_expired",  # Section 9.6 catalog (no audit.* expiry)
        reason_code="lease_expired",
        wired=True,
    )


def _wired_verdict_pass_spec() -> TransitionSpec:
    """The T13 row — merge-pending is a sub-status, never a seventh state."""
    return TransitionSpec(
        transition_id="T13",
        trigger="audit_verdict_pass",
        from_states=frozenset({TaskState.TO_BE_AUDITED}),
        to_state=None,  # §8.2 To "merge-pending (still to_be_audited until merge)"
        actor_types=frozenset({"agent", "system"}),  # Section 8.2 actors A, S
        guard=_guard_verdict_outcome,
        side_effect=_side_effect_verdict_pass,
        event_type="audit.passed",
        reason_code="audit_passed",
        wired=True,
    )


def _wired_verdict_escalated_spec() -> TransitionSpec:
    """The T14 row — verdict + any rule fails → ``in_human_review``."""
    return TransitionSpec(
        transition_id="T14",
        trigger="audit_verdict_escalated",
        from_states=frozenset({TaskState.TO_BE_AUDITED}),
        to_state=TaskState.IN_HUMAN_REVIEW,
        actor_types=frozenset({"agent", "system"}),  # Section 8.2 actors A, S
        guard=_guard_verdict_outcome,
        side_effect=_side_effect_verdict_escalated,
        event_type="audit.escalated",
        reason_code="audit_escalated",
        wired=True,
    )


def ensure_audit_wired() -> None:
    """Put the wired T11-T14 rows on the process registry (idempotent).

    Registration intentionally **not** import-time or ``AppConfig.ready``
    (the WP-1.5 suites assert the loader's stub rows and snapshot/restore
    the registry per test), so wiring happens lazily on the first auditor
    claim, verdict or audit sweep — production gets it on the first audit
    operation, tests get it inside their own restore guards.
    """
    ensure_registered()
    for trigger, spec in (
        ("audit_claim", _wired_audit_claim_spec),
        ("audit_lease_expired", _wired_audit_lease_expired_spec),
        ("audit_verdict_pass", _wired_verdict_pass_spec),
        ("audit_verdict_escalated", _wired_verdict_escalated_spec),
    ):
        row = DEFAULT_REGISTRY.get(trigger)
        if row is None or not row.wired:
            DEFAULT_REGISTRY.register(spec(), replace=True)


__all__ = ["ensure_audit_wired"]
