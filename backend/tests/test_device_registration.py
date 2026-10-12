"""MT-1.2-04 — device registration and revocation (Section 9.2 Devices row).

Proves the ADR-006/Section 12.2 mobile slice end to end:

* ``POST /devices`` (after Owner login) creates a Device **and** its
  ``kind = device`` API Token in one transaction; the plaintext is returned
  exactly once and only its SHA-256 hash is stored (Section 7.2); the
  sensitive ``push_token`` never appears in a response (Section 12.4);
* ``DELETE /devices/{id}`` revokes device **and** token together — the lost
  phone's credential fails authentication on its very next request
  (FR-SEC-02; no cache);
* the device credential is a distinct token kind that authenticates through
  the bearer class (403 on Owner-only rows, not 401) while maintaining
  ``last_used_at`` and ``last_seen_at`` (Section 7.2);
* failures use only Section 9.2 catalog codes.

Run with ``pytest backend/tests -k device`` (MT test command).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, cast

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, Device, TokenKind, User

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"
TOKEN_LIST_URL = "/api/v1/tokens"

PASSWORD = "device-token-tests-1!"  # pragma: allowlist secret
PUSH_TOKEN = "apns-device-secret-example"


@pytest.fixture
def owner(db: None) -> User:
    """The owner account devices register under."""
    return User.objects.create_user(username="owner", password=PASSWORD)


@pytest.fixture
def client() -> APIClient:
    """Fresh API client per test."""
    return APIClient()


def _envelope(response: Any) -> dict[str, Any]:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return cast(dict[str, Any], error)


def _login(api: APIClient, user: User) -> None:
    response = api.post(LOGIN_URL, {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200, response.content


def _register(api: APIClient, **extra: Any) -> dict[str, Any]:
    payload = {"platform": "ios", "push_token": PUSH_TOKEN, **extra}
    response = api.post(REGISTER_URL, payload)
    assert response.status_code == 201, response.content
    return cast(dict[str, Any], response.json())


# --- POST /devices ---------------------------------------------------------


def test_register_creates_device_and_token_with_hashed_secret_only(
    client: APIClient, owner: User
) -> None:
    """One transaction, two rows, one plaintext — returned exactly once."""
    _login(client, owner)

    body = _register(client, biometric_bound=True)

    # Exact response contract (risk note: fix the shape in the snapshot).
    assert set(body) == {"id", "platform", "biometric_bound", "expires_at", "token"}
    assert body["platform"] == "ios"
    assert body["biometric_bound"] is True

    device = Device.objects.get(pk=body["id"])
    plaintext = body["token"]
    assert isinstance(plaintext, str) and len(plaintext) >= 32
    assert device.user_id == owner.pk
    assert device.token.kind == TokenKind.DEVICE  # distinct kind (FR-SEC-02)
    assert device.token.hash == hashlib.sha256(plaintext.encode()).hexdigest()
    assert device.token.expires_at is not None

    # No plaintext anywhere in either row.
    device_values = [str(field.value_from_object(device)) for field in Device._meta.fields]
    token_values = [str(field.value_from_object(device.token)) for field in ApiToken._meta.fields]
    assert plaintext not in device_values + token_values
    assert PUSH_TOKEN not in body, "push_token must never be echoed (12.4)"


def test_register_is_owner_only(client: APIClient, owner: User) -> None:
    """Section 12.2: registration happens after Owner login — 401/403."""
    anonymous = client.post(REGISTER_URL, {"platform": "ios", "push_token": PUSH_TOKEN})
    assert anonymous.status_code == 401
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"

    _login(client, owner)
    agent_row = ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hashlib.sha256(b"agent-for-device-test").hexdigest(),
        user=owner,
        project_id="PID00001",
    )
    # The agent credential authenticates but is the wrong role (catalog 403).
    response = client.post(
        REGISTER_URL,
        {"platform": "ios", "push_token": PUSH_TOKEN},
        headers={"Authorization": "Bearer agent-for-device-test"},
    )
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"
    assert agent_row.pk is not None  # created directly; never persisted plaintext


def test_register_validates_payload(client: APIClient, owner: User) -> None:
    """Closed platform vocabulary + required push_token; flag defaults false."""
    _login(client, owner)

    bad_platform = client.post(REGISTER_URL, {"platform": "blackberry", "push_token": PUSH_TOKEN})
    assert bad_platform.status_code == 400
    assert _envelope(bad_platform)["code"] == "VALIDATION_ERROR"

    missing_push = client.post(REGISTER_URL, {"platform": "android"})
    assert missing_push.status_code == 400
    assert _envelope(missing_push)["code"] == "VALIDATION_ERROR"

    defaulted = _register(client)  # biometric_bound omitted
    assert defaulted["biometric_bound"] is False


def test_device_lifetime_comes_from_settings(client: APIClient, owner: User, settings: Any) -> None:
    """Section 9.10: TOKEN_LIFETIME_DEVICE_DAYS drives the token expiry."""
    settings.TOKEN_LIFETIME_DEVICE_DAYS = 7
    _login(client, owner)

    body = _register(client)

    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(cast(str, body["expires_at"]))
    assert parsed is not None
    delta = parsed - timezone.now()
    assert abs(delta - timedelta(days=7)) < timedelta(minutes=5)


# --- The device credential in use ------------------------------------------


def test_device_token_authenticates_and_marks_presence(client: APIClient, owner: User) -> None:
    """Bearer device token: authenticated (403 on Owner rows), presence kept."""
    _login(client, owner)
    body = _register(client)
    client.logout()  # cookies gone — only the device credential remains

    response = client.get(TOKEN_LIST_URL, headers={"Authorization": f"Bearer {body['token']}"})
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"

    device = Device.objects.get(pk=body["id"])
    assert device.last_seen_at is not None  # Section 7.2 hygiene
    assert device.token.last_used_at is not None


def test_delete_revokes_device_and_token_together(client: APIClient, owner: User) -> None:
    """Lost-phone control: one DELETE, both rows dead on the next request."""
    _login(client, owner)
    body = _register(client)
    device = Device.objects.get(pk=body["id"])
    bearer = {"Authorization": f"Bearer {body['token']}"}
    # Live before revocation (403 = authenticated, wrong role).
    assert client.get(TOKEN_LIST_URL, headers=bearer).status_code == 403

    revoke = client.delete(f"{REGISTER_URL}/{body['id']}")
    assert revoke.status_code == 200
    revoked_at = revoke.json()["revoked_at"]
    assert revoked_at is not None

    device.refresh_from_db()
    device.token.refresh_from_db()
    assert device.revoked_at is not None
    assert device.token.revoked_at is not None  # revoked together, one action

    after = client.get(TOKEN_LIST_URL, headers=bearer)
    assert after.status_code == 401
    assert _envelope(after)["code"] == "AUTH_REQUIRED"

    # Idempotent: repeating returns the original instant.
    again = client.delete(f"{REGISTER_URL}/{body['id']}")
    assert again.status_code == 200
    assert again.json()["revoked_at"] == revoked_at


def test_delete_unknown_and_foreign_ids_answer_identically(
    client: APIClient, owner: User, db: None
) -> None:
    """No existence probing: unknown and other users' devices look the same."""
    other = User.objects.create_user(username="other", password=PASSWORD)
    _login(client, owner)
    body = _register(client)

    unknown = client.delete(f"{REGISTER_URL}/999999")
    assert unknown.status_code == 400
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"

    other_client = APIClient()
    _login(other_client, other)
    foreign = other_client.delete(f"{REGISTER_URL}/{body['id']}")
    assert foreign.status_code == 400
    assert _envelope(foreign)["code"] == "VALIDATION_ERROR"
    assert Device.objects.get(pk=body["id"]).revoked_at is None  # untouched
