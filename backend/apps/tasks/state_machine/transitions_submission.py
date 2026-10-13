"""WP-3.2 wiring of the submission rows T7, T8, T10 — the sanctioned seam.

MT-1.5-04 fixed the extension point: ``DEFAULT_REGISTRY.register(spec,
replace=True)`` — "the dispatcher never names a concrete row". This
module is WP-3.2's side of that contract: it rebuilds **T7** (submit)
and **T8** (submit flagged) with their Section 8.2 guard/side-effect
columns implemented, and *adds* **T10's** row(s), replacing/adding on
the process registry. The dispatcher, registry, loader and hooks files
are never edited (concurrent-agent territory; the extension point is
the sanctioned seam — same discipline as ``apps.leases.wiring``).

Idempotence without a module flag (:func:`ensure_submission_wired`
asks the *registry*, not a global): test fixtures snapshot and restore
``DEFAULT_REGISTRY`` around suites, so a cached "already wired" boolean
would skip re-wiring after a restore. The rows' own ``wired`` bits (and
T10's presence) are the state.

**T10's shape — a recorded reading (Section 20.1 item 5).** Section 8.2
gives T10 ``To = "policy decision"``: a *decision*, not one of the six
G-01 states, so no single registry row can carry it (``to_state`` must
be canonical; the registry refuses anything else). Section 8.5 names
exactly two outcomes, so T10 registers as the pair of rows its plan row
describes:

* ``submit_unreviewed`` — the escalation branch: ``in_progress`` →
  ``in_human_review`` with an enumerated Section 8.4 reason (§8.5's
  "otherwise it goes to in_human_review"); the dispatcher's
  Section 9.8 push fires on entry like every ``in_human_review`` row.
* ``submit_policy_approved`` — the approve branch: ``in_progress`` →
  ``to_be_audited`` with ``merge_status = pending`` — "merge-pending",
  which Section 8.2's T13 parenthetical records as a *sub-status*
  carried on ``to_be_audited`` "until merge", never a seventh state.

Both branches consult the single **policy-decision seam**:
:func:`resolve_policy_decision` runs the WP-3.4 Policy Engine when its
hook is installed and otherwise fails closed to *escalate* — invariant
8.3.4 ("the Policy Engine is the only component that can set a
policy-approved outcome") is structural here: each branch's side effect
re-consults the seam (it is a pure, deterministic evaluator per
Section 9.4, so the service's trigger choice and the row's re-check
agree by construction) and refuses a branch the engine did not choose.
Approve is unreachable without the engine; the stub can only escalate.

**T7/T8 guard transcription (Section 8.2 verbatim, in order):**

* *Lease owner and not expired* — ``leases.fencing.require_current_lease``
  on the ``session_id``/``lease_generation`` pair (the shared gate; no
  second implementation).
* *resolution valid* — the ``TaskResolution`` riding ``context.extra``
  belongs to this task at this ``attempt_number``.
* *``audit_required`` true* (T7) / **ordering** — the service evaluates
  ``requires_human_attention`` and scope *first* (MT-3.2-05): a
  self-flagged or out-of-scope submission takes T8 regardless of
  ``audit_required``; T7's guard repeats the three structural clauses so
  a direct dispatcher caller cannot skip them.
* *not self-flagged* (T7) — ``requires_human_attention`` false.
* *scope check ok* (T7) — the shared :class:`ScopeVerdict` from
  ``services.scope`` (one matcher: ``globs.glob_matches``); a violation
  arriving here answers the catalog ``SCOPE_VIOLATION`` (409).
* T8's guard is its own cell: ``requires_human_attention`` true **or**
  changed files outside scope — neither answers
  ``TASK_STATE_CONFLICT``.

Side effects: T7 stores nothing new (the service stored resolution +
patch in the same transaction *before* dispatch — sequencing required
so T8's guard can read the scope verdict; the row asserts the stored
resolution rides ``extra``) and clears the worker; T8 sets
``review_reason`` to the strict pair (``self_flagged`` /
``scope_violation`` — Section 8.4 verbatim, scope wins when both
apply) and clears the worker; T10's branches apply the engine verdict.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from apps.leases.fencing import require_current_lease

from ..exceptions import ScopeViolation, TaskStateConflict
from ..models import MergeStatus, ReviewReason, Task, TaskResolution, TaskState
from ..services.scope import ScopeVerdict
from .guards import clear_coder_lease
from .loader import ensure_registered
from .registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec
from .transitions_agent import T8_REVIEW_REASONS

# --- the policy-decision seam (Section 8.5; invariant 8.3.4; MT-3.4-07 fills) -


@dataclass(frozen=True)
class PolicyDecision:
    """The Policy Engine's verdict (Section 9.4: approve | escalate)."""

    approve: bool
    #: Enumerated Section 8.4 reason the escalation carries (``None`` only
    #: when ``approve`` is true — the plan fixes no reason for approval).
    reason: str | None = None


