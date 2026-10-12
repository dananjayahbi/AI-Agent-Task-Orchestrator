"""MT-5.3-01 — device registration surface (Section 9.2; Sections 12.2, 20.4, 20.5).

Complements the WP-1.2 behavioral suite (``test_device_registration.py``)
with the MT-5.3-01 acceptance surface:

* **owner-session-only registration** — Section 12.2 "device registration
  after Owner login": anonymous callers get ``AUTH_REQUIRED`` (401), an
  agent credential gets ``ROLE_NOT_PERMITTED`` (403);
* **Section 9.2 surface exactness** (Section 20.5): ``/api/v1/devices``
  serves POST (register) plus GET (list, added by MT-5.3-04) and the
  detail route serves DELETE — every other method answers the catalog's
  ``VALIDATION_ERROR`` mapping of ``MethodNotAllowed`` (no 404/405 code
  exists; Section 20.4 item 5), so no route or verb is invented;
* **throttle wiring** on both device routes (FR-SEC-05) while the Owner
  list read stays outside the rule (asserted in ``test_device_list.py``);
* **``Idempotency-Key`` replay** on POST (the Section 9.2 rule that all
  mutating endpoints accept the header; ADR-012): same key + same body
  replays the original 201 **verbatim** without a second Device/token row;
  same key + different body executes normally (headers.md leaves the
  mismatch response open — no error is invented); no key means every call
  executes;
* the header is declared in the generated OpenAPI contract (NFR-11).

Deferred, recorded in the WP changelog rather than faked here: the
audit-event assertion (the MT-1.9-02 helper does not exist and the
Section 9.6 catalog has no device/token type — inventing either is out of
bounds), and live tunnel reachability (the Section 15.2 ``auth/devices``
allowlist group is WP-5.2 infrastructure; cross-checked against
MT-5.2-02's route allowlist — there is nothing backend-side to run).

Run with ``pytest backend/tests/test_device_registration_surface.py -v``
(MT test command; flat path deviation from the MT's ``tests/accounts/``
wording recorded in the WP changelog — WP-1.2 landed flat).
"""

from __future__ import annotations

import hashlib
from typing import Any, cast

import pytest
from django.urls import Resolver404, resolve
from drf_spectacular.generators import SchemaGenerator
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.views import DeviceCollectionView, DeviceRevokeView
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.core.throttling import DeviceEndpointThrottle

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"
TOKEN_LIST_URL = "/api/v1/tokens"

PASSWORD = "device-surface-tests-1!"  # pragma: allowlist secret
PUSH_TOKEN = "apns-device-surface-example"

# The scheme word stays separate from credential values; the canonical
# spelling lives on TokenBearerAuthentication.keyword.
_AUTH_SCHEME = "Bearer"
# Preimage of the agent row's stored hash — the bearer form is built from
# the same constant so hash and header can never drift.
AGENT_CREDENTIAL = "agent-for-surface-test"


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


def _payload(**extra: Any) -> dict[str, Any]:
    return {"platform": "ios", "push_token": PUSH_TOKEN, **extra}


# --- Section 9.2 surface exactness -----------------------------------------


def test_routes_resolve_to_the_documented_device_views() -> None:
    """Exactly the Section 9.2 paths — no neighbouring or wildcard routes."""
    collection = resolve(REGISTER_URL)
    assert getattr(collection.func, "view_class", None) is DeviceCollectionView

    detail = resolve(f"{REGISTER_URL}/12")
    assert getattr(detail.func, "view_class", None) is DeviceRevokeView

    # The detail route is int-keyed only: a non-integer segment is 404, not
    # some invented sub-resource (Section 20.5 — no invented routes).
    with pytest.raises(Resolver404):
        resolve(f"{REGISTER_URL}/not-an-id")


def test_only_documented_methods_are_allowed(client: APIClient, owner: User) -> None:
    """Allowed verbs are POST+GET (collection) and DELETE (detail) — 400 else."""
    _login(client, owner)

    assert client.post(REGISTER_URL, _payload()).status_code == 201
    assert client.get(REGISTER_URL).status_code == 200
    assert client.delete(f"{REGISTER_URL}/999999").status_code == 400

    for method in ("put", "patch", "delete"):
        response = getattr(client, method)(REGISTER_URL, _payload())
        assert response.status_code == 400, method
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"  # MethodNotAllowed mapping

    for method in ("get", "post", "put", "patch"):
        response = getattr(client, method)(f"{REGISTER_URL}/1", _payload())
        assert response.status_code == 400, method
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"


