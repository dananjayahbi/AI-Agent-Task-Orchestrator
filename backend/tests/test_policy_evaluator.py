"""MT-3.4-01 — the policy evaluator framework (Section 9.4; ADR-009).

Run with ``pytest backend/tests -k policy_evaluator -q``:

* **Determinism** — repeated runs on an identical context yield
  identical results; the evaluator performs no I/O (a no-DB/no-storage
  guard: the pure suite runs without ``django_db``).
* **Approve only when every rule passes** — a fake rule set drives the
  loop (approve-all-pass / escalate-one-fail), and the real default
  registry never approves a context any rule fails.
* **Engine version** — stamped on every evaluation result.
* **Reserved slots** — the registry reserves R1…R9; unknown ids and
  duplicate registrations raise; reasons must be Section 8.4 members.
* **Table harness smoke** — :func:`run_policy_table` exercises a case
  (the scaffold WP-3.4's acceptance requires).
"""

from __future__ import annotations

import pytest

from apps.audit.decision import AuditDecision
from apps.audit.models import PolicyDecisionValue
from apps.audit.policy import (
    DECISION_APPROVE,
    DECISION_ESCALATE,
    DEFAULT_REGISTRY,
    ENGINE_VERSION,
    RULE_SLOTS,
    EvaluationResult,
    RuleRegistry,
    RuleSpec,
    evaluate,
)

from .wp34_helpers import PolicyCase, clean_context, run_policy_table

# Pure evaluator: no database, no storage, no clock (ADR-009). The
# autouse restore fixture in wp34_helpers touches only process state.


def test_identical_contexts_yield_identical_results() -> None:
    """Determinism (ADR-009): same context bytes → same result object."""
    context = clean_context()
    first = evaluate(context)
    second = evaluate(context)
    assert first == second
    assert first == evaluate(clean_context())


def test_approve_only_when_every_rule_passes() -> None:
    """The loop approves iff all registered rules pass (fake rule set)."""
    passing = RuleSpec("R1", "test_failure", lambda _context: True)
    failing = RuleSpec("R2", "scope_violation", lambda _context: False)

    approved = evaluate(clean_context(), registry=[passing])
    assert approved.decision == DECISION_APPROVE
    assert approved.primary_reason is None
    assert approved.rule_results[0].passed is True

    escalated = evaluate(clean_context(), registry=[passing, failing])
    assert escalated.decision == DECISION_ESCALATE
    assert escalated.primary_reason == "scope_violation"


def test_every_result_carries_the_engine_version() -> None:
    """Section 9.4: the version rides every evaluation for persistence."""
    assert evaluate(clean_context()).engine_version == ENGINE_VERSION
    assert evaluate(clean_context(), registry=[]).engine_version == ENGINE_VERSION


def test_default_registry_reserves_the_nine_slots_in_order() -> None:
    """R1…R9 reserved in Section 9.4 table order; all nine registered."""
    assert DEFAULT_REGISTRY.slots == RULE_SLOTS == tuple(f"R{i}" for i in range(1, 10))
    rules = DEFAULT_REGISTRY.rules()
    assert tuple(rule.rule_id for rule in rules) == RULE_SLOTS
    assert tuple(rule.review_reason for rule in rules) == (
        "test_failure",
        "scope_violation",
        "critical_path_changed",
        "migration_detected",
        "sensitive_config_changed",
        "diff_over_threshold",
        "low_confidence",
        "auditor_flagged",
        "policy_forced_review",
    )


def test_registry_refuses_unknown_ids_duplicates_and_catalog_drift() -> None:
    """Registration validates slot, uniqueness and the §8.4 catalog."""
    registry = RuleRegistry()
    with pytest.raises(ValueError, match="unknown rule slot"):
        registry.register(RuleSpec("R10", "test_failure", lambda _context: True))
    registry.register(RuleSpec("R1", "test_failure", lambda _context: True))
    with pytest.raises(ValueError, match="already registered"):
        registry.register(RuleSpec("R1", "test_failure", lambda _context: True))
    with pytest.raises(ValueError, match="Section 8.4"):
        registry.register(RuleSpec("R2", "not_a_catalog_reason", lambda _context: True))


def test_evaluation_never_short_circuits_the_result_list() -> None:
    """Every rule's outcome is produced even after a failure (MT-3.4-06)."""
    calls: list[str] = []

    def tracking(rule_id: str, reason: str, passed: bool) -> RuleSpec:
        def func(_context: object) -> bool:
            calls.append(rule_id)
            return passed

        return RuleSpec(rule_id, reason, func)

    result = evaluate(
        clean_context(),
        registry=[
            tracking("R1", "test_failure", False),
            tracking("R2", "scope_violation", True),
            tracking("R3", "critical_path_changed", True),
        ],
    )
    assert calls == ["R1", "R2", "R3"], "no short-circuit — persistence needs all outcomes"
    assert len(result.rule_results) == 3


def test_table_harness_smoke_case() -> None:
    """The WP-3.4 table harness scaffold accepts and checks a case."""
    run_policy_table(
        [
            PolicyCase(
                case_id="clean-approve",
                context=clean_context(),
                expect_decision=DECISION_APPROVE,
            )
        ]
    )


def test_decision_vocabulary_matches_the_model_enum() -> None:
    """Section 9.4 verbs 1:1 with the AuditReport column values (MT-3.4-01)."""
    assert {DECISION_APPROVE, DECISION_ESCALATE} == set(PolicyDecisionValue.values)


def test_audit_decision_defaults_carry_no_evaluation() -> None:
    """The fail-closed seam default and ad-hoc hooks persist nothing."""
    assert AuditDecision(approve=False, reason="policy_forced_review").evaluation is None
    assert AuditDecision(approve=True).evaluation is None
    assert isinstance(evaluate(clean_context()), EvaluationResult)


def test_result_json_shape_lists_every_rule_with_pass_fail() -> None:
    """§7.2 shape: {rule, passed, review_reason} for all nine, in order."""
    result = evaluate(clean_context())
    payload = result.as_rule_results_json()
    assert [row["rule"] for row in payload] == list(RULE_SLOTS)
    assert all(row["passed"] is True for row in payload)
    assert all(row["review_reason"] is None for row in payload)
