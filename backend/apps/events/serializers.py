"""Wire contracts for the realtime gateway surface (Sections 9.6, 9.2).

Two request shapes and two response shapes, one projection each:

* **Filters** — the optional ``project`` and ``task`` query parameters of
  Section 9.6, shared verbatim by ``GET /events/stream`` and ``GET /events``
  (MT-1.10-01 risk note: Section 9.6's names are used on both endpoints, one
  choice recorded in the WP changelog). Values are validated against the
  Section 7.3 id patterns at the API boundary, so malformed input answers
  ``VALIDATION_ERROR`` (Section 9.2; Section 20.4 item 5) — never a silent
  match-nothing stream.
* **History** — the pagination.md two-member envelope wrapping stored rows
  rendered by :func:`apps.events.envelope.event_envelope`, in ``id`` order
  (Section 20.5). The response serializers below *document* that projection
  for the OpenAPI contract; the endpoint emits ``event_envelope`` directly so
  the history item, the published message and the SSE frame can never drift
  apart (one row, one wire shape — MT-1.9-01).

``occurred_at`` is a ``CharField`` in the output schema because the envelope
renders the plan's second-precision UTC instant (``2026-10-11T12:45:02Z``) —
the documented Section 9.6 shape, not a locale-locale DRF datetime default.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.projects.services.pids import PROJECT_ID_PATTERN
from apps.tasks.services.ids import TASK_ID_PATTERN

from .models import EventActorType, EventType


class StreamQuerySerializer(serializers.Serializer[Any]):
    """The Section 9.6 filters (``project``, ``task``) — stream and history."""

    project = serializers.RegexField(
        regex=PROJECT_ID_PATTERN,
        required=False,
        help_text="Only events for this project id (PID + five digits, Section 7.3).",
    )
    task = serializers.RegexField(
        regex=TASK_ID_PATTERN,
        required=False,
        help_text="Only events for this task id ({PID}-T{index}, Section 7.3).",
    )


class HistoryQuerySerializer(StreamQuerySerializer):
    """``GET /events`` query parameters: filters + the cursor contract."""

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor.",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            "Items per page (default 25, maximum 100; values above the "
            "maximum are clamped — pagination.md documented defaults)."
        ),
    )


class EventActorSerializer(serializers.Serializer[Any]):
    """Envelope ``actor`` — the structured Section 9.6 object, never flattened."""

    type = serializers.ChoiceField(choices=EventActorType.choices)
    ref = serializers.CharField()


class EventEnvelopeSerializer(serializers.Serializer[Any]):
    """The Section 9.6 event envelope — exactly the seven documented keys."""

    id = serializers.IntegerField(
        help_text="Monotonic event id — the SSE event id (Section 9.6).",
    )
    type = serializers.ChoiceField(
        choices=EventType.choices,
        help_text="One of the Section 9.6 catalog types (closed set).",
    )
    project_id = serializers.CharField()
    task_id = serializers.CharField(allow_null=True)
    occurred_at = serializers.CharField(
        help_text="UTC instant rendered as YYYY-MM-DDTHH:MM:SSZ (Section 9.6).",
    )
    actor = EventActorSerializer()
    # The envelope's `data` key collides with DRF's `Serializer.data`
    # property at the type level only (runtime: declared fields win) —
    # documented here rather than renamed away from Section 9.6.
    data = serializers.JSONField()  # type: ignore[assignment]


class EventListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = EventEnvelopeSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


__all__ = [
    "EventActorSerializer",
    "EventEnvelopeSerializer",
    "EventListEnvelopeSerializer",
    "HistoryQuerySerializer",
    "StreamQuerySerializer",
]
