"""Processing status state machine and event emission (Sections 9.5, 9.6; MT-1.12-01/07).

One linear machine over the four FR-ATT-07 statuses — ``uploaded →
processing → ready | failed`` — with exactly the Section 9.6 event
catalog values attached:

======================  =========================  =====================
Transition              Event, exactly once        Emission site
======================  =========================  =====================
``uploaded→processing`` ``attachment.processing``   :func:`begin_processing`
``processing→ready``    ``attachment.ready``        :func:`mark_ready`
``processing→failed``   ``attachment.failed``       :func:`mark_failed`
======================  =========================  =====================

Design rules (each from the plan, not from taste):

* **Compare-and-set, never read-modify-write** (MT-1.12-07 risk note):
  every terminal transition is a single conditional ``UPDATE`` guarded
  on the current status (``filter(processing_status=...)``), so two
  workers — or a late retry racing a manual outcome — cannot both win.
  The event row is written **inside the same transaction as the
  winning update** via the MT-1.9-02 ``write_event`` helper, so an
  event exists if and only if the transition committed (Section 9.6;
  Section 20.4 item 6): exactly one ``attachment.processing`` on entry
  and exactly one terminal event per attachment.
* **Terminal statuses are absorbing** (``ready``/``failed`` have no
  outgoing edges): a stale stage result arriving after completion loses
  the CAS and writes nothing — no overwrite, no duplicate event.
* **Soft-deleted rows never emit**: the CAS filters ``deleted_at``
  ``NULL``, so an attachment deleted mid-flight loses the race against
  the deletion and stays silent.
* **Events carry identifiers and reasons, never content**
  (Section 12.4): payloads hold ids, counts and our own truncated
  failure reason — no filenames is a choice, no text is a rule.
"""

from __future__ import annotations

from typing import Final, Literal

from django.db import transaction

from apps.events.models import EventType
from apps.events.services import write_event

from .models import ProcessingStatus, TaskAttachment

#: The Section 9.6 actor-ref for pipeline-emitted events (Section 12.5).
ACTOR_REF: Final = "attachment-pipeline"

#: Failure reasons are human sentences; cap the stored/emitted length so
#: a runaway message can never bloat a record or event (Section 12.4).
REASON_MAX_CHARS: Final = 1000

#: The complete legal-transition table — only the FR-ATT-07 line
#: (Section 20.3: "each state-machine transition gets its own test").
LEGAL_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    ProcessingStatus.UPLOADED: frozenset({ProcessingStatus.PROCESSING}),
    ProcessingStatus.PROCESSING: frozenset({ProcessingStatus.READY, ProcessingStatus.FAILED}),
    ProcessingStatus.READY: frozenset(),
    ProcessingStatus.FAILED: frozenset(),
}

BeginDecision = Literal["started", "resumed", "gone"]


class IllegalTransition(ValueError):
    """A transition outside the table above — programmer error."""


def assert_legal(source: str, target: str) -> None:
    """Raise :class:`IllegalTransition` unless ``source→target`` is legal.

    Kept as an explicit guard beside the CAS filters: the database is
    the enforcement point, this is the test-facing contract.
    """
    if target not in LEGAL_TRANSITIONS.get(source, frozenset()):
        raise IllegalTransition(
            f"{source!r} → {target!r} is not a Section 9.5/FR-ATT-07 transition"
        )


def _truncate(reason: str) -> str:
    return reason[:REASON_MAX_CHARS]


def begin_processing(attachment_id: str) -> BeginDecision:
    """Enter (or re-enter) ``processing``; emit the event **once**.

    Returns:

    * ``"started"`` — won the ``uploaded→processing`` CAS: the row lock
      serialised concurrent deliveries, so exactly one
      ``attachment.processing`` event exists (MT-1.12-01 idempotent
      re-entry).
    * ``"resumed"`` — the row was already ``processing`` (crash resume
      or duplicate delivery): stages may safely re-run (derived data is
      re-creatable, Section 9.5) but **no second event** is written.
    * ``"gone"`` — terminal (``ready``/``failed``) or soft-deleted:
      re-processing is de-duplicated away; nothing runs, nothing emits.
    """
    with transaction.atomic():
        row = (
            TaskAttachment.objects.select_for_update()
            .filter(pk=attachment_id, deleted_at__isnull=True)
            .first()
        )
        if row is None:
            return "gone"
        if row.processing_status == ProcessingStatus.UPLOADED:
            assert_legal(row.processing_status, ProcessingStatus.PROCESSING)
            row.processing_status = ProcessingStatus.PROCESSING
            row.failure_detail = ""
            row.save(update_fields=["processing_status", "failure_detail"])
            write_event(
                type=EventType.ATTACHMENT_PROCESSING,
                project_id=row.task.project_id,
                task_id=row.task_id,
                actor_type="system",
                actor_ref=ACTOR_REF,
                data={"attachment_id": str(row.pk)},
            )
            return "started"
        if row.processing_status == ProcessingStatus.PROCESSING:
            return "resumed"
        return "gone"


def mark_ready(
    attachment_id: str,
    *,
    token_count: int | None = None,
    page_count: int | None = None,
) -> bool:
    """CAS ``processing→ready``; ``True`` iff this caller won.

    Losing the CAS (a concurrent worker finished first, the row went
    terminal, or it was soft-deleted) writes nothing — the stale-result
    guard of MT-1.12-07.
    """
    with transaction.atomic():
        updated = TaskAttachment.objects.filter(
            pk=attachment_id,
            processing_status=ProcessingStatus.PROCESSING,
            deleted_at__isnull=True,
        ).update(processing_status=ProcessingStatus.READY)
        if not updated:
            return False
        row = TaskAttachment.objects.select_related("task").get(pk=attachment_id)
        write_event(
            type=EventType.ATTACHMENT_READY,
            project_id=row.task.project_id,
            task_id=row.task_id,
            actor_type="system",
            actor_ref=ACTOR_REF,
            data={
                "attachment_id": str(row.pk),
                "token_count": row.token_estimate if token_count is None else token_count,
                "page_count": row.page_count if page_count is None else page_count,
            },
        )
        return True


def mark_failed(attachment_id: str, *, reason: str) -> bool:
    """CAS ``processing→failed`` with a human-readable reason; ``True`` iff won.

    The reason is stored on the record (``failure_detail`` → the
    descriptor's ``failure_reason``, FR-ATT-07 "visible") and carried on
    the ``attachment.failed`` event — truncated, and never containing
    attachment content (Section 12.4).
    """
    clean = _truncate(reason.strip() or "attachment processing failed")
    with transaction.atomic():
        updated = TaskAttachment.objects.filter(
            pk=attachment_id,
            processing_status=ProcessingStatus.PROCESSING,
            deleted_at__isnull=True,
        ).update(processing_status=ProcessingStatus.FAILED, failure_detail=clean)
        if not updated:
            return False
        row = TaskAttachment.objects.select_related("task").get(pk=attachment_id)
        write_event(
            type=EventType.ATTACHMENT_FAILED,
            project_id=row.task.project_id,
            task_id=row.task_id,
            actor_type="system",
            actor_ref=ACTOR_REF,
            data={"attachment_id": str(row.pk), "reason": clean},
        )
        return True


__all__ = [
    "ACTOR_REF",
    "LEGAL_TRANSITIONS",
    "REASON_MAX_CHARS",
    "BeginDecision",
    "IllegalTransition",
    "assert_legal",
    "begin_processing",
    "mark_failed",
    "mark_ready",
]
