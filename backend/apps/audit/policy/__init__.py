"""The Policy Engine — parent plan Section 9.4 (WP-3.4; ADR-009).

A pure, deterministic rules evaluator: inputs are exactly Task, Project
Policy, Resolution (changed files and stats) and Audit Report evidence
(:mod:`context`), the output is ``approve`` or ``escalate`` with a list
of per-rule results (:mod:`engine`). Rule implementations live in
:mod:`rules`; the persisted-row adapter (the only module that touches
the database or storage) lives in :mod:`adapter`; the seam wiring and
the transactional persistence helper live in :mod:`wiring` /
:mod:`persist`.

The package re-exports only the pure surface — the adapter and wiring
modules are deliberately *not* imported here so the engine's imports
can never drag in I/O (Section 9.4; ADR-009).
"""

from __future__ import annotations

from .context import VERDICT_PASS, EvidenceCommand, PolicyContext
from .engine import (
    DECISION_APPROVE,
    DECISION_ESCALATE,
    DEFAULT_REGISTRY,
    ENGINE_VERSION,
    RULE_SLOTS,
    EvaluationResult,
    RuleOutcome,
    RuleRegistry,
    RuleSpec,
    evaluate,
)
from .rules import added_lines_of

__all__ = [
    "DECISION_APPROVE",
    "DECISION_ESCALATE",
    "DEFAULT_REGISTRY",
    "ENGINE_VERSION",
    "RULE_SLOTS",
    "EvidenceCommand",
    "EvaluationResult",
    "PolicyContext",
    "RuleOutcome",
    "RuleRegistry",
    "RuleSpec",
    "VERDICT_PASS",
    "added_lines_of",
    "evaluate",
]
