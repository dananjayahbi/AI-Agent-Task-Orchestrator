"""The evaluator: rule registry, evaluation loop, version stamp (MT-3.4-01).

Section 9.4's contract, fixed here once:

* rules declare stable ids **R1…R9** in registration order, each with
  its Section 9.4 review-reason association for failure;
* evaluation runs **every** registered rule — the result list is never
  short-circuited, because MT-3.4-06 persists each rule's outcome and
  the review panel shows the human exactly why the task was escalated;
* the decision is ``approve`` only when every rule passes, otherwise
  ``escalate`` (Section 9.4's exact verbs — WP-3.4's acceptance: "the
  engine never approves when any rule fails");
* every result carries the engine version for persistence onto the
  Audit Report (Section 9.4 design note);
* evaluation is pure: same context bytes → same result (ADR-009).

Reason codes are validated against the Section 8.4 catalog at
registration time (``ReviewReason``), so a rule can never escalate
with a code the plan does not enumerate (Section 20.4 item 5).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Final

from apps.tasks.models import ReviewReason

from .context import PolicyContext
from .rules import (
    rule_r1_tests,
    rule_r2_scope,
    rule_r3_critical_paths,
    rule_r4_migrations,
    rule_r5_sensitive_config,
    rule_r6_diff_size,
    rule_r7_confidence,
    rule_r8_auditor_flag,
    rule_r9_switch,
)

#: The engine's version stamp (Section 9.4: "the version is stored on
#: each Audit Report for traceability"). Bump on any rule or context
#: semantic change so stored histories stay interpretable.
ENGINE_VERSION: Final = "1.0.0"

#: Section 9.4's output verbs — the exact words MT-3.4-07's T13/T14
#: mapping consumes (MT-3.4-01 risk note: fix the vocabulary here).
DECISION_APPROVE: Final = "approve"
DECISION_ESCALATE: Final = "escalate"

#: The reserved registry slots, R1…R9 in Section 9.4 table order.
RULE_SLOTS: Final[tuple[str, ...]] = ("R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9")


@dataclass(frozen=True)
class RuleOutcome:
    """One rule's result — the Section 9.4 "rule result" persisted per rule."""

    rule: str  # "R1" … "R9"
    passed: bool
    #: The Section 8.4 member this rule escalates with; ``None`` when passed.
    review_reason: str | None

    def as_dict(self) -> dict[str, str | bool | None]:
        """The §7.2 ``policy_rule_results`` JSON row (stable key names)."""
        return {"rule": self.rule, "passed": self.passed, "review_reason": self.review_reason}


@dataclass(frozen=True)
class EvaluationResult:
    """The engine's full output (Section 9.4: approve/escalate + results)."""

    decision: str  # DECISION_APPROVE | DECISION_ESCALATE
    engine_version: str
    #: Every registered rule's outcome, registration order (R1…R9) — never partial.
    rule_results: tuple[RuleOutcome, ...]

    @property
    def approved(self) -> bool:
        """The approve/escalate verdict as a boolean."""
        return self.decision == DECISION_APPROVE

    @property
    def primary_reason(self) -> str | None:
        """The deterministic escalation reason (``None`` on approval).

        Ordering rule (MT-3.4-07 risk note — documented here): the
        **first failing rule in Section 9.4 table order R1→R9** owns
        the Task's single ``review_reason``; every failing reason is
        still persisted in ``rule_results`` for the review panel.
        """
        for outcome in self.rule_results:
            if not outcome.passed and outcome.review_reason is not None:
                return outcome.review_reason
        return None

    @property
    def failed_rules(self) -> tuple[RuleOutcome, ...]:
        """Only the failing outcomes (for assertions; persistence keeps all)."""
        return tuple(outcome for outcome in self.rule_results if not outcome.passed)

    def as_rule_results_json(self) -> list[dict[str, str | bool | None]]:
        """The §7.2 ``policy_rule_results`` shape: every rule, pass/fail."""
        return [outcome.as_dict() for outcome in self.rule_results]


@dataclass(frozen=True)
class RuleSpec:
    """One registered rule: stable id, escalation reason, pure function."""

    rule_id: str
    review_reason: str
    func: Callable[[PolicyContext], bool]  # True = pass


