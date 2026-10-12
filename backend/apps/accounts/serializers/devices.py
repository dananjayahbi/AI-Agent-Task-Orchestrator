"""Contracts for the Devices row (Section 9.2; MT-1.2-04; ADR-006).

Registration is deliberately minimal (MT risk note: the plan pins no shape
beyond the caller, so define once here and fix it in the OpenAPI snapshot):

* **in** — ``platform`` (closed ``ios``/``android`` — flagged decision),
  ``push_token`` (required by the MT scope; sensitive at rest, Section 12.4,
  never echoed back), ``biometric_bound`` (optional boolean, default
  ``false`` — how the flag arrives was ambiguous in the plan; recorded as a
  documented default rather than guessed twice);
* **out** — device id, the recorded platform/biometric flag, the token
  expiry, and ``token``: the device-bound plaintext **exactly once** for the
  client's secure storage (Section 12.2).

``DELETE /devices/{id}`` answers with the same ``revoked_at`` confirmation
as logout/token revocation (one confirmation shape across the surface).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.accounts.models import Platform


class DeviceRegisterRequestSerializer(serializers.Serializer[Any]):
    """POST /devices body."""

    platform = serializers.ChoiceField(
        choices=Platform.choices,
        help_text="Mobile platform: ios or android.",
    )
    push_token = serializers.CharField(
        allow_blank=False,
        help_text=(
            "APNs/FCM registration token for push dispatch (Section 9.8). "
            "Sensitive at rest (Section 12.4) — stored, never returned."
        ),
    )
    biometric_bound = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "Whether the client has enrolled the biometric gate for this "
            "device (Section 12.2; enforcement is client-side, M5)."
        ),
    )


class DeviceRegisterResponseSerializer(serializers.Serializer[Any]):
    """POST /devices 201 body: metadata + the token shown exactly once."""

    id = serializers.IntegerField()
    platform = serializers.ChoiceField(choices=Platform.choices)
    biometric_bound = serializers.BooleanField()
    expires_at = serializers.DateTimeField()
    token = serializers.CharField(
        help_text=(
            "The device-bound plaintext token — returned exactly once, now; "
            "store it in platform secure storage. The server keeps only its "
            "SHA-256 hash (Section 7.2) and cannot show it again."
        ),
    )


__all__ = ["DeviceRegisterRequestSerializer", "DeviceRegisterResponseSerializer"]
