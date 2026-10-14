"""Attachment pipeline entry: integrity check, type detection, dispatch
(Section 9.5 stage 1; Section 9.9 "on upload, retry with backoff";
MT-1.12-01) — plus the retry wiring MT-1.12-07 places here.

One function per concern, composed by :func:`run_pipeline`:

1. :func:`begin_processing` — the ``uploaded→processing`` CAS with its
   single ``attachment.processing`` event (MT-1.12-01); a row already
   terminal is **de-duplicated**: re-delivery of the same job changes
   nothing and emits nothing (idempotent re-entry acceptance).
2. **Integrity** — the stored object is re-read and its sha256
   re-derived against the record; a mismatch (or a record that no
   longer sniffs to its recorded type) *fails the attachment with a
   human-readable reason* instead of processing it (MT-1.12-01 risk
   note: disagreement is a data-integrity signal — trust neither side
   silently).
3. **Dispatch** — re-detected content type → stage: images (02), PDF
   (03), DOCX/Markdown/plain (04). Detection is content-based, never
   the filename (Section 9.5 stage 1).
4. **Chunk + summarize** (05/06), then ``mark_ready`` (07).

Retry (MT-1.12-07, Section 9.9): the Celery task classifies failures —
permanent ones land ``failed`` at once (``run_pipeline`` catches them);
transient ones re-enter through :func:`_retry_or_fail`, which backs off
exponentially (``ATTACHMENT_RETRY_BACKOFF_SECONDS × 2^attempt``,
documented defaults) up to ``ATTACHMENT_RETRY_MAX_ATTEMPTS`` total
attempts and then lands ``failed`` with the reason. The seam is
deliberately one function so policy changes never touch the stages
(MT-1.12-01 risk note).

**Synchronous invocation** (tests, corpus runs — documented): the task
body executes locally without a broker via
``process_attachment_task.apply(args=[attachment_id])`` or, for retry
drills, ``_execute(task_stub, attachment_id)`` with a stub exposing
``request.retries`` and ``retry()`` — no Celery daemon required.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any, Final, Literal

from celery import shared_task
from django.conf import settings

from .chunking import ExtractionResult, persist_chunks
from .errors import PermanentPipelineError, TransientPipelineError, describe_exception
from .models import TaskAttachment
from .pipeline_documents import process_document
from .pipeline_images import process_image
from .pipeline_pdf import process_pdf
from .status import begin_processing, mark_failed, mark_ready
from .storage import get_storage, hash_bytes
from .summarize import apply_summary
from .validation import (
    ALLOWED_MIME_TYPES,
    DOCX_MIME,
    IMAGE_MIME_TYPES,
    TEXT_MIME_TYPES,
    sniff_mime,
    types_agree,
)

PDF_MIME: Final = "application/pdf"

#: One stage's call shape (MT-1.12-01 dispatch contract).
StageFn = Callable[..., ExtractionResult]

PipelineOutcome = Literal["ready", "failed", "skipped", "gone"]


def stage_for(mime: str) -> StageFn:
    """Map a re-detected content type to its MT-1.12-02/03/04 stage."""
    if mime in IMAGE_MIME_TYPES:
        return process_image
    if mime == PDF_MIME:
        return process_pdf
    if mime == DOCX_MIME or mime in TEXT_MIME_TYPES:
        return process_document
    raise PermanentPipelineError(
        f"content type {mime!r} is not in the Section 9.5 allowlist (unsupported for processing)"
    )


def run_pipeline(attachment_id: str) -> PipelineOutcome:
    """Section 17 instrumentation wrapper: time and record one pipeline run.

    Delegates to ``_run_pipeline_inner`` then records duration + outcome
    (``attachment_pipeline``). Transient exceptions still propagate to the
    retry seam unrecorded — they are not terminal, so counting them here would
    double-count a run that later lands ``ready``/``failed``.
    """
    from apps.core.metrics import record_pipeline

    start = time.monotonic()
    outcome = _run_pipeline_inner(attachment_id)
    record_pipeline(outcome, (time.monotonic() - start) * 1000.0)
    return outcome


def _run_pipeline_inner(attachment_id: str) -> PipelineOutcome:
    """Run every pipeline stage for one attachment; never raises transient.

    Transient failures propagate to the task's retry seam (MT-1.12-07);
    permanent ones are caught here, recorded through ``mark_failed``
    with their human-readable reason, and reported as ``"failed"``.
    """
    attachment = (
        TaskAttachment.objects.select_related("task")
        .filter(pk=attachment_id, deleted_at__isnull=True)
        .first()
    )
    if attachment is None:
        return "gone"
    if begin_processing(attachment_id) == "gone":
        # Terminal already (or deleted mid-lookup): idempotent re-entry
        # de-duplicates — no stages, no duplicate events (MT-1.12-01).
        return "skipped"

    deadline = time.monotonic() + settings.ATTACHMENT_PARSE_TIMEOUT_SECONDS
    try:
        try:
            data = get_storage().get(attachment.storage_key)
        except KeyError as exc:
            raise PermanentPipelineError(
                "the stored object referenced by this attachment is missing "
                "from storage (integrity failure)"
            ) from exc
        except OSError as exc:
            raise TransientPipelineError(
                "storage read failed (transient I/O; retried with backoff)"
            ) from exc

        # Stage 1, verbatim: verify checksum, detect type from content.
        if hash_bytes(data) != attachment.sha256:
            raise PermanentPipelineError(
                "stored object checksum does not match the record "
                "(data integrity failure; not processed)"
            )
        sniffed = sniff_mime(data)
        if sniffed is None or sniffed not in ALLOWED_MIME_TYPES:
            raise PermanentPipelineError(
                "stored content no longer matches any Section 9.5 allowlisted "
                "type (integrity failure; not processed)"
            )
        if not types_agree(attachment.mime_type, sniffed):
            raise PermanentPipelineError(
                f"content re-detects as {sniffed!r} but the record says "
                f"{attachment.mime_type!r} (data integrity failure; not processed)"
            )

        stage = stage_for(sniffed)
        result = stage(attachment, data, deadline=deadline)
        chunks = persist_chunks(attachment, result)
        apply_summary(attachment, chunks)
        mark_ready(
            attachment_id,
            token_count=attachment.token_estimate,
            page_count=attachment.page_count,
        )
        return "ready"
    except PermanentPipelineError as exc:
        mark_failed(attachment_id, reason=exc.reason)
        return "failed"


def _retry_or_fail(task: Any, attachment_id: str, reason: str) -> str:
    """MT-1.12-07's retry seam: back off, or land ``failed`` with *reason*.

    Attempt accounting is ``task.request.retries + 1`` (the current try
    is already spent); the countdown doubles per attempt from the
    documented base. Reaching the cap writes the human-readable reason
    through :func:`mark_failed` — which CAS-guards the terminal
    transition, so a racing success still wins exactly once.
    """
    attempt = int(task.request.retries) + 1
    max_attempts = settings.ATTACHMENT_RETRY_MAX_ATTEMPTS
    if attempt >= max_attempts:
        mark_failed(
            attachment_id,
            reason=f"{reason} (retry limit: {max_attempts} attempts exhausted)",
        )
        return "failed"
    countdown = settings.ATTACHMENT_RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
    raise task.retry(exc=TransientPipelineError(reason), countdown=countdown)


def _execute(task: Any, attachment_id: str) -> str:
    """Task body: run the pipeline, classify anything unexpected (07)."""
    try:
        return run_pipeline(attachment_id)
    except TransientPipelineError as exc:
        return _retry_or_fail(task, attachment_id, exc.reason)
    except Exception as exc:  # unknown → transient, reason type-only (12.4)
        return _retry_or_fail(task, attachment_id, describe_exception(exc))


# Celery ships no type hints (pyproject's mypy override ignores its
# imports); the decorator is therefore Any — the functions it wraps are
# fully typed, which is where the correctness lives.
@shared_task(bind=True, name="attachments.process_attachment")  # type: ignore[untyped-decorator]
def process_attachment_task(self: Any, attachment_id: str) -> str:
    """The Section 9.9 attachment-pipeline job (registered "on upload")."""
    return _execute(self, attachment_id)


def enqueue_attachment_job(attachment_id: str) -> None:
    """The real MT-1.11-03 seam body: hand the job to the Celery worker.

    Installed process-wide by ``AttachmentsConfig.ready()`` outside the
    unit layer (the hermetic suite keeps the documented no-op seam and
    invokes the task synchronously — see this module's docstring).
    """
    process_attachment_task.delay(attachment_id)


def install_pipeline_enqueue_seam() -> bool:
    """Wire ``enqueue_processing`` → the worker task unless unit-testing.

    Returns whether the real seam was installed. The unit layer runs on
    ``apps.core.settings.test`` with **no broker** (Section 18), so the
    seam stays the WP-1.11 no-op default there and tests opt in
    explicitly via ``set_enqueue_seam`` — existing suites keep their
    exact assertions, while dev/prod/worker processes get the real job
    (Section 9.9 "on upload").
    """
    if os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".test"):
        return False
    from .services import set_enqueue_seam

    set_enqueue_seam(enqueue_attachment_job)
    return True


__all__ = [
    "enqueue_attachment_job",
    "install_pipeline_enqueue_seam",
    "process_attachment_task",
    "run_pipeline",
    "stage_for",
]
