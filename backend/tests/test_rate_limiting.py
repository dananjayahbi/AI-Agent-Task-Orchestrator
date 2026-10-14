"""MT-1.2-06 — rate limiting on agent and device endpoints (FR-SEC-05).

Proves the MT's acceptance criteria against the running API:

* under-limit requests pass; a burst over the configured limit returns the
  Section 9.2 envelope with the catalog code ``RATE_LIMITED`` (429,
  ``retryable: true`` — MT-0.5-02's envelope, ``Throttled`` mapping in
  ``apps/core/exceptions.py``);
* the budget is keyed per **authenticated token** (Section 12.3 layering —
  two sessions never share a budget) with a client-address fallback for
  unauthenticated callers;
* a window reset lets requests through again (no permanent lockout);
* **owner-session endpoints are not throttled** — FR-SEC-05 scopes this rule
  to agent and device endpoints and must not be silently widened;
* an endpoint-coverage test enumerates every Section 9.2 endpoint whose
  caller column is Agent/Auditor/Bridge/Mobile (FR-SEC-05: *all* of them):
  present routes must carry their throttle, deferred ones must not exist yet
  — a route landing without its throttle (or without flipping its row here)
  fails the suite, so the rule cannot be forgotten;
* limits trace to the Section 9.10 ``ORCHESTRATOR_RATE_LIMIT_*`` settings —
  no magic numbers.

Run with ``pytest backend/tests -k "ratelimit or throttle"`` (MT test command).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any, NamedTuple, cast

import pytest
from django.core.cache import cache
from django.urls import Resolver404, resolve
from rest_framework.request import Request
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.models import ApiToken, TokenKind, User
from apps.accounts.views import (
    AgentTokenIssueView,
    LoginView,
    LogoutView,
    RefreshView,
    TokenListView,
    TokenRevokeView,
)
from apps.core.errors import CANONICAL_ERROR_CODES, RATE_LIMITED
from apps.core.throttling import (
    AgentEndpointThrottle,
    DeviceEndpointThrottle,
    TokenKeyedRateThrottle,
)

REGISTER_URL = "/api/v1/devices"
REVOKE_URL = "/api/v1/devices/1"  # any id — throttling happens before the view
TOKEN_LIST_URL = "/api/v1/tokens"
LOGIN_URL = "/api/v1/auth/login"

PASSWORD = "rate-limit-tests-1!"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """LocMem throttle history is process state — never leak it across tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner(db: None) -> User:
    """The owner account used to open a session for device requests."""
    return User.objects.create_user("owner", None, PASSWORD)


@pytest.fixture
def client() -> APIClient:
    """Fresh API client per test."""
    return APIClient()


