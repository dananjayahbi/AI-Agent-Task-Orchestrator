"""MT-5.2-03 — edge and API rate limits on the tunnel path (FR-SEC-05).

Section 15.3 layer 4 requires rate limits at *both* the edge and the API.
The edge half is configuration in ``infra/cloudflare/rate-limits.md``
(operator-applied); what can be proven locally — and is proven here — is
the **API half behind an edge-representing request context**:

* a burst on a device endpoint arriving with tunnel headers (forwarded
  chain, Cloudflare headers) still ends in the canonical ``RATE_LIMITED``
  envelope (429, ``retryable``, catalog-closed — Sections 9.2 / 20.4
  item 5): WP-1.2 throttles keep applying behind the edge;
* edge-identity headers neither authenticate a caller nor re-key, split or
  reset a throttle budget (Sections 12.2/15.3: edge identity is not
  authentication) — API budgets key on the Django token id only;
* two tokens behind one (shared) edge address hold independent budgets, so
  the tunnel's single connector address cannot collapse remote clients into
  one bucket (MT-5.2-03 risk note);
* the machine-readable edge rules in ``rate-limits.md`` cover every
  Section 15.2 group the allowlist exposes, and every edge threshold that
  has an API counterpart is ≥ the live ``ORCHESTRATOR_RATE_LIMIT_*`` value,
  so the API's canonical envelope trips first for a single client — the
  documented "no contradiction" arithmetic (rate-limits.md §3);
* Owner auth stays API-unthrottled exactly as FR-SEC-05's scope (MT-1.2-06
  decision, pinned by ``test_rate_limiting.py``) while the edge rule E1
  covers it — the dual-layer reading recorded in rate-limits.md §3.

Run: ``pytest backend/tests/test_rate_limits_tunnel.py -v``. Live edge-rule
application and the checklist hooks are operator-pending (OQ-11) and run
from ``infra/cloudflare/route-verification-checklist.md``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.views import LoginView
from apps.core.errors import CANONICAL_ERROR_CODES, RATE_LIMITED

REPO_ROOT = Path(__file__).resolve().parents[2]
RATE_LIMITS_MD = REPO_ROOT / "infra" / "cloudflare" / "rate-limits.md"
ALLOWLIST_MD = REPO_ROOT / "infra" / "cloudflare" / "route-allowlist.md"

REGISTER_URL = "/api/v1/devices"
LOGIN_URL = "/api/v1/auth/login"

PASSWORD = "rate-limit-tunnel-tests-1!"  # pragma: allowlist secret

#: What a request looks like after passing the Cloudflare edge and the
#: cloudflared connector: forwarded chain, Cloudflare request headers, and
#: (spoofable by anyone, meaningless to the origin) Access identity headers.
TUNNEL_HEADERS: dict[str, Any] = {
    "HTTP_X_FORWARDED_FOR": "203.0.113.7, 198.51.100.44",
    "HTTP_X_FORWARDED_PROTO": "https",
    "HTTP_CF_CONNECTING_IP": "203.0.113.7",
    "HTTP_CF_IPCOUNTRY": "XX",
    "HTTP_CF_VISITOR": '{"scheme":"https"}',
}

#: Two *different* edge-identity header sets — same client, same token.
#: The backend must ignore both (they are not credentials and never key a
#: budget); a difference in them must not move a throttle bucket.
EDGE_IDENTITY_A: dict[str, Any] = {
    **TUNNEL_HEADERS,
    "HTTP_CF_ACCESS_JWT_ASSERTION": "eyJhbGciOi.header-a.signature",
    "HTTP_CF_ACCESS_SERVICE_TOKEN": "client-id-a",
}
EDGE_IDENTITY_B: dict[str, Any] = {
    **TUNNEL_HEADERS,
    "HTTP_CF_ACCESS_JWT_ASSERTION": "eyJhbGciOi.header-b.signature",
    "HTTP_CF_ACCESS_SERVICE_TOKEN": "client-id-b",
}


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """LocMem throttle history is process state — never leak it across tests."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner(db: None) -> User:
    return User.objects.create_user("tunnel-owner", None, PASSWORD)


