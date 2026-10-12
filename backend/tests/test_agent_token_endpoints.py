"""MT-1.2-03 — agent token issuance, listing and revocation (Section 9.2).

Covers the Tokens row end to end plus the bearer authentication that makes
the WP-1.2 acceptance testable:

* ``POST /tokens/agent`` (Owner-only) returns the plaintext **once** and
  persists only its SHA-256 hash with ``kind = agent`` + one ``project_id``
  (Section 7.2; ADR-004);
* ``GET /tokens`` returns metadata only, cursor-paginated with the exact
  pagination.md envelope (``results`` + ``next_cursor``), filterable by
  kind/project — never hashes or plaintext;
* ``DELETE /tokens/{id}`` sets ``revoked_at`` idempotently and the revoked
  token fails authentication on its **very next request** (WP-1.2
  acceptance: "revoked tokens fail immediately"; FR-SEC-02, no cache);
* ``last_used_at`` is maintained on successful bearer authentication
  (Section 7.2);
* failures use only Section 9.2 catalog codes: ``AUTH_REQUIRED``,
  ``ROLE_NOT_PERMITTED``, ``VALIDATION_ERROR``.

Run with ``pytest backend/tests -k "token"`` (MT test command).
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any, cast

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import ApiToken, TokenKind, User
from apps.accounts.services.tokens import generate_token

ISSUE_URL = "/api/v1/tokens/agent"
LIST_URL = "/api/v1/tokens"
LOGIN_URL = "/api/v1/auth/login"

PID_ONE = "PID00001"
PID_TWO = "PID00002"

PASSWORD = "agent-token-tests-1!"  # pragma: allowlist secret


@pytest.fixture
def owner(db: None) -> User:
    """The issuing owner account."""
    return User.objects.create_user(username="owner", password=PASSWORD)


@pytest.fixture
def client() -> APIClient:
    """Fresh API client; each test logs in explicitly when it needs a session."""
    return APIClient()


def _envelope(response: Any) -> dict[str, Any]:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return cast(dict[str, Any], error)


def _login(client: APIClient, user: User) -> None:
    response = client.post(LOGIN_URL, {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200, response.content


def _issue(client: APIClient, project_id: str = PID_ONE, **extra: Any) -> dict[str, Any]:
    response = client.post(ISSUE_URL, {"project_id": project_id, **extra})
    assert response.status_code == 201, response.content
    return cast(dict[str, Any], response.json())


def _bearer(plaintext: str) -> dict[str, str]:
    """Header form of the credential (Django test-client `headers=` mapping)."""
    return {"Authorization": f"Bearer {plaintext}"}


# --- POST /tokens/agent ----------------------------------------------------


def test_issue_returns_plaintext_once_and_stores_only_the_hash(
    client: APIClient, owner: User
) -> None:
    """201 contract: plaintext + metadata; the row holds no secret but hash."""
    _login(client, owner)

    body = _issue(client, scopes=["coder", "auditor"])

    # Exact response contract (risk note: a wrong shape strands the token).
    assert set(body) == {"id", "kind", "project_id", "scopes", "expires_at", "token"}
    assert body["kind"] == TokenKind.AGENT
    assert body["project_id"] == PID_ONE
    assert body["scopes"] == ["coder", "auditor"]

    plaintext = body["token"]
    assert isinstance(plaintext, str) and len(plaintext) >= 32
    row = ApiToken.objects.get(pk=body["id"])
    assert row.hash == hashlib.sha256(plaintext.encode()).hexdigest()
    assert row.kind == TokenKind.AGENT
    assert row.project_id == PID_ONE
    assert row.user_id == owner.pk
    stored = [str(field.value_from_object(row)) for field in ApiToken._meta.fields]
    assert plaintext not in stored
    # The plaintext never comes back through any later read.
    listed = client.get(LIST_URL)
    assert plaintext.encode() not in listed.content
    assert row.hash.encode() not in listed.content


def test_issue_is_owner_only(client: APIClient, owner: User) -> None:
    """Section 12.2 token management row: anonymous 401, agent 403."""
    anonymous = client.post(ISSUE_URL, {"project_id": PID_ONE})
    assert anonymous.status_code == 401
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"

    # An agent credential is *authenticated* but the wrong role (catalog 403).
    _login(client, owner)
    plaintext = _issue(client)["token"]
    client.logout()
    agent_post = client.post(ISSUE_URL, {"project_id": PID_ONE}, headers=_bearer(plaintext))
    assert agent_post.status_code == 403
    assert _envelope(agent_post)["code"] == "ROLE_NOT_PERMITTED"


def test_issue_validates_project_id_and_scopes(client: APIClient, owner: User) -> None:
    """Malformed PID or unknown role: 400 VALIDATION_ERROR, nothing written."""
    _login(client, owner)
    before = ApiToken.objects.count()

    for payload in (
        {"project_id": "not-a-pid"},
        {"project_id": "PID000001"},
        {"scopes": ["coder"]},  # missing project_id
        {"project_id": PID_ONE, "scopes": ["wizard"]},
    ):
        response = client.post(ISSUE_URL, payload)
        assert response.status_code == 400, payload
        assert _envelope(response)["code"] == "VALIDATION_ERROR"

    assert ApiToken.objects.count() == before


def test_issue_expiry_comes_from_the_agent_lifetime_setting(
    client: APIClient, owner: User, settings: Any
) -> None:
    """Section 9.10: one configuration knob drives issuance expiry."""
    settings.TOKEN_LIFETIME_AGENT_HOURS = 48
    _login(client, owner)

    body = _issue(client)

    expires_at = body["expires_at"]
    assert isinstance(expires_at, str)
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(expires_at)
    assert parsed is not None
    delta = parsed - timezone.now()
    assert abs(delta - timedelta(hours=48)) < timedelta(minutes=5)


# --- Bearer authentication + last_used_at (Section 7.2) --------------------


def test_bearer_authentication_succeeds_and_updates_last_used_at(
    client: APIClient, owner: User
) -> None:
    """A live agent token authenticates (403 on an Owner row, not 401)."""
    _login(client, owner)
    plaintext = _issue(client)["token"]
    client.logout()

    response = client.get(LIST_URL, headers=_bearer(plaintext))
    assert response.status_code == 403  # authenticated, wrong role
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"

    row = ApiToken.objects.get(hash=_hash_of(plaintext))
    assert row.last_used_at is not None  # hygiene field maintained


def test_unknown_and_malformed_bearer_credentials_fail_with_auth_required(
    client: APIClient,
    db: None,
) -> None:
    """Garbage or absent credentials: catalog 401, never a 500."""
    for header in (
        {"Authorization": "Bearer not-a-real-token"},
        {"Authorization": "Basic Zm9vOmJhcg=="},  # undefined scheme: pass-through
        {"Authorization": "Bearer"},  # malformed
    ):
        response = client.get(LIST_URL, headers=header)
        assert response.status_code == 401, header
        assert _envelope(response)["code"] == "AUTH_REQUIRED"


def _hash_of(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


# --- DELETE /tokens/{id} — immediate revocation (WP-1.2 acceptance) --------


def test_revoked_token_fails_authentication_on_its_very_next_request(
    client: APIClient, owner: User
) -> None:
    """The WP-1.2 acceptance half: revoke now, next call is AUTH_REQUIRED."""
    _login(client, owner)
    body = _issue(client)
    plaintext = body["token"]
    assert client.get(LIST_URL, headers=_bearer(plaintext)).status_code == 403  # live

    revoke = client.delete(f"{LIST_URL}/{body['id']}")
    assert revoke.status_code == 200
    assert revoke.json()["revoked_at"] is not None

    after = client.get(LIST_URL, headers=_bearer(plaintext))
    assert after.status_code == 401
    assert _envelope(after)["code"] == "AUTH_REQUIRED"

    # Idempotent: a repeated revoke returns the original instant.
    again = client.delete(f"{LIST_URL}/{body['id']}")
    assert again.status_code == 200
    assert again.json()["revoked_at"] == revoke.json()["revoked_at"]


def test_expired_token_fails_authentication(client: APIClient, owner: User) -> None:
    """Section 12.1 "expiring": past expiry dies on the next use."""
    _login(client, owner)
    body = _issue(client)
    row = ApiToken.objects.get(pk=body["id"])
    row.expires_at = timezone.now() - timedelta(seconds=1)
    row.save(update_fields=["expires_at"])
    client.logout()

    response = client.get(LIST_URL, headers=_bearer(body["token"]))
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


def test_unknown_and_foreign_ids_revoke_identically(
    client: APIClient, owner: User, db: None
) -> None:
    """No existence probing: unknown ids and other users' ids look the same."""
    other = User.objects.create_user(username="other", password=PASSWORD)
    _login(client, owner)
    body = _issue(client)

    unknown = client.delete(f"{LIST_URL}/999999")
    assert unknown.status_code == 400
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"  # no generic 404 code

    # A different owner's client must not revoke the first owner's token.
    other_client = APIClient()
    _login(other_client, other)
    foreign = other_client.delete(f"{LIST_URL}/{body['id']}")
    assert foreign.status_code == 400
    assert _envelope(foreign)["code"] == "VALIDATION_ERROR"
    assert ApiToken.objects.get(pk=body["id"]).revoked_at is None  # untouched


