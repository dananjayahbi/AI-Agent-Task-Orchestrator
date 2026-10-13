"""MT-1.12-01 — pipeline entry: checksum, type re-detection, dispatch, idempotence.

Run with ``pytest backend/tests/attachments/test_pipeline_entry.py -v``.

Proves the entry stage's acceptance against the real task:

* an upload's seam reaches the worker task (the real seam body is the
  Celery job; the unit layer's documented default stays a no-op);
* checksum mismatch / type disagreement fail the attachment with a
  human-readable reason **without running format stages**;
* status moves ``uploaded → processing`` with exactly one
  ``attachment.processing`` event written in-transaction, then exactly
  one terminal event;
* re-delivery of the same job is idempotent — no second processing
  event, no duplicated derived data;
* dispatch routes images / PDF / DOCX-Markdown by re-detected content.

The synchronous invocation used throughout (documented for the whole
WP): ``process_attachment_task.apply(args=[attachment_id])`` — the real
task body, eagerly, no broker (also what ``test_sample_corpus.py`` uses
with the seam installed as ``lambda id: task.apply(...)``).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.attachments import pipeline
from apps.attachments.errors import PermanentPipelineError
from apps.attachments.models import ProcessingStatus, TaskAttachment
from apps.attachments.pipeline import (
    enqueue_attachment_job,
    install_pipeline_enqueue_seam,
    process_attachment_task,
    run_pipeline,
    stage_for,
)
from apps.attachments.pipeline_documents import process_document
from apps.attachments.pipeline_images import process_image
from apps.attachments.pipeline_pdf import process_pdf
from apps.attachments.retention import delete_attachment
from apps.attachments.services import create_attachment, set_enqueue_seam
from apps.attachments.storage import content_key, get_storage, hash_bytes
from apps.attachments.validation import DOCX_MIME
from apps.events.models import Event

from .helpers import MARKDOWN_BYTES, PDF_BYTES, make_project, make_task

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(tmp_path: Any) -> Any:
    """Uploads and derived artifacts land in an isolated media root."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture
def task() -> Any:
    """One pending task in an active project."""
    return make_task(make_project())


def _upload(task: Any, data: bytes, name: str, mime: str | None = None) -> TaskAttachment:
    """Accept one upload through the real service path (seam: unit default)."""
    outcome = create_attachment(
        task_id=task.pk,
        filename=name,
        declared_mime=mime,
        data=data,
        uploaded_by="wp12-tests",
    )
    assert not outcome.deduplicated
    return outcome.attachment


def _events(event_type: str, task: Any) -> list[Event]:
    return list(Event.objects.filter(type=event_type, task_id=task.pk))


# --- the enqueue seam (MT-1.11-03 completed; Section 9.9 "on upload") -------


def test_enqueue_seam_body_hands_the_job_to_the_worker_task() -> None:
    """``enqueue_attachment_job`` is the real seam: one Celery ``delay``."""
    with patch.object(process_attachment_task, "delay") as delayed:
        enqueue_attachment_job("att-123")
    delayed.assert_called_once_with("att-123")


def test_unit_layer_keeps_the_no_op_seam_by_default(task: Any) -> None:
    """Section 18 unit layer runs with no broker: the install is a no-op
    and an upload without an explicitly installed seam never touches
    Celery (the documented MT-1.12-01 test-settings gate)."""
    assert install_pipeline_enqueue_seam() is False
    with patch.object(process_attachment_task, "delay") as delayed:
        _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    delayed.assert_not_called()


def test_installed_seam_fires_on_upload(task: Any) -> None:
    """With the seam installed, an upload enqueues the pipeline job once."""
    seen: list[str] = []
    set_enqueue_seam(lambda attachment_id: seen.append(attachment_id))
    try:
        attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    finally:
        set_enqueue_seam(None)
    assert seen == [str(attachment.pk)]


# --- dispatch table (MT-1.12-01 scope: stages registered here, owned by 02/03/04) -


def test_dispatch_routes_each_family_to_its_stage() -> None:
    """Content type decides the stage — never the filename (Section 9.5)."""
    assert stage_for("image/png") is process_image
    assert stage_for("image/jpeg") is process_image
    assert stage_for("image/webp") is process_image
    assert stage_for("application/pdf") is process_pdf
    assert stage_for(DOCX_MIME) is process_document
    assert stage_for("text/markdown") is process_document
    assert stage_for("text/plain") is process_document


def test_dispatch_rejects_anything_off_the_allowlist() -> None:
    """Off-allowlist types are a permanent failure with a clear reason."""
    with pytest.raises(PermanentPipelineError) as caught:
        stage_for("application/x-msdownload")
    assert "allowlist" in caught.value.reason


# --- status + events on a full run (Sections 9.5, 9.6; FR-ATT-07) -----------


