"""MT-6.4-02 — the six Section 17 alert rules, each forced to fire (WP-6.4
acceptance: "each listed alert can be triggered in a test"; Section 19).

One forcing test per plan alert, each driving the rule's *real* signal path —
a stopped heartbeat, stuck attachment rows, real failed pushes through
``record_push_outcome``, a dropped tunnel report, an auth-failure burst
through the real login endpoint, and disk pressure via an injected usage
function (Section 18 isolation: nothing here fills a real volume or poisons
another suite). Plus the catalog contract (exactly six rules, plan names
verbatim), the since-tracking semantics, the no-secrets payload rule
(Section 12.4), and the WARNING log on ok→firing (the recorded surfacing
channel).

Run: ``uv run --directory backend pytest tests/test_alerts.py -v``
(MT test command: ``pytest backend/tests/ -k alert -v``).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.utils import timezone

from apps.core import alerts
from apps.core.alerts import evaluate_alerts
from apps.core.metrics import record_heartbeat, record_push_outcome

pytestmark = pytest.mark.django_db

#: The plan's Section 17 Alerts row, verbatim order — the catalog contract.
SECTION_17_ALERTS = (
    "Sweeper not running",
    "Backlog of unprocessed attachments",
    "Push failures",
    "Tunnel down",
    "Repeated auth failures",
    "Disk usage on media volume",
)


@pytest.fixture(autouse=True)
def _fresh_alert_cache() -> Iterator[None]:
    """Isolate alert state (firing-since, counters) per test."""
    cache.clear()
    yield
    cache.clear()


def _by_id(states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {state["id"]: state for state in states}


def _firing(state: dict[str, Any]) -> bool:
    return bool(state["firing"])


# --- catalog contract --------------------------------------------------------


def test_catalog_lists_exactly_the_six_plan_alerts_in_order() -> None:
    """None renamed, added or dropped (Section 20.5; MT acceptance)."""
    assert alerts.ALERT_IDS == (
        "sweeper_not_running",
        "attachment_backlog",
        "push_failures",
        "tunnel_down",
        "repeated_auth_failures",
        "media_disk_usage",
    )
    states = _by_id(evaluate_alerts())
    assert tuple(state["name"] for state in _by_id(evaluate_alerts()).values()) == SECTION_17_ALERTS
    assert set(states) == set(alerts.ALERT_IDS)


def test_alert_payloads_carry_no_secrets() -> None:
    """Section 12.4: names, counts, ages and thresholds only — never a raw
    auth source, token, task id, or attachment content."""
    alerts.record_auth_failure("10.9.8.7")  # a raw IP that must not escape
    body = json.dumps(evaluate_alerts())
    assert "10.9.8.7" not in body
    for banned in ("token", "secret", "password", "session_id"):
        assert banned not in body


# --- one forcing test per Section 17 alert -----------------------------------


def test_sweeper_alert_fires_when_the_heartbeat_stops_and_clears_when_it_resumes() -> None:
    """RISK-12: a stopped sweeper is visible within the threshold window."""
    record_heartbeat("sweeper")  # a real sweep stamps it
    resting = _by_id(evaluate_alerts())["sweeper_not_running"]
    assert not _firing(resting), "a fresh heartbeat must not fire"

    # Age the stamp past the 180 s margin without waiting real minutes.
    stale = (timezone.now() - timedelta(seconds=181)).isoformat()
    cache.set("metrics:heartbeat:sweeper", stale, None)
    firing = _by_id(evaluate_alerts())["sweeper_not_running"]
    assert _firing(firing)
    assert firing["severity"] == "critical"
    assert firing["since"] is not None, "firing state must carry an onset"

    record_heartbeat("sweeper")  # the sweeper comes back
    cleared = _by_id(evaluate_alerts())["sweeper_not_running"]
    assert not _firing(cleared)
    assert cleared["since"] is None, "onset clears with the alert"


def test_sweeper_alert_fires_on_a_never_swept_stack() -> None:
    """No heartbeat ever = the sweeper has not run — firing, not silent."""
    state = _by_id(evaluate_alerts())["sweeper_not_running"]
    assert _firing(state)
    assert state["signal"]["heartbeat_age_seconds"] is None


def test_backlog_alert_fires_on_stuck_attachment_rows() -> None:
    """Oldest-item age past the documented bound — the real DB signal."""
    from apps.attachments.models import ProcessingStatus, TaskAttachment
    from tests.wp16_helpers import active_policy_project, make_pending_task

    project = active_policy_project()
    task = make_pending_task(project, 1)
    attachment = TaskAttachment.objects.create(
        task=task,
        filename="stuck.md",
        mime_type="text/markdown",
        size_bytes=4,
        is_image=False,
        storage_key="sha256-test",
        sha256="0" * 64,
        processing_status=ProcessingStatus.UPLOADED,
    )
    # Backdate past the 900 s bound (auto_now_add owns created_at).
    TaskAttachment.objects.filter(pk=attachment.pk).update(
        created_at=timezone.now() - timedelta(seconds=901)
    )

    state = _by_id(evaluate_alerts())["attachment_backlog"]
    assert _firing(state)
    assert state["signal"]["depth"] == 1
    assert state["signal"]["oldest_age_seconds"] >= 901

    # Terminal row: the backlog clears (the pipeline's own outcome).
    TaskAttachment.objects.filter(pk=attachment.pk).update(processing_status=ProcessingStatus.READY)
    assert not _firing(_by_id(evaluate_alerts())["attachment_backlog"])


def test_push_alert_fires_below_the_rate_floor_past_the_sample() -> None:
    """Real counter path: three of ten dispatches failed → firing."""
    for _ in range(7):
        record_push_outcome(True)
    for _ in range(3):
        record_push_outcome(False)

    state = _by_id(evaluate_alerts())["push_failures"]
    assert _firing(state)
    assert state["signal"]["success_rate"] == 0.7
    assert state["signal"]["dispatched"] == 10


def test_push_alert_ignores_small_samples_and_absent_dispatchers() -> None:
    """No flapping below the sample floor; honest ok when nothing dispatched
    (WP-5.4's dispatcher has not landed — a null rate is not a failure)."""
    record_push_outcome(False)  # 1 dispatch, 0 % — below the sample floor
    state = _by_id(evaluate_alerts())["push_failures"]
    assert not _firing(state)
    assert state["signal"]["success_rate"] == 0.0

    cache.clear()
    resting = _by_id(evaluate_alerts())["push_failures"]
    assert not _firing(resting)
    assert resting["signal"]["success_rate"] is None


def test_tunnel_alert_fires_on_a_down_report_and_on_a_silent_reporter() -> None:
    """Section 15.4: tunnel-down is a warning (LAN and agents continue),
    and a reporter that goes silent cannot confirm the tunnel either."""
    alerts.record_tunnel_status(True)
    ok = _by_id(evaluate_alerts())["tunnel_down"]
    assert not _firing(ok)
    assert ok["status"] == "ok"
    assert ok["runbook"] == "tunnel down", "Section 17 names a tunnel runbook"

    alerts.record_tunnel_status(False)
    firing = _by_id(evaluate_alerts())["tunnel_down"]
    assert _firing(firing)
    assert firing["severity"] == "warning", "15.4: not a page — LAN continues"

    # A stale-but-once-up report: the reporter went quiet.
    alerts.record_tunnel_status(True)
    cache.set(
        alerts._TUNNEL_STATUS_KEY,  # test forcing the exact signal key
        {"up": True, "at": (timezone.now() - timedelta(seconds=301)).isoformat()},
        None,
    )
    stale = _by_id(evaluate_alerts())["tunnel_down"]
    assert _firing(stale)


def test_tunnel_alert_reads_unknown_until_a_first_report_exists() -> None:
    """The documented detection limitation: no report → unknown, not firing
    (never pretending a state the host cannot observe)."""
    state = _by_id(evaluate_alerts())["tunnel_down"]
    assert not _firing(state)
    assert state["status"] == "unknown"


@override_settings(ALERT_AUTH_FAILURE_WINDOW_SECONDS=86400)
def test_auth_failures_alert_fires_on_a_burst_through_the_real_login() -> None:
    """Section 15.3 layer 4: the forcing path is the real login endpoint —
    ten bad passwords from one source trip the rule. The window is pinned to
    a day so the fixed bucket cannot straddle the test run."""
    for _ in range(10):
        response = Client().post(
            "/api/v1/auth/login",
            {"username": "nobody", "password": "wrong-password-1!"},  # pragma: allowlist secret
            content_type="application/json",
        )
        assert response.status_code == 401

    state = _by_id(evaluate_alerts())["repeated_auth_failures"]
    assert _firing(state)
    assert state["signal"]["worst_source_failures"] == 10
    assert state["signal"]["sources_over_threshold"] == 1

    # Nine from a *different* source stays under the floor: no flapping.
    cache.clear()
    for _ in range(9):
        Client().post(
            "/api/v1/auth/login",
            {
                "username": "someone-else",
                "password": "wrong-password-2!",  # pragma: allowlist secret
            },
            content_type="application/json",
        )
    assert not _firing(_by_id(evaluate_alerts())["repeated_auth_failures"])


def test_disk_alert_fires_at_the_threshold_via_an_injected_usage(monkeypatch: Any) -> None:
    """Disk pressure forced with a fake ``shutil.disk_usage`` — the fixture
    fills no volume and disturbs no shared stack (MT risk note)."""
    from collections import namedtuple

    # The stdlib namedtuple shape (total, used, free) the rule unpacks.
    Fake = namedtuple("Fake", "total used free")

    def fake_usage(path: str) -> Any:
        return Fake(total=100, used=95, free=5)

    monkeypatch.setattr("apps.core.alerts.shutil.disk_usage", fake_usage)
    state = _by_id(evaluate_alerts())["media_disk_usage"]
    assert _firing(state)
    assert state["severity"] == "critical"
    assert state["signal"]["used_percent"] == 95.0

    def healthy_usage(path: str) -> Any:
        return Fake(total=100, used=50, free=50)

    monkeypatch.setattr("apps.core.alerts.shutil.disk_usage", healthy_usage)
    assert not _firing(_by_id(evaluate_alerts())["media_disk_usage"])


def test_disk_alert_reads_unknown_when_the_media_root_is_gone(monkeypatch: Any) -> None:
    """Cannot measure → unknown, not firing, not pretending (20.4 item 1)."""

    def broken_usage(path: str) -> Any:
        raise OSError("media volume unmounted")

    monkeypatch.setattr("apps.core.alerts.shutil.disk_usage", broken_usage)
    state = _by_id(evaluate_alerts())["media_disk_usage"]
    assert not _firing(state)
    assert state["status"] == "unknown"


# --- evaluation discipline ---------------------------------------------------


def test_evaluation_is_a_read_path_that_logs_transitions(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """ok→firing logs one WARNING (the recorded surfacing channel); a
    re-evaluation while still firing does not repeat it (fatigue guard)."""
    record_heartbeat("sweeper")
    with caplog.at_level(logging.WARNING, logger="apps.core.alerts"):
        evaluate_alerts()  # resting: no warning
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]

    caplog.clear()
    stale = (timezone.now() - timedelta(seconds=200)).isoformat()
    cache.set("metrics:heartbeat:sweeper", stale, None)
    with caplog.at_level(logging.WARNING, logger="apps.core.alerts"):
        evaluate_alerts()
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "sweeper_not_running" in warnings[0].getMessage()

    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="apps.core.alerts"):
        evaluate_alerts()  # still firing: no repeat
    assert not [r for r in caplog.records if r.levelno == logging.WARNING]


