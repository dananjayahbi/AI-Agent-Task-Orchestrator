"""MT-3.4-02 — rules R1 (tests) and R2 (scope), table-driven (Section 9.4).

Run with ``pytest backend/tests -k policy_rules_r1_r2 -q``:

* R1 passes on all-zero exits; fails on one non-zero exit, on empty
  evidence, on missing evidence (``None``), and on an entry whose exit
  code is unprovable — reason ``test_failure`` verbatim (§8.4).
* R2 passes when every changed file sits inside ``target_scope``; fails
  on one file outside every glob — ``scope_violation`` — recomputed
  from the authoritative file list through the *shared* MT-3.2-04
  matcher (never from any agent's text).
* Combined cases list both failures with ``test_failure`` as the
  deterministic primary (R1→R9 table order).
"""

from __future__ import annotations

from apps.audit.policy import DECISION_APPROVE, DECISION_ESCALATE, EvidenceCommand

from .wp34_helpers import PolicyCase, clean_context, run_policy_table


def test_r1_r2_table() -> None:
    """The Section 9.4 R1/R2 rows: pass/fail, boundaries and combinations."""
    run_policy_table(
        [
            PolicyCase(
                "r1-pass-all-zero-exits",
                clean_context(
                    evidence_commands=(
                        EvidenceCommand("tests", "pytest -q", 0),
                        EvidenceCommand("lint", "ruff check .", 0),
                    )
                ),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r1-fail-one-non-zero-exit",
                clean_context(
                    evidence_commands=(
                        EvidenceCommand("tests", "pytest -q", 1),
                        EvidenceCommand("lint", "ruff check .", 0),
                    )
                ),
                DECISION_ESCALATE,
                frozenset({"R1"}),
                "test_failure",
            ),
            PolicyCase(
                "r1-fail-empty-commands",
                clean_context(evidence_commands=()),
                DECISION_ESCALATE,
                frozenset({"R1"}),
                "test_failure",
            ),
            PolicyCase(
                "r1-fail-missing-evidence",
                clean_context(evidence_commands=None),
                DECISION_ESCALATE,
                frozenset({"R1"}),
                "test_failure",
            ),
            PolicyCase(
                "r1-fail-unprovable-exit-code",
                clean_context(evidence_commands=(EvidenceCommand("tests", "pytest -q", None),)),
                DECISION_ESCALATE,
                frozenset({"R1"}),
                "test_failure",
            ),
            PolicyCase(
                "r2-pass-all-in-scope",
                clean_context(
                    target_scope=("src/**", "docs/**"),
                    changed_files=("src/app.py", "docs/readme.md"),
                ),
                DECISION_APPROVE,
            ),
            PolicyCase(
                "r2-fail-one-file-outside",
                clean_context(
                    target_scope=("src/**",),
                    changed_files=("src/app.py", "docs/readme.md"),
                ),
                DECISION_ESCALATE,
                frozenset({"R2"}),
                "scope_violation",
            ),
            PolicyCase(
                "r2-fail-empty-scope-with-files",
                clean_context(target_scope=(), changed_files=("src/app.py",)),
                DECISION_ESCALATE,
                frozenset({"R2"}),
                "scope_violation",
            ),
            PolicyCase(
                "r2-fail-unnormalizable-path",
                clean_context(target_scope=("src/**",), changed_files=("../escape.py",)),
                DECISION_ESCALATE,
                frozenset({"R2"}),
                "scope_violation",
            ),
            PolicyCase(
                "combined-r1-r2-both-fail",
                clean_context(
                    evidence_commands=(EvidenceCommand("tests", "pytest -q", 2),),
                    target_scope=("src/**",),
                    changed_files=("docs/readme.md",),
                ),
                DECISION_ESCALATE,
                frozenset({"R1", "R2"}),
                "test_failure",  # deterministic primary: first failing rule R1→R9
            ),
        ]
    )


def test_r2_recomputation_matches_the_submission_scope_verdict() -> None:
    """R2 and the T7 guard share one matcher (MT-3.2-04/MT-3.4-02 risk)."""
    from apps.audit.policy.rules import rule_r2_scope
    from apps.tasks.services.scope import evaluate_scope

    files = ["src/app.py", "docs/readme.md"]
    shared = evaluate_scope(["src/**"], files)
    assert not shared.ok, "one matcher: the shared verdict sees the violation"
    out_of_scope = clean_context(target_scope=("src/**",), changed_files=tuple(files))
    assert rule_r2_scope(out_of_scope) is False
    assert rule_r2_scope(clean_context()) is True
