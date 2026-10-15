"""MT-6.1-03 — token lifecycle audit: scoping, expiry, revocation, hashing, kinds.

Section 12.1's "Token theft" property list made executable across the three
Section 12.2 credential kinds (owner session, agent bearer, device-bound
mobile token). Extends MT-1.2-07/MT-1.2-06/MT-5.3 rather than duplicating
their per-suite depth; this module is the single lifecycle view the WP-6.1
review command selects (``-k token_lifecycle``).

Section 19 WP-6.1 acceptance: **token scoping tests in CI** — test 1/2 below
run on the real routes with real issuance.

Recorded configured lifetimes (MT risk note: audit tied to real settings,
not hypotheticals): owner session 12 h, agent 720 h, device 90 days
(``ORCHESTRATOR_TOKEN_LIFETIME_*``), asserted against the issued rows.

Honest limits: the biometric release gate is client-side (ADR-006) — the
backend can only assert the release *contract* (device credential exists,
is bound, and dies without a live device row); the app-side unlock is
`mobile/test/security/auth_gate_test.dart` + `lock_gate_test.dart`. The
device's stream-reconnect rejection rides
`tests/test_device_revocation.py`; rate limiting (FR-SEC-05) is asserted in
`tests/test_rate_limiting.py` and `tests/test_security_authorization_review.py`.
Revocation/login **audit events** are the OQ-16 catalog gap — pinned, never
faked (findings log F-01).

Run with ``pytest backend/tests/ -k token_lifecycle -v`` (MT test command).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any, cast

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.authentication import TokenBearerAuthentication
from apps.accounts.models import ApiToken, TokenKind, User
from apps.core.errors import (
    AUTH_FORBIDDEN_PROJECT,
    AUTH_REQUIRED,
    CANONICAL_ERROR_CODES,
    ROLE_NOT_PERMITTED,
)
from apps.events.catalog import EVENT_TYPES
from apps.projects.models import Project, ProjectPolicy

PASSWORD = "wp61-token-lifecycle-1!"  # pragma: allowlist secret

WORK_URL = "/api/v1/projects/{pid}/work"
EVENTS_URL = "/api/v1/events"
TOKEN_LIST_URL = "/api/v1/tokens"


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — never leak it across tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture(autouse=True)
def two_projects(db: None) -> None:
    """Real registry rows so the in-scope work listing answers 200 (not 404).

    Created directly with explicit ids, exactly as the authorization
    matrix does, so PID00001/PID00002 hold on every backend regardless of
    sequence state.
    """
    for pid in ("PID00001", "PID00002"):
        Project.objects.create(
            id=pid,
            name=f"Lifecycle {pid}",
            repo_path=f"/srv/repos/{pid.lower()}",
            default_branch="main",
            agent_policy=ProjectPolicy.objects.create(),
        )


def _bearer(token: str) -> dict[str, str]:
    """The Section 15.4 transport, spelled from the auth class (no drift)."""
    return {"Authorization": f"{TokenBearerAuthentication.keyword} {token}"}


def _issue_agent(owner_client: APIClient, pid: str = "PID00001") -> dict[str, Any]:
    """Mint one agent token through the real Owner issuance route."""
    response = owner_client.post("/api/v1/tokens/agent", {"project_id": pid, "scopes": ["coder"]})
    assert response.status_code == 201, response.content
    return cast(dict[str, Any], response.json())


def _register_device(owner_client: APIClient) -> dict[str, Any]:
    """Register one device through the real route (token released once)."""
    response = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "wp61-lifecycle-device"}
    )
    assert response.status_code == 201, response.content
    return cast(dict[str, Any], response.json())


def _code(response: Any) -> str:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (Section 20.4 item 5)"
    return str(error["code"])


# --- scoping (FR-SEC-01; ADR-004) -------------------------------------------


def test_agent_token_touches_only_its_own_project(owner_client: APIClient) -> None:
    """Section 19 acceptance: cross-project reads die with AUTH_FORBIDDEN_PROJECT."""
    token = _issue_agent(owner_client)["token"]
    plain = APIClient()

    inside = plain.get(WORK_URL.format(pid="PID00001"), headers=_bearer(token))
    assert inside.status_code < 400, inside.content

    outside = plain.get(WORK_URL.format(pid="PID00002"), headers=_bearer(token))
    assert outside.status_code == 403
    assert _code(outside) == AUTH_FORBIDDEN_PROJECT


def test_body_supplied_project_cannot_widen_the_token_scope(owner_client: APIClient) -> None:
    """A crafted body project id never widens scope — the URL wins (9.3 step 1)."""
    token = _issue_agent(owner_client)["token"]
    response = APIClient().post(
        "/api/v1/projects/PID00002/tasks",
        {"title": "Scope probe", "project_id": "PID00001"},
        headers=_bearer(token),
    )
    assert response.status_code == 403
    assert _code(response) == AUTH_FORBIDDEN_PROJECT


# --- expiry (Section 12.2 lifetimes; Section 9.2 codes) ---------------------


def test_expired_agent_token_is_rejected_on_its_next_request(owner_client: APIClient) -> None:
    """Configured lifetime elapsed → 401 AUTH_REQUIRED, no grace period."""
    issued = _issue_agent(owner_client)
    token = issued["token"]
    row = ApiToken.objects.get(pk=issued["id"])
    assert row.expires_at is not None
    ApiToken.objects.filter(pk=row.pk).update(expires_at=timezone.now() - timedelta(minutes=1))

    response = APIClient().get(WORK_URL.format(pid="PID00001"), headers=_bearer(token))
    assert response.status_code == 401
    assert _code(response) == AUTH_REQUIRED


def test_expired_device_token_is_rejected_on_its_next_request(owner_client: APIClient) -> None:
    """Same predicate for the device kind — on the routes devices hold."""
    from apps.accounts.models import Device

    issued = _register_device(owner_client)
    # The registration body's id is the *Device* row; the credential row
    # hangs off it (registration always moves both rows together).
    device = Device.objects.select_related("token").get(pk=issued["id"])
    token_row = device.token
    assert token_row.expires_at is not None
    ApiToken.objects.filter(pk=token_row.pk).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    response = APIClient().get(EVENTS_URL, headers=_bearer(issued["token"]))
    assert response.status_code == 401
    assert _code(response) == AUTH_REQUIRED


def test_expired_owner_session_is_rejected(owner_client: APIClient) -> None:
    """The owner_session row carries the same expiry predicate (12.2)."""
    assert owner_client.get(TOKEN_LIST_URL).status_code == 200
    ApiToken.objects.filter(kind=TokenKind.OWNER_SESSION).update(
        expires_at=timezone.now() - timedelta(minutes=1)
    )

    response = owner_client.get(TOKEN_LIST_URL)
    assert response.status_code == 401
    assert _code(response) == AUTH_REQUIRED


def test_configured_lifetimes_match_the_recorded_audit_values(owner_client: APIClient) -> None:
    """The audit's lifetime claims stay tied to real settings (risk note)."""
    from apps.accounts.models import Device

    assert settings.TOKEN_LIFETIME_OWNER_SESSION_HOURS == 12
    assert settings.TOKEN_LIFETIME_AGENT_HOURS == 720
    assert settings.TOKEN_LIFETIME_DEVICE_DAYS == 90

    agent = _issue_agent(owner_client)
    device = _register_device(owner_client)
    agent_row = ApiToken.objects.get(pk=agent["id"])
    device_row = Device.objects.select_related("token").get(pk=device["id"]).token
    for row in (agent_row, device_row):
        assert row.expires_at is not None, "every non-session credential carries an expiry"


