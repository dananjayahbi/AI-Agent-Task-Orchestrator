"""The context adapter — the only Policy Engine module touching rows (MT-3.4-01).

Section 9.4's inputs, assembled from what is *already persisted*:
the locked Task, its Project Policy, the submitted Resolution
(authoritative ``changed_files`` / ``diff_summary`` from MT-3.2-03,
the stored patch body for R5's added-line scan) and — on the audited
path — the Audit Report's evidence, confidence and proposed verdict.

I/O discipline (ADR-009 + MT-3.4-01): every database or storage read
happens **here**, before evaluation; :func:`evaluate_audit` and
:func:`evaluate_submission` return the pure
:class:`~apps.audit.policy.engine.EvaluationResult` computed by
:func:`apps.audit.policy.engine.evaluate`, so rule functions stay
functions of context bytes.

Recorded readings (Section 20.1 item 5):

* **Patch body availability** — the artifact row within the Section
  9.7 cap contributes its stored body; an oversize artifact (body
  dropped at storage time) or a missing artifact yields
  ``added_lines=None`` and rule R5(b) fails closed (the scan could not
  run — never a vacuous pass).
* **T10's evidence gap** (Section 8.5 vs the §10.5 submit contract) —
  the coder path has no structured evidence carrier today, so the
  submission context carries ``evidence_commands=None``: R1 fails
  closed with ``test_failure`` and the coder path escalates. The plan
  asserts coder submissions "include evidence" (§8.5) but fixes no
  field for it (§10.5); the approve branch stays structurally gated
  until such a field lands (OQ in the WP changelog — no unplanned
  column invented here). R7/R8 are not applicable there (``None``).
* **The scope ``ScopeVerdict`` parameter** of the T10 seam is
  informational: the engine *recomputes* scope from the authoritative
  file list through the same shared matcher (Section 9.4 design note),
  which yields the identical verdict by construction.
"""

from __future__ import annotations

from typing import Any

from apps.attachments.storage import get_storage
from apps.tasks.models import Task, TaskResolution
from apps.tasks.services.resolutions import PATCH_MAX_BYTES
from apps.tasks.services.scope import ScopeVerdict

from ..models import AuditReport
from .context import EvidenceCommand, PolicyContext
from .engine import EvaluationResult, evaluate
from .rules import added_lines_of


def _stat(diff_summary: Any, key: str) -> int | None:
    """One authoritative diff stat; unusable values read as unprovable."""
    if not isinstance(diff_summary, dict):
        return None
    value = diff_summary.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _stored_added_lines(resolution: TaskResolution) -> tuple[str, ...] | None:
    """The stored patch body's added lines; ``None`` = body unavailable.

    Oversize artifacts (Section 9.7) never reach storage and a direct
    seeded resolution may lack the artifact row entirely — both read
    as unavailable (R5(b) then fails closed, never vacuously).
    """
    artifact = resolution.artifacts.filter(kind="patch").first()
    if artifact is None or artifact.size_bytes > PATCH_MAX_BYTES:
        return None
    body = get_storage().get(artifact.storage_key)
    return added_lines_of(body.decode("utf-8", errors="replace"))


def _evidence_commands(report: AuditReport) -> tuple[EvidenceCommand, ...] | None:
    """The report's ``evidence.commands`` as R1 reads them.

    A missing/``None``/non-list ``commands`` value is "no test
    evidence" (``None``); entries missing a usable integer exit code
    keep ``exit_code=None`` so R1 fails closed on them.
    """
    evidence = report.evidence
    if not isinstance(evidence, dict):
        return None
    commands = evidence.get("commands")
    if not isinstance(commands, list) or not commands:
        return None
    parsed: list[EvidenceCommand] = []
    for entry in commands:
        if not isinstance(entry, dict):
            return None
        exit_code = entry.get("exit_code")
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            exit_code = None  # unprovable exit code — R1 fails closed on it
        parsed.append(
            EvidenceCommand(
                label=str(entry.get("label", "")),
                command=str(entry.get("command", "")),
                exit_code=exit_code,
            )
        )
    return tuple(parsed)


def _policy_inputs(task: Task) -> dict[str, Any]:
    """The Project Policy fields the Section 9.4 table reads."""
    policy = task.project.agent_policy
    return {
        "critical_path_globs": tuple(policy.critical_path_globs or ()),
        "migration_path_globs": tuple(policy.migration_path_globs or ()),
        "sensitive_config_globs": tuple(policy.sensitive_config_globs or ()),
        "autonomous_diff_threshold_lines": int(policy.autonomous_diff_threshold_lines),
        "auditor_min_confidence": int(policy.auditor_min_confidence),
        "auto_complete_enabled": bool(policy.auto_complete_enabled),
    }


def _resolution_inputs(resolution: TaskResolution) -> dict[str, Any]:
    """The authoritative Resolution values (MT-3.2-03; stored patch)."""
    return {
        "changed_files": tuple(
            entry for entry in (resolution.changed_files or ()) if isinstance(entry, str)
        ),
        "insertions": _stat(resolution.diff_summary, "insertions"),
        "deletions": _stat(resolution.diff_summary, "deletions"),
        "added_lines": _stored_added_lines(resolution),
    }


def build_audit_context(
    task: Task, resolution: TaskResolution, report: AuditReport
) -> PolicyContext:
    """The audited path's context (Section 9.4: all four input groups)."""
    return PolicyContext(
        target_scope=tuple(glob for glob in (task.target_scope or ()) if isinstance(glob, str)),
        **_resolution_inputs(resolution),
        **_policy_inputs(task),
        evidence_commands=_evidence_commands(report),
        auditor_confidence=report.confidence,
        proposed_verdict=report.proposed_verdict,
    )


def build_submission_context(task: Task, resolution: TaskResolution) -> PolicyContext:
    """The T10 coder path's context (Section 8.5: coder evidence only).

    ``verdict`` is accepted for seam-signature parity and ignored — the
    engine recomputes scope from the authoritative file list (the same
    shared matcher, so the recomputation and the service's verdict
    always agree).
    """
    return PolicyContext(
        target_scope=tuple(glob for glob in (task.target_scope or ()) if isinstance(glob, str)),
        **_resolution_inputs(resolution),
        **_policy_inputs(task),
        evidence_commands=None,  # no structured coder evidence exists yet (OQ)
        auditor_confidence=None,  # no auditor on the T10 path — R7 n/a
        proposed_verdict=None,  # no auditor on the T10 path — R8 n/a
    )


def evaluate_audit(task: Task, resolution: TaskResolution, report: AuditReport) -> EvaluationResult:
    """Evaluate the audited resolution — pure engine over an assembled context."""
    return evaluate(build_audit_context(task, resolution, report))


def evaluate_submission(
    task: Task, resolution: TaskResolution, verdict: ScopeVerdict | None = None
) -> EvaluationResult:
    """Evaluate a coder submission (T10, Section 8.5) — same engine, coder context."""
    del verdict  # informational only; scope is recomputed (see the module docstring)
    return evaluate(build_submission_context(task, resolution))


__all__ = [
    "build_audit_context",
    "build_submission_context",
    "evaluate_audit",
    "evaluate_submission",
]
