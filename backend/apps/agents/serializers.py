"""Agent session request/response serializers (Section 7.2; MT-1.6-09).

The create input declares exactly the Section 7.2 fields the *bridge*
may supply — ``id``, ``agent_label``, ``client_name``, ``capability``,
``transport`` — under ``StrictSerializerMixin``: a body-supplied
``project_id`` (or any unknown key) is rejected with
``VALIDATION_ERROR`` instead of silently ignored, making ADR-004's
"project from the token, never the body" executable at the boundary
(same acceptance shape as the task routes).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.serializers import StrictSerializerMixin

from .models import SessionCapability, SessionTransport, validate_session_id


class AgentSessionSerializer(serializers.Serializer[Any]):
    """The Section 7.2 Agent Session row as it goes over the wire."""

    id = serializers.CharField(read_only=True)
    project_id = serializers.CharField(read_only=True)
    token_id = serializers.IntegerField(read_only=True)
    agent_label = serializers.CharField(read_only=True)
    client_name = serializers.CharField(read_only=True)
    capability = serializers.ChoiceField(choices=SessionCapability.choices, read_only=True)
    transport = serializers.ChoiceField(choices=SessionTransport.choices, read_only=True)
    started_at = serializers.DateTimeField(read_only=True)
    last_seen_at = serializers.DateTimeField(read_only=True)
    ended_at = serializers.DateTimeField(allow_null=True, read_only=True)


class AgentSessionCreateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /agent-sessions`` input — no project field exists here (ADR-004)."""

    id = serializers.CharField(max_length=128, validators=[validate_session_id])
    agent_label = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    client_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    capability = serializers.ChoiceField(
        choices=SessionCapability.choices,
        required=False,
        default=SessionCapability.UNKNOWN,  # Section 10.4: default unknown
    )
    transport = serializers.ChoiceField(choices=SessionTransport.choices)