#: The hook signature WP-3.4 installs with :func:`set_policy_decision_hook`.
type PolicyDecisionHook = Callable[[Task, TaskResolution, ScopeVerdict], PolicyDecision]

_policy_hook: PolicyDecisionHook | None = None

#: Fail-closed default (MT-3.2-05 out of scope): with no engine the only
#: honest outcome is escalate — never auto-approve (invariant 8.3.4).
#: ``policy_forced_review`` is the Section 8.4 member the reading picks
#: for "policy forced this review before any rule could pass" (the exact
#: engine-supplied reason arrives with MT-3.4-07; recorded as an OQ in
#: the WP changelog — no new code, Section 20.4 item 5).
_DEFAULT_DECISION: Final = PolicyDecision(
    approve=False,
    reason=ReviewReason.POLICY_FORCED_REVIEW,
)


def set_policy_decision_hook(hook: PolicyDecisionHook | None) -> None:
    """Install (or remove) the WP-3.4 Policy Engine evaluator."""
    global _policy_hook
    _policy_hook = hook


def resolve_policy_decision(
    task: Task, resolution: TaskResolution, verdict: ScopeVerdict
) -> PolicyDecision:
    """The engine's verdict — the single seam both service and rows read.

    Pure by contract (Section 9.4's "pure, deterministic rules
    evaluator"), so the service's trigger choice and the row's side
    effect re-consult agree; without an installed hook the fail-closed
    default escalates.
    """
    if _policy_hook is None:
        return _DEFAULT_DECISION
    decision = _policy_hook(task, resolution, verdict)
    if not isinstance(decision, PolicyDecision):  # pragma: no cover - contract
        raise ValueError("policy decision hook must return a PolicyDecision")
    if decision.approve:
        return decision
    if decision.reason not in set(ReviewReason.values):
        raise ValueError(
            f"policy escalation reason {decision.reason!r} is not a Section 8.4 member"
        )
    return decision


# --- shared guards -----------------------------------------------------------


def _extra_resolution(context: TransitionContext, task: Task) -> TaskResolution:
    """The stored resolution riding the dispatch (the service's contract)."""
    resolution = context.extra.get("resolution")
    if not isinstance(resolution, TaskResolution):
        raise ValueError("transition context requires the stored TaskResolution")
    if resolution.task_id != task.pk:  # pragma: no cover - service contract
        raise ValueError("resolution belongs to a different task")
    return resolution


def _require_lease(context: TransitionContext, task: Task) -> None:
    """Section 8.2's "lease owner and not expired" — the shared gate."""
    require_current_lease(
        task,
        session_id=context.extra.get("session_id"),
        lease_generation=context.extra.get("lease_generation"),
    )


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


def _scope_verdict(context: TransitionContext) -> ScopeVerdict:
    """The shared verdict the service computed before dispatch."""
    verdict = context.extra.get("scope_verdict")
    if not isinstance(verdict, ScopeVerdict):
        raise ValueError("transition context requires the computed ScopeVerdict")
    return verdict


def _review_reason(context: TransitionContext, allowed: tuple[str, ...]) -> str:
    """The escalation reason the service chose (catalog-validated here)."""
    reason = context.extra.get("review_reason")
    if reason not in allowed:
        raise ValueError(f"transition context requires review_reason in {allowed}")
    return str(reason)


# --- T7: submit (Section 8.2 row T7) -----------------------------------------