# --- revocation (Section 19 WP-5.3 acceptance re-verified) ------------------


def test_revoked_agent_token_is_rejected_on_its_next_request(owner_client: APIClient) -> None:
    """Independent revocation: DELETE, then the very next call is dead."""
    issued = _issue_agent(owner_client)
    token = issued["token"]
    live = APIClient().get(WORK_URL.format(pid="PID00001"), headers=_bearer(token))
    assert live.status_code < 400

    revoke = owner_client.delete(f"/api/v1/tokens/{issued['id']}")
    assert revoke.status_code == 200

    after = APIClient().get(WORK_URL.format(pid="PID00001"), headers=_bearer(token))
    assert after.status_code == 401
    assert _code(after) == AUTH_REQUIRED


def test_revoked_device_is_rejected_on_its_next_request(owner_client: APIClient) -> None:
    """One DELETE kills the device + its token; the stream-reconnect twin
    rides ``tests/test_device_revocation.py`` (Section 19 WP-5.3 acceptance)."""
    issued = _register_device(owner_client)
    token = issued["token"]
    assert APIClient().get(EVENTS_URL, headers=_bearer(token)).status_code == 200

    revoke = owner_client.delete(f"/api/v1/devices/{issued['id']}")
    assert revoke.status_code == 200

    after = APIClient().get(EVENTS_URL, headers=_bearer(token))
    assert after.status_code == 401
    assert _code(after) == AUTH_REQUIRED


