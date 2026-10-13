"""The audit-outcome decision seam — invariant 8.3.4 (MT-3.3-05).

The verdict endpoint **never approves**: Section 8.3 rule 4 makes the
Policy Engine the only component that can set a policy-approved outcome.
This module is the WP-3.3 side of that boundary — a deliberate copy of
the T10 seam's shape (``transitions_submission.resolve_policy_decision``,
which its own changelog names as the model), specialized to the audit
inputs Section 9.4 defines: Task, Project Policy (read by the engine
inside the hook), the Resolution under audit, and the **Audit Report**
evidence/confidence/proposed verdict the coder-flow seam cannot see.

Until MT-3.4-07 installs the engine via :func:`set_audit_decision_hook`,
:func:`resolve_audit_decision` **fails closed to escalate** — never an
implicit approve (invariant 8.3.4; MT-3.3-05 risk note). The escalation
reason is chosen from the enumerated Section 8.4 catalog only:

* proposed verdict ``flag_risk`` / ``fail`` → ``auditor_flagged`` —
  Section 8.4's own definition of R8's reason ("Auditor proposed verdict
  is not pass"), already true without any rule evaluation;
* proposed verdict ``pass`` → ``policy_forced_review`` — the same
  member WP-3.2's T10 seam records for "policy forced this review
  before any rule could pass" (its OQ applies here too: §8.4 has no
  "engine not yet wired" member, so no thirteenth code is invented).

The hook is pure by contract (Section 9.4's "pure, deterministic rules
evaluator"), so the verdict service's trigger choice and the T13/T14
rows' side-effect re-consult agree by construction — exactly how T10's
branches made approve structurally unreachable without the engine.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from apps.tasks.models import ReviewReason, Task, TaskResolution

from .models import AuditReport, VerdictChoice

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .policy.engine import EvaluationResult

#: The hook signature MT-3.4-07 installs (audit inputs: the report's
#: evidence, confidence and proposed verdict ride the row).
type AuditDecisionHook = Callable[[Task, TaskResolution, AuditReport], "AuditDecision"]


@dataclass(frozen=True)
class AuditDecision:
    """The engine's verdict for one audited resolution (Section 9.4).

    ``approve`` selects T13; an escalation carries exactly one
    enumerated Section 8.4 reason (validated by
    :func:`resolve_audit_decision` before it leaves this module).
    ``evaluation`` rides the engine's own decisions so the T13/T14
    side effects can persist every rule's outcome and the engine
    version (MT-3.4-06); the fail-closed default and ad-hoc test
    hooks carry ``None`` — nothing is persisted for them, never
    faked (invariant 8.3.4).
    """

    approve: bool
    reason: str | None = None
    #: The full Section 9.4 evaluation behind this decision, when the
    #: engine produced it (MT-3.4-06's persistence source).
    evaluation: EvaluationResult | None = None


#: Fail-closed default (MT-3.3-05): with no engine the only honest
#: outcome is escalate — never auto-approve (invariant 8.3.4).
_policy_hook: AuditDecisionHook | None = None

#: Section 8.4 member for "no engine, verdict was pass" (recorded
#: reading — the T10 seam's OQ, reused verbatim; see the module doc).
_FORCED_REVIEW: Final = ReviewReason.POLICY_FORCED_REVIEW


def set_audit_decision_hook(hook: AuditDecisionHook | None) -> None:
    """Install (or remove) the WP-3.4 Policy Engine evaluator."""
    global _policy_hook
    _policy_hook = hook


def resolve_audit_decision(
    task: Task, resolution: TaskResolution, report: AuditReport
) -> AuditDecision:
    """The engine's verdict — the single seam service and rows read.

    Fail-closed: no hook → escalate with the Section 8.4 reason the
    report's own proposed verdict proves (``auditor_flagged`` for a
    non-pass verdict, ``policy_forced_review`` for a pass the rules
    have not yet cleared). Installed hooks must return an
    :class:`AuditDecision`; an escalation reason outside the Section 8.4
    catalog is a programming error (``ValueError``), never a silent
    write (Section 20.4 item 5).
    """
    if _policy_hook is None:
        return AuditDecision(
            approve=False,
            reason=(
                ReviewReason.AUDITOR_FLAGGED
                if report.proposed_verdict != VerdictChoice.PASS
                else _FORCED_REVIEW
            ),
        )
    decision = _policy_hook(task, resolution, report)
    if not isinstance(decision, AuditDecision):  # pragma: no cover - contract
        raise ValueError("audit decision hook must return an AuditDecision")
    if decision.approve:
        return decision
    if decision.reason is None or decision.reason not in set(ReviewReason.values):
        raise ValueError(f"audit escalation reason {decision.reason!r} is not a Section 8.4 member")
    return decision


__all__ = [
    "AuditDecision",
    "AuditDecisionHook",
    "resolve_audit_decision",
    "set_audit_decision_hook",
]