def _guard_submit(task: Task, context: TransitionContext) -> None:
    """T7 guards — Section 8.2 verbatim: all five clauses, in order."""
    _require_lease(context, task)  # "Lease owner and not expired"
    resolution = _extra_resolution(context, task)
    _require_valid_attempt(resolution, task)  # "resolution valid"
    if not task.audit_required:  # "audit_required true"
        raise TaskStateConflict(
            task.pk,
            reason="is marked audit_required=false (T10's row, not T7)",
        )
    if resolution.requires_human_attention:  # "not self-flagged"
        raise TaskStateConflict(
            task.pk,
            reason="submission is self-flagged (T8's row, not T7)",
        )
    verdict = _scope_verdict(context)
    if not verdict.ok:  # "scope check ok" — catalog code, no new one
        raise ScopeViolation(task.pk, violations=", ".join(verdict.violations))


def _side_effect_submit(task: Task, context: TransitionContext) -> Task | None:
    """T7 side effects — Section 8.2: "Store resolution + patch; clear worker".

    Storage happened in the submission service's transaction *before*
    dispatch (sequencing required so T8's guard could read the scope
    verdict — same transaction either way, Section 8.2 rule 2); this
    row asserts the stored resolution rides the context and clears the
    worker (``guards.clear_coder_lease`` keeps Section 8.3 invariant 1
    honest on the ``to_be_audited`` row).
    """
    _extra_resolution(context, task)  # the stored half of the cell
    clear_coder_lease(task)
    return None


# --- T8: self-flagged / scope-violation submit (Section 8.2 row T8) ----------


def _guard_submit_flagged(task: Task, context: TransitionContext) -> None:
    """T8 guard — Section 8.2 verbatim: "``requires_human_attention``
    true or changed files outside scope"."""
    _require_lease(context, task)
    resolution = _extra_resolution(context, task)
    _require_valid_attempt(resolution, task)
    verdict = _scope_verdict(context)
    if not (resolution.requires_human_attention or not verdict.ok):
        raise TaskStateConflict(
            task.pk,
            reason="submission is neither self-flagged nor out of scope (T8 needs one)",
        )


def _side_effect_submit_flagged(task: Task, context: TransitionContext) -> Task | None:
    """T8 side effects — Section 8.2: ``review_reason`` = the strict pair.

    Section 8.4 verbatim: ``self_flagged`` or ``scope_violation``,
    nothing wider (the pair is :data:`T8_REVIEW_REASONS`). The service
    applies the recorded precedence — scope wins when both hold — and
    the row validates it. The Section 9.8 push rides the dispatcher's
    ``in_human_review``-entry rule; the worker clears with the row.
    """
    task.review_reason = _review_reason(context, T8_REVIEW_REASONS)
    clear_coder_lease(task)
    return None


# --- T10: the policy decision (Section 8.2 row T10; Section 8.5) -------------


def _guard_unreviewed(task: Task, context: TransitionContext) -> None:
    """T10's structural guard — ``audit_required`` false, clean submission."""
    _require_lease(context, task)
    resolution = _extra_resolution(context, task)
    _require_valid_attempt(resolution, task)
    if task.audit_required:
        raise TaskStateConflict(
            task.pk,
            reason="is marked audit_required=true (T7's row, not T10)",
        )
    if resolution.requires_human_attention:
        raise TaskStateConflict(task.pk, reason="self-flagged submissions take T8, not T10")
    verdict = _scope_verdict(context)
    if not verdict.ok:
        raise ScopeViolation(task.pk, violations=", ".join(verdict.violations))


def _side_effect_unreviewed(task: Task, context: TransitionContext) -> Task | None:
    """T10's escalation branch — the engine's verdict, fail-closed.

    Re-consults the seam (pure evaluator — same answer the service's
    trigger choice saw): an engine that *approved* refuses this branch
    (``TASK_STATE_CONFLICT``), and an escalation writes the enumerated
    Section 8.4 reason on the task before the row lands in
    ``in_human_review`` (Section 8.5).
    """
    resolution = _extra_resolution(context, task)
    decision = resolve_policy_decision(task, resolution, _scope_verdict(context))
    if decision.approve:
        raise TaskStateConflict(
            task.pk,
            reason="policy engine approved — the merge-pending branch applies",
        )
    task.review_reason = decision.reason  # validated as a Section 8.4 member
    clear_coder_lease(task)
    return None


