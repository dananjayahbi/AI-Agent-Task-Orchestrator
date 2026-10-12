"""MT-5.3-04 backend surface — ``GET /devices`` (Section 13.1 account settings).

The Owner-facing list half of "devices (list and revoke)":

* **owner-session-only** (Section 9.2 caller column): anonymous 401
  ``AUTH_REQUIRED``, agent credential 403 ``ROLE_NOT_PERMITTED``;
* **metadata only** — never ``push_token`` (Section 12.4), never token
  material (Section 7.2); revoked devices stay listed with ``revoked_at``
  set so settings can show history;
* **pagination.md envelope** — exactly ``results`` + ``next_cursor``,
  ``-pk`` (newest first) stable sort, ``cursor``/``page_size`` query
  contract, canonical errors for bad input (Section 20.4 item 5);
* **the Owner read is not throttled** while POST registration keeps
  ``DeviceEndpointThrottle`` (FR-SEC-05 never widens to Owner rows).

Section 9.2 does not list ``GET /devices`` yet — the route lands here with
**OQ-15** raised for the plan amendment (Section 22), flagged in the WP
changelog per MT-5.3-01's risk note rather than added silently. The web
UI that consumes this endpoint is the WP changelog's web follow-up note
(web account-settings components are not in this file's scope).

Run with ``pytest backend/tests/test_device_list.py -v`` (flat path
deviation recorded in the WP changelog — WP-1.2 landed flat).
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.urls import resolve
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, TokenKind, User
from apps.accounts.views import DeviceCollectionView
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.core.throttling import DeviceEndpointThrottle

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"
TOKEN_LIST_URL = "/api/v1/tokens"

PASSWORD = "device-list-tests-1!"  # pragma: allowlist secret
PUSH_TOKEN = "apns-device-list-secret-never-echoed"

# The scheme word stays separate from credential values; the canonical
# spelling lives on TokenBearerAuthentication.keyword.
_AUTH_SCHEME = "Bearer"
# Preimage of the agent row's stored hash — bearer form built from the same
# constant so hash and header can never drift.
AGENT_CREDENTIAL = "agent-probe-device-list"

ITEM_FIELDS = {"id", "platform", "biometric_bound", "last_seen_at", "revoked_at", "expires_at"}


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """LocMem throttle/idempotency history is process state — never leak it."""
    cache.clear()
    yield
    cache.clear()


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


def _set_rates(settings: Any, **rates: str) -> None:
    """Override DEFAULT_THROTTLE_RATES, keeping the rest of DRF's config."""
    rest = dict(settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest.get("DEFAULT_THROTTLE_RATES", {}), **rates}
    settings.REST_FRAMEWORK = rest


# --- guard and access control -----------------------------------------------


def test_list_shares_the_collection_route_and_write_throttle_stays() -> None:
    """GET rides the Section 9.2 ``/devices`` path; POST keeps its throttle."""
    view = getattr(resolve(REGISTER_URL).func, "view_class", None)
    assert view is DeviceCollectionView
    assert DeviceEndpointThrottle in view.throttle_classes  # registration stays


def test_list_requires_an_owner_session(client: APIClient, owner: User) -> None:
    """Anonymous 401 / agent 403 — the Section 9.2 caller column."""
    anonymous = client.get(REGISTER_URL)
    assert anonymous.status_code == 401
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"

    _login(client, owner)
    agent = ApiToken.objects.create(
        kind=TokenKind.AGENT,
        hash=hashlib.sha256(AGENT_CREDENTIAL.encode()).hexdigest(),
        user=owner,
        project_id="PID00001",
    )
    response = client.get(
        REGISTER_URL,
        headers={"Authorization": f"{_AUTH_SCHEME} {AGENT_CREDENTIAL}"},
    )
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"
    assert agent.pk is not None


# --- payload contract -------------------------------------------------------


def test_lists_only_own_devices_with_metadata_only(
    client: APIClient, owner: User, db: None
) -> None:
    """Owner-scoped rows; exact item shape; no push token, no token material."""
    other = User.objects.create_user("other", None, PASSWORD)
    other_client = APIClient()
    _login(other_client, other)
    _register(other_client)

    _login(client, owner)
    mine = _register(client)
    plaintext = mine["token"]

    response = client.get(REGISTER_URL)
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"results", "next_cursor"}

    results = body["results"]
    assert [row["id"] for row in results] == [mine["id"]]  # other owner invisible
    assert set(results[0]) == ITEM_FIELDS
    assert results[0]["platform"] == "ios"
    assert results[0]["revoked_at"] is None
    assert results[0]["expires_at"] is not None

    text = response.text
    assert PUSH_TOKEN not in text, "push_token is sensitive at rest (12.4)"
    assert plaintext not in text, "token material never leaves the server"
    assert "hash" not in results[0]


def test_revoked_devices_stay_listed_with_history(client: APIClient, owner: User) -> None:
    """Settings shows revoked rows (revoked_at set) instead of hiding them."""
    _login(client, owner)
    body = _register(client)
    assert client.delete(f"{REGISTER_URL}/{body['id']}").status_code == 200

    results = client.get(REGISTER_URL).json()["results"]
    row = next(item for item in results if item["id"] == body["id"])
    assert row["revoked_at"] is not None


# --- pagination contract (pagination.md) ------------------------------------


def test_pages_newest_first_until_the_cursor_runs_out(client: APIClient, owner: User) -> None:
    """cursor/page_size contract: one row per page, -pk order, terminal None."""
    _login(client, owner)
    ids = [_register(client)["id"] for _ in range(3)]

    collected: list[int] = []
    cursor: str | None = None
    for _ in range(10):  # bounded loop — a runaway cursor fails the test
        query: dict[str, Any] = {"page_size": 1}
        if cursor is not None:
            query["cursor"] = cursor
        response = client.get(REGISTER_URL, query)
        assert response.status_code == 200, response.content
        page = response.json()
        assert set(page) == {"results", "next_cursor"}
        assert len(page["results"]) == 1
        collected.append(page["results"][0]["id"])
        cursor = page["next_cursor"]
        if cursor is None:
            break

    assert collected == sorted(ids, reverse=True)  # declared -pk sort
    assert cursor is None  # end signalled by null, not an empty page


def test_invalid_cursor_and_page_size_are_canonical_errors(client: APIClient, owner: User) -> None:
    """Bad query input → catalog VALIDATION_ERROR, five-field envelope."""
    _login(client, owner)

    bad_cursor = client.get(REGISTER_URL, {"cursor": "not-base64-int!"})
    bad_size = client.get(REGISTER_URL, {"page_size": 0})

    for response in (bad_cursor, bad_size):
        assert response.status_code == 400, response.content
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"
        assert error["code"] in CANONICAL_ERROR_CODES


# --- FR-SEC-05 scope: the Owner read is not throttled ------------------------


def test_owner_list_read_is_not_throttled(client: APIClient, owner: User, settings: Any) -> None:
    """device=1/min: POST enforces it, GET stays outside the rule."""
    _set_rates(settings, device="1/min")
    _login(client, owner)

    payload = {"platform": "ios", "push_token": PUSH_TOKEN}
    assert client.post(REGISTER_URL, payload).status_code == 201  # under budget
    throttled = client.post(REGISTER_URL, payload)  # write side enforces it
    assert throttled.status_code == 429

    for _ in range(5):  # far beyond the configured budget — read is exempt
        assert client.get(REGISTER_URL).status_code == 200
