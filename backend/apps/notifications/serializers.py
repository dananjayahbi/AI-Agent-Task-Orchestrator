"""Serializers for the MT-5.4-05 preferences endpoint (Section 9.2 shape).

One envelope member — ``preferences`` — carries the full closed set of
Section 9.8 types; the response serializer doubles as the read model and the
request serializer accepts a partial list (update only what the client
changed — the mobile toggles and the web settings surface PATCH-by-example
against the same record). Strict input throughout (the shared
``StrictSerializerMixin`` rule): unknown keys and unknown/duplicated event
types are rejected with ``VALIDATION_ERROR``, never silently ignored.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.serializers import StrictSerializerMixin

from .preferences import NOTIFICATION_EVENT_TYPES

_EVENT_TYPE_CHOICES = [(key, key) for key in NOTIFICATION_EVENT_TYPES]


class NotificationPreferenceSerializer(StrictSerializerMixin):
    """One ``{event_type, enabled}`` pair — the wire shape both clients edit."""

    event_type = serializers.ChoiceField(choices=_EVENT_TYPE_CHOICES)
    enabled = serializers.BooleanField()


class NotificationPreferencesRequestSerializer(StrictSerializerMixin):
    """``PUT`` body: a non-empty list of preference pairs to update."""

    preferences = NotificationPreferenceSerializer(many=True, allow_empty=False)

    def validate_preferences(
        self,
        value: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Reject duplicate event types (ambiguous intent → VALIDATION_ERROR)."""
        seen: set[str] = set()
        for item in value:
            event_type = str(item["event_type"])
            if event_type in seen:
                raise serializers.ValidationError(f"{event_type} appears more than once.")
            seen.add(event_type)
        return value


class NotificationPreferencesResponseSerializer(serializers.Serializer[Any]):
    """``GET``/``PUT`` response: every Section 9.8 type with its switch."""

    preferences = NotificationPreferenceSerializer(many=True)