class RuleRegistry:
    """The reserved R1…R9 slots and their registered rules, in order.

    Ids are reserved up front so rule MTs register into stable slots
    (Section 20.5 traceability to the Section 9.4 table); an unknown id
    or a duplicate registration is a programming error (``ValueError``),
    never a silent overwrite.
    """

    def __init__(self, slots: Sequence[str] = RULE_SLOTS) -> None:
        """Reserve *slots*; nothing is registered yet."""
        self._slots: tuple[str, ...] = tuple(slots)
        self._registered: dict[str, RuleSpec] = {}

    @property
    def slots(self) -> tuple[str, ...]:
        """The reserved ids in registration order."""
        return self._slots

    def register(self, spec: RuleSpec) -> None:
        """Register one rule into its reserved slot (in order or later)."""
        if spec.rule_id not in self._slots:
            raise ValueError(f"unknown rule slot {spec.rule_id!r}; reserved: {self._slots}")
        if spec.rule_id in self._registered:
            raise ValueError(f"rule {spec.rule_id!r} is already registered")
        if spec.review_reason not in set(ReviewReason.values):
            raise ValueError(
                f"rule {spec.rule_id!r} reason {spec.review_reason!r} is not a Section 8.4 member"
            )
        self._registered[spec.rule_id] = spec

    def rules(self) -> tuple[RuleSpec, ...]:
        """The registered rules, slot order (R1…R9)."""
        return tuple(self._registered[slot] for slot in self._slots if slot in self._registered)


def _build_default_registry() -> RuleRegistry:
    """Register the nine Section 9.4 rules in table order (MT-3.4-02…05)."""
    registry = RuleRegistry()
    for spec in (
        RuleSpec("R1", ReviewReason.TEST_FAILURE, rule_r1_tests),
        RuleSpec("R2", ReviewReason.SCOPE_VIOLATION, rule_r2_scope),
        RuleSpec("R3", ReviewReason.CRITICAL_PATH_CHANGED, rule_r3_critical_paths),
        RuleSpec("R4", ReviewReason.MIGRATION_DETECTED, rule_r4_migrations),
        RuleSpec("R5", ReviewReason.SENSITIVE_CONFIG_CHANGED, rule_r5_sensitive_config),
        RuleSpec("R6", ReviewReason.DIFF_OVER_THRESHOLD, rule_r6_diff_size),
        RuleSpec("R7", ReviewReason.LOW_CONFIDENCE, rule_r7_confidence),
        RuleSpec("R8", ReviewReason.AUDITOR_FLAGGED, rule_r8_auditor_flag),
        RuleSpec("R9", ReviewReason.POLICY_FORCED_REVIEW, rule_r9_switch),
    ):
        registry.register(spec)
    return registry


#: The process registry the engine evaluates against (all nine slots).
DEFAULT_REGISTRY: Final = _build_default_registry()


def evaluate(
    context: PolicyContext, registry: RuleRegistry | Iterable[RuleSpec] | None = None
) -> EvaluationResult:
    """Run every registered rule over *context* — the whole Section 9.4 table.

    Pure and deterministic (ADR-009): no I/O, no clock, no randomness;
    identical context bytes yield an identical
    :class:`EvaluationResult`. ``registry`` defaults to
    :data:`DEFAULT_REGISTRY`; the table-driven harness passes small
    fake registries to test the loop itself (MT-3.4-01).
    """
    if registry is None:
        specs = DEFAULT_REGISTRY.rules()
    elif isinstance(registry, RuleRegistry):
        specs = registry.rules()
    else:
        specs = tuple(registry)

    outcomes: list[RuleOutcome] = []
    for spec in specs:
        passed = bool(spec.func(context))
        outcomes.append(
            RuleOutcome(
                rule=spec.rule_id,
                passed=passed,
                review_reason=None if passed else spec.review_reason,
            )
        )

    approved = all(outcome.passed for outcome in outcomes)
    return EvaluationResult(
        decision=DECISION_APPROVE if approved else DECISION_ESCALATE,
        engine_version=ENGINE_VERSION,
        rule_results=tuple(outcomes),
    )


__all__ = [
    "DECISION_APPROVE",
    "DECISION_ESCALATE",
    "DEFAULT_REGISTRY",
    "ENGINE_VERSION",
    "RULE_SLOTS",
    "EvaluationResult",
    "RuleOutcome",
    "RuleRegistry",
    "RuleSpec",
    "evaluate",
]
