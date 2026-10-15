"""MT-6.4-03 — ``GET /api/v1/ops/overview`` (Section 17 Dashboards row; NFR-10).

The operations view's data source (``web/app/(app)/ops`` consumes it through
the generated client — NFR-11 import boundary). Payload contract:

* ``metrics`` — verbatim MT-6.4-01 ``collect()["metrics"]`` (nine Section 17
  metrics + worker/beat/sweeper heartbeats); the endpoint embeds the same
  collector, so this field and ``/metrics`` cannot disagree (the view never
  computes its own numbers);
* ``alerts`` — verbatim ``evaluate_alerts()``: all six Section 17 rules in
  plan order with firing/since/signal/threshold context (docs/plan/alerts.md);
* ``health`` — the Section 17 Health row: live + ready-check pings;
* caller matrix — owner session 200; every agent role and a device token
  403 ``ROLE_NOT_PERMITTED``; anonymous 401 ``AUTH_REQUIRED`` (Section 12.2
  prints no dashboard/ops capability row for agents/devices);
* read path purity — no events, no mutations.

Run with ``uv run --directory backend pytest tests/test_ops_overview.py -q``;
the file is also the PROOF pointer for the endpoint's GAPS entry in
``tests/auth/test_section_9_2_authorization.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core import metrics as metrics_module
from apps.events.models import Event

OPS_URL = "/api/v1/ops/overview"
PASSWORD = "ops-overview-tests-1!"  # pragma: allowlist secret
AGENT_ROLES = ("coder", "auditor", "decomposer", "merge_executor")

#: The six Section 17 Alerts rows in plan order (MT-6.4-02 contract).
ALERT_IDS = (
    "sweeper_not_running",
    "attachment_backlog",
    "push_failures",
    "tunnel_down",
    "repeated_auth_failures",
    "media_disk_usage",
)


@pytest.fixture(autouse=True)
def clean_state() -> Iterator[None]:
    """Cache counters/heartbeats and throttle history are process state.

    Fresh worker/beat/sweeper stamps model the *running* stack the ops view
    is designed for — on a cold cache the sweeper rule honestly fires
    (heartbeat missing; MT-6.4-02 semantics), which the forcing test
    re-establishes explicitly with a backdated stamp.
    """
    cache.clear()
    for kind in ("worker", "beat", "sweeper"):
        metrics_module.record_heartbeat(kind)
    yield
    cache.clear()


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


def _issue_agent_token(owner_client: APIClient, project_id: str, role: str) -> str:
    """Mint an agent bearer token scoped to *project_id* (plaintext back)."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": [role]}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