# --- GET /tokens — metadata list with the cursor envelope ------------------


def test_list_returns_metadata_only_without_secrets(client: APIClient, owner: User) -> None:
    """No ``hash`` and no ``token`` member can ever appear in list items."""
    _login(client, owner)
    body = _issue(client)

    response = client.get(LIST_URL)
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"results", "next_cursor"}
    item_keys = {
        "id",
        "kind",
        "project_id",
        "scopes",
        "expires_at",
        "revoked_at",
        "last_used_at",
    }
    for item in payload["results"]:
        assert set(item) == item_keys
    assert any(item["id"] == body["id"] for item in payload["results"])
    stored_hash = ApiToken.objects.get(pk=body["id"]).hash
    assert stored_hash not in response.content.decode()


def test_list_paginates_with_opaque_cursor(client: APIClient, owner: User) -> None:
    """pagination.md: 25 default/100 max, newest first, next_cursor drives pages.

    The cursor math runs over the three **agent** rows (``kind=agent`` filter,
    one of the endpoint's documented filters): login's own ``owner_session``
    row shares the table and would otherwise spill onto page two, which would
    test the filter rather than the cursor. The unfiltered shape — session row
    included, still one default-size page — is asserted at the end.
    """
    _login(client, owner)
    ids = [_issue(client)["id"] for _ in range(3)]

    first_params: dict[str, str | int] = {"page_size": 2, "kind": "agent"}
    first = client.get(LIST_URL, first_params)
    assert first.status_code == 200
    page_one = first.json()
    assert len(page_one["results"]) == 2
    assert page_one["next_cursor"]  # more pages exist
    assert [item["id"] for item in page_one["results"]] == list(reversed(ids))[:2]

    page_params: dict[str, str | int] = {
        "page_size": 2,
        "cursor": str(page_one["next_cursor"]),
        "kind": "agent",
    }
    second = client.get(LIST_URL, page_params)
    page_two = second.json()
    assert [item["id"] for item in page_two["results"]] == ids[:1]
    assert page_two["next_cursor"] is None  # end of list signal alone

    # Default page size: the three tokens plus the owner_session row fit
    # within 25, so one page, no cursor needed.
    only = client.get(LIST_URL)
    assert only.json()["next_cursor"] is None

    # page_size above the documented maximum is clamped, not rejected.
    clamped = client.get(LIST_URL, {"page_size": 1000})
    assert clamped.status_code == 200

    # A malformed cursor is a catalog validation error, not a crash.
    bad = client.get(LIST_URL, {"cursor": "%%%%"})
    assert bad.status_code == 400
    assert _envelope(bad)["code"] == "VALIDATION_ERROR"


