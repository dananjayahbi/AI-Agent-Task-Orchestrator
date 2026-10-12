"""Device registration and revocation (Section 12.2; ADR-006; MT-1.2-04).

Both operations keep the Device row and its ``kind = device`` API Token in
one transaction: registration can never leave a device without a credential
(or a credential without a device), and revocation always hits both — the
lost-phone control is a single action (Section 12.1 threat table).

The plaintext device token exists only in ``register_device``'s return
value: the mobile client stores it in platform secure storage (Section 12.2,
12.4) and the server keeps just the SHA-256 hash, exactly like every other
token kind (Section 7.2).
"""

from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from ..models import ApiToken, Device, TokenKind, User
from .tokens import device_lifetime, generate_token, hash_token


def register_device(
    *,
    user: User,
    platform: str,
    push_token: str,
    biometric_bound: bool,
) -> tuple[Device, str]:
    """Create a Device row + its device token atomically (Section 12.2).

    Returns ``(device, plaintext)`` — plaintext once for the client's secure
    storage; the row pair stores only the hash. ``expires_at`` follows the
    Section 9.10 ``TOKEN_LIFETIME_DEVICE_DAYS`` setting.
    """
    plaintext = generate_token()
    with transaction.atomic():
        token = ApiToken.objects.create(
            kind=TokenKind.DEVICE,
            hash=hash_token(plaintext),
            user=user,
            expires_at=timezone.now() + device_lifetime(),
        )
        device = Device.objects.create(
            user=user,
            platform=platform,
            push_token=push_token,
            token=token,
            biometric_bound=biometric_bound,
        )
    return device, plaintext


def revoke_device(device: Device) -> datetime:
    """Revoke the device **and** its token together; idempotent.

    Returns the device's ``revoked_at`` — the instant access stopped. Both
    rows are written in one transaction so no path can revoke one without
    the other (FR-SEC-02 independent revocation; NFR-12 safe retry).
    """
    with transaction.atomic():
        revoked_at = device.revoked_at
        if revoked_at is None:
            revoked_at = timezone.now()
            device.revoked_at = revoked_at
            device.save(update_fields=["revoked_at"])
        token = device.token
        if token.revoked_at is None:
            token.revoked_at = revoked_at
            token.save(update_fields=["revoked_at"])
    return revoked_at
