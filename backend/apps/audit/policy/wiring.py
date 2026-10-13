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

The hooks are thin conversions of the pure
:func:`~apps.audit.policy.engine.evaluate` result onto the two seam
shapes; rule results ride the audit seam's
:class:`~apps.audit.decision.AuditDecision` so the T13/T14 side
effects can persist them (MT-3.4-06). The T10 seam carries no
persistence payload — the coder path has no §7.2 row to write (OQ
recorded in the WP changelog).
"""

from __future__ import annotations

from apps.tasks.models import Task, TaskResolution
from apps.tasks.services.scope import ScopeVerdict
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


def ensure_policy_engine_wired() -> None:
    """Install the engine on both decision seams (idempotent)."""
    set_audit_decision_hook(audit_decision_hook)
    set_policy_decision_hook(submission_decision_hook)


__all__ = [
    "audit_decision_hook",
    "ensure_policy_engine_wired",
    "submission_decision_hook",
]
