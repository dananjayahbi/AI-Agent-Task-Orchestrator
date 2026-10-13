"""The Policy Engine evaluation context — parent plan Section 9.4 (MT-3.4-01).

Section 9.4 fixes the engine's inputs: *Task, Project Policy, Resolution
(changed files and stats), Audit Report evidence*. This module is the
**pure data contract** carrying exactly those inputs as plain immutable
values — no ORM rows, no storage handles, no clock — so evaluation is a
function of the context bytes alone (ADR-009: same context → same
result). The database/storage reads live in :mod:`apps.audit.policy.adapter`,
which assembles contexts from persisted rows *before* evaluation.

Absence conventions (MT-3.4-01 risk note — recorded readings, Section
20.1 item 5; each is asserted by a table case, never a silent default):

* **``evidence_commands``** — the Section 10.5 ``evidence.commands``
  shape (label / command / exit_code). ``None`` (no evidence section)
  and ``()`` (no command results) both mean *no test evidence at all*;
  rule R1 fails closed on either (Section 9.4 verbatim — "or no test
  evidence at all"). A command whose ``exit_code`` is missing or is not
  an integer also fails R1 (exit code unproven → not zero-proven).
* **``auditor_confidence`` / ``proposed_verdict``** — present on the
  audited path (every stored report carries them); ``None`` on the
  coder-evidence **T10** path (Section 8.5), where no auditor exists.
  Rules R7/R8 treat ``None`` as *not applicable* and pass — the
  documented convention, deliberately **not** "confidence silently
  defaults to 4" and deliberately **not** "a missing verdict counts as
  not-pass" (MT-3.4-04/05 risk notes forbid both silent readings).
  T10 submissions still cannot auto-approve while R1 fails closed on
  their absent evidence (the §8.5-vs-§10.5 evidence gap, recorded as
  an OQ in the WP changelog).
* **``added_lines``** — the unified patch's ``+`` lines, extracted from
  the **stored** patch (Section 9.4: the engine recomputes from the
  patch the bridge uploaded, never from agent/auditor text). ``None``
  means the body is unavailable (Section 9.7 oversize artifacts store
  stats and the file list only; a resolution without a stored artifact
  body is the same category); rule R5(b) fails closed rather than
  passing vacuously on data it could not scan (MT-3.4-03 risk note).
* **``insertions`` / ``deletions``** — the authoritative
  ``diff_summary`` stats (MT-3.2-03). ``None`` (stats unprovable)
  fails R6 closed; the real submission path always populates them (the
  parse runs before the oversize body-drop, Section 9.7).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class EvidenceCommand:
    """One Section 10.5 ``evidence.commands[]`` entry as R1 reads it.

    ``exit_code`` is ``None`` when the stored evidence lacks a usable
    integer exit code — R1 fails closed on it (never "treat as 0").
    """

    label: str
    command: str
    exit_code: int | None


@dataclass(frozen=True)
class PolicyContext:
    """Exactly the Section 9.4 inputs, as plain deterministic values.

    The field set is closed around the rule table: every field exists
    because some rule R1–R9 reads it (Section 20.5 traceability); no
    free-form extras ride along.
    """

    # --- Task (Section 7.2) ------------------------------------------------
    target_scope: tuple[str, ...]

    # --- Resolution (Section 7.2; MT-3.2-03 authoritative values) ---------
    changed_files: tuple[str, ...]
    insertions: int | None
    deletions: int | None
    #: The stored patch's added lines; ``None`` = body unavailable (fail-closed).
    added_lines: tuple[str, ...] | None

    # --- Project Policy (Section 7.2) -------------------------------------
    critical_path_globs: tuple[str, ...]
    migration_path_globs: tuple[str, ...]
    sensitive_config_globs: tuple[str, ...]
    autonomous_diff_threshold_lines: int
    auditor_min_confidence: int
    auto_complete_enabled: bool

    # --- Audit Report evidence (Section 7.2 / 10.5) -----------------------
    #: ``None`` or empty = no test evidence at all (R1 fails closed).
    evidence_commands: tuple[EvidenceCommand, ...] | None
    #: ``None`` = no auditor (T10 path) — R7 not applicable, passes.
    auditor_confidence: int | None
    #: ``None`` = no auditor (T10 path) — R8 not applicable, passes.
    proposed_verdict: str | None


#: Section 10.5 verdict "pass" — the only value R8 passes on.
VERDICT_PASS: Final = "pass"

__all__ = ["EvidenceCommand", "PolicyContext", "VERDICT_PASS"]