def _envelope(response: Any) -> dict[str, Any]:
    """Assert the five-field Section 9.2 envelope; return the error body."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in ("AUTH_REQUIRED", "ROLE_NOT_PERMITTED")
    return cast(dict[str, Any], error)


def test_overview_is_owner_only(owner_client: APIClient) -> None:
    """Caller matrix: owner 200; agents + device 403; anonymous 401.

    Section 12.2 prints no dashboard/ops capability row for any agent role
    or devices — the Owner-session-only guard applies exactly as on the
    Dashboard row (this test is the endpoint's PROOF pointer in
    ``tests/auth/test_section_9_2_authorization.py``'s GAPS entry).
    """
    from apps.projects.models import Project, ProjectPolicy

    Project.objects.create(
        id="PID00001",
        name="Orchestrator",
        repo_path="/srv/repos/orchestrator",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )

    assert owner_client.get(OPS_URL).status_code == status.HTTP_200_OK

    plain = APIClient()
    anonymous = plain.get(OPS_URL)
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"

    for role in AGENT_ROLES:
        token = _issue_agent_token(owner_client, "PID00001", role)
        response = plain.get(OPS_URL, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_403_FORBIDDEN, role
        assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED", role

    device = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-ops-overview"}
    )
    assert device.status_code == status.HTTP_201_CREATED, device.content
    response = plain.get(
        OPS_URL, headers={"Authorization": f"Bearer {cast(str, device.json()['token'])}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"


def test_snapshot_carries_metrics_alerts_and_health(
    owner_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The three-field snapshot: metrics document, six rules, health row.

    Disk usage is injected healthy (the rules' test discipline in
    ``tests/test_alerts.py``) so the resting state does not depend on the
    host machine's real media volume.
    """
    from collections import namedtuple

    Fake = namedtuple("Fake", "total used free")
    monkeypatch.setattr(
        "apps.core.alerts.shutil.disk_usage",
        lambda _path: Fake(total=1000, used=100, free=900),
    )

    response = owner_client.get(OPS_URL)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    assert body["schema_version"] == "ops-overview-1"
    assert body["generated_at"]  # ISO timestamp for the view's freshness display

    metrics = body["metrics"]
    assert set(metrics) == {
        "claims_per_minute",
        "claim_conflicts",
        "active_leases",
        "lease_expirations",
        "task_cycle_time_per_state",
        "attachment_pipeline",
        "sse_connections",
        "push_success_rate",
        "api_latency",
        "heartbeats",
    }, "the nine Section 17 metrics + heartbeats (docs/plan/metrics.md)"

    alerts = body["alerts"]
    assert [alert["id"] for alert in alerts] == list(ALERT_IDS), "plan order"
    for alert in alerts:
        assert set(alert) >= {"id", "name", "severity", "firing", "status", "signal", "threshold"}
        assert alert["firing"] is False, alert["id"]  # resting: nothing recorded
        assert alert["since"] is None
        assert "secret" not in repr(alert).lower()  # no-secrets rule (12.4)

    health = body["health"]
    assert health["live"] is True
    assert health["checks"]["database"] == "ok"
    assert health["checks"]["cache"] == "ok"


def test_snapshot_embeds_the_same_collector_as_metrics(
    owner_client: APIClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The view never computes: it returns collect()'s metrics document itself.

    A double scrape cannot be compared literally (heartbeat ages and the
    request's own latency sample move between calls), so the collector is
    wrapped to capture the exact document the view saw — the response's
    ``metrics`` must be *that* document, byte for byte.
    """
    from apps.core import ops as ops_module
    from apps.core.metrics import collect

    captured: list[dict[str, Any]] = []
    real_collect = collect

    def spy_collect() -> dict[str, Any]:
        document = real_collect()
        captured.append(document)
        return document

    monkeypatch.setattr(ops_module, "collect", spy_collect)

    response = owner_client.get(OPS_URL)
    assert response.status_code == status.HTTP_200_OK
    assert len(captured) == 1, "exactly one collector call per request"
    assert response.json()["metrics"] == captured[0]["metrics"]


def test_firing_sweeper_alert_surfaces_with_since(owner_client: APIClient) -> None:
    """Forcing half: a stale sweeper heartbeat appears as firing + since."""
    stamp = (timezone.now() - timedelta(minutes=10)).isoformat()
    cache.set(f"{metrics_module._PREFIX}:heartbeat:sweeper", stamp, None)

    response = owner_client.get(OPS_URL)
    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    sweeper = next(a for a in body["alerts"] if a["id"] == "sweeper_not_running")
    assert sweeper["firing"] is True
    assert sweeper["status"] == "firing"
    assert sweeper["since"] is not None
    assert sweeper["signal"]["heartbeat_age_seconds"] >= 600

    heartbeat = body["metrics"]["heartbeats"]["sweeper"]
    assert heartbeat["age_seconds"] >= 600, "health row reads the same stamp"


def test_read_path_writes_no_events(owner_client: APIClient) -> None:
    """Read purity: two snapshots emit zero events (Section 9.6 catalog)."""
    assert owner_client.get(OPS_URL).status_code == status.HTTP_200_OK
    assert owner_client.get(OPS_URL).status_code == status.HTTP_200_OK
    assert Event.objects.count() == 0


def test_snapshot_is_single_resource_not_a_page(owner_client: APIClient) -> None:
    """No pagination envelope (pagination.md) — one snapshot object."""
    body = owner_client.get(OPS_URL).json()
    assert "results" not in body
    assert "next_cursor" not in body