def _login(api: APIClient, user: User) -> None:
    response = api.post(LOGIN_URL, {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200, response.content


def _register(api: APIClient) -> Any:
    return api.post(REGISTER_URL, {"platform": "ios", "push_token": "apns-rate-test"})


def _set_rates(settings: Any, **rates: str) -> None:
    """Override DEFAULT_THROTTLE_RATES, keeping the rest of DRF's config.

    ``TokenKeyedRateThrottle.get_rate`` reads ``api_settings`` per request,
    and DRF reloads them on the ``setting_changed`` signal the pytest-django
    ``settings`` fixture fires.
    """
    rest = dict(settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest.get("DEFAULT_THROTTLE_RATES", {}), **rates}
    settings.REST_FRAMEWORK = rest


def _envelope(response: Any) -> dict[str, Any]:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return cast(dict[str, Any], error)


# --- behaviour under the limit / over the limit -----------------------------


def test_under_limit_requests_pass(client: APIClient, owner: User, settings: Any) -> None:
    """A burst that stays inside the budget is never touched by the throttle."""
    _set_rates(settings, device="3/min")
    _login(client, owner)

    for _ in range(3):
        assert _register(client).status_code == 201


def test_over_limit_returns_the_rate_limited_envelope(
    client: APIClient, owner: User, settings: Any
) -> None:
    """FR-SEC-05 + Section 9.2: 429 with catalog RATE_LIMITED, retryable."""
    _set_rates(settings, device="2/min")
    _login(client, owner)

    assert _register(client).status_code == 201
    assert _register(client).status_code == 201

    throttled = _register(client)
    assert throttled.status_code == 429
    error = _envelope(throttled)
    assert error["code"] == RATE_LIMITED
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    assert error["retryable"] is True, "RATE_LIMITED is a retryable failure"
    assert error["correlation_id"], "the envelope carries this exchange's id"
    assert throttled.headers.get("Retry-After"), "clients get the wait hint (NFR-12)"


def test_budget_is_keyed_per_token_not_shared_between_sessions(
    client: APIClient, owner: User, settings: Any
) -> None:
    """Two sessions = two budgets (Section 12.3: key on the credential)."""
    _set_rates(settings, device="2/min")

    _login(client, owner)
    assert _register(client).status_code == 201
    assert _register(client).status_code == 201
    assert _register(client).status_code == 429  # first session's budget spent

    # A second login issues a second owner_session row: a fresh token key
    # starts a fresh budget even though caller, address and body are identical.
    _login(client, owner)
    assert _register(client).status_code == 201
    assert _register(client).status_code == 201


def test_window_reset_allows_requests_again(client: APIClient, owner: User, settings: Any) -> None:
    """History older than the window is dropped — throttling is not a ban."""
    _set_rates(settings, device="2/sec")
    _login(client, owner)

    assert _register(client).status_code == 201
    assert _register(client).status_code == 201
    assert _register(client).status_code == 429

    time.sleep(1.1)  # past the one-second window

    assert _register(client).status_code == 201


def test_owner_session_endpoints_are_not_throttled(
    client: APIClient, owner: User, settings: Any
) -> None:
    """FR-SEC-05 scope respected: agent/device rule never widens to Owner."""
    _set_rates(settings, device="1/min", agent="1/min")
    _login(client, owner)

    for _ in range(5):  # far beyond every configured budget
        assert client.get(TOKEN_LIST_URL).status_code == 200
        assert client.post("/api/v1/auth/refresh").status_code == 200


def test_owner_session_views_declare_no_throttles() -> None:
    """Static half of the FR-SEC-05 scope: no throttle class on Owner rows."""
    for view in (
        LoginView,
        LogoutView,
        RefreshView,
        AgentTokenIssueView,
        TokenListView,
        TokenRevokeView,
    ):
        assert getattr(view, "throttle_classes", []) == [], view.__name__


# --- Section 9.2 endpoint enumeration (FR-SEC-05: ALL of them) --------------


class _Route(NamedTuple):
    """One Section 9.2 row in the Agent/Auditor/Bridge/Mobile caller column."""

    path: str
    throttle: type[TokenKeyedRateThrottle]
    lands_with: str  # WP/Micro-task that must wire the throttle when it lands
    present: bool  # True: exists after WP-1.2 and must carry the throttle


AGENT_OR_DEVICE_ROUTES: tuple[_Route, ...] = (
    # --- Devices row (Mobile): present with MT-1.2-04, throttled by MT-1.2-06
    _Route(REGISTER_URL, DeviceEndpointThrottle, "MT-1.2-04", True),
    _Route(REVOKE_URL, DeviceEndpointThrottle, "MT-1.2-04", True),
    # --- Agent work row (Agent): landed with MT-1.6-07 (WP-1.6) --------
    _Route("/api/v1/projects/PID00001/work", AgentEndpointThrottle, "MT-1.6-07", True),
    _Route("/api/v1/tasks/1/claim", AgentEndpointThrottle, "MT-1.6-07", True),
    _Route("/api/v1/tasks/1/release", AgentEndpointThrottle, "MT-1.6-07", True),
    # --- Progress row (Agent / Owner): landed with MT-1.8-03 (WP-1.8) ---
    # The shared GET+POST route carries AgentEndpointThrottle on the view
    # class (the write half is the agent-authenticated cell); an owner
    # GET rides the same class budget — recorded in the WP-1.8 changelog.
    _Route("/api/v1/tasks/1/checkpoints", AgentEndpointThrottle, "MT-1.8-03", True),
    # --- Submission row (Agent / Owner): landed with WP-3.2 --------------
    # The POST carries the throttle on the view class (FR-SEC-05); the
    # two reads share the class the WP-1.8/WP-1.11 recorded pattern for
    # Agent/Owner rows (the owner GET rides the same class budget —
    # recorded in the WP-3.2 changelog). The patch path carries a real
    # UUID so the resolver matches its <uuid:id> converter.
    _Route("/api/v1/tasks/1/resolution", AgentEndpointThrottle, "WP-3.2", True),
    _Route("/api/v1/tasks/1/resolutions", AgentEndpointThrottle, "WP-3.2", True),
    _Route(
        "/api/v1/resolutions/3f7a1c9e-5d2b-4f81-9c0a-2e6d8b4f1a70/patch",
        AgentEndpointThrottle,
        "WP-3.2",
        True,
    ),
    # --- Audit row (Auditor / Owner): landed with WP-3.3 -----------------
    # The verdict POST carries the throttle on the view class
    # (FR-SEC-05); the reports GET shares the class the WP-1.8/WP-1.11/
    # WP-3.2 recorded pattern for Agent/Owner rows (the owner GET rides
    # the same class budget — recorded in the WP-3.3 changelog).
    _Route("/api/v1/tasks/1/audit-verdict", AgentEndpointThrottle, "WP-3.3", True),
    _Route("/api/v1/tasks/1/audit-reports", AgentEndpointThrottle, "WP-3.3", True),
    # --- Review row (Owner / Device): landed with WP-3.6 ---------------
    # The row's non-owner cell is Device (mobile review sheet), so the
    # view carries DeviceEndpointThrottle; an owner request rides the
    # same per-token budget (the shared-row recording of WP-1.8/WP-3.2/
    # WP-3.3, once more — recorded in the WP-3.6 changelog).
    _Route("/api/v1/tasks/1/review", DeviceEndpointThrottle, "WP-3.6", True),
    # --- Merge queue row (Merge Executor): WP-3.x
    _Route("/api/v1/merge/pending", AgentEndpointThrottle, "WP-3.x", False),
    _Route("/api/v1/merge/1/start", AgentEndpointThrottle, "WP-3.x", False),
    _Route("/api/v1/merge/1/result", AgentEndpointThrottle, "WP-3.x", False),
    # --- Sessions row: landed with MT-1.6-09 (WP-1.6; the bridge caller
    # uses these routes from WP-2.x)
    _Route("/api/v1/agent-sessions", AgentEndpointThrottle, "MT-1.6-09", True),
    _Route("/api/v1/agent-sessions/1/end", AgentEndpointThrottle, "MT-1.6-09", True),
    # --- Attachments row reads (Owner / Agent): landed with MT-1.11-03/04.
    # The shared routes carry AgentEndpointThrottle on the view classes
    # (WP-1.8's recorded pattern for shared Owner/Agent routes); the
    # owner's POST/DELETE halves ride the same class budget — recorded
    # in the WP-1.11 changelog.
    _Route("/api/v1/tasks/1/attachments", AgentEndpointThrottle, "MT-1.11-03", True),
    _Route("/api/v1/attachments/1", AgentEndpointThrottle, "MT-1.11-04", True),
    # Note: GET /events and GET /events/stream are deliberately absent —
    # their caller column is Owner (Section 9.6: agents never subscribe to
    # events; MT-1.2-05's CanReadEvents), so they are not agent endpoints.
    # Reads that exist only after their owning WP lands flip `present` to
    # True **with** the throttle wired; the assertions below enforce both.
)


@pytest.mark.parametrize(
    "route", AGENT_OR_DEVICE_ROUTES, ids=[r.path for r in AGENT_OR_DEVICE_ROUTES]
)
def test_every_agent_or_device_route_is_throttled(route: _Route) -> None:
    """FR-SEC-05 endpoint coverage: present routes carry their throttle."""
    if route.present:
        match = resolve(route.path)
        view = getattr(match.func, "view_class", None)
        assert view is not None, route.path
        assert route.throttle in getattr(view, "throttle_classes", []), (
            f"{route.path} must use {route.throttle.__name__} (FR-SEC-05); "
            f"wire it in {route.lands_with}'s view when adding throttle support"
        )
    else:
        try:
            resolve(route.path)
        except Resolver404:
            return
        pytest.fail(
            f"{route.path} landed — wire {route.throttle.__name__} and flip "
            f"its row in AGENT_OR_DEVICE_ROUTES (owner: {route.lands_with})"
        )


# --- configuration (Section 9.10) and keying fallback ----------------------


def test_rate_limits_come_from_documented_section_9_10_settings(
    settings: Any,
) -> None:
    """The two canonical env-backed settings drive the DRF scopes 1:1."""
    assert settings.RATE_LIMIT_AGENT_PER_MINUTE == 120  # configuration.md row
    assert settings.RATE_LIMIT_DEVICE_PER_MINUTE == 60  # configuration.md row
    assert settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] == {
        "agent": "120/min",
        "device": "60/min",
    }


def test_authenticated_key_is_the_token_and_anonymous_falls_back_to_address(
    db: None,
) -> None:
    """MT keying rule: token id when authenticated, client address otherwise."""
    raw = APIRequestFactory().post("/probe")
    anonymous = Request(raw)
    anonymous.auth = None
    key = DeviceEndpointThrottle().get_cache_key(anonymous, object())
    assert key is not None and "addr:" in key

    token = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        hash="d" * 64,  # any unique placeholder — no secret involved
        user_id=User.objects.create_user("keyed", None, PASSWORD).pk,
    )
    authenticated = Request(APIRequestFactory().post("/probe"))
    authenticated.auth = token
    keyed = DeviceEndpointThrottle().get_cache_key(authenticated, object())
    assert keyed is not None and f"token:{token.pk}" in keyed
