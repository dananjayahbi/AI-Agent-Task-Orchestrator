"""The Task Attachment entity — Section 7.2 (MT-1.11-01/03; FR-ATT-01/07).

Exactly the Section 7.2 "Task Attachment" field list — **none added,
dropped or renamed** — plus one documented addition:

* ``deleted_at`` (nullable) is **not** in the Section 7.2 table; it exists
  because MT-1.11-05 requires the API to *mark the record deleted* (soft
  delete) while the retention job owns the hard removal (Section 16.3:
  "deletion is by retention job, never by user action on completed
  tasks"). Recorded in the WP changelog as the one schema addition.

Layered decisions, each recorded so nothing is hidden:

* **``storage_key`` is content-addressed** (Sections 9.5, 16.3): the key
  is derived from the sha256 of the bytes by
  ``apps.attachments.storage.content_key`` — identical bytes map to one
  stored object (the foundation for MT-1.11-02 de-duplication). Access
  control is enforced per attachment **record**, never by key secrecy
  (MT-1.11-01 risk note).
* **``processing_status`` is frozen at the database** like ``state``/
  ``kind`` elsewhere (Section 7.4 double-constraint discipline): choices
  at the boundary **and** a CheckConstraint on the column. The four
  canonical FR-ATT-07 values, none added.
* **Derived-data columns** (``ocr_text``, ``extracted_markdown``,
  ``description``, ``layout_caption``, ``token_estimate``,
  ``page_count``, ``failure_detail``) exist now with no behavior —
  Section 7.2 defines the entity once; WP-1.12's pipeline fills them.
  They are nullable/blank until then (FR-ATT-03: the descriptor's token
  count and short description are null before ``ready``).
* **Listing index** — ``(task, created_at)`` serves MT-1.11-04's
  per-task descriptor listing (cursor pagination); ``task``+``sha256``
  serves MT-1.11-02's de-duplication probe.
* **Deleting a task is not supported** (Section 7.3) so the FK is
  PROTECT — an attachment is never orphaned by a task cascade.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.tasks.models import Task


class ProcessingStatus(models.TextChoices):
    """FR-ATT-07's four canonical values — none added."""

    UPLOADED = "uploaded", "uploaded"
    PROCESSING = "processing", "processing"
    READY = "ready", "ready"
    FAILED = "failed", "failed"


