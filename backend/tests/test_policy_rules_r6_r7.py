"""MT-3.4-04 — rules R6 (diff size) and R7 (confidence), table-driven.

Run with ``pytest backend/tests -k policy_rules_r6_r7 -q``:

* R6 passes exactly *at* ``autonomous_diff_threshold_lines`` and fails
  one line over — the strict "greater than" comparison Section 9.4
  words — with ``diff_over_threshold``.
* R7 passes at the minimum and fails below it — ``low_confidence``.
* Policy variance: non-default threshold/minimum from the §7.2 fields
  drive the rules (FR-PRJ-05).
* Unprovable stats fail R6 closed (recorded reading; the real path
  always populates them — MT-3.2-03 parses before the oversize drop).
"""

from __future__ import annotations

from apps.audit.policy import DECISION_APPROVE, DECISION_ESCALATE

from .wp34_helpers import PolicyCase, clean_context, run_policy_table


def test_r6_r7_table() -> None:
    """The Section 9.4 R6/R7 rows: boundaries, variance, combinations."""
    run_policy_table(
        [
            PolicyCase(
                "r6-pass-at-threshold",
                clean_context(insertions=200, deletions=50, autonomous_diff_threshold_lines=250),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r6-fail-one-line-over",
                clean_context(insertions=200, deletions=51, autonomous_diff_threshold_lines=250),
                DECISION_ESCALATE,
                frozenset({"R6"}),
                "diff_over_threshold",
            ),
            PolicyCase(
                "r6-custom-threshold-honored",
                clean_context(insertions=40, deletions=0, autonomous_diff_threshold_lines=40),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r6-custom-threshold-one-over",
                clean_context(insertions=40, deletions=1, autonomous_diff_threshold_lines=40),
                DECISION_ESCALATE,
                frozenset({"R6"}),
                "diff_over_threshold",
            ),
            PolicyCase(
                "r6-fail-unprovable-stats",
                clean_context(insertions=None, deletions=10),
                DECISION_ESCALATE,
                frozenset({"R6"}),
                "diff_over_threshold",
            ),
            PolicyCase(
                "r7-pass-at-minimum",
                clean_context(auditor_confidence=4, auditor_min_confidence=4),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r7-fail-one-below-minimum",
                clean_context(auditor_confidence=3, auditor_min_confidence=4),
                DECISION_ESCALATE,
                frozenset({"R7"}),
                "low_confidence",
            ),
            PolicyCase(
                "r7-custom-minimum-honored",
                clean_context(auditor_confidence=2, auditor_min_confidence=2),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r7-custom-minimum-one-below",
                clean_context(auditor_confidence=1, auditor_min_confidence=2),
                DECISION_ESCALATE,
                frozenset({"R7"}),
                "low_confidence",
            ),
            PolicyCase(
                "combined-r6-r7-both-fail",
                clean_context(
                    insertions=999,
                    deletions=0,
                    auditor_confidence=1,
                    auditor_min_confidence=4,
                ),
                DECISION_ESCALATE,
                frozenset({"R6", "R7"}),
                "diff_over_threshold",  # deterministic primary: first failing rule
            ),
        ]
    )
