"""The audit write path and the report listing — Sections 7.2/9.2/9.4/10.5.

Layers, one module (the ``services.resolutions`` structure, WP-3.3 side):

* :func:`submit_audit_verdict` (MT-3.3-05) — the whole verdict in
  **one transaction**: lock the task, scope check, state check, the
  shared fencing gate (auditor lease owner), the independence re-check
  (MT-3.3-02's function, not a second implementation), store the Audit
  Report, consult the decision seam, then dispatch exactly one of
  T13/T14 through the state machine (Section 9.1: ``tasks`` owns all
  state changes — this service never writes ``state``).
* the listing query + cursor helpers (MT-3.3-04) — reverse-chronological
  per-task paging per docs/plan/conventions/pagination.md.

Recorded readings (Section 20.1 item 5):

* **The endpoint never approves** (invariant 8.3.4): the trigger choice
  comes from :func:`apps.audit.decision.resolve_audit_decision`, the
  same pure seam the T13/T14 rows re-consult — fail-closed to escalate
  until MT-3.4-07 installs the engine, so today every accepted verdict
  lands T14 (``in_human_review`` + an enumerated Section 8.4 reason)
  and T13 stays structurally unreachable without an approving hook.
* **One report row per accepted POST** — created *before* the dispatch
  inside the same transaction, so a refused transition rolls the report
  away with it (Section 8.2 rule 2). A replay of the same
  ``Idempotency-Key`` never reaches here (the view's stored-outcome
  replay answers first); a retry *without* a key dies at the state or
  fencing gate, never double-writing a report or a transition
  (Section 9.2 idempotency rule).
* **Independence is re-proven at verdict time** with the same function
  the T11 guard ran — a lease whose session could claim is already
  independent by construction, and the re-check keeps a direct
  dispatcher caller honest (MT-3.3-02's "verdict-time recheck" note).
* **``acceptance_criteria_results`` rides ``evidence``** when the
  client sends the Section 10.5 sibling key: §7.2 gives the report no
  column for it (the field list is closed — Section 20.5), and dropping
  what the auditor sent would lose FR-AUD-02 evidence — so the service
  nests it inside the schemaless ``evidence`` JSON. The §10.5 *evidence*
  object itself round-trips verbatim (the nest only appears when the
  sibling was supplied); flagged as an OQ in the WP changelog.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.core.pagination import decode_str_cursor, encode_cursor
from apps.leases.fencing import require_current_lease
from apps.tasks.exceptions import TaskNotFound, TaskStateConflict
from apps.tasks.models import Task, TaskState
from apps.tasks.services.ids import ensure_valid_task_id
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.transitions_submission import ensure_submission_wired

from .decision import AuditDecision, resolve_audit_decision
from .independence import assert_auditor_independent
from .models import AuditReport
from .transitions import ensure_audit_wired

# Section 10.5 verdict enum — mirrored at the model and serializer layers.
VERDICT_VALUES: tuple[str, ...] = ("pass", "flag_risk", "fail")


@dataclass(frozen=True)
class VerdictSubmission:
    """One accepted verdict's outcome (the endpoint's response source)."""

    report: AuditReport
    task: Task  # the post-transition row the dispatcher returned
    trigger: str  # which Section 8.2 row fired ("audit_verdict_escalated", ...)
    decision: AuditDecision  # the seam's verdict the trigger choice read


def submit_audit_verdict(
    task_id: str,
    *,
    session_id: str,
    lease_generation: int,
    verdict: str,
    confidence: int,
    notes: str,
    evidence: dict[str, Any],
    acceptance_criteria_results: list[dict[str, Any]] | None = None,
    caller_project_id: str | None = None,
) -> VerdictSubmission:
    """Store the auditor's proposal and fire exactly one Section 8.2 row.

    Lock, fencing, independence, store, seam, dispatch — all in one
    transaction (Section 8.2 rule 2), so a refused transition never
    leaves an Audit Report row behind.
    """
    ensure_valid_task_id(task_id)
    ensure_submission_wired()  # T7-T10 rows (the verdict's from-state came from one)
    ensure_audit_wired()  # T13/T14 rows (lazy WP-1.6-style wiring)

    stored_evidence = dict(evidence)
    if acceptance_criteria_results is not None:
        # §7.2 has no column for the sibling input (see the module docstring).
        stored_evidence["acceptance_criteria_results"] = acceptance_criteria_results

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.state != TaskState.TO_BE_AUDITED:
            # Cheap early refusal: only an awaiting-audit row accepts a
            # verdict (the dispatcher would answer the same 409).
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.state}, not to_be_audited (no verdict accepted)",
            )
        # The shared gate under the row lock (no second implementation —
        # LEASE_EXPIRED 409 / LEASE_NOT_OWNED 403): only the current
        # auditor lease owner may submit (Section 12.2 "Submit verdict").
        require_current_lease(task, session_id=session_id, lease_generation=lease_generation)

        # MT-3.3-02's re-check at verdict time — the same function, not a
        # second implementation; also returns the current-attempt
        # resolution the report attaches to.
        resolution = assert_auditor_independent(
            task,
            auditor_session_id=session_id,
            auditor_label=str(task.worker_agent_id or session_id),
        )

        report = AuditReport.objects.create(
            task=task,
            resolution=resolution,
            auditor_session_id=session_id,
            evidence=stored_evidence,
            confidence=confidence,
            auditor_notes=notes,
            proposed_verdict=verdict,
        )

        # MT-3.3-05: the endpoint never approves — the seam decides
        # (fail-closed escalate until MT-3.4-07), and the row re-checks.
        decision = resolve_audit_decision(task, resolution, report)
        trigger = "audit_verdict_pass" if decision.approve else "audit_verdict_escalated"
        updated = dispatch_transition(
            task_id=task.pk,
            trigger=trigger,
            actor_type="agent",
            actor_ref=session_id,
            # An escalation records *why* on the history row (the Section
            # 8.4 member, like T8/T10); the approve branch keeps the row's
            # own catalog code (audit_passed).
            reason_code=None if decision.approve else decision.reason,
            extra={
                "session_id": session_id,
                "lease_generation": lease_generation,
                "resolution": resolution,
                "report": report,
            },
        )
        return VerdictSubmission(
            report=report,
            task=updated,
            trigger=trigger,
            decision=decision,
        )


# --- reading the stored reports (Section 9.2 GET /tasks/{id}/audit-reports) ---

# The canonical five-field §7.2 shape the API returns (field for field).
REPORT_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "task_id",
        "resolution_id",
        "auditor_session_id",
        "evidence",
        "confidence",
        "auditor_notes",
        "proposed_verdict",
        "policy_decision",
        "policy_rule_results",
        "created_at",
    }
)


def report_payload(report: AuditReport) -> dict[str, Any]:
    """Build the API shape of one stored row (§7.2, field for field)."""
    return {
        "id": report.pk,
        "task_id": report.task_id,
        "resolution_id": report.resolution_id,
        "auditor_session_id": report.auditor_session_id,
        "evidence": report.evidence,
        "confidence": report.confidence,
        "auditor_notes": report.auditor_notes,
        "proposed_verdict": report.proposed_verdict,
        "policy_decision": report.policy_decision,
        "policy_rule_results": report.policy_rule_results,
        "created_at": report.created_at,
    }


def report_or_404(report_id: UUID | str) -> AuditReport:
    """One report by id — unknown ids answer the documented mapping.

    No report-scoped catalog code exists (Section 9.2), so the generic
    DRF ``NotFound`` flows through the envelope handler's recorded
    ``VALIDATION_ERROR`` mapping (see ``apps.core.exceptions``). Kept
    for the review panel's single-report reads (WP-4.8) and tests.
    """
    try:
        return AuditReport.objects.get(pk=report_id)
    except (AuditReport.DoesNotExist, ValueError, ValidationError):
        raise NotFound("Audit report does not exist.") from None


class ReportCursorKey(NamedTuple):
    """The composite sort key a listing cursor resumes from (opaque outside)."""

    created_at: datetime
    report_id: UUID


def report_list_queryset(task: Task) -> QuerySet[AuditReport]:
    """One task's reports, **newest first** (the listing-order choice).

    MT-3.3-04 asks for *newest first or by attempt — pick one, document
    it*: newest first (``-created_at``, ``-id`` tie-break) matches the
    resolution listing and puts the freshest verdict on the review
    panel's first page regardless of which attempt or retry produced it.
    """
    return AuditReport.objects.filter(task=task).order_by("-created_at", "-id")


def encode_report_cursor(report: AuditReport) -> str:
    """Opaque cursor carrying the full sort key of *report* (rule 1)."""
    material = f"{report.created_at.isoformat()}|{report.pk}"
    return encode_cursor(material)


def decode_report_cursor(raw: str | None) -> ReportCursorKey | None:
    """Parse a cursor back into its sort key; ``None`` = first page.

    A cursor that does not decode into this endpoint's exact key shape
    answers ``VALIDATION_ERROR`` (pagination.md rule 1 — opaque cursors,
    a mangled one is a client error from the closed catalog).
    """
    material = decode_str_cursor(raw)
    if material is None:
        return None
    parts = material.split("|")
    if len(parts) != 2:
        raise ValidationError("Invalid cursor.")
    timestamp_text, report_id_text = parts
    try:
        created_at = datetime.fromisoformat(timestamp_text)
        report_id = UUID(report_id_text)
    except ValueError as exc:
        raise ValidationError("Invalid cursor.") from exc
    return ReportCursorKey(created_at=created_at, report_id=report_id)


def filter_beyond_cursor(
    queryset: QuerySet[AuditReport], cursor: ReportCursorKey
) -> QuerySet[AuditReport]:
    """Keyset continuation: rows strictly *before* the cursor (newest-first)."""
    return queryset.filter(
        Q(created_at__lt=cursor.created_at)
        | Q(created_at=cursor.created_at, id__lt=cursor.report_id)
    )


def report_page(
    task: Task, *, cursor: ReportCursorKey | None, page_size: int
) -> tuple[list[AuditReport], str | None]:
    """One page of *task*'s reports plus its ``next_cursor``.

    Fetch-one-lookahead (pagination.md): ``next_cursor`` is ``None``
    exactly when the page is the last one.
    """
    queryset = report_list_queryset(task)
    if cursor is not None:
        queryset = filter_beyond_cursor(queryset, cursor)
    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_report_cursor(rows[-1]) if has_more and rows else None
    return rows, next_cursor


def latest_report_or_none(task: Task) -> AuditReport | None:
    """The newest report for *task* (tests and the review panel's preview)."""
    return report_list_queryset(task).first()


__all__ = [
    "REPORT_FIELDS",
    "ReportCursorKey",
    "VERDICT_VALUES",
    "VerdictSubmission",
    "decode_report_cursor",
    "encode_report_cursor",
    "filter_beyond_cursor",
    "latest_report_or_none",
    "report_list_queryset",
    "report_or_404",
    "report_page",
    "report_payload",
    "submit_audit_verdict",
]
