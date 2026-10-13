"""Rule implementations R1–R9 — parent plan Section 9.4 (MT-3.4-02 … 05).

One pure function per Section 9.4 rule, each over the
:class:`~apps.audit.policy.context.PolicyContext` only: no I/O, no
clock, no database (ADR-009). Registration into the engine's reserved
slots happens in :mod:`apps.audit.policy.engine`; this module never
decides, it only answers "does this rule pass?".

The Section 9.4 design note is honored at the data layer: the changed
file list and stats are the authoritative values MT-3.2-03 parsed from
the stored patch (they ride the context), the scope comparison reuses
the *shared* matcher MT-3.2-04 fixed (:func:`evaluate_scope` — one
matcher, not two), and the diff pattern scan runs over the stored
patch's added lines (Section 12.1's secrets-in-diffs mitigation).

Recorded readings (Section 20.1 item 5; each is a changelog entry):

* **R1 "test command"** — every entry of ``evidence.commands`` is a
  command run for this task (the Section 10.5 shape carries no
  per-command type discriminator), so R1 fails when *any* entry has a
  non-zero exit code, when an entry lacks a usable integer exit code,
  or when the evidence holds no commands at all.
* **R2** recomputes through :func:`evaluate_scope` — the exact
  function the T7 submission guard used — so a submission cannot pass
  the gate and then fail R2 (or the reverse) on the same file list.
* **R3/R4/R5(a) path matching** normalizes each changed path with the
  shared :func:`normalize_changed_path` and matches with the shared
  :func:`glob_matches`. A stored glob that raises ``ValueError`` (a
  hand-edited row predating validation) makes the rule **fail** — an
  unverifiable "this file is not critical" cannot pass. A changed path
  that cannot be normalized is *skipped* by R3–R5 (it can't be shown
  to match any tree); rule R2 already fails closed on exactly such
  paths in the same evaluation, so escalation is never lost.
* **R5's env/key pattern set** (:data:`SECRET_PATTERNS`) is data, not
  folklore: the backend mirror of the bridge's Section 10.8 helper
  (``bridge/src/orchestrator_bridge/git_helper/secret_patterns.toml``
  — one conceptual list, asserted equal by
  ``tests/test_policy_rules_r3_r4_r5.py``). Adding or tuning a pattern
  is a reviewed data edit on both sides, never a silent code change.
* **R6/R7 boundary words** are the plan's verbatim comparisons: R6
  fails on insertions+deletions *greater than* the threshold (equal
  passes); R7 fails on confidence *below* the minimum (equal passes).
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

from apps.projects.services.globs import glob_matches
from apps.tasks.services.scope import evaluate_scope, normalize_changed_path

from .context import VERDICT_PASS, EvidenceCommand, PolicyContext

# --- R5's documented env/key pattern set (data; Section 12.1 / 10.8) --------


@dataclass(frozen=True)
class SecretPattern:
    """One secret-like indicator scanned against added lines (Section 10.8)."""

    id: str
    severity: str  # "high" | "medium" — mirrored for review parity
    description: str
    regex: re.Pattern[str]


def _pattern(id: str, severity: str, description: str, regex: str) -> SecretPattern:
    """Compile one documented pattern once at import (deterministic)."""
    return SecretPattern(id=id, severity=severity, description=description, regex=re.compile(regex))


#: The backend's copy of the bridge helper's default pattern set — ids,
#: severities and regexes stay 1:1 with ``secret_patterns.toml`` (one
#: conceptual list; the backend scan of the stored patch is the
#: authoritative one, Section 9.4/10.8). Entropy/ML scanning is
#: deliberately absent (not in the plan — RISK-08's conservative posture).
SECRET_PATTERNS: Final[tuple[SecretPattern, ...]] = (
    _pattern(
        "private-key-block",
        "high",
        "PEM-encoded private key block header",
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----",
    ),
    _pattern(
        "aws-access-key-id",
        "high",
        "AWS-style access key id shape",
        r"\bAKIA[0-9A-Z]{16}\b",
    ),
    _pattern(
        "secret-assignment",
        "high",
        "Secret-looking name assigned a non-trivial literal value",
        r"""(?i)\b(?:api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?key|"""
        r"""auth[_-]?token|access[_-]?token|client[_-]?secret|private[_-]?key|"""
        r"""password|passwd|secret|token)\b\s*[:=]=?\s*["'][^"'\s]{8,}["']""",
    ),
    _pattern(
        "bearer-token-literal",
        "medium",
        "****** header with a literal credential",
        r"(?i)\bbearer\s+[A-Za-z0-9._+/=-]{16,}",
    ),
    _pattern(
        "github-token",
        "high",
        "GitHub personal-access/app/installation token prefix",
        r"\b(?:gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,})\b",
    ),
)


# --- added-line extraction from a stored unified patch (Section 9.4) --------

_HUNK_HEADER: Final = re.compile(r"^@@ -\d+(?:,\d+)? \+\d+(?:,\d+)? @@")


def _hunk_counts(line: str) -> tuple[int, int]:
    """``(old_lines, new_lines)`` from a ``@@ -a,b +c,d @@`` header."""
    match = re.match(r"^@@ -\d+(?:,(\d+))? \+\d+(?:,(\d+))? @@", line)
    if match is None:  # defensive: the caller matched _HUNK_HEADER first
        return (1, 1)
    old = int(match.group(1)) if match.group(1) is not None else 1
    new = int(match.group(2)) if match.group(2) is not None else 1
    return (old, new)


def added_lines_of(patch: str) -> tuple[str, ...]:
    """The stored patch's added-line **contents** (the R5 scan surface).

    Hunk-header counts track the boundary exactly like MT-3.2-03's
    authoritative parser, so a ``+++ …`` content line inside a hunk is
    scan surface, never a file header, and header-looking text outside
    hunks is never scanned. Pure and deterministic (ADR-009): same
    bytes → same lines.
    """
    added: list[str] = []
    old_remaining = 0
    new_remaining = 0
    for line in patch.splitlines():
        in_hunk = old_remaining > 0 or new_remaining > 0
        if not in_hunk:
            if _HUNK_HEADER.match(line) is not None:
                old_remaining, new_remaining = _hunk_counts(line)
            continue
        if line.startswith("+"):
            added.append(line[1:])
            new_remaining -= 1
        elif line.startswith("-"):
            old_remaining -= 1
        elif line.startswith("\\"):  # "\ No newline at end of file"
            pass
        else:  # context (leading space or an empty line)
            old_remaining -= 1
            new_remaining -= 1
    return tuple(added)


# --- the nine rules (Section 9.4 table, verbatim fail conditions) -----------

RuleFunc = Callable[[PolicyContext], bool]


def rule_r1_tests(context: PolicyContext) -> bool:
    """R1 Tests — pass iff every evidence command exited 0 and evidence exists.

    Section 9.4: fails when "any test command in evidence has a
    non-zero exit code, **or no test evidence at all**". ``None`` and
    ``()`` are both "no test evidence"; an entry without a usable
    integer exit code cannot prove a zero exit, so it fails closed.
    """
    commands: tuple[EvidenceCommand, ...] | None = context.evidence_commands
    if not commands:
        return False
    return all(command.exit_code is not None and command.exit_code == 0 for command in commands)


def rule_r2_scope(context: PolicyContext) -> bool:
    """R2 Scope — pass iff no changed file lies outside ``target_scope``.

    Recomputed from the authoritative changed-file list through the
    *shared* MT-3.2-04 matcher (Section 9.4 design note: never from
    auditor/coder claims or text).
    """
    return evaluate_scope(list(context.target_scope), list(context.changed_files)).ok


def _any_file_matches(
    context: PolicyContext, globs: Sequence[str], *, unparseable_is_match: bool
) -> bool:
    """Does any changed file match any glob? Shared matcher, one reading.

    Unparseable stored globs fail *closed* in both directions: for the
    escalation rules (``unparseable_is_match=True``) the rule fails;
    skipping them would let a broken policy row silently approve.
    """
    for raw in context.changed_files:
        path = normalize_changed_path(raw)
        if path is None:
            continue  # R2 fails closed on unprovable paths (same evaluation)
        for pattern in globs:
            try:
                if glob_matches(pattern, path):
                    return True
            except ValueError:
                if unparseable_is_match:
                    return True
    return False


def rule_r3_critical_paths(context: PolicyContext) -> bool:
    """R3 Critical paths — pass iff no changed file matches ``critical_path_globs``."""
    return not _any_file_matches(context, context.critical_path_globs, unparseable_is_match=True)


def rule_r4_migrations(context: PolicyContext) -> bool:
    """R4 Migrations — pass iff no changed file matches ``migration_path_globs``."""
    return not _any_file_matches(context, context.migration_path_globs, unparseable_is_match=True)


def _secret_in_added_lines(context: PolicyContext) -> bool:
    """R5(b) — any documented secret-like pattern in the added lines.

    ``added_lines`` ``None`` means the stored body is unavailable
    (Section 9.7 oversize, or a missing artifact): the scan cannot run,
    so the condition reads as *present* — R5 fails closed, never
    vacuously (MT-3.4-03 risk note; OQ recorded in the changelog).
    """
    if context.added_lines is None:
        return True
    for line in context.added_lines:
        for pattern in SECRET_PATTERNS:
            if pattern.regex.search(line):
                return True
    return False


def rule_r5_sensitive_config(context: PolicyContext) -> bool:
    """R5 Sensitive config — glob match **or** env/key pattern in added lines."""
    glob_hit = _any_file_matches(context, context.sensitive_config_globs, unparseable_is_match=True)
    return not (glob_hit or _secret_in_added_lines(context))


def rule_r6_diff_size(context: PolicyContext) -> bool:
    """R6 Diff size — fails when changed lines *exceed* the threshold.

    Patch-derived stats only (MT-3.2-03 authoritative values, never
    agent/auditor claims). Unprovable stats (``None`` — a degraded row
    the real path cannot produce) fail closed; "greater than" is
    strict, so exactly the threshold passes (Section 9.4 verbatim).
    """
    if context.insertions is None or context.deletions is None:
        return False
    return context.insertions + context.deletions <= context.autonomous_diff_threshold_lines


def rule_r7_confidence(context: PolicyContext) -> bool:
    """R7 Confidence — fails when auditor confidence is *below* the minimum.

    The stored report confidence only. ``None`` = no auditor (the T10
    coder path, Section 8.5): not applicable, passes — the documented
    convention, never a silent "4 by default" (MT-3.4-04 risk note).
    """
    if context.auditor_confidence is None:
        return True
    return context.auditor_confidence >= context.auditor_min_confidence


def rule_r8_auditor_flag(context: PolicyContext) -> bool:
    """R8 Auditor flag — fails when the proposed verdict is not "pass".

    ``None`` = no auditor (T10): not applicable, passes — the same
    convention R7 records; "no verdict" never reads as "not pass"
    (MT-3.4-05 risk note).
    """
    if context.proposed_verdict is None:
        return True
    return context.proposed_verdict == VERDICT_PASS


def rule_r9_switch(context: PolicyContext) -> bool:
    """R9 Switch — fails when ``auto_complete_enabled`` is false.

    The persisted policy flag only; model text, auditor notes and rule
    prose can never flip it (Section 19: "model text cannot override").
    """
    return context.auto_complete_enabled


__all__ = [
    "SECRET_PATTERNS",
    "SecretPattern",
    "added_lines_of",
    "rule_r1_tests",
    "rule_r2_scope",
    "rule_r3_critical_paths",
    "rule_r4_migrations",
    "rule_r5_sensitive_config",
    "rule_r6_diff_size",
    "rule_r7_confidence",
    "rule_r8_auditor_flag",
    "rule_r9_switch",
]
