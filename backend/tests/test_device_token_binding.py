"""MT-5.3-02 — device-bound token issuance, binding, and release contract.

Pins the backend half of the Section 12.2/ADR-006 device-binding contract:

* **one token per registered device**, structurally bound to its Device row
  (distinct rows and hashes for two registrations of the same owner);
* **hash-at-rest** — the plaintext exists only in the 201 response, never
  in any column (Section 7.2);
* **expiry enforced** on the next request (Section 9.10 lifetime);
* **binding enforced**: a device credential whose Device row is revoked —
  or deleted (orphaned) — authenticates nowhere; a sibling device's token
  is unaffected (the token *is* the binding: authentication resolves the
  Device row through the token FK, so a token can never act as another
  device's credential);
* **edge identity is never sufficient** (Section 15.3 layer 2): Access-style
  headers without the Django bearer grant nothing;
* the **Section 12.2 "Device" matrix row** at the permission-class level —
  complementary to (not a copy of) ``tests/test_authorization_matrix.py``,
  which the file protocol keeps owned by another agent;
* the **release contract** for the mobile client exists and states the
  secure-storage / biometric-gate / cold-start / inactivity / edge rules
  (``docs/mobile/device-auth-release-contract.md``).

The server cannot verify a biometric — that trust boundary is documented
honestly in the release contract rather than tested away (MT risk note).

Run with ``pytest backend/tests/test_device_token_binding.py -v``
(flat path deviation from the MT's ``tests/accounts/`` wording recorded
in the WP changelog — WP-1.2 landed flat).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import Path
from typing import Any, cast

import pytest
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.permissions import (
    CanClaimAuditTasks,
    CanClaimPendingTasks,
    CanCreateDraftTasks,
    CanManageProjects,
    CanOperateMergeQueue,
    CanPublishTasks,
    CanReadEvents,
    CanReadMergeQueue,
    CanReviewDecisions,
    CanSubmitAuditVerdict,
    CanSubmitResolution,
    IsOwnerSession,
)
from apps.core.errors import CANONICAL_ERROR_CODES

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"
TOKEN_LIST_URL = "/api/v1/tokens"

PASSWORD = "device-binding-tests-1!"  # pragma: allowlist secret
PUSH_TOKEN = "apns-device-binding-example"

# The scheme word stays separate from credential values; the canonical
# spelling lives on TokenBearerAuthentication.keyword.
_AUTH_SCHEME = "Bearer"

RELEASE_CONTRACT = (
    Path(__file__).resolve().parents[2] / "docs" / "mobile" / "device-auth-release-contract.md"
)


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


# --- issuance: one bound, hashed, expiring token per device -----------------


def test_each_registration_issues_its_own_bound_token(client: APIClient, owner: User) -> None:
    """Two registrations → two distinct device tokens, each bound to its row."""
    _login(client, owner)
    first = _register(client)
    second = _register(client)

    device_a = Device.objects.select_related("token").get(pk=first["id"])
    device_b = Device.objects.select_related("token").get(pk=second["id"])

    assert device_a.token_id != device_b.token_id
    assert device_a.token.kind == TokenKind.DEVICE
    assert device_b.token.kind == TokenKind.DEVICE
    assert device_a.token.hash != device_b.token.hash
    assert first["token"] != second["token"]


def test_token_material_is_hashed_at_rest(client: APIClient, owner: User) -> None:
    """The plaintext lives only in the 201 body — SHA-256 in every column."""
    _login(client, owner)
    body = _register(client)

    device = Device.objects.select_related("token").get(pk=body["id"])
    plaintext = body["token"]
    assert device.token.hash == hashlib.sha256(plaintext.encode()).hexdigest()

    row_values = [str(field.value_from_object(device)) for field in Device._meta.fields]
    row_values += [str(field.value_from_object(device.token)) for field in ApiToken._meta.fields]
    assert plaintext not in row_values


def test_expired_device_token_is_rejected_on_the_next_request(
    client: APIClient, owner: User
) -> None:
    """Section 9.10 expiry is enforced per request — no grace window."""
    _login(client, owner)
    body = _register(client)
    device = Device.objects.select_related("token").get(pk=body["id"])
    assert _probe(client, body["token"]).status_code == 403  # live before

    device.token.expires_at = timezone.now() - timedelta(days=1)
    device.token.save(update_fields=["expires_at"])

    response = _probe(client, body["token"])
    assert response.status_code == 401
    error = _envelope(response)
    assert error["code"] == "AUTH_REQUIRED"
    assert error["code"] in CANONICAL_ERROR_CODES


# --- binding enforcement (ADR-006; FR-SEC-02) -------------------------------


def test_a_credential_is_bound_to_its_device_and_no_other(client: APIClient, owner: User) -> None:
    """Revoking device B kills B's token; device A's credential still works."""
    _login(client, owner)
    device_a = _register(client)
    device_b = _register(client)

    revoke = client.delete(f"{REGISTER_URL}/{device_b['id']}")
    assert revoke.status_code == 200

    dead = _probe(client, device_b["token"])
    assert dead.status_code == 401
    assert _envelope(dead)["code"] == "AUTH_REQUIRED"

    alive = _probe(client, device_a["token"])
    assert alive.status_code == 403  # authenticated, wrong row — not dead
    assert _envelope(alive)["code"] == "ROLE_NOT_PERMITTED"


def test_a_token_without_a_live_device_row_authenticates_nowhere(
    client: APIClient, owner: User
) -> None:
    """Orphaned credential (Device row gone, token row alive) fails closed."""
    _login(client, owner)
    body = _register(client)
    device = Device.objects.get(pk=body["id"])
    token_id = device.token_id

    device.delete()  # partial state the FK alone cannot express
    assert ApiToken.objects.filter(pk=token_id).exists()  # token survived

    response = _probe(client, body["token"])
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


def test_edge_identity_headers_alone_grant_nothing(client: APIClient, owner: User) -> None:
    """Section 15.3 layer 2: Access-style identity is never a credential."""
    response = client.get(
        TOKEN_LIST_URL,
        headers={
            "CF-Access-Client-Id": "edge-client-example",
            "CF-Access-Jwt-Assertion": "edge-assertion-example",
            "X-Forwarded-For": "203.0.113.9",
        },
    )
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


# --- Section 12.2 "Device" matrix row (permission classes) ------------------


def _as_credential(token: ApiToken, user: User) -> Request:
    """A DRF request whose ``auth`` is this exact token row (kind matters)."""
    request = Request(APIRequestFactory().get("/probe"))
    request.user = user
    request.auth = token
    return request


def test_device_matrix_row_authorizations(client: APIClient, owner: User) -> None:
    """Section 12.2 Device column: publish/review/events/drafts — nothing else."""
    _login(client, owner)
    body = _register(client)
    device = Device.objects.select_related("token").get(pk=body["id"])
    request = _as_credential(device.token, owner)

    granted = (
        CanPublishTasks,  # Publish tasks — Yes
        CanReviewDecisions,  # Review decisions — Yes
        CanReadEvents,  # Read events — Yes
        CanCreateDraftTasks,  # Create draft tasks — Could (granted, MT-1.4-03)
    )
    denied = (
        CanManageProjects,
        CanClaimPendingTasks,
        CanClaimAuditTasks,
        CanSubmitResolution,
        CanSubmitAuditVerdict,
        CanReadMergeQueue,
        CanOperateMergeQueue,
        IsOwnerSession,  # token/device management stays Owner-only (Section 9.2)
    )
    for granted_cls in granted:
        assert granted_cls().has_permission(request, None), granted_cls.__name__
    for denied_cls in denied:
        assert not denied_cls().has_permission(request, None), denied_cls.__name__


def test_device_credential_is_not_an_owner_session_on_the_wire(
    client: APIClient, owner: User
) -> None:
    """The same row over HTTP: 403 (wrong role), never owner-level access."""
    _login(client, owner)
    body = _register(client)
    client.logout()  # cookies gone — only the device credential remains

    response = _probe(client, body["token"])
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"


# --- release contract documentation (MT acceptance) -------------------------


def test_release_contract_documents_the_client_rules() -> None:
    """The documented client half exists and states every required rule."""
    assert RELEASE_CONTRACT.is_file(), (
        "docs/mobile/device-auth-release-contract.md is the MT-5.3-02 release-contract deliverable"
    )
    text = RELEASE_CONTRACT.read_text(encoding="utf-8").lower()
    for phrase in (
        "exactly once",
        "secure storage",
        "biometric",
        "cold start",
        "inactivity",
        "edge",
        "never sufficient",
    ):
        assert phrase in text, f"release contract must state: {phrase}"
