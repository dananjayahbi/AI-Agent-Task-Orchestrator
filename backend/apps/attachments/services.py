"""Attachment write path — upload service (MT-1.11-03; Sections 9.2, 9.5, 9.9).

One transaction, one lock, documented order:

1. lock the task row (``select_for_update``) — the Section 9.5 counters
   (count, total bytes) are computed **under the lock** so concurrent
   uploads cannot overshoot the caps (MT-1.11-02 risk note);
2. run the MT-1.11-02 validation stage on the bytes — size, content
   sniffing, declared-type agreement — *before* anything is stored;
3. de-duplicate: same task + same sha256 maps to the existing live
   record (Sections 9.5, 16.3) — one stored object, one record;
4. store the bytes through the MT-1.11-01 abstraction under the
   content-addressed key;
5. create the record with ``processing_status = uploaded`` (FR-ATT-07);
6. after commit, invoke the pipeline enqueue seam (MT-1.12-01 completes
   it; today a documented no-op — MT-1.11-03 acceptance asks only that
   the seam exists and is exercised).

Recorded readings (Section 20.1 item 5):

* **De-duplication is per task, not global** — identical bytes attached
  to two tasks are two records sharing one stored object (the content
  key makes that cheap); MT-1.11-05's reference counting protects the
  shared object from premature deletion. Content-hash keys expose
  cross-task equality by design (de-duplication is a deliverable);
  access control stays per-record (MT-1.11-01 risk note).
* **Orphan window** — bytes land in storage inside the transaction but
  a rollback after the put leaves an unreferenced object (content-
  addressed, so it is harmless and self-healing on re-upload); the
  Section 9.9 retention job's orphan sweep (MT-1.11-05) is the designed
  cleanup, not an afterthought.
* **The enqueue seam runs post-commit** — a pipeline job must never
  observe a row that the upload transaction then rolls back.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.tasks.models import Task

from .models import TaskAttachment
from .storage import content_key, get_storage
from .validation import (
    ValidatedUpload,
    check_task_capacity,
    existing_attachment_for,
    validate_upload,
)


# The MT-1.11-03 pipeline hook: MT-1.12-01 replaces the process-wide
# implementation with a real Celery ``delay`` call. Invoked **after**
# the upload transaction commits (module docstring); always with the
# stored row's id.
def _default_enqueue(attachment_id: str) -> None:
    """The documented no-op seam body (MT-1.12-01 replaces it)."""


_enqueue_seam: Callable[[str], None] = _default_enqueue


def set_enqueue_seam(function: Callable[[str], None] | None) -> None:
    """Install (or reset with ``None``) the pipeline enqueue seam.

    Tests use this to exercise the seam (MT-1.11-03 acceptance);
    MT-1.12-01 uses it to wire the real worker job.
    """
    global _enqueue_seam
    _enqueue_seam = function if function is not None else _default_enqueue


def enqueue_processing(attachment_id: str) -> None:
    """Run the pipeline enqueue seam (today: documented no-op)."""
    _enqueue_seam(attachment_id)


@dataclass(frozen=True)
class UploadOutcome:
    """One accepted upload's result (the endpoint's response source)."""

    attachment: TaskAttachment
    deduplicated: bool  # True: mapped onto an existing record (9.5)


def _store_attachment(
    task: Task, validated: ValidatedUpload, data: bytes, *, uploaded_by: str | None
) -> TaskAttachment:
    """Put the bytes, then insert the record (status ``uploaded``; FR-ATT-07).

    Caller holds the task row lock. The put is idempotent (content
    addressing: same key, same bytes), so a retry after the recorded
    rollback window re-writes nothing new.
    """
    key = content_key(validated.sha256)
    get_storage().put(key, data)
    return TaskAttachment.objects.create(
        task=task,
        filename=validated.filename,
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        is_image=validated.is_image,
        storage_key=key,
        sha256=validated.sha256,
        uploaded_by=uploaded_by,
    )


def create_attachment(
    *,
    task_id: str,
    filename: str,
    declared_mime: str | None,
    data: bytes,
    uploaded_by: str | None,
) -> UploadOutcome:
    """Accept one multipart upload: validate, store, record (MT-1.11-03).

    ``task_id`` must already be boundary-validated and resolved by the
    view (``get_task_or_404``); this function locks the row, re-checks
    capacity under the lock, and writes. Rejections raise before any
    storage call: ``VALIDATION_ERROR`` (size/count/total), 415
    ``ATTACHMENT_UNSUPPORTED_FORMAT`` (sniffing), or the de-duplicated
    hit simply returns the existing record with no new bytes stored.
    """
    with transaction.atomic():
        locked_task = Task.objects.select_for_update().get(pk=task_id)

        validated = validate_upload(filename=filename, declared_mime=declared_mime, data=data)

        # De-duplication before capacity: a duplicate adds no record and
        # no bytes, so it can never hit a cap (Section 19 acceptance).
        duplicate = existing_attachment_for(locked_task, validated.sha256)
        if duplicate is not None:
            return UploadOutcome(attachment=duplicate, deduplicated=True)

        check_task_capacity(locked_task, validated.size_bytes)
        attachment = _store_attachment(locked_task, validated, data, uploaded_by=uploaded_by)

        # No event is emitted here: the Section 9.6 catalog carries no
        # "attachment.uploaded" value — the pipeline's stages emit
        # attachment.processing|ready|failed (WP-1.12). Recorded, not
        # silently skipped (Section 20.1 item 5).

    enqueue_processing(str(attachment.pk))
    return UploadOutcome(attachment=attachment, deduplicated=False)


def attachment_payload(attachment: TaskAttachment) -> dict[str, Any]:
    """The FR-ATT-03 descriptor shape (shared by upload and listing)."""
    return {
        "id": attachment.pk,
        "task_id": attachment.task_id,
        "filename": attachment.filename,
        "mime_type": attachment.mime_type,
        "size": attachment.size_bytes,
        "is_image": attachment.is_image,
        "processing_status": attachment.processing_status,
        "token_count": attachment.token_estimate,
        "short_description": attachment.description or None,
        "created_at": attachment.created_at,
    }


__all__ = [
    "UploadOutcome",
    "attachment_payload",
    "create_attachment",
    "enqueue_processing",
    "set_enqueue_seam",
]
