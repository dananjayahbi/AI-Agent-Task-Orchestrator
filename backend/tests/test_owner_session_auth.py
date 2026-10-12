"""MT-1.2-01 — owner session auth: login / logout / refresh (Sections 9.2, 12.2).

Proves the acceptance criteria of the WP-1.2 first slice end to end against the
real request pipeline (cookies, CSRF, envelope):

* login issues a secure HTTP-only session cookie plus the csrftoken cookie and
  returns the plaintext binding exactly once (Section 9.2 Auth row);
* passwords and session tokens are stored **hashed** — no plaintext secret in
  any table (Section 7.2; NFR-07);
* logout revokes the ``owner_session`` row immediately and a *retained/stolen*
  session cookie still cannot authenticate afterwards — the row, not the
  cookie, is the authority (FR-SEC-02; WP-1.2 acceptance);
* refresh extends a live session and can never resurrect a revoked or expired
  one; failures answer with Section 9.2 catalog codes only;
* the lifetime comes from the Section 9.10 configuration setting;
* mutations are CSRF-protected (Section 12.2).

Run with ``pytest backend/tests -k "auth or session"`` (MT's test command).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any, cast

import pytest
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, TokenKind, User
from apps.accounts.services.sessions import SESSION_BINDING_KEY
from apps.core.errors import AUTH_REQUIRED, CANONICAL_ERROR_CODES, VALIDATION_ERROR

LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"

PASSWORD = "correct-horse-battery-staple-1!"  # pragma: allowlist secret


@pytest.fixture
def owner(db: None) -> User:
    """A fresh owner account (plaintext known only to the test)."""
    return User.objects.create_user(username="owner", password=PASSWORD)


@pytest.fixture
def client() -> APIClient:
    """A fresh API client (no cookies, no default credentials)."""
    return APIClient()


def _envelope(response: Any) -> dict[str, Any]:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "envelope code must be catalog-closed"
    return cast(dict[str, Any], error)


def _login(client: APIClient, owner: User) -> dict[str, Any]:
    response = client.post(LOGIN_URL, {"username": owner.username, "password": PASSWORD})
    assert response.status_code == 200, response.content
    return cast(dict[str, Any], response.json())


def _expiry_delta(expires_at: str) -> timedelta:
    """Time from now until *expires_at* (parsed, never string-compared)."""
    parsed: datetime | None = parse_datetime(expires_at)
    assert parsed is not None
    return parsed - timezone.now()


def test_login_returns_binding_once_and_sets_secure_session_cookies(
    client: APIClient, owner: User
) -> None:
    """200 body carries token/expires_at/user; sessionid is HTTP-only (12.2)."""
    response = client.post(LOGIN_URL, {"username": owner.username, "password": PASSWORD})

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["token"], str) and data["token"]
    assert data["user"] == {"id": owner.pk, "username": owner.username}
    # Secure, HTTP-only cookie session: the session cookie must be HttpOnly;
    # Secure is environment-dependent (prod.py forces it) so asserted there.
    session_morsel = response.cookies["sessionid"]
    assert session_morsel["httponly"], "session cookie must be HTTP-only (12.2)"
    # The CSRF half of the protection: the client gets the csrftoken cookie to
    # echo back as X-CSRFToken on every mutation.
    assert "csrftoken" in response.cookies
    # Session lifetime follows the Section 9.10 setting (default 12h).
    expires_at = data["expires_at"]
    assert isinstance(expires_at, str)
    delta = _expiry_delta(expires_at)
    expected = timedelta(hours=settings.TOKEN_LIFETIME_OWNER_SESSION_HOURS)
    assert abs(delta - expected) < timedelta(minutes=5)


def test_auth_secrets_are_never_stored_in_plaintext(client: APIClient, owner: User) -> None:
    """NFR-07/Section 7.2: password hashed by Django, token stored as hash only."""
    data = _login(client, owner)

    owner.refresh_from_db()
    # Password: a Django hasher output, never the plaintext.
    assert owner.password != PASSWORD
    assert PASSWORD not in owner.password
    assert owner.password.startswith("pbkdf2_")

    # Token: the row stores only the SHA-256 of the binding returned once.
    plaintext = str(data["token"])
    token = ApiToken.objects.get(kind=TokenKind.OWNER_SESSION, user=owner)
    assert token.hash == hashlib.sha256(plaintext.encode()).hexdigest()
    assert plaintext not in token.hash and len(token.hash) == 64
    assert token.expires_at is not None
    assert token.revoked_at is None


def test_logout_revokes_session_immediately(client: APIClient, owner: User) -> None:
    """FR-SEC-02: logout revokes; the very next request is AUTH_REQUIRED."""
    _login(client, owner)

    logout = client.post(LOGOUT_URL)
    assert logout.status_code == 200
    assert logout.json()["revoked_at"] is not None
    token = ApiToken.objects.get(kind=TokenKind.OWNER_SESSION, user=owner)
    assert token.revoked_at is not None

    after = client.post(REFRESH_URL)
    assert after.status_code == 401
    assert _envelope(after)["code"] == AUTH_REQUIRED


def test_revoked_row_rejects_retained_session_cookie(client: APIClient, owner: User) -> None:
    """A replayed pre-logout cookie still fails: the row is the authority.

    Signed-cookie sessions are otherwise stateless and un-revokeable; this is
    the WP-1.2 acceptance that revocation takes effect on the very next call
    (no server-side session store involved).
    """
    login = client.post(LOGIN_URL, {"username": owner.username, "password": PASSWORD})
    retained_cookie = login.cookies["sessionid"].value

    assert client.post(LOGOUT_URL).status_code == 200

    # Replay the pre-logout cookie as if it had been captured.
    client.cookies["sessionid"] = retained_cookie
    replay = client.post(REFRESH_URL)
    assert replay.status_code == 401
    assert _envelope(replay)["code"] == AUTH_REQUIRED


def test_refresh_extends_session_and_cannot_resurrect_it(client: APIClient, owner: User) -> None:
    """Refresh pushes expiry forward while live; dead sessions never reach it."""
    _login(client, owner)

    # Prove the extension deterministically: shrink the remaining lifetime to
    # one hour first, so the outcome differs by hours rather than by two
    # clock reads. Login and refresh a few milliseconds apart can land inside
    # the same system-clock tick (equal instants made a naive `>` comparison
    # flaky on Windows-hosted runners).
    row = ApiToken.objects.get(kind=TokenKind.OWNER_SESSION, user=owner)
    row.expires_at = timezone.now() + timedelta(hours=1)
    row.save(update_fields=["expires_at"])
    shrunk_expiry = row.expires_at

    refreshed = client.post(REFRESH_URL)
    assert refreshed.status_code == 200
    refreshed_expiry = parse_datetime(str(refreshed.json()["expires_at"]))
    assert refreshed_expiry is not None
    assert refreshed_expiry > shrunk_expiry  # live session extended

    assert client.post(LOGOUT_URL).status_code == 200
    after_logout = client.post(REFRESH_URL)
    assert after_logout.status_code == 401
    assert _envelope(after_logout)["code"] == AUTH_REQUIRED


def test_refresh_of_expired_session_fails_with_catalog_code(client: APIClient, owner: User) -> None:
    """Expiry (even with a still-valid cookie) answers AUTH_REQUIRED, not 500."""
    _login(client, owner)
    token = ApiToken.objects.get(kind=TokenKind.OWNER_SESSION, user=owner)
    token.expires_at = timezone.now() - timedelta(seconds=1)
    token.save(update_fields=["expires_at"])

    response = client.post(REFRESH_URL)
    assert response.status_code == 401
    assert _envelope(response)["code"] == AUTH_REQUIRED


def test_session_lifetime_comes_from_settings(
    client: APIClient, owner: User, settings: Any
) -> None:
    """Section 9.10: one configuration knob drives the recorded expiry."""
    settings.TOKEN_LIFETIME_OWNER_SESSION_HOURS = 24

    data = _login(client, owner)

    delta = _expiry_delta(data["expires_at"])
    assert abs(delta - timedelta(hours=24)) < timedelta(minutes=5)


def test_bad_credentials_return_auth_required(client: APIClient, owner: User) -> None:
    """Unknown user and wrong password share one non-enumerating answer."""
    wrong_password = client.post(LOGIN_URL, {"username": owner.username, "password": "nope"})
    assert wrong_password.status_code == 401
    assert _envelope(wrong_password)["code"] == AUTH_REQUIRED

    unknown_user = client.post(LOGIN_URL, {"username": "ghost", "password": "nope"})
    assert unknown_user.status_code == 401
    assert _envelope(unknown_user)["code"] == AUTH_REQUIRED


def test_auth_login_body_validation_uses_catalog_code(client: APIClient) -> None:
    """Malformed login body -> 400 VALIDATION_ERROR (closed catalog, 20.4.5)."""
    response = client.post(LOGIN_URL, {}, format="json")
    assert response.status_code == 400
    assert _envelope(response)["code"] == VALIDATION_ERROR


def test_anonymous_auth_request_returns_auth_required(client: APIClient) -> None:
    """Unauthenticated callers hit the Owner-only rows with AUTH_REQUIRED."""
    for url in (LOGOUT_URL, REFRESH_URL):
        response = client.post(url)
        assert response.status_code == 401
        assert _envelope(response)["code"] == AUTH_REQUIRED


def test_owner_session_mutation_requires_csrf(owner: User) -> None:
    """Section 12.2: mutations are CSRF-protected; failure is AUTH_REQUIRED.

    ``enforce_csrf_checks=True`` makes the test client behave like production
    (Django's test client skips CSRF unless asked not to), and DRF enforces
    the check inside ``OwnerSessionAuthentication``.
    """
    strict = APIClient(enforce_csrf_checks=True)
    login = strict.post(LOGIN_URL, {"username": owner.username, "password": PASSWORD})
    assert login.status_code == 200
    csrf_value = login.cookies["csrftoken"].value

    missing = strict.post(LOGOUT_URL)
    assert missing.status_code == 401
    assert _envelope(missing)["code"] == AUTH_REQUIRED

    # With the cookie echoed back as the X-CSRFToken header, the same mutation
    # succeeds — CSRF protection, not denial of service.
    ok = strict.post(LOGOUT_URL, HTTP_X_CSRFTOKEN=csrf_value)
    assert ok.status_code == 200


def test_session_binding_is_stored_only_inside_the_signed_session(
    client: APIClient, owner: User
) -> None:
    """The binding exists in session data + response body — never a raw column."""
    data = _login(client, owner)
    binding = str(data["token"])

    # No ApiToken column stores the plaintext...
    for token in ApiToken.objects.all():
        assert binding not in (token.hash, token.kind, str(token.pk))
    # ...and the binding is carried by the session (signed cookie) only.
    session_response = client.post(REFRESH_URL)
    assert session_response.status_code == 200
    assert SESSION_BINDING_KEY not in str(session_response.content)
