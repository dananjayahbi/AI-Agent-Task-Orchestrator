"""Attachment serializers — Sections 7.2/9.2/9.5; FR-ATT-03/07.

* ``AttachmentSerializer`` — the descriptor the API returns (the shape
  FR-ATT-03 fixes for task payloads and the web/mobile lists): ``id``,
  ``task_id``, ``filename``, ``mime_type``, ``size``, ``is_image``,
  ``processing_status``, plus FR-ATT-03's ``token_count`` and
  ``short_description`` — **null until the WP-1.12 pipeline fills them**
  (the field shape is locked now so WP-1.4 task serialization and the
  clients reuse it — MT-1.11-04's risk note).
* ``AttachmentListEnvelopeSerializer`` / ``AttachmentListQuerySerializer``
  — pagination.md's exact ``{results, next_cursor}`` contract with the
  canonical ``cursor``/``page_size`` parameters (MT-0.5-04).
* ``AttachmentDeleteSerializer`` — MT-1.11-05's DELETE response (the
  soft-deleted record's identity and marker).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE

from .models import TaskAttachment
from .services import attachment_payload


class AttachmentSerializer(serializers.Serializer[Any]):
    """One attachment descriptor — FR-ATT-03's field shape, locked here.

    One documented addition by WP-1.12 (MT-1.12-07, FR-ATT-07
    "visible"): ``failure_reason`` carries the human-readable permanent-
    failure reason when ``processing_status`` is ``failed``, null
    otherwise — schema follow-up flagged for the OpenAPI owner.
    """

    id = serializers.UUIDField(help_text="Server-generated row identity (Section 7.2).")
    task_id = serializers.CharField(help_text="The owning task (Section 7.2).")
    filename = serializers.CharField(help_text="Client filename, path components stripped.")
    mime_type = serializers.CharField(
        help_text="The sniffed content type (Section 9.5 — never the declared one)."
    )
    size = serializers.IntegerField(help_text="Stored size in bytes (Section 7.2 ``size_bytes``).")
    is_image = serializers.BooleanField(
        help_text="Whether the sniffed type is an image — drives the pipeline split (9.5)."
    )
    processing_status = serializers.CharField(
        help_text="FR-ATT-07 enum: uploaded | processing | ready | failed."
    )
    failure_reason = serializers.CharField(
        allow_null=True,
        help_text="Human-readable reason when processing_status is failed "
        "(FR-ATT-07 visible; Section 9.5 stage 5; null otherwise).",
    )
    token_count = serializers.IntegerField(
        allow_null=True,
        help_text="FR-ATT-03 token count — null until the WP-1.12 pipeline computes it.",
    )
    short_description = serializers.CharField(
        allow_null=True,
        help_text="FR-ATT-03 short description — null until the WP-1.12 pipeline produces it.",
    )
    created_at = serializers.DateTimeField(help_text="Server upload time (P7).")


class AttachmentListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = AttachmentSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class AttachmentListQuerySerializer(serializers.Serializer[Any]):
    """``GET /tasks/{id}/attachments`` query parameters (MT-1.11-04)."""

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor; valid "
        "only for this task's listing (pagination.md rule 1).",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values "
            "above the maximum are clamped — pagination.md documented "
            "defaults, same per-endpoint choice as the other list routes)."
        ),
    )


class AttachmentDeleteSerializer(serializers.Serializer[Any]):
    """MT-1.11-05's DELETE response — the soft-deleted record's marker."""

    id = serializers.UUIDField(help_text="The deleted attachment's identity.")
    task_id = serializers.CharField(help_text="The owning task.")
    deleted_at = serializers.DateTimeField(
        help_text="Server time of the soft delete (MT-1.11-05): the retention "
        "job (Section 9.9) owns the hard removal (Section 16.3)."
    )


def attachment_descriptor(attachment: TaskAttachment) -> dict[str, object]:
    """Build the API shape of one stored record (FR-ATT-03, locked)."""
    return attachment_payload(attachment)


__all__ = [
    "AttachmentDeleteSerializer",
    "AttachmentListEnvelopeSerializer",
    "AttachmentListQuerySerializer",
    "AttachmentSerializer",
    "attachment_descriptor",
]