@pytest.fixture
def client() -> APIClient:
    return APIClient()


def _login(api: APIClient, user: User) -> None:
    response = api.post(LOGIN_URL, {"username": user.username, "password": PASSWORD})
    assert response.status_code == 200, response.content


def _set_rates(settings: Any, **rates: str) -> None:
    """Override DEFAULT_THROTTLE_RATES the way DRF reloads them (signal)."""
    rest = dict(settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest.get("DEFAULT_THROTTLE_RATES", {}), **rates}
    settings.REST_FRAMEWORK = rest


def _register(api: APIClient, headers: dict[str, Any], push_token: str) -> Any:
    return api.post(
        REGISTER_URL,
        {"platform": "ios", "push_token": push_token},
        **headers,
    )


def _envelope(response: Any) -> dict[str, Any]:
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return cast(dict[str, Any], error)


def _json_block_after(md_path: Path, heading: str) -> dict[str, Any]:
    text = md_path.read_text(encoding="utf-8")
    assert heading in text, f"{md_path.name} lost {heading!r}"
    tail = text.split(heading, 1)[1]
    match = re.search(r"```json\n(.*?)\n```", tail, flags=re.DOTALL)
    assert match, f"{md_path.name} has no JSON block after {heading!r}"
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


# --- API limits still apply behind the edge ---------------------------------


def test_throttled_device_request_on_the_tunnel_path_returns_rate_limited(
    client: APIClient, owner: User, settings: Any
) -> None:
    """MT acceptance: an API-throttled request arriving through the tunnel
    context answers with the canonical RATE_LIMITED envelope (Section 9.2)."""
    _set_rates(settings, device="2/min")
    _login(client, owner)

    assert _register(client, TUNNEL_HEADERS, "apns-tunnel-1").status_code == 201
    assert _register(client, TUNNEL_HEADERS, "apns-tunnel-2").status_code == 201

    throttled = _register(client, TUNNEL_HEADERS, "apns-tunnel-3")
    assert throttled.status_code == 429
    error = _envelope(throttled)
    assert error["code"] == RATE_LIMITED
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    assert error["retryable"] is True
    assert error["correlation_id"]
    assert throttled.headers.get("Retry-After"), "NFR-12 wait hint survives the edge"


def test_edge_identity_headers_neither_authenticate_nor_rekey_budgets(
    client: APIClient, owner: User, settings: Any
) -> None:
    """Sections 12.2/15.3: edge identity is not authentication, and API
    budgets key on the Django token id — not on any edge-supplied header."""
    _set_rates(settings, device="2/min")
    _login(client, owner)

    # Same token, two *different* edge-identity header sets: one shared budget.
    assert _register(client, EDGE_IDENTITY_A, "apns-id-a1").status_code == 201
    assert _register(client, EDGE_IDENTITY_B, "apns-id-b1").status_code == 201
    assert _register(client, EDGE_IDENTITY_A, "apns-id-a2").status_code == 429
    # …and the budget does not reset just because the edge headers changed.
    assert _register(client, EDGE_IDENTITY_B, "apns-id-b2").status_code == 429

    # A caller carrying plausible Access identity headers but no Django
    # credential is refused — the edge headers are not a credential.
    anonymous = APIClient()
    response = _register(anonymous, EDGE_IDENTITY_A, "apns-anon")
    assert response.status_code == 401
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


def test_tokens_behind_one_edge_address_keep_independent_budgets(
    client: APIClient, owner: User, settings: Any
) -> None:
    """The MT risk note: behind the tunnel every request shares the
    connector address — per-token keying must keep the budgets apart."""
    _set_rates(settings, device="1/min")

    _login(client, owner)  # owner_session token #1
    assert _register(client, TUNNEL_HEADERS, "apns-sess1-1").status_code == 201
    assert _register(client, TUNNEL_HEADERS, "apns-sess1-2").status_code == 429

    second = APIClient()
    _login(second, owner)  # owner_session token #2, identical headers
    assert _register(second, TUNNEL_HEADERS, "apns-sess2-1").status_code == 201


