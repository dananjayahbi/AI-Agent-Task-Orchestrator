"""MT-6.1-01 — WP-6.1 authorization-review additions (Section 12.5, FR-SEC-05).

Three review results turned into CI-enforced assertions, extending MT-1.2-07
(``tests/test_authorization_matrix.py``) rather than duplicating it:

* **Section 12.5 audit viewer is read-only**: the events API surface exposes
  exactly the two read routes, neither view declares a mutation handler, and
  unsafe methods answer through the catalog envelope without ever creating or
  altering an Event row (the viewer-read-only half of Section 12.5; the
  DB-role half is ``tests/events/test_insert_only_permissions.py``).
* **State-changing API calls record actor AND correlation id**: a real
  ``POST /api/v1/projects`` writes ``project.created`` carrying the session
  actor and the very correlation id the client saw on the response — the
  API-path half of Section 12.5 (``tests/events/test_event_writes.py``
  asserts the service paths).
* **FR-SEC-05 observed end-to-end** on one agent endpoint and one device
  endpoint inside this review's own command (``-k authorization``); the
  every-route enumeration stays in ``tests/test_rate_limiting.py``.

Findings and severity scale: ``docs/plan/security-findings-log.md``; threat
mapping: ``docs/plan/security-threat-test-mapping.md`` (WP-6.1 deliverables).

Run with ``pytest backend/tests/ -k authorization -v`` (MT test command).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.authentication import TokenBearerAuthentication
from apps.accounts.models import User
from apps.core.errors import AUTH_REQUIRED, CANONICAL_ERROR_CODES, RATE_LIMITED
from apps.events.models import Event
from apps.events.views import EventHistoryView, EventStreamView

PASSWORD = "wp61-review-tests-1!"  # pragma: allowlist secret

EVENT_PATHS = ("/api/v1/events", "/api/v1/events/stream")
UNSAFE_METHODS = ("post", "put", "patch", "delete")


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


def _set_rates(settings: Any, **rates: str) -> None:
    """Override DEFAULT_THROTTLE_RATES (pytest-django reloads DRF settings)."""
    rest = dict(settings.REST_FRAMEWORK)
    rest["DEFAULT_THROTTLE_RATES"] = {**rest.get("DEFAULT_THROTTLE_RATES", {}), **rates}
    settings.REST_FRAMEWORK = rest


# --- Section 12.5: the audit viewer surfaces no mutation path ----------------


def test_event_urlconf_lists_only_the_two_read_routes() -> None:
    """The events app publishes history + stream and nothing else (12.5)."""
    from apps.events.urls import urlpatterns

    assert sorted(str(pattern.name) for pattern in urlpatterns) == [
        "events-history",
        "events-stream",
    ]


def test_event_viewer_views_declare_no_mutation_handler() -> None:
    """Neither viewer class can be POSTed/PUTed/PATCHed/DELETEd into (12.5)."""
    for view in (EventHistoryView, EventStreamView):
        for method in UNSAFE_METHODS:
            assert not hasattr(view, method), f"{view.__name__}.{method} mutates the audit trail"


@pytest.mark.parametrize("path", EVENT_PATHS)
@pytest.mark.parametrize("method", UNSAFE_METHODS)
def test_unsafe_methods_never_mutate_the_audit_trail(
    owner_client: APIClient, path: str, method: str
) -> None:
    """An unsafe method answers through the catalog envelope; zero rows change.

    DRF maps ``MethodNotAllowed`` to the catalog ``VALIDATION_ERROR`` (400 —
    ``apps/core/exceptions.py``); the assertion below accepts any non-2xx
    refusal so the test tracks the property (no mutation), not one status.
    """
    before = Event.objects.count()

    response = getattr(owner_client, method)(path, {}, format="json")

    assert not 200 <= response.status_code < 300, "the viewer must refuse every write method"
    assert Event.objects.count() == before, "the refused call wrote no audit row"


# --- Section 12.5: state changes carry actor and correlation id -------------


def test_state_changing_api_call_records_actor_and_correlation_id(
    owner_client: APIClient,
) -> None:
    """A real API write carries the session actor and the caller's id join key.

    ``X-Correlation-ID`` round-trips per ``docs/plan/conventions/headers.md``
    (MT-0.5-03): the response echoes it and the audit row stores it verbatim,
    so the viewer can join the exchange to its Event row (NFR-10).
    """
    supplied = "wp61-review-corr-01"

    response = owner_client.post(
        "/api/v1/projects",
        {
            "name": "WP61 audit correlation",
            "repo_path": "/srv/repos/wp61-audit-correlation",
            "default_branch": "main",
        },
        headers={"X-Correlation-ID": supplied},
    )
    assert response.status_code == 201, response.content
    assert response.headers["X-Correlation-ID"] == supplied

    project_id = response.json()["id"]
    event = Event.objects.get(project_id=project_id, type="project.created")
    assert event.actor_type == "owner", "Section 12.5: the row names its actor"
    assert event.actor_ref not in ("", "owner"), "the API path carries the session user id"
    assert event.correlation_id == supplied, "the row joins the exchange by correlation id"


# --- FR-SEC-05: rate limiting observed in the review's own selector ---------


def test_device_endpoint_trips_rate_limited_within_the_review(
    owner_client: APIClient, settings: Any
) -> None:
    """FR-SEC-05 device half: a burst answers the RATE_LIMITED envelope."""
    _set_rates(settings, device="1/min")

    def register() -> Any:
        return owner_client.post(
            "/api/v1/devices", {"platform": "ios", "push_token": "wp61-rate-device"}
        )

    assert register().status_code == 201
    throttled = register()

    assert throttled.status_code == 429
    error = throttled.json()["error"]
    assert error["code"] == RATE_LIMITED
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    assert error["retryable"] is True
    assert error["correlation_id"]


def test_agent_endpoint_trips_rate_limited_within_the_review(
    owner_client: APIClient, settings: Any
) -> None:
    """FR-SEC-05 agent half: the scoped /work route throttles its token."""
    _set_rates(settings, agent="1/min")
    issued = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": "PID00001", "scopes": ["coder"]}
    )
    assert issued.status_code == 201, issued.content
    headers = {"Authorization": f"{TokenBearerAuthentication.keyword} {issued.json()['token']}"}
    plain = APIClient()

    def work() -> Any:
        return plain.get("/api/v1/projects/PID00001/work", headers=headers)

    under_budget = work()
    assert under_budget.status_code < 429, under_budget.content

    throttled = work()
    assert throttled.status_code == 429, throttled.content
    error = throttled.json()["error"]
    assert error["code"] == RATE_LIMITED
    assert error["retryable"] is True


# --- the two event endpoints' caller cells ride the standing suites ---------
# (events/test_event_authorization.py for owner/device/agent/anonymous cells;
#  test_rate_limiting.py for the per-route throttle enumeration.)


def test_event_history_still_requires_an_authenticated_reader(
    owner_client: APIClient,
) -> None:
    """Sanity pin for the new suite: anonymous stays AUTH_REQUIRED (12.2)."""
    for path in EVENT_PATHS:
        response = APIClient().get(path)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == AUTH_REQUIRED


def test_owner_session_cookie_does_not_leak_into_a_second_client(
    owner_client: APIClient,
) -> None:
    """The read-only viewer answer is credential-scoped, not ambient."""
    assert owner_client.get("/api/v1/events").status_code == 200
    fresh = APIClient()
    assert fresh.get("/api/v1/events").status_code == 401
