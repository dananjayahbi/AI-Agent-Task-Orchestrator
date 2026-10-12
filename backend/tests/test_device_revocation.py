"""MT-5.3-03 — device revocation with immediate rejection (Sections 9.2, 12.1, 12.2).

The lost-phone control end to end:

* **rejected on the next REST request** — the device credential that answered
  403 (authenticated, wrong role) a moment earlier answers 401
  ``AUTH_REQUIRED`` immediately after one DELETE, with both rows stamped;
* **rejected on SSE stream reconnect** — conditional: ``GET /events/stream``
  is WP-1.10 scope and does not exist yet, so that case activates when the
  route lands (the rejection itself rides the same
  ``TokenBearerAuthentication`` device check the REST probe exercises — no
  cache on the auth path, ADR-006/FR-SEC-02). The chosen live-connection
  semantics ("reject on next use at minimum; close-active deferred until
  the stream exists") are recorded in the WP changelog;
* **independence** — revoking device A never touches device B, agent
  tokens, or the Owner's sessions (Section 12.2; FR-SEC-02);
* **owner-only** — a different Owner (or anonymous caller) cannot revoke,
  and foreign/unknown ids answer identically (no existence probing);
* **idempotent** — repeating the DELETE returns the original
  ``revoked_at``.

Audit event: deferred, not invented — the MT-1.9-02 helper does not exist
and the Section 9.6 catalog has no device/token type (recorded in the WP
changelog with the pending token-event OQ).

Run with ``pytest backend/tests/test_device_revocation.py -v``
(flat path deviation from the MT's ``tests/accounts/`` wording recorded
in the WP changelog — WP-1.2 landed flat).
"""

from __future__ import annotations

import hashlib
from typing import Any, cast

import pytest
from django.urls import Resolver404, resolve
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.core.errors import CANONICAL_ERROR_CODES

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"
TOKEN_LIST_URL = "/api/v1/tokens"

PASSWORD = "device-revocation-tests-1!"  # pragma: allowlist secret
PUSH_TOKEN = "apns-device-revocation-example"

# The scheme word stays separate from credential values; the canonical
# spelling lives on TokenBearerAuthentication.keyword.
_AUTH_SCHEME = "Bearer"
# Preimage of the agent row's stored hash — bearer form built from the same
# constant so hash and header can never drift.
AGENT_CREDENTIAL = "agent-after-device-revoke"

# WP-1.10's stream lives at a Section 9.6 path; check both spellings a future
# URLConf might use so this case activates the day the route lands.
_STREAM_CANDIDATES = ("/api/v1/events/stream", "/events/stream")


def _stream_path() -> str | None:
    """The live SSE route, or ``None`` while WP-1.10 is unlanded."""
    for candidate in _STREAM_CANDIDATES:
        try:
            resolve(candidate)
        except Resolver404:
            continue
        return candidate
    return None


@pytest.fixture
def owner(db: None) -> User:
    """The owner account devices register under."""
    return User.objects.create_user("owner", None, PASSWORD)


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


def _probe(api: APIClient, plaintext: str) -> Any:
    """One authenticated request carrying only the device credential."""
    return api.get(TOKEN_LIST_URL, headers={"Authorization": f"{_AUTH_SCHEME} {plaintext}"})


def _assert_alive(response: Any) -> None:
    """Authenticated-but-wrong-role: the credential still works (403)."""
    assert response.status_code == 403, response.content
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"


def _assert_rejected(response: Any) -> None:
    """Canonical immediate rejection on the very next use (401 catalog)."""
    assert response.status_code == 401, response.content
    error = _envelope(response)
    assert error["code"] == "AUTH_REQUIRED"
    assert error["code"] in CANONICAL_ERROR_CODES
    assert error["retryable"] is False


# --- immediate rejection ----------------------------------------------------