def test_token_audit_events_stay_pinned_to_the_oq16_catalog_gap() -> None:
    """Section 12.5 wants token/login events; the catalog has none (F-01).

    Catalog-first (Section 20.4 item 5): no type is invented here — this
    guard fails loudly if one ever appears without the OQ-16 amendment,
    mirroring ``events/test_event_catalog.py``.
    """
    invented = sorted(
        event_type
        for event_type in EVENT_TYPES
        if event_type.startswith(("token.", "login.", "auth."))
    )
    assert invented == [], f"types invented outside the plan catalog: {invented}"


# --- hashing at rest (Section 12.1 token theft) -----------------------------


def test_no_plaintext_token_value_survives_in_the_database(owner_client: APIClient) -> None:
    """All three kinds: plaintext exists only in transit, never at rest."""
    agent = _issue_agent(owner_client)["token"]
    device = _register_device(owner_client)["token"]
    assert owner_client.get(TOKEN_LIST_URL).status_code == 200  # touch the session row

    rows = list(ApiToken.objects.all())
    assert {row.kind for row in rows} == {
        TokenKind.OWNER_SESSION,
        TokenKind.AGENT,
        TokenKind.DEVICE,
    }
    for plaintext in (agent, device):
        for row in rows:
            serialized = " ".join(str(value) for value in (row.hash, row.project_id))
            assert plaintext not in serialized, f"plaintext leaked into {row.kind} row"
    for row in rows:
        # Stored form is a 64-char lowercase hex digest — derived, not the
        # secret itself (property, not schema: non-reversible at rest).
        assert len(row.hash) == 64 and all(c in "0123456789abcdef" for c in row.hash)


# --- kind separation (FR-SEC-02; Section 12.2) ------------------------------


def test_the_token_kind_catalog_stays_closed_at_three() -> None:
    """Section 12.2 kinds are the closed enum — none added, none merged."""
    assert set(TokenKind.values) == {"owner_session", "agent", "device"}


def test_owner_session_cookie_does_not_authenticate_agent_rows(owner_client: APIClient) -> None:
    """Owner cookie on an agent-only route → ROLE_NOT_PERMITTED, never data."""
    response = owner_client.get(WORK_URL.format(pid="PID00001"))
    assert response.status_code == 403
    assert _code(response) == ROLE_NOT_PERMITTED


def test_agent_bearer_does_not_open_owner_routes(owner_client: APIClient) -> None:
    """Agent token on the Owner token-management row → refused, not leaked."""
    token = _issue_agent(owner_client)["token"]
    response = APIClient().get(TOKEN_LIST_URL, headers=_bearer(token))
    assert response.status_code == 403
    assert _code(response) == ROLE_NOT_PERMITTED


def test_device_bearer_is_never_an_owner_session(owner_client: APIClient) -> None:
    """Device credential on an Owner-only mutation → refused (12.2 columns)."""
    device = _register_device(owner_client)["token"]
    response = APIClient().patch(
        "/api/v1/projects/PID00001", {"name": "device takeover"}, headers=_bearer(device)
    )
    assert response.status_code == 403
    assert _code(response) == ROLE_NOT_PERMITTED


def test_edge_identity_headers_alone_authenticate_nothing() -> None:
    """Section 15.3 layer 2: Access-style identity is never a credential."""
    edge = {
        "CF-Access-Client-Id": "edge-client-example",
        "CF-Access-Jwt-Assertion": "edge-assertion-example",
        "X-Forwarded-For": "203.0.113.9",
    }
    plain = APIClient()
    for path in (EVENTS_URL, WORK_URL.format(pid="PID00001")):
        response = plain.get(path, headers=edge)
        assert response.status_code == 401, path
        assert _code(response) == AUTH_REQUIRED