def test_list_filters_by_kind_and_project(client: APIClient, owner: User) -> None:
    """Section 9.2: filterable by project/kind; bad filters are 400s."""
    _login(client, owner)
    agent_one = _issue(client, project_id=PID_ONE)
    agent_two = _issue(client, project_id=PID_TWO)

    by_project = client.get(LIST_URL, {"project_id": PID_ONE})
    assert by_project.status_code == 200
    assert [item["id"] for item in by_project.json()["results"]] == [agent_one["id"]]

    by_kind_project = client.get(LIST_URL, {"kind": TokenKind.AGENT, "project_id": PID_TWO})
    assert [item["id"] for item in by_kind_project.json()["results"]] == [agent_two["id"]]

    sessions = client.get(LIST_URL, {"kind": TokenKind.OWNER_SESSION})
    kinds = {item["kind"] for item in sessions.json()["results"]}
    assert kinds == {TokenKind.OWNER_SESSION}

    for params in ({"kind": "wizard"}, {"project_id": "PID1"}):
        response = client.get(LIST_URL, params)
        assert response.status_code == 400
        assert _envelope(response)["code"] == "VALIDATION_ERROR"


def test_list_is_owner_only(client: APIClient, owner: User) -> None:
    """Anonymous callers get AUTH_REQUIRED on the list endpoint too."""
    response = client.get(LIST_URL)
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


# --- Guard: plaintext generation helper stays honest -----------------------


def test_issued_plaintext_is_unguessable_material() -> None:
    """Sanity for the minting primitive the issuance path depends on."""
    first, second = generate_token(), generate_token()
    assert first != second
    assert len(first) >= 43  # 32 bytes urlsafe-base64 encoded
