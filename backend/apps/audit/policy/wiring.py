"""Seam wiring: install the Policy Engine as the decision hooks (MT-3.4-07).

Invariant 8.3.4 closed: the engine — and only the engine — produces
policy-approved outcomes. :func:`ensure_policy_engine_wired` installs

* the **audit seam** (:func:`apps.audit.decision.set_audit_decision_hook`)
  so ``POST /tasks/{id}/audit-verdict`` and the T13/T14 rows decide by
  the Section 9.4 table over the Audit Report's evidence, and
* the **T10 seam**
  (:func:`apps.tasks.state_machine.transitions_submission.set_policy_decision_hook`)
  so ``audit_required`` false submissions funnel through the *same*
  engine on coder evidence (Section 8.5; MT-3.2-05's stub retired).

Wiring runs from ``AuditConfig.ready()`` — the events-app precedent
(:mod:`apps.events.apps`) for *hook* installation; registry rows stay
lazily wired (the WP-1.5 suites' snapshot/restore owns that state).
Both seams fail closed when a fixture removes the hooks: no hook →
escalate, never approve (MT-3.3-05 / MT-3.2-05 defaults, unchanged).
The same registration also installs WP-3.9's rule-details reader
(:func:`review_rule_details_hook`) behind the ``review.requested``
event — a read of the persisted evaluation, never a second decision
path (MT-3.9-01).

The hooks are thin conversions of the pure
:func:`~apps.audit.policy.engine.evaluate` result onto the two seam
shapes; rule results ride the audit seam's
:class:`~apps.audit.decision.AuditDecision` so the T13/T14 side
effects can persist them (MT-3.4-06). The T10 seam carries no
persistence payload — the coder path has no §7.2 row to write (OQ
recorded in the WP changelog).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.tasks.models import Task, TaskResolution
from apps.tasks.services.scope import ScopeVerdict
from apps.tasks.state_machine.hooks import set_default_review_rule_details_hook
from apps.tasks.state_machine.transitions_submission import (
    PolicyDecision,
    set_policy_decision_hook,
)

from ..decision import AuditDecision, set_audit_decision_hook
from ..models import AuditReport
from .adapter import evaluate_audit, evaluate_submission


def audit_decision_hook(
    task: Task, resolution: TaskResolution, report: AuditReport
) -> AuditDecision:
    """The audit seam's engine: evaluate the Section 9.4 table, convert."""
    evaluation = evaluate_audit(task, resolution, report)
    return AuditDecision(
        approve=evaluation.approved,
        reason=evaluation.primary_reason,
        evaluation=evaluation,
    )


def submission_decision_hook(
    task: Task, resolution: TaskResolution, verdict: ScopeVerdict
) -> PolicyDecision:
    """The T10 seam's engine: the same table over coder evidence (§8.5)."""
    evaluation = evaluate_submission(task, resolution, verdict)
    return PolicyDecision(approve=evaluation.approved, reason=evaluation.primary_reason)


def review_rule_details_hook(task: Task, transition_id: str) -> Mapping[str, Any]:
    """MT-3.9-01's rule-details half of the ``review.requested`` payload.

    Only the row where the Policy Engine decided carries rule results —
    **T14** (MT-3.9-02: "T14 carries rule results; T8/T9/T18 carry no
    policy rule results"), keyed by the dispatcher-provided transition
    id so a later T8 self-flag can never inherit a previous escalation's
    evaluation. The source is the **persisted** Audit Report field
    (MT-3.4-06's ``policy_rule_results`` — WP-3.4's exact shape, one
    vocabulary): the T14 side effect persisted it inside the same
    dispatch transaction, before the dispatcher emits, so the read
    cannot lag the event (MT-3.9-02 risk note). The report is scoped to
    the current attempt (a stale attempt's report is never this entry's
    evidence); newest first for T12 audit retries. Empty mapping when
    nothing persisted — absence, never a fabricated rule set.
    """
    if transition_id != "T14":
        return {}
    report = (
        AuditReport.objects.filter(
            task_id=task.pk,
            policy_rule_results__isnull=False,
            resolution__attempt_number=task.attempt_number,
        )
        .order_by("-created_at")
        .first()
    )
    if report is None or not report.policy_rule_results:
        return {}
    return {"policy_rule_results": report.policy_rule_results}


def ensure_policy_engine_wired() -> None:
    """Install the engine on both decision seams (idempotent).

    Also installs the MT-3.9-01 rule-details reader as the default
    provider behind ``review.requested`` — a *read* of what the engine
    persisted, so unlike the decision seams it stays ambient (test
    fixtures reset the decision hooks to fail closed; the reader
    changes no outcome and never fabricates).
    """
    set_audit_decision_hook(audit_decision_hook)
    set_policy_decision_hook(submission_decision_hook)
    set_default_review_rule_details_hook(review_rule_details_hook)


__all__ = [
    "audit_decision_hook",
    "ensure_policy_engine_wired",
    "review_rule_details_hook",
    "submission_decision_hook",
]
