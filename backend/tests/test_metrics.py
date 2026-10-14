"""MT-6.4-01 — observability metrics scaffold (Section 17; NFR-10).

Each test drives one real action through its instrumentation seam and asserts
the matching metric moves in ``collect()`` (and, where it is an HTTP surface,
through the ``/metrics`` endpoint). The final test greps the payload for the
secret-bearing fields that must never appear (Section 17 no-secrets rule).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from apps.core import metrics
from apps.core.metrics import collect
from apps.leases.sweeper import sweep_expired_leases
from apps.tasks.models import ActorType, Task, TaskState, TaskTransition

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _clear_metric_cache() -> None:
    """Isolate each test's counters (LocMem is per-process, shared across tests)."""
    from django.core.cache import cache

    cache.clear()


@pytest.fixture
def media_root(tmp_path: Path) -> Iterator[Path]:
    """Uploads and derived artifacts land in an isolated media root, never
    the container's ``/media`` default (WP suite convention)."""
    with override_settings(STORAGE_BACKEND="local", MEDIA_ROOT=str(tmp_path)):
        yield tmp_path


@pytest.fixture(autouse=True)
def _fresh_metrics() -> Iterator[None]:
    _clear_metric_cache()
    yield
    _clear_metric_cache()


# --- each metric moves when its action occurs --------------------------------


def test_claim_bumps_claims_per_minute() -> None:
    project = active_policy_project()
    task = make_pending_task(project, 1)

    claim(task, session_id="sess_metrics")

    m = collect()["metrics"]
    assert m["claims_per_minute"] == 1
    assert m["claim_conflicts"] == 0


def test_claim_race_bumps_conflicts_not_claims() -> None:
    from apps.leases.exceptions import TaskAlreadyClaimed

    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_first")

    with pytest.raises(TaskAlreadyClaimed):
        claim(task, session_id="sess_second")

    m = collect()["metrics"]
    assert m["claim_conflicts"] == 1


def _expire(task: Task) -> Task:
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    task.refresh_from_db()
    return task


def test_sweeper_expiry_bumps_lease_expirations_and_heartbeats() -> None:
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_dead")
    _expire(task)

    report = sweep_expired_leases()

    m = collect()["metrics"]
    assert report.reclaimed == 1
    assert m["lease_expirations"] == 1
    # A sweep firing stamps the worker/beat heartbeats (MT-6.4-02 alert input).
    assert m["heartbeats"]["worker"]["last_seen"] is not None
    assert m["heartbeats"]["sweeper"]["age_seconds"] is not None


def test_pipeline_run_bumps_attachment_pipeline(media_root: Path) -> None:
    """The real upload → pipeline action (Section 17) times and records a
    terminal run; a failed run counts under its own outcome label."""
    from apps.attachments.pipeline import run_pipeline
    from tests.attachments.helpers import MARKDOWN_BYTES, make_attachment

    project = active_policy_project()
    task = make_pending_task(project, 1)
    attachment = make_attachment(task, MARKDOWN_BYTES, name="metrics.md", mime="text/markdown")
    assert run_pipeline(str(attachment.pk)) == "ready"

    pipe = collect()["metrics"]["attachment_pipeline"]
    assert pipe["count_by_outcome"]["ready"] == 1
    assert pipe["duration_ms_avg"] is not None

    metrics.record_pipeline("failed", 3.0)
    assert collect()["metrics"]["attachment_pipeline"]["count_by_outcome"]["failed"] == 1


def test_sse_connections_reflect_hub() -> None:
    """A connect moves the gauge and its close moves it back (baseline-
    relative: earlier suites can leave registrations behind — only
    tests/events' conftest clears the hub — so assert this connection's
    contribution, not a global zero)."""
    from apps.events.fanout import hub

    class _FakeConn:
        pass

    baseline = collect()["metrics"]["sse_connections"]
    conn = _FakeConn()
    hub.register(conn)  # type: ignore[arg-type]
    assert collect()["metrics"]["sse_connections"] == baseline + 1
    hub.unregister(conn)  # type: ignore[arg-type]
    assert collect()["metrics"]["sse_connections"] == baseline


def test_push_outcome_reads_zero_until_dispatcher_lands() -> None:
    # WP-5.4's dispatcher does not exist yet; the ratio is null, not a lie.
    assert collect()["metrics"]["push_success_rate"] is None
    metrics.record_push_outcome(True)
    metrics.record_push_outcome(False)
    assert collect()["metrics"]["push_success_rate"] == 0.5


def test_api_latency_and_cycle_time_gauges() -> None:
    metrics.record_api_latency("GET", "api/v1/tasks/<id>", 200, 4.0)
    metrics.record_api_latency("GET", "api/v1/tasks/<id>", 200, 6.0)

    project = active_policy_project()
    task = make_pending_task(project, 1)
    # Timestamps are auto_now_add and the history is append-only, so freeze the
    # clock to land the two transitions exactly 120s apart.
    real_now = timezone.now()
    with patch("django.utils.timezone.now") as frozen:
        frozen.return_value = real_now - timedelta(minutes=2)
        t1 = TaskTransition.objects.create(
            task=task,
            from_state=TaskState.PENDING,
            to_state=TaskState.IN_PROGRESS,
            actor_type=ActorType.SYSTEM,
            actor_ref="metrics-test",
            reason_code="claim",
        )
        frozen.return_value = real_now
        t2 = TaskTransition.objects.create(
            task=task,
            from_state=TaskState.IN_PROGRESS,
            to_state=TaskState.COMPLETED,
            actor_type=ActorType.SYSTEM,
            actor_ref="metrics-test",
            reason_code="complete",
        )
    assert t1.pk and t2.pk

    m = collect()["metrics"]
    assert m["api_latency"]["count"] == 2
    assert m["api_latency"]["duration_ms_avg"] == 5.0
    assert "GET api/v1/tasks/<id> 200" in m["api_latency"]["by_route"]
    assert m["task_cycle_time_per_state"][TaskState.IN_PROGRESS] == 120.0


# --- the endpoint itself ------------------------------------------------------


def test_metrics_endpoint_returns_json_document() -> None:
    response = Client().get("/metrics")

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    body = json.loads(response.content)
    assert body["schema_version"] == "metrics-1"
    present = set(body["metrics"])
    assert {
        "claims_per_minute",
        "claim_conflicts",
        "active_leases",
        "lease_expirations",
        "task_cycle_time_per_state",
        "attachment_pipeline",
        "sse_connections",
        "push_success_rate",
        "api_latency",
    } <= present


def test_metrics_endpoint_disabled_when_flag_off(settings: Any) -> None:
    settings.METRICS_ENABLED = False
    assert Client().get("/metrics").status_code == 404


def test_payload_carries_no_secrets() -> None:
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_secret_probe")
    _expire(task)
    sweep_expired_leases()

    body = json.dumps(collect())
    for banned in ("sess_secret_probe", "worker_session_id", "token", "secret"):
        assert banned not in body
