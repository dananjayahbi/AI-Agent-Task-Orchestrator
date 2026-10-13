"""MT-3.4-05 — rules R8 (auditor flag) and R9 (auto-complete switch), table-driven.

Run with ``pytest backend/tests -k policy_rules_r8_r9 -q``:

* R8 passes on ``pass``; fails on ``flag_risk`` and on ``fail`` —
  ``auditor_flagged`` (Section 10.5 verdict enum; §8.4 reason).
* R9 passes when ``auto_complete_enabled`` is true; fails when false —
  ``policy_forced_review`` — even when every other rule is green.
* Verdict-absent (the T10 coder path, §8.5) is *not applicable*: R8
  passes, by the MT-3.4-01 context contract's documented convention
  ("no verdict" never reads as "not pass").
* Combined R8+R9 case; R9 decided only by the policy flag (no text).
"""

from __future__ import annotations

from apps.audit.policy import DECISION_APPROVE, DECISION_ESCALATE

from .wp34_helpers import PolicyCase, clean_context, run_policy_table


def test_r8_r9_table() -> None:
    """The Section 9.4 R8/R9 rows: pass/fail each, combined, conventions."""
    run_policy_table(
        [
            PolicyCase(
                "r8-pass-pass-verdict",
                clean_context(proposed_verdict="pass"),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r8-fail-flag-risk",
                clean_context(proposed_verdict="flag_risk"),
                DECISION_ESCALATE,
                frozenset({"R8"}),
                "auditor_flagged",
            ),
            PolicyCase(
                "r8-fail-fail-verdict",
                clean_context(proposed_verdict="fail"),
                DECISION_ESCALATE,
                frozenset({"R8"}),
                "auditor_flagged",
            ),
            PolicyCase(
                "r8-absent-verdict-is-not-applicable",
                clean_context(proposed_verdict=None),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r9-pass-enabled",
                clean_context(auto_complete_enabled=True),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r9-fail-disabled-all-other-rules-green",
                clean_context(auto_complete_enabled=False),
                DECISION_ESCALATE,
                frozenset({"R9"}),
                "policy_forced_review",
            ),
            PolicyCase(
                "combined-r8-r9-both-fail",
                clean_context(proposed_verdict="fail", auto_complete_enabled=False),
                DECISION_ESCALATE,
                frozenset({"R8", "R9"}),
                "auditor_flagged",  # deterministic primary: first failing rule
            ),
            PolicyCase(
                "t10-shaped-context-no-auditor-still-escalates-via-r1",
                clean_context(
                    evidence_commands=None,
                    auditor_confidence=None,
                    proposed_verdict=None,
                ),
                DECISION_ESCALATE,
                frozenset({"R1"}),
                "test_failure",
            ),
        ]
    )


def test_r9_reads_only_the_persisted_flag() -> None:
    """Model text cannot flip R9 (Section 19: "model text cannot override")."""
    from apps.audit.policy.rules import rule_r9_switch

    # The rule's entire input surface is the boolean context field —
    # there is no notes/summary channel for text to influence it.
    assert rule_r9_switch(clean_context(auto_complete_enabled=False)) is False
    assert rule_r9_switch(clean_context(auto_complete_enabled=True)) is True
