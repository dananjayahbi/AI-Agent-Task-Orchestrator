"""Transactional persistence of the engine's output (MT-3.4-06).

Section 9.4: *"The result (every rule and its outcome) is persisted so
the human reviewer sees exactly why the task was escalated"* and *"the
version is stored on each Audit Report for traceability"*. Section 7.2
allots the columns; the T13/T14 side effects in
:mod:`apps.audit.transitions` call :func:`persist_evaluation` **inside
the dispatch transaction** (Section 8.2 rule 2), so a report can never
show a policy decision without its rule results, nor a transition
without the decision that caused it.

Restriction (invariant 8.3.4; MT-3.4-06 AC): this function is the only
writer of ``policy_decision`` / ``policy_rule_results`` /
``policy_engine_version`` — the model refuses every other update path
(``PolicyFieldsImmutable`` in :mod:`apps.audit.models`), and the
verdict API's strict input serializer refuses the fields outright, so
model text, auditor notes and API callers can never alter them.

The fail-closed seam default (no engine installed) carries no
evaluation — :func:`persist_evaluation` then writes *nothing* (the
fields stay ``null`` exactly as WP-3.3 left them: never faked).
"""

from __future__ import annotations

from ..models import AuditReport
from .engine import EvaluationResult


def persist_evaluation(report: AuditReport, evaluation: EvaluationResult | None) -> None:
    """Write the engine's decision, all-nine rule results and version.

    ``evaluation=None`` means the seam answered without an engine (the
    fail-closed default): nothing is written — policy fields stay
    ``null``, never fabricated (invariant 8.3.4).
    """
    if evaluation is None:
        return
    report.policy_decision = evaluation.decision
    report.policy_rule_results = evaluation.as_rule_results_json()
    report.policy_engine_version = evaluation.engine_version
    # One guarded save, same transaction as the transition: the model's
    # engine-only guard lifts for exactly this write (and resets after).
    report._policy_engine_write = True  # type: ignore[attr-defined]
    report.save(
        update_fields=[
            "policy_decision",
            "policy_rule_results",
            "policy_engine_version",
        ]
    )


__all__ = ["persist_evaluation"]
