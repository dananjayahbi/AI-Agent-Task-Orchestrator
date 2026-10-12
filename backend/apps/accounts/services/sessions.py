"""Owner session lifecycle: start, revoke, refresh (Sections 12.2, 9.2; ADR-006).

Storage mechanic, recorded here per MT-1.2-01's risk note ("record the chosen
storage mechanics in the changelog"):

* the session itself lives in a **signed-cookie** Django session (Section 12.2
  — secure, HTTP-only cookie; no plaintext session credential exists in the
  database at all);
* every login additionally writes one **`owner_session` API Token row** whose
  ``hash`` binds the session to a revocable, expiring server-side authority —
  this row is what makes FR-SEC-02 revocation *immediate*: signed cookies are
  stateless and otherwise un-revokeable, but authentication re-reads the row
  on every request, so a logout (or expiry) takes effect on the very next call
  with no cache lag (WP-1.2 acceptance);
* ``refresh`` extends that row (and the cookie's max-age) and can never
  resurrect a revoked or expired one — authentication rejects those before the
  view runs.

The binding value (``SESSION_BINDING_KEY`` inside the session) is what the
login response also returns as ``token``: API clients (the mobile app in M5,
Section 15.4 "token auth") send it as a bearer, web clients never see it —
both forms hash to the same row, so revocation hits both transports at once.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest
from django.utils import timezone

from apps.accounts.models import ApiToken, TokenKind, User

from .tokens import generate_token, hash_token

# Key for the per-session binding stored inside the (signed) session data.
SESSION_BINDING_KEY = "_owner_sid"


def session_lifetime() -> timedelta:
    """The Section 9.10 owner-session lifetime as a timedelta (one source)."""
    return timedelta(hours=settings.TOKEN_LIFETIME_OWNER_SESSION_HOURS)


def binding_for_request(request: HttpRequest) -> str | None:
    """The session's binding value, or ``None`` when the session has none."""
    value = request.session.get(SESSION_BINDING_KEY)
    return value if isinstance(value, str) and value else None


def start_owner_session(request: HttpRequest, user: User) -> tuple[ApiToken, str]:
    """Log *user* in: signed-cookie session + revocable ``owner_session`` row.

    Returns the token row and the plaintext binding — the caller (the login
    view) puts the binding in the response body exactly once; only its hash is
    stored (Section 7.2).
    """
    login(request, user)
    binding = generate_token()
    ttl = session_lifetime()
    request.session[SESSION_BINDING_KEY] = binding
    # Cookie max-age tracks the row's expiry so the browser drops the session
    # when the token lifetime elapses (Section 9.10 documented default).
    request.session.set_expiry(int(ttl.total_seconds()))
    now = timezone.now()
    token = ApiToken.objects.create(
        kind=TokenKind.OWNER_SESSION,
        user=user,
        hash=hash_token(binding),
        expires_at=now + ttl,
        last_used_at=now,
    )
    return token, binding


def end_owner_session(request: HttpRequest, token: ApiToken) -> datetime:
    """Revoke *token* immediately and drop the local session (FR-SEC-02).

    Idempotent: a repeat call returns the original ``revoked_at`` — logout is
    a safe retry (NFR-12 spirit) and never shortens/extends a past instant.
    """
    revoked_at = token.revoked_at
    if revoked_at is None:
        revoked_at = timezone.now()
        token.revoked_at = revoked_at
        token.save(update_fields=["revoked_at"])
    if binding_for_request(request) is not None:
        # Cookie transport: clear the session too (the response then deletes
        # the cookie). Bearer-transport callers have no local session — the
        # row revocation alone already kills their credential.
        request.session.flush()
    return revoked_at


def refresh_owner_session(request: HttpRequest, token: ApiToken) -> datetime:
    """Extend the session's lifetime — only ever called on a *valid* row.

    The authentication layer has already proven the row is neither revoked nor
    expired (a revoked/expired refresh request never reaches this function —
    it fails with ``AUTH_REQUIRED``), so this cannot resurrect one.
    """
    expires_at = timezone.now() + session_lifetime()
    token.expires_at = expires_at
    token.save(update_fields=["expires_at"])
    if binding_for_request(request) is not None:
        request.session.set_expiry(int(session_lifetime().total_seconds()))
    return expires_at