def _guard_policy_approved(task: Task, context: TransitionContext) -> None:
    """T10's approve branch — same structural gate, engine must agree."""
    _guard_unreviewed(task, context)


def _side_effect_policy_approved(task: Task, context: TransitionContext) -> Task | None:
    """T10's approve branch — merge-pending (Section 8.5; T13's reading).

    ``merge_status = pending`` *is* the merge-pending sub-status
    (Section 8.2 T13: "still ``to_be_audited`` until merge" — never a
    seventh state), and the branch is reachable **only** when the
    engine seam approves: without the hook the fail-closed default
    escalates and this row refuses (invariant 8.3.4 made structural).
    """
    resolution = _extra_resolution(context, task)
    decision = resolve_policy_decision(task, resolution, _scope_verdict(context))
    if not decision.approve:
        raise TaskStateConflict(
            task.pk,
            reason="policy engine has not approved (auto-approve is forbidden)",
        )
    task.merge_status = MergeStatus.PENDING
    clear_coder_lease(task)
    return None


# --- registration ------------------------------------------------------------


def _wired_submit_spec() -> TransitionSpec:
    """The T7 row with its WP-3.2 behavior filled in (shape from MT-1.5-04)."""
    return TransitionSpec(
        transition_id="T7",
        trigger="submit",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.TO_BE_AUDITED,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor C
        guard=_guard_submit,
        side_effect=_side_effect_submit,
        event_type="task.transitioned",
        reason_code="submit",
        wired=True,
    )


def _wired_submit_flagged_spec() -> TransitionSpec:
    """The T8 row with its WP-3.2 behavior filled in (shape from MT-1.5-04)."""
    return TransitionSpec(
        transition_id="T8",
        trigger="submit_flagged",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.IN_HUMAN_REVIEW,
        actor_types=frozenset({"agent", "system"}),  # Section 8.2 actors C, S
        guard=_guard_submit_flagged,
        side_effect=_side_effect_submit_flagged,
        event_type="task.transitioned",
        reason_code="submit_flagged",
        wired=True,
    )


def _wired_submit_unreviewed_spec() -> TransitionSpec:
    """T10's escalation branch — §8.2 To "policy decision" (§8.5 outcome 2)."""
    return TransitionSpec(
        transition_id="T10",
        trigger="submit_unreviewed",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.IN_HUMAN_REVIEW,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor C
        guard=_guard_unreviewed,
        side_effect=_side_effect_unreviewed,
        event_type="task.transitioned",
        reason_code="submit_unreviewed",
        wired=True,
    )


def _wired_submit_policy_approved_spec() -> TransitionSpec:
    """T10's approve branch — §8.5 outcome 1: merge-pending, engine-gated."""
    return TransitionSpec(
        transition_id="T10",
        trigger="submit_policy_approved",
        from_states=frozenset({TaskState.IN_PROGRESS}),
        to_state=TaskState.TO_BE_AUDITED,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor C
        guard=_guard_policy_approved,
        side_effect=_side_effect_policy_approved,
        event_type="task.transitioned",
        reason_code="submit_policy_approved",
        wired=True,
    )


def ensure_submission_wired() -> None:
    """Put the wired T7/T8/T10 rows on the process registry (idempotent).

    Registration intentionally **not** import-time or ``AppConfig.ready``:
    the WP-1.5 suites assert the loader's stub rows and snapshot/restore
    the registry per test, so wiring happens lazily on the first
    submission call — production gets it on the first submit, tests get
    it inside their own restore guards (the WP-1.6 ``ensure_wired``
    pattern, its docstring's reason recorded here too).
    """
    ensure_registered()
    for trigger, spec in (
        ("submit", _wired_submit_spec),
        ("submit_flagged", _wired_submit_flagged_spec),
        ("submit_unreviewed", _wired_submit_unreviewed_spec),
        ("submit_policy_approved", _wired_submit_policy_approved_spec),
    ):
        row = DEFAULT_REGISTRY.get(trigger)
        if row is None or not row.wired:
            DEFAULT_REGISTRY.register(spec(), replace=True)


__all__ = [
    "PolicyDecision",
    "PolicyDecisionHook",
    "ensure_submission_wired",
    "resolve_policy_decision",
    "set_policy_decision_hook",
]
