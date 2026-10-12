"""Request/response contracts for the Tokens row (Section 9.2; MT-1.2-03).

Three shapes, each mirroring its OpenAPI operation (risk note: the plaintext
token's one-and-only appearance is the ``AgentTokenIssueResponseSerializer``
contract — a wrong response shape makes the token unusable):

* issue: ``project_id`` + optional ``scopes`` in; ``token`` (plaintext,
  once) + row metadata out;
* list: the pagination.md two-member envelope wrapping **metadata only** —
  no ``hash``, no plaintext, ever (Section 7.2);
* revoke: the same ``revoked_at`` confirmation as logout.

The list ``next_cursor`` is nullable-optional on the wire (absent or ``null``
means end-of-list) and rendered as an explicit ``null`` here so the generated
schema states the member rather than implying it (pagination.md envelope is
exactly ``results`` + ``next_cursor``).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import AGENT_ROLE_SCOPES, TokenKind, validate_project_id


class AgentTokenIssueRequestSerializer(serializers.Serializer[Any]):
    """POST /tokens/agent body: which project, which roles."""

    project_id = serializers.CharField(
        validators=[validate_project_id],
        help_text="Target project id (PID + five digits, Section 7.3).",
    )
    scopes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text=(
            "Agent roles this token may act as (Section 12.2 matrix roles). "
            f"Allowed: {', '.join(AGENT_ROLE_SCOPES)}."
        ),
    )

    def validate_scopes(self, value: list[str]) -> list[str]:
        """Closed vocabulary: unknown roles are a 400, not silently dropped."""
        unknown = sorted(set(value) - set(AGENT_ROLE_SCOPES))
        if unknown:
            raise serializers.ValidationError(
                f"Unknown scopes: {', '.join(unknown)}. Allowed: {', '.join(AGENT_ROLE_SCOPES)}."
            )
        # Preserve order, drop duplicates — evaluation treats scopes as a set.
        return list(dict.fromkeys(value))


class TokenSummarySerializer(serializers.Serializer[Any]):
    """List item metadata — deliberately without ``hash`` (FR-SEC-04)."""

    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=TokenKind.choices)
    project_id = serializers.CharField(allow_null=True)
    scopes = serializers.JSONField()
    expires_at = serializers.DateTimeField(allow_null=True)
    revoked_at = serializers.DateTimeField(allow_null=True)
    last_used_at = serializers.DateTimeField(allow_null=True)


class AgentTokenIssueResponseSerializer(serializers.Serializer[Any]):
    """POST /tokens/agent 201 body: plaintext exactly once + row metadata."""

    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=TokenKind.choices)
    project_id = serializers.CharField(allow_null=True)
    scopes = serializers.JSONField()
    expires_at = serializers.DateTimeField(allow_null=True)
    token = serializers.CharField(
        help_text=(
            "The plaintext bearer token — returned exactly once, now. The "
            "server stores only its SHA-256 hash and cannot show it again "
            "(Section 7.2); lost tokens must be revoked and reissued."
        ),
    )


class TokenListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = TokenSummarySerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class TokenListQuerySerializer(serializers.Serializer[Any]):
    """GET /tokens query parameters (filter + cursor contract)."""

    kind = serializers.ChoiceField(
        choices=TokenKind.choices,
        required=False,
        help_text="Filter by token kind.",
    )
    project_id = serializers.CharField(
        validators=[validate_project_id],
        required=False,
        help_text="Filter by project id (agent tokens are project-scoped).",
    )
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


__all__ = [
    "AgentTokenIssueRequestSerializer",
    "AgentTokenIssueResponseSerializer",
    "TokenListEnvelopeSerializer",
    "TokenListQuerySerializer",
    "TokenSummarySerializer",
]