def test_revoked_device_is_rejected_on_its_next_rest_request(
    client: APIClient, owner: User
) -> None:
    """Section 19.1 acceptance: revoked device dies on the very next call."""
    _login(client, owner)
    body = _register(client)
    _assert_alive(_probe(client, body["token"]))  # live before the DELETE

    revoke = client.delete(f"{REGISTER_URL}/{body['id']}")
    assert revoke.status_code == 200
    assert revoke.json()["revoked_at"] is not None

    _assert_rejected(_probe(client, body["token"]))

    device = Device.objects.select_related("token").get(pk=body["id"])
    assert device.revoked_at is not None
    assert device.token.revoked_at is not None  # both rows, one action


def test_revoked_device_is_rejected_on_stream_reconnect(client: APIClient, owner: User) -> None:
    """Section 19.1 acceptance — conditional until WP-1.10 lands the route."""
    path = _stream_path()
    if path is None:
        pytest.skip(
            "GET /events/stream not landed yet (WP-1.10); reconnect rides the "
            "same TokenBearerAuthentication device check proven by the REST "
            "next-request test — live-connection semantics recorded in the "
            "WP changelog"
        )

    _login(client, owner)
    body = _register(client)
    before = client.get(path, headers={"Authorization": f"{_AUTH_SCHEME} {body['token']}"})
    assert before.status_code != 401, "device credential must connect while live"

    assert client.delete(f"{REGISTER_URL}/{body['id']}").status_code == 200

    after = client.get(path, headers={"Authorization": f"{_AUTH_SCHEME} {body['token']}"})
    _assert_rejected(after)


# --- independence and authorization (Section 12.2) --------------------------


def test_revocation_leaves_other_devices_tokens_and_sessions_working(
    client: APIClient, owner: User
) -> None:
    """Independently revocable: A dies, B / agent token / session survive."""
    _login(client, owner)
    device_a = _register(client)
    device_b = _register(client)
    agent = ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hashlib.sha256(AGENT_CREDENTIAL.encode()).hexdigest(),
        user=owner,
        project_id="PID00001",
    )

    assert client.delete(f"{REGISTER_URL}/{device_a['id']}").status_code == 200

    _assert_rejected(_probe(client, device_a["token"]))
    _assert_alive(_probe(client, device_b["token"]))

    # Still authenticating (403 = wrong role), not dead (401 would be dead).
    agent_response = client.get(
        TOKEN_LIST_URL,
        headers={"Authorization": f"{_AUTH_SCHEME} {AGENT_CREDENTIAL}"},
    )
    assert agent_response.status_code == 403
    assert agent.pk is not None

    # The Owner session is untouched by device revocation.
    assert client.get(TOKEN_LIST_URL).status_code == 200


def test_only_the_owning_owner_can_revoke(client: APIClient, owner: User, db: None) -> None:
    """Cross-owner denial; foreign and unknown ids answer identically."""
    other = User.objects.create_user("other", None, PASSWORD)
    _login(client, owner)
    body = _register(client)

    foreign_client = APIClient()
    _login(foreign_client, other)
    foreign = foreign_client.delete(f"{REGISTER_URL}/{body['id']}")
    unknown = foreign_client.delete(f"{REGISTER_URL}/999999")

    for response in (foreign, unknown):
        assert response.status_code == 400, response.content
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"
        assert error["code"] in CANONICAL_ERROR_CODES

    # Untouched: the device still authenticates for its owner.
    _assert_alive(_probe(client, body["token"]))


def test_anonymous_cannot_revoke(client: APIClient, owner: User) -> None:
    """No credential → catalog 401, never a side effect."""
    _login(client, owner)
    body = _register(client)
    client.logout()

    response = client.delete(f"{REGISTER_URL}/{body['id']}")
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"
    assert Device.objects.get(pk=body["id"]).revoked_at is None


# --- idempotency ------------------------------------------------------------


def test_revocation_is_idempotent_on_repeat(client: APIClient, owner: User) -> None:
    """Repeat DELETE returns the original instant; rejection is permanent."""
    _login(client, owner)
    body = _register(client)

    first = client.delete(f"{REGISTER_URL}/{body['id']}")
    second = client.delete(f"{REGISTER_URL}/{body['id']}")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["revoked_at"] == first.json()["revoked_at"]
    _assert_rejected(_probe(client, body["token"]))
    _assert_rejected(_probe(client, body["token"]))  # still dead, no recovery