class TaskAttachment(models.Model):
    """One uploaded file attached to a task (Section 7.2)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated, never client-supplied.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # tasks are never deleted (Section 7.3); attachments follow
        related_name="attachments",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    filename = models.CharField(
        max_length=255,
        help_text="Original client filename, path components stripped (Section 9.5).",
    )
    mime_type = models.CharField(
        max_length=100,
        help_text="The **sniffed** content type (Section 9.5: sniffing, not extension).",
    )
    size_bytes = models.PositiveBigIntegerField(
        help_text="Stored byte count (Section 7.2).",
    )
    is_image = models.BooleanField(
        help_text="Derived from the sniffed type — drives the Section 9.5 pipeline split.",
    )
    storage_key = models.CharField(
        max_length=255,
        help_text="Content-addressed key (Sections 9.5/16.3): derived from sha256, "
        "identical bytes share one stored object.",
    )
    sha256 = models.CharField(
        max_length=64,
        help_text="Hex digest of the stored bytes — de-duplication identity (9.5).",
    )
    processing_status = models.CharField(
        max_length=16,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.UPLOADED,
        help_text="FR-ATT-07 enum (uploaded/processing/ready/failed); default "
        "uploaded — a new attachment starts there (MT-1.11-03).",
    )
    failure_detail = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable permanent-failure reason (Section 9.5 step 5; WP-1.12).",
    )
    ocr_text = models.TextField(
        blank=True,
        default="",
        help_text="OCR transcript (Section 9.5 stage 2; WP-1.12).",
    )
    extracted_markdown = models.TextField(
        blank=True,
        default="",
        help_text="Extracted document text (Section 9.5 stage 3; WP-1.12).",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Short description, AI or heuristic (Section 7.2; WP-1.12/1.13).",
    )
    layout_caption = models.TextField(
        blank=True,
        default="",
        help_text="Image layout caption (Section 9.5 stage 2; WP-1.13).",
    )
    token_estimate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Estimated tokens (Section 9.5 stage 3) — null until WP-1.12.",
    )
    page_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Page count for paginated documents (Section 9.5) — null until WP-1.12.",
    )
    uploaded_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Actor reference of the uploader (user id for an owner session) — "
        "the Section 9.6 actor-ref convention; agents cannot upload (9.2).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Server clock at upload (principle P7 — the API accepts no client time).",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Soft-delete marker (MT-1.11-05's documented addition to the 7.2 "
        "list): set by DELETE before completion; the retention job owns "
        "the hard removal (Section 16.3).",
    )

    class Meta:
        """Boundary + database constraints; the two per-task access paths."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(processing_status__in=ProcessingStatus.values),
                name="attachment_status_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(size_bytes__gte=1),
                name="attachment_size_positive",
            ),
        ]
        indexes = [
            # MT-1.11-04's per-task descriptor listing (cursor pagination).
            models.Index(fields=["task", "created_at"], name="attachment_task_created"),
            # MT-1.11-02's de-duplication probe: same task, same bytes.
            models.Index(fields=["task", "sha256"], name="attachment_task_sha256"),
        ]

    def __str__(self) -> str:
        """Identify the row as task, filename and status."""
        return f"{self.task_id}: {self.filename} ({self.processing_status})"


class AttachmentChunk(models.Model):
    """One derived page/chunk of extracted text (Section 19 WP-1.12 deliverable).

    Exactly the MT-1.12-05 field list — sequence position, page number
    (when page-based), text, estimated token count — plus the two
    constraints that make the derived data trustworthy:

    * ``unique (attachment, sequence)`` — the ordering key is a
      per-attachment dense position, so a re-run replaces the derived
      set (delete + insert, Section 9.5 "re-creatable") and a
      concurrent duplicate run cannot interleave two half-sets silently
      (the loser's insert hits the constraint and retries as
      transient);
    * ``page_number ≥ 1`` when present — pages are 1-based, so
      ``page_number``/``total_pages`` derivability (Section 9.5
      pagination data, MT-1.12-05 acceptance) holds by construction.

    ``page_number`` is ``NULL`` for the token-bounded path (DOCX,
    Markdown, plain text — Section 9.5 "pages **or** token-bounded
    chunks") and set for the page-oriented path (PDF, image OCR).
    """

    attachment = models.ForeignKey(
        TaskAttachment,
        on_delete=models.CASCADE,  # derived data dies with its record (Section 9.5)
        related_name="chunks",
        help_text="Owning attachment; chunks are derived, re-creatable data.",
    )
    sequence = models.PositiveIntegerField(
        help_text="Dense 0-based position across the attachment's whole extraction."
    )
    page_number = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="1-based page number for page-oriented outputs; null for "
        "token-bounded-only documents (Section 9.5).",
    )
    text = models.TextField(
        help_text="The chunk's extracted text (sensitive content — Section 12.4; never logged).",
    )
    token_estimate = models.PositiveIntegerField(
        help_text="Deterministic token estimate for this chunk (Section 9.5; "
        "MT-1.12-05's documented estimator).",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attachment", "sequence"],
                name="attachment_chunk_sequence_unique",
            ),
            models.CheckConstraint(
                condition=models.Q(page_number__isnull=True) | models.Q(page_number__gte=1),
                name="attachment_chunk_page_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(token_estimate__gte=0),
                name="attachment_chunk_tokens_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        """Identify the row as attachment, sequence and page."""
        page = f" p{self.page_number}" if self.page_number is not None else ""
        return f"{self.attachment_id} #{self.sequence}{page}"