def test_forcing_an_alert_needs_no_sweeper_scheduler() -> None:
    """The pull model: states are derivable with no beat, no worker, no
    scheduler — exactly what the MT's evaluation/triggering slice promises."""
    states = evaluate_alerts()
    assert len(states) == 6
    assert all(
        set(s)
        == {"id", "name", "severity", "firing", "status", "since", "signal", "threshold", "runbook"}
        for s in states
    )


def test_thresholds_come_from_configurable_settings() -> None:
    """Every threshold is an ORCHESTRATOR_ALERT_* setting (no magic numbers
    baked into the rules); override one and the rule follows."""
    from django.test import override_settings as _override

    with _override(ALERT_SWEEPER_MAX_HEARTBEAT_SECONDS=5):
        record_heartbeat("sweeper")
        cache.set(
            "metrics:heartbeat:sweeper",
            (timezone.now() - timedelta(seconds=10)).isoformat(),
            None,
        )
        state = _by_id(evaluate_alerts())["sweeper_not_running"]
        assert _firing(state), "a 6 s-old heartbeat exceeds a 5 s threshold"


@override_settings(METRICS_ENABLED=False)
def test_the_alert_layer_does_not_depend_on_the_metrics_flag() -> None:
    """Alerts read the same counters the endpoint exposes; disabling the
    /metrics *endpoint* (Section 9.10 flag) must not disable the rules."""
    states = evaluate_alerts()
    assert len(states) == 6