# --- owner-session guard (Section 12.2) -------------------------------------


def test_registration_requires_an_owner_session(client: APIClient, owner: User) -> None:
    """Anonymous 401 / agent 403 — both from the Section 9.2 catalog."""
    anonymous = client.post(REGISTER_URL, _payload())
    assert anonymous.status_code == 401
    error = _envelope(anonymous)
    assert error["code"] == "AUTH_REQUIRED"
    assert error["retryable"] is False
    assert error["code"] in CANONICAL_ERROR_CODES

    agent_row = ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hashlib.sha256(AGENT_CREDENTIAL.encode()).hexdigest(),
        user=owner,
        project_id="PID00001",
    )
    response = client.post(
        REGISTER_URL,
        _payload(),
        headers={"Authorization": f"{_AUTH_SCHEME} {AGENT_CREDENTIAL}"},
    )
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"
    assert agent_row.pk is not None  # created directly; plaintext never persisted


def test_refusals_use_only_catalog_codes(client: APIClient, owner: User) -> None:
    """Every error body is the five-field envelope with a catalog code."""
    _login(client, owner)

    bad_platform = client.post(REGISTER_URL, {"platform": "blackberry", "push_token": PUSH_TOKEN})
    missing_push = client.post(REGISTER_URL, {"platform": "ios"})
    unknown_detail = client.delete(f"{REGISTER_URL}/999999")
    invalid_cursor = client.get(REGISTER_URL, {"cursor": "not-base64-int!"})

    for response in (bad_platform, missing_push, unknown_detail, invalid_cursor):
        assert response.status_code == 400, response.content
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"
        assert error["code"] in CANONICAL_ERROR_CODES


# --- throttle wiring (FR-SEC-05) -------------------------------------------


def test_both_device_routes_declare_the_device_throttle() -> None:
    """The Mobile-caller row carries DeviceEndpointThrottle on every verb."""
    for path in (REGISTER_URL, f"{REGISTER_URL}/1"):
        view = getattr(resolve(path).func, "view_class", None)
        assert view is not None, path
        assert DeviceEndpointThrottle in getattr(view, "throttle_classes", []), path


# --- Idempotency-Key replay (Section 9.2; ADR-012) -------------------------


def test_idempotency_key_replays_registration_verbatim(client: APIClient, owner: User) -> None:
    """Same key + same body: the retry gets the original 201, no new rows."""
    _login(client, owner)
    payload = _payload(biometric_bound=True)
    headers = {"Idempotency-Key": "wp53-mt01-replay"}

    first = client.post(REGISTER_URL, payload, headers=headers)
    retry = client.post(REGISTER_URL, payload, headers=headers)

    assert first.status_code == 201, first.content
    assert retry.status_code == 201, retry.content
    assert retry.json() == first.json(), "replay must be indistinguishable"
    assert retry.json()["token"] == first.json()["token"]
    assert Device.objects.filter(user=owner).count() == 1
    assert ApiToken.objects.filter(kind=TokenKind.DEVICE).count() == 1


def test_idempotency_key_with_a_different_body_executes(client: APIClient, owner: User) -> None:
    """Fingerprint mismatch: no replay, the new request runs normally."""
    _login(client, owner)
    headers = {"Idempotency-Key": "wp53-mt01-mismatch"}

    first = client.post(REGISTER_URL, _payload(), headers=headers)
    second = client.post(REGISTER_URL, _payload(platform="android"), headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
    assert Device.objects.filter(user=owner).count() == 2


def test_registration_without_a_key_always_executes(client: APIClient, owner: User) -> None:
    """No header → no replay store: two calls register two devices."""
    _login(client, owner)

    first = client.post(REGISTER_URL, _payload())
    second = client.post(REGISTER_URL, _payload())

    assert first.status_code == 201
    assert second.status_code == 201
    assert Device.objects.filter(user=owner).count() == 2


def test_idempotency_key_is_declared_in_the_openapi_contract() -> None:
    """NFR-11: the canonical header is part of the generated client contract."""
    schema = SchemaGenerator().get_schema(  # type: ignore[no-untyped-call]
        request=None, public=True
    )
    assert schema is not None
    path_item = cast(dict[str, Any], schema["paths"][REGISTER_URL])
    operation = cast(dict[str, Any], path_item["post"])
    parameters = list(operation.get("parameters", [])) + list(path_item.get("parameters", []))
    names = {
        parameter["name"]
        for parameter in parameters
        if isinstance(parameter, dict) and parameter.get("in") == "header"
    }
    assert "Idempotency-Key" in names