# --- documentation consistency (rate-limits.md §6 vs allowlist vs settings) -


@pytest.fixture(scope="module")
def edge_doc() -> dict[str, Any]:
    return _json_block_after(RATE_LIMITS_MD, "## 6. Machine-readable coverage block")


@pytest.fixture(scope="module")
def allowlist_doc() -> dict[str, Any]:
    return _json_block_after(ALLOWLIST_MD, "## 7. Machine-readable rule table")


def test_edge_rules_cover_every_exposed_section_15_2_group(
    edge_doc: dict[str, Any], allowlist_doc: dict[str, Any]
) -> None:
    """Acceptance: every group Section 15.2 exposes through the tunnel has a
    defined edge limit (conditional rows included — flip-ready)."""
    exposed = {
        row["id"]
        for row in allowlist_doc["rows"]
        if row["decision"] in {"allow", "conditional-deny"}
    }
    covered = {group for rule in edge_doc["edge_rules"] for group in rule["groups"]}
    assert exposed <= covered, f"exposed rows without an edge limit: {exposed - covered}"
    ids = [rule["id"] for rule in edge_doc["edge_rules"]]
    assert len(ids) == len(set(ids)), "edge rule ids must be unique"
    for rule in edge_doc["edge_rules"]:
        assert rule["pattern"].startswith("^"), rule["id"]
        assert rule["per_minute"] > 0 and rule["key"] == "ip"


def test_edge_thresholds_never_mask_the_api_canonical_envelope(
    edge_doc: dict[str, Any], settings: Any
) -> None:
    """rate-limits.md §3 arithmetic: where an API scope exists, the edge
    budget is ≥ it, so a single token trips RATE_LIMITED at the API first."""
    api_settings_doc = edge_doc["meta"]["api_settings"]
    assert api_settings_doc["ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE"] == (
        settings.RATE_LIMIT_DEVICE_PER_MINUTE
    ), "rate-limits.md must document the deployed device default (9.10)"
    assert api_settings_doc["ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE"] == (
        settings.RATE_LIMIT_AGENT_PER_MINUTE
    ), "rate-limits.md must document the deployed agent default (9.10)"

    scope_values = {
        "device": settings.RATE_LIMIT_DEVICE_PER_MINUTE,
        "agent": settings.RATE_LIMIT_AGENT_PER_MINUTE,
    }
    for rule in edge_doc["edge_rules"]:
        for scope in rule["api_scopes"]:
            assert rule["per_minute"] >= scope_values[scope], (
                f"{rule['id']} ({rule['per_minute']}/min) would mask the "
                f"{scope} API budget ({scope_values[scope]}/min) — rate-limits.md §3"
            )


def test_auth_group_is_edge_covered_with_api_side_gap_recorded(
    edge_doc: dict[str, Any],
) -> None:
    """Dual layer for the 'Auth, devices' row: E1 covers auth at the edge
    (API-side exclusion is the recorded FR-SEC-05 scope, not an omission)."""
    auth_rules = [
        rule
        for rule in edge_doc["edge_rules"]
        if "auth-devices" in rule["groups"] and rule["pattern"].startswith("^/api/v1/auth/")
    ]
    assert auth_rules, "no edge rule covers the auth endpoints"
    assert auth_rules[0]["api_scopes"] == [], "owner auth is API-unthrottled by scope"
    text = RATE_LIMITS_MD.read_text(encoding="utf-8")
    assert "FR-SEC-05" in text and "MT-1.2-06" in text
    assert "WP-6.4" in text, "anomaly-alert dependency must stay recorded (17/20.4)"
    assert RATE_LIMITED in text


def test_owner_auth_views_stay_api_unthrottled_per_plan_scope() -> None:
    """Guard against silently widening FR-SEC-05: the API half keeps Owner
    auth out (test_rate_limiting.py pins the same); the edge E1 rule above
    is its limit — the two together are the documented dual layer."""
    assert getattr(LoginView, "throttle_classes", []) == []
