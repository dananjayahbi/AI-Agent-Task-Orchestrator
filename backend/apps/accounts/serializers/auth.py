"""Request/response contracts for POST /auth/login|logout|refresh (Section 9.2).

The login response carries the plaintext session binding exactly once (the
only moment the client can obtain it — Section 7.2; the row stores only its
hash). ``user`` is the minimal owner summary the web/mobile clients need to
render identity; no other account fields are invented (Section 20.5).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class UserSummarySerializer(serializers.Serializer[Any]):
    """The owner identity as returned by login."""

    id = serializers.IntegerField()
    username = serializers.CharField()


class LoginRequestSerializer(serializers.Serializer[Any]):
    """POST /auth/login body (Section 9.2 Auth row, caller Owner)."""

    username = serializers.CharField()
    # trim_whitespace=False: a password may legitimately begin/end with a space.
    password = serializers.CharField(trim_whitespace=False, style={"input_type": "password"})


class OwnerSessionSerializer(serializers.Serializer[Any]):
    """The login payload: plaintext binding once + row expiry + identity."""

    token = serializers.CharField(
        help_text=(
            "The owner session token. Returned exactly once at login; the "
            "server stores only its SHA-256 hash (Section 7.2). Web clients "
            "rely on the session cookie and may ignore it; token-auth clients "
            "(Section 15.4) send it as `Authorization: Bearer <token>`."
        )
    )
    expires_at = serializers.DateTimeField()
    user = UserSummarySerializer()


class RevokedSerializer(serializers.Serializer[Any]):
    """POST /auth/logout: the instant the session token stopped working."""

    revoked_at = serializers.DateTimeField()


class RefreshedSerializer(serializers.Serializer[Any]):
    """POST /auth/refresh: the extended expiry (same lifetime settings)."""

    expires_at = serializers.DateTimeField()
