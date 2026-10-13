"""Deletion rules and the retention hook (MT-1.11-05; Sections 9.2, 9.5, 12.4, 16.3, 9.9).

Two entry points over one shared primitive:

* :func:`delete_attachment` — the API rule behind
  ``DELETE /attachments/{id}`` (Owner only; enforced by the view's
  permission classes). Section 16.3 resolves the Section 9.2 endpoint vs
  "never by user action on completed tasks" conservatively: on a
  **completed or archived** task the call is refused with the canonical
  409 ``TASK_STATE_CONFLICT`` (:class:`AttachmentOnImmutableTask`) whose
  message points at the retention path. On any earlier state the record
  is **soft-deleted** (``deleted_at`` stamped — MT-1.11-01's documented
  model addition) and the stored object is removed **only when no other
  live record references the same content key**.
* :func:`purge_archived_attachments` — the hook the Section 9.9 daily
  retention job (WP-1.7's beat wiring — scheduling is out of scope
  here) calls: attachments are retained until the task is archived plus
  the configurable grace period (Section 12.4; **OQ-10 default: 30
  days** — the documented default is used, never re-decided, per
  MT-1.11-05's out-of-scope note). Past the boundary the records are
  hard-deleted and their orphaned stored objects removed.

**Content-key reference counting** (the MT's sharp edge, risk note): a
content-addressed key may back several records (per-task de-duplication
in MT-1.11-02, and cross-task equality by design — MT-1.11-03's
recorded reading). Every removal path therefore asks
:func:`_key_still_referenced` before touching storage: a key with any
remaining **live** (not soft-deleted) record keeps its bytes. Soft-
deleted records no longer count as references — their bytes are already
gone or pending purge — but they also never *trigger* a delete, since
the API path only deletes the object when the count drops to zero.

**Derived data** (Section 9.5: "originals retained, derived data
re-creatable"): chunks, OCR text, summaries and captions may be dropped
while an original is retained. :func:`drop_derived_data` is the
standalone hook for that (a future storage-pressure or reprocessing
path calls it); the retention purge naturally removes derived data with
the record, and this function proves the two concerns are independent
(MT-1.11-05 acceptance).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.tasks.models import Task, TaskState

from .derived import delete_derived_artifacts
from .exceptions import AttachmentOnImmutableTask
from .models import AttachmentChunk, TaskAttachment
from .storage import get_storage


def _key_still_referenced(storage_key: str, *, exclude: TaskAttachment) -> bool:
    """Whether any **live** record other than *exclude* uses this key."""
    return (
        TaskAttachment.objects.filter(storage_key=storage_key, deleted_at__isnull=True)
        .exclude(pk=exclude.pk)
        .exists()
    )


@dataclass(frozen=True)
class DeletionOutcome:
    """One soft delete's result (the endpoint's response source)."""

    attachment: TaskAttachment
    object_removed: bool


def delete_attachment(attachment: TaskAttachment) -> DeletionOutcome:
    """Apply the Section 16.3 API deletion rule to one record.

    Raises ``AttachmentOnImmutableTask`` (409 ``TASK_STATE_CONFLICT``)
    when the task is completed or archived — the retention path owns the
    bytes there. Otherwise stamps ``deleted_at`` (soft delete, recorded
    model addition) and removes the stored object **iff** no other live
    record shares the content key (reference counting — the MT risk
    note). Idempotent in the NFR-12 sense: repeating the call on an
    already soft-deleted record is refused as unknown by the view (the
    listing and lookups exclude deleted rows), so no second storage
    decision can race the first.
    """
    task = attachment.task
    if task.state == TaskState.COMPLETED or task.archived_at is not None:
        raise AttachmentOnImmutableTask(
            f"Task {task.pk} is completed or archived; its attachments are "
            "retained until the archive grace period ends (Section 12.4) and "
            "purged by the retention job (Sections 9.9, 16.3)."
        )

    with transaction.atomic():
        locked = TaskAttachment.objects.select_for_update().get(pk=attachment.pk)
        if locked.deleted_at is not None:
            # A concurrent duplicate DELETE lost the race: report the
            # original outcome without a second storage decision.
            return DeletionOutcome(attachment=locked, object_removed=False)

        still_referenced = _key_still_referenced(locked.storage_key, exclude=locked)
        locked.deleted_at = timezone.now()
        locked.save(update_fields=["deleted_at"])

        # Derived artifacts are per-attachment (storage.py's recorded
        # design — no sharing, no refcount) and re-creatable (9.5), so
        # they are always removed with the soft delete (MT-1.12-02).
        delete_derived_artifacts(locked)

        if still_referenced:
            return DeletionOutcome(attachment=locked, object_removed=False)

        get_storage().delete(locked.storage_key)
        return DeletionOutcome(attachment=locked, object_removed=True)


# --- the retention hook (Section 9.9 daily job; OQ-10 default) ---------------


@dataclass(frozen=True)
class RetentionOutcome:
    """What one retention sweep removed (the job's log line)."""

    records_deleted: int
    objects_removed: int
    tasks_processed: int


def purge_archived_attachments(*, now: datetime | None = None) -> RetentionOutcome:
    """Hard-delete attachments of tasks archived beyond the grace period.

    Section 12.4: attachments are retained until the task is archived
    plus a configurable grace period; **OQ-10's default is 30 days**
    (``ATTACHMENT_RETENTION_GRACE_DAYS`` — the Section 9.10 group;
    MT-1.11-05: use the documented default, do not re-decide). The
    boundary is inclusive-at-retain: an attachment whose cutoff instant
    equals ``now`` is **not** yet purged (``archived_at + grace > now``
    retains) — the grace period is fully served before removal.

    Steps, all idempotent (a crashed sweep resumes cleanly):
    1. select archived tasks past the boundary;
    2. collect their **live** records' storage keys, then hard-delete
       **every** record of the task (live and soft-deleted — the
       soft-delete marker is bookkeeping that must not accumulate
       forever; its bytes were already removed at delete time when
       unreferenced);
    3. remove each key's object that no **live** record references
       (reference counting — shared keys survive).
    Orphaned objects not covered here (e.g. the upload rollback window
    of MT-1.11-03) are the Section 9.9 job's separate sweep; this hook
    handles exactly what its Section 12.4 rule names.
    """
    moment = now or timezone.now()
    grace_days = settings.ATTACHMENT_RETENTION_GRACE_DAYS
    cutoff = moment - timedelta(days=grace_days)

    records_deleted = 0
    objects_removed = 0
    tasks_processed = 0

    archived = Task.objects.filter(archived_at__isnull=False, archived_at__lt=cutoff)
    storage = get_storage()
    for task in archived.iterator():
        live = TaskAttachment.objects.filter(task=task, deleted_at__isnull=True)
        keys = list(live.values_list("storage_key", flat=True).distinct())
        attachments = list(TaskAttachment.objects.filter(task=task))
        deleted, _ = TaskAttachment.objects.filter(task=task).delete()
        records_deleted += deleted
        tasks_processed += 1
        # Per-attachment derived artifacts (normalized images — WP-1.12)
        # die with their records: no refcount, by construction.
        for attachment in attachments:
            objects_removed += delete_derived_artifacts(attachment)
        for key in keys:
            # Reference counting after the purge: a key shared with a
            # record outside this task (or a not-yet-purged soft delete
            # is irrelevant — soft deletes are not references) keeps its
            # bytes.
            if not TaskAttachment.objects.filter(storage_key=key).exists():
                storage.delete(key)
                objects_removed += 1

    return RetentionOutcome(
        records_deleted=records_deleted,
        objects_removed=objects_removed,
        tasks_processed=tasks_processed,
    )


# --- derived data (Section 9.5: re-creatable, droppable independently) -------


# The Section 7.2 derived columns; originals (storage_key, sha256, size,
# filename, mime) are never in this list (Section 9.5 retention intent).
# ``token_estimate``/``page_count`` are the two nullable numerics; the
# rest are blank-default text columns.
_DERIVED_TEXT_FIELDS: tuple[str, ...] = (
    "ocr_text",
    "extracted_markdown",
    "description",
    "layout_caption",
    "failure_detail",
)
_DERIVED_NULLABLE_FIELDS: tuple[str, ...] = ("token_estimate", "page_count")
_DERIVED_FIELDS: tuple[str, ...] = _DERIVED_TEXT_FIELDS + _DERIVED_NULLABLE_FIELDS


def drop_derived_data(attachment: TaskAttachment) -> TaskAttachment:
    """Clear every derived artefact, keeping the original intact (9.5).

    Derived data — the chunk rows (WP-1.12's table), the derived storage
    artifacts (normalized images, MT-1.12-02) and the Section 7.2
    derived columns — is re-creatable by the pipeline, so it may be
    dropped even when the original is retained — MT-1.11-05's
    acceptance, proven standalone here for the future storage-pressure/
    reprocessing paths. The record returns to a "re-creatable" shape:
    status is *not* touched (only the WP-1.12 pipeline owns
    ``processing_status`` transitions — Section 9.1 ownership).
    """
    for field in _DERIVED_TEXT_FIELDS:
        setattr(attachment, field, "")
    for field in _DERIVED_NULLABLE_FIELDS:
        setattr(attachment, field, None)
    attachment.save(update_fields=list(_DERIVED_FIELDS))
    AttachmentChunk.objects.filter(attachment=attachment).delete()
    delete_derived_artifacts(attachment)
    return attachment


__all__ = [
    "DeletionOutcome",
    "RetentionOutcome",
    "delete_attachment",
    "drop_derived_data",
    "purge_archived_attachments",
]