def test_run_moves_uploaded_to_processing_then_ready_with_one_event_each(
    task: Any,
) -> None:
    """Exactly one ``attachment.processing`` and one ``attachment.ready``,
    both written in-transaction with the change (Section 20.4 item 6)."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    assert attachment.processing_status == ProcessingStatus.UPLOADED

    result = process_attachment_task.apply(args=[str(attachment.pk)])
    assert result.get() == "ready"

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.READY
    assert row.failure_detail == ""
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.ready", task)) == 1
    assert _events("attachment.failed", task) == []


def test_processing_event_carries_the_attachment_id(task: Any) -> None:
    """The event envelope's data names the attachment — ids, no content."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    process_attachment_task.apply(args=[str(attachment.pk)])
    event = _events("attachment.processing", task)[0]
    assert event.data == {"attachment_id": str(attachment.pk)}
    assert event.actor_type == "system"
    assert event.actor_ref == "attachment-pipeline"


# --- integrity: checksum and type re-detection (Section 9.5 stage 1) --------


def test_checksum_mismatch_fails_without_running_stages(task: Any, media_root: Any) -> None:
    """Corrupted stored object → ``failed`` with a human-readable reason;
    the format stages never run (MT-1.12-01 risk note)."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    # Corrupt the stored bytes behind the record's back (delete first:
    # the content-addressed put is a no-op on an existing key).
    get_storage().delete(attachment.storage_key)
    get_storage().put(attachment.storage_key, MARKDOWN_BYTES + b" tampered")

    result = process_attachment_task.apply(args=[str(attachment.pk)])
    assert result.get() == "failed"

    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert row.processing_status == ProcessingStatus.FAILED
    assert "checksum" in row.failure_detail
    assert row.extracted_markdown == ""  # stages did not run
    assert row.chunks.count() == 0
    # The event pair still holds: processing on entry, failed at the end.
    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.failed", task)) == 1


def test_missing_stored_object_fails_with_a_clear_reason(task: Any, media_root: Any) -> None:
    """A record pointing at nothing is an integrity failure, not a crash."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    get_storage().delete(attachment.storage_key)

    result = process_attachment_task.apply(args=[str(attachment.pk)])
    assert result.get() == "failed"
    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert "missing" in row.failure_detail


def test_type_disagreement_fails_the_attachment(task: Any) -> None:
    """Content re-detecting differently from the record is an integrity
    signal — fail with the disagreement spelled out, process nothing."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    # Swap the stored object to PDF bytes and re-stamp the digest, so
    # only the *type* disagrees (checksum alone would mask it). The
    # content-addressed put is a no-op on an existing key — replace it.
    get_storage().delete(attachment.storage_key)
    get_storage().put(attachment.storage_key, PDF_BYTES)
    TaskAttachment.objects.filter(pk=attachment.pk).update(sha256=hash_bytes(PDF_BYTES))

    result = process_attachment_task.apply(args=[str(attachment.pk)])
    assert result.get() == "failed"
    row = TaskAttachment.objects.get(pk=attachment.pk)
    assert "application/pdf" in row.failure_detail
    assert "text/markdown" in row.failure_detail
    assert row.extracted_markdown == ""


# --- idempotent re-entry (MT-1.12-01 acceptance) -----------------------------


def test_re_delivery_neither_reprocesses_nor_duplicates_events(task: Any) -> None:
    """Same job delivered twice: the second run is a no-op — no duplicate
    processing event, no derived data churn (Section 9.5 dedup)."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    assert process_attachment_task.apply(args=[str(attachment.pk)]).get() == "ready"
    chunks_first = attachment.chunks.count()

    assert run_pipeline(str(attachment.pk)) == "skipped"
    assert process_attachment_task.apply(args=[str(attachment.pk)]).get() == "skipped"

    assert len(_events("attachment.processing", task)) == 1
    assert len(_events("attachment.ready", task)) == 1
    assert TaskAttachment.objects.get(pk=attachment.pk).chunks.count() == chunks_first


def test_soft_deleted_attachment_is_never_processed(task: Any) -> None:
    """Deletion wins: a late job for a deleted row runs nothing (07 CAS)."""
    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    delete_attachment(attachment)

    assert run_pipeline(str(attachment.pk)) == "gone"
    assert _events("attachment.processing", task) == []


def test_unknown_attachment_id_is_a_quiet_noop() -> None:
    """A stale id (row purged by retention) de-duplicates silently."""
    assert run_pipeline("00000000-0000-0000-0000-000000000000") == "gone"


def test_storage_key_shape_used_by_the_entry_is_content_addressed(
    task: Any, media_root: Any
) -> None:
    """Guard the entry's premise: the record's key resolves to bytes whose
    digest is the record's sha256 (the integrity check's happy path)."""
    import hashlib

    attachment = _upload(task, MARKDOWN_BYTES, "notes.md", "text/markdown")
    stored = get_storage().get(attachment.storage_key)
    assert hashlib.sha256(stored).hexdigest() == attachment.sha256
    assert attachment.storage_key == content_key(attachment.sha256)
    assert install_pipeline_enqueue_seam() is False


def test_pipeline_module_exports_the_task_for_autodiscovery() -> None:
    """``apps.attachments.tasks`` (the autodiscovery shim) exposes the
    same task object the pipeline defines (Section 9.9 wiring)."""
    from apps.attachments import tasks as attachment_tasks

    assert attachment_tasks.process_attachment_task is process_attachment_task
    assert pipeline.process_attachment_task.name == "attachments.process_attachment"
