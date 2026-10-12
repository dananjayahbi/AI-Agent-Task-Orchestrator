"""Token minting, hashing and lifecycle primitives (Section 7.2; FR-SEC-04).

One place decides how a token looks and how it is hashed, so owner sessions
(MT-1.2-01), agent tokens (MT-1.2-03) and device tokens (MT-1.2-04) can never
drift into two representations of "the same" secret.

Algorithm decision (recorded here and in the WP changelog per MT-1.2-02's risk
note): **SHA-256, unsalted, hex-encoded**. Passwords need slow salted hashing
because the input is low-entropy human text; these tokens are 256-bit
`secrets`-generated values, so a fast preimage-resistant hash is the standard
choice — it makes the on-disk row unusable as a credential while allowing an
O(1) lookup by hash on every authenticated request.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from ..models import ApiToken, TokenKind, User


def generate_token() -> str:
    """Return a fresh unguessable plaintext token (256 bits of entropy)."""
    return secrets.token_urlsafe(32)


def hash_token(plaintext: str) -> str:
    """Return the SHA-256 hex digest — the *only* form ever persisted (7.2)."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def mark_token_used(token: ApiToken, at: datetime | None = None) -> None:
    """Record a successful authentication (Section 7.2 ``last_used_at``).

    Shared by both authentication classes so token hygiene ("was this token
    used recently?") is maintained identically on every transport. A trivial
    per-request write — deliberately no cache in front of it (risk note:
    caching would make revocation lag; see ``ApiToken.is_valid``).
    """
    token.last_used_at = at or timezone.now()
    token.save(update_fields=["last_used_at"])


def agent_lifetime() -> timedelta:
    """The Section 9.10 agent-token lifetime as a timedelta (one source)."""
    return timedelta(hours=settings.TOKEN_LIFETIME_AGENT_HOURS)


def device_lifetime() -> timedelta:
    """The Section 9.10 device-token lifetime as a timedelta (one source)."""
    return timedelta(days=settings.TOKEN_LIFETIME_DEVICE_DAYS)


def issue_agent_token(
    user: User, project_id: str, scopes: list[str] | None = None
) -> tuple[ApiToken, str]:
    """Mint a project-scoped agent token (Section 12.2; ADR-004).

    Returns ``(row, plaintext)`` — the plaintext exists only in this return
    value, for the response body exactly once (Section 7.2); the row stores
    ``hash_token(plaintext)`` and the Section 9.10 expiry. ``project_id`` has
    already passed the Section 7.3 format check (serializer/model/DB
    constraint). WP-1.3 seam: existence/active-status of the project cannot
    be verified until the Project registry lands — recorded as an open
    deviation in the WP changelog, not silently skipped.
    """
    plaintext = generate_token()
    token = ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hash_token(plaintext),
        user=user,
        project_id=project_id,
        scopes=list(scopes or []),
        expires_at=timezone.now() + agent_lifetime(),
    )
    return token, plaintext


def revoke_token(token: ApiToken) -> datetime:
    """Set ``revoked_at`` once; idempotent like logout (NFR-12 spirit).

    The validity predicate reads the row per request, so the next use of this
    token fails immediately — no cache to invalidate (WP-1.2 acceptance).
    """
    if token.revoked_at is None:
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])
    return token.revoked_at
