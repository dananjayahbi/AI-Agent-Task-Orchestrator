"""Attachment listing query + cursor helpers (MT-1.11-04; pagination.md).

One task's descriptors, newest first: ``(-created_at, -id)`` — the
server clock leads and the UUID primary key breaks ties
deterministically (pagination.md rule 2's default shape; the same
composite the checkpoint listing uses). The composite cursor carries
both halves, so paging never skips or repeats a row.

The ``id`` half of the sort also satisfies MT-1.11-04's "ordering
stable (by id)": the tiebreak *is* the id, in its generation-stable
UUID form (Section 7.3 — UUIDs compare consistently on every backend,
unlike the task-id strings the pagination doc warns about).

Soft-deleted records (MT-1.11-05) are excluded from every listing: the
API surface shows live attachments only.
"""

from __future__ import annotations

from datetime import datetime
from typing import NamedTuple
from uuid import UUID

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from apps.core.pagination import decode_str_cursor, encode_cursor
from apps.tasks.models import Task

from .models import TaskAttachment


class AttachmentCursorKey(NamedTuple):
    """The composite sort key a listing cursor resumes from (opaque outside)."""

    created_at: datetime  # server clock (P7) — the primary sort column
    attachment_id: UUID  # stable tiebreak for identical timestamps


def attachment_list_queryset(task: Task) -> QuerySet[TaskAttachment]:
    """One task's live attachments, newest first (Section 13.2 feed order)."""
    return TaskAttachment.objects.filter(task=task, deleted_at__isnull=True).order_by(
        "-created_at", "-id"
    )


def encode_attachment_cursor(attachment: TaskAttachment) -> str:
    """Opaque cursor carrying the full sort key of *attachment* (rule 1)."""
    material = f"{attachment.created_at.isoformat()}|{attachment.pk}"
    return encode_cursor(material)


def decode_attachment_cursor(raw: str | None) -> AttachmentCursorKey | None:
    """Parse a cursor back into its sort key; ``None`` = first page.

    A cursor that does not decode into this endpoint's exact key shape
    (two parts, a parseable instant, a valid UUID) answers
    ``VALIDATION_ERROR`` — cursors are opaque, and a mangled one is a
    client error from the closed catalog (rule 1).
    """
    material = decode_str_cursor(raw)
    if material is None:
        return None
    parts = material.split("|")
    if len(parts) != 2:
        raise ValidationError("Invalid cursor.")
    try:
        created_at = datetime.fromisoformat(parts[0])
        attachment_id = UUID(parts[1])
    except ValueError as exc:
        raise ValidationError("Invalid cursor.") from exc
    return AttachmentCursorKey(created_at=created_at, attachment_id=attachment_id)


def filter_beyond_cursor(
    queryset: QuerySet[TaskAttachment], cursor: AttachmentCursorKey
) -> QuerySet[TaskAttachment]:
    """Advance *queryset* past *cursor* under the ``(-created_at, -id)`` sort."""
    from django.db.models import Q

    return queryset.filter(
        Q(created_at__lt=cursor.created_at)
        | (Q(created_at=cursor.created_at) & Q(pk__lt=cursor.attachment_id))
    )


def attachment_page(
    task: Task, *, cursor: AttachmentCursorKey | None, page_size: int
) -> tuple[list[TaskAttachment], str | None]:
    """One page of *task*'s descriptors plus its ``next_cursor``.

    Fetch-one-lookahead (pagination.md): ``next_cursor`` is ``None``
    exactly when the page is the last one — clients stop on that signal
    alone.
    """
    queryset = attachment_list_queryset(task)
    if cursor is not None:
        queryset = filter_beyond_cursor(queryset, cursor)
    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_attachment_cursor(rows[-1]) if has_more and rows else None
    return rows, next_cursor


__all__ = [
    "AttachmentCursorKey",
    "attachment_list_queryset",
    "attachment_page",
    "decode_attachment_cursor",
    "encode_attachment_cursor",
    "filter_beyond_cursor",
]
