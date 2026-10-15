"""MT-5.4-01 — FCM configuration contract and the worker-side sender.

Section 9.8 dispatches push **via FCM from the worker** (ADR-003); this
suite pins the WP-5.4 foundations those later MTs build on:

* **config contract** — ``ORCHESTRATOR_PUSH_ENABLED`` defaults off and
  requires the Section 9.10 FCM values only when enabled; weak
  credentials fail at startup naming the variable (never the value);
  push-disabled deployments boot clean with no FCM project at all
  (the MT's risk note: a fail-fast that bricked the stack on a push-
  only setting would be wrong);
* **sender** — one token, one attempt: accepted, transient-retry with
  the documented exponential backoff schedule, permanent failure
  classified once (never retried), unknown codes retried but never
  treated as token-death (MT-5.4-04's pruning rests on this table);
* **job wiring** — the Section 9.8 ``in_human_review`` entry trigger
  reaches the Section 9.9 dispatch job strictly post-commit, and the
  job fans out to active devices only (the ADR-006 revoked-device
  control), invoking the sender per device.

Run with ``pytest backend/tests -k fcm_sender -q``.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.services.tokens import hash_token
from apps.notifications import dispatch as dispatch_module
from apps.notifications.sender import (
    FcmTransportError,
    SendOutcome,
    classify_fcm_error,
    get_fcm_transport,
    send_to_token,
    set_fcm_transport,
)
from apps.projects.models import Project
from apps.tasks.models import ClaimedRole, Task, TaskState
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY
from tests.wp15_helpers import make_project, make_task, reset_hooks
from tests.wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)

pytestmark = pytest.mark.django_db

# A service-account shaped stand-in (well-formed for the validator; the
# key material is obviously fake and never reaches a real FCM call).
_FAKE_SA_JSON = json.dumps({"private_key": "fake-key-material", "client_email": "x@y.z"})


@pytest.fixture(autouse=True)
def clean_push_seams() -> Iterator[None]:
    """Snapshot the registry and the push seams; restore after every test."""
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        reset_hooks()
        set_fcm_transport(None)


# --- configuration contract (Section 9.10; MT-5.4-01 AC 1) -------------------


def test_disabled_push_requires_no_fcm_values() -> None:
    """The default deployment needs no FCM project at all."""
    from apps.core.settings.base import missing_fcm_settings

    assert missing_fcm_settings(False, "", "") == []


def test_enabled_push_names_every_missing_variable() -> None:
    """Enabled push lists both missing names; either alone lists one."""
    from apps.core.settings.base import missing_fcm_settings

    assert missing_fcm_settings(True, "", "") == [
        "ORCHESTRATOR_FCM_PROJECT_ID",
        "ORCHESTRATOR_FCM_CREDENTIALS_JSON",
    ]
    assert missing_fcm_settings(True, "proj-123", "") == ["ORCHESTRATOR_FCM_CREDENTIALS_JSON"]
    assert missing_fcm_settings(True, "", _FAKE_SA_JSON) == ["ORCHESTRATOR_FCM_PROJECT_ID"]
    assert missing_fcm_settings(True, "proj-123", _FAKE_SA_JSON) == []


def test_weak_credentials_fail_the_wellformedness_check() -> None:
    """Non-JSON, non-object, or object without private_key is weak (16.2)."""
    from apps.core.settings.base import fcm_credentials_wellformed

    assert fcm_credentials_wellformed("") is True  # empty = missing, not weak
    assert fcm_credentials_wellformed("not-json{") is False
    assert fcm_credentials_wellformed("[]") is False
    assert fcm_credentials_wellformed('{"client_email": "x@y.z"}') is False
    assert fcm_credentials_wellformed(_FAKE_SA_JSON) is True


def test_settings_defaults_are_the_documented_off_switch() -> None:
    """Section 9.10 defaults: push off, 3 attempts, 1 s backoff base."""
    from django.conf import settings

    assert settings.PUSH_ENABLED is False
    assert settings.PUSH_RETRY_MAX_ATTEMPTS == 3
    assert settings.PUSH_RETRY_BACKOFF_SECONDS == 1


def _run_manage_check(overrides: dict[str, str]) -> tuple[int, str]:
    """``manage.py check`` under a scrubbed env (the boot-test pattern)."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("ORCHESTRATOR_") and key != "DJANGO_SETTINGS_MODULE"
    }
    env.update(overrides)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "manage.py", "check"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        check=False,
        timeout=120,
    )
    return result.returncode, (result.stdout + result.stderr).decode("utf-8", "replace")


def test_boot_fails_fast_when_push_enabled_without_credentials() -> None:
    """Section 9.10: enabled + missing names the variables, not the values."""
    returncode, output = _run_manage_check({"ORCHESTRATOR_PUSH_ENABLED": "true"})
    assert returncode != 0, "enabled push with no FCM config must refuse to boot"
    assert "ORCHESTRATOR_FCM_PROJECT_ID" in output
    assert "ORCHESTRATOR_FCM_CREDENTIALS_JSON" in output


def test_boot_refuses_weak_credentials_when_push_enabled() -> None:
    """Section 16.2: a truncated paste fails at startup, not first push."""
    returncode, output = _run_manage_check(
        {
            "ORCHESTRATOR_PUSH_ENABLED": "true",
            "ORCHESTRATOR_FCM_PROJECT_ID": "proj-123",
            "ORCHESTRATOR_FCM_CREDENTIALS_JSON": "not-a-json{",
        }
    )
    assert returncode != 0, "weak credentials must refuse to boot"
    assert "ORCHESTRATOR_FCM_CREDENTIALS_JSON" in output
    assert "not-a-json{" not in output  # names the variable, never the value


def test_boot_passes_with_complete_push_configuration() -> None:
    """Enabled push with strong-shaped values boots (the clean-success path)."""
    returncode, output = _run_manage_check(
        {
            "ORCHESTRATOR_PUSH_ENABLED": "true",
            "ORCHESTRATOR_FCM_PROJECT_ID": "proj-123",
            "ORCHESTRATOR_FCM_CREDENTIALS_JSON": _FAKE_SA_JSON,
        }
    )
    assert returncode == 0, f"complete push config must boot:\n{output}"


# --- the sender (retry/backoff; classification) ------------------------------


class FakeTransport:
    """A scripted transport: per-call outcomes, every call recorded."""

    def __init__(self, *outcomes: Exception | None) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, dict[str, str]]] = []

    def send(self, device_token: str, data: Any) -> None:
        self.calls.append((device_token, dict(data)))
        outcome = self.outcomes.pop(0) if self.outcomes else None
        if outcome is not None:
            raise outcome


def _transient(code: str = "UNAVAILABLE") -> FcmTransportError:
    return FcmTransportError("transient", code=code, transient=True)


def _permanent(code: str = "UNREGISTERED", *, invalid_token: bool = True) -> FcmTransportError:
    return FcmTransportError("permanent", code=code, transient=False, invalid_token=invalid_token)


def test_success_is_one_attempt_one_call() -> None:
    """First-try acceptance: no retry, no backoff, data delivered."""
    transport = FakeTransport()
    result = send_to_token(
        "token-a",
        {"task_id": "PID00001-T001"},
        transport=transport,
        max_attempts=3,
        backoff_seconds=1,
        sleep=lambda _seconds: pytest.fail("success must not sleep"),
    )
    assert result.outcome == SendOutcome.ACCEPTED
    assert result.attempts == 1
    assert transport.calls == [("token-a", {"task_id": "PID00001-T001"})]


def test_transient_failures_back_off_then_accept() -> None:
    """base × 2^(n-1): sleeps 1 s then 2 s, then the third attempt lands."""
    transport = FakeTransport(_transient(), _transient(), None)
    naps: list[float] = []
    result = send_to_token(
        "token-a",
        {"task_id": "t"},
        transport=transport,
        max_attempts=3,
        backoff_seconds=1,
        sleep=naps.append,
    )
    assert result.outcome == SendOutcome.ACCEPTED
    assert result.attempts == 3
    assert naps == [1.0, 2.0]
    assert len(transport.calls) == 3


def test_transient_exhaustion_stops_at_the_budget() -> None:
    """The configured attempt budget is a hard ceiling (Section 9.10)."""
    transport = FakeTransport(_transient(), _transient(), _transient())
    naps: list[float] = []
    result = send_to_token(
        "token-a",
        {"task_id": "t"},
        transport=transport,
        max_attempts=3,
        backoff_seconds=1,
        sleep=naps.append,
    )
    assert result.outcome == SendOutcome.TRANSIENT_FAILURE
    assert result.attempts == 3
    assert result.error_code == "UNAVAILABLE"
    assert naps == [1.0, 2.0]  # no sleep after the final attempt


def test_permanent_failure_returns_after_one_attempt() -> None:
    """A permanent error is never retried — retrying cannot succeed."""
    transport = FakeTransport(_permanent())
    result = send_to_token(
        "token-a",
        {"task_id": "t"},
        transport=transport,
        max_attempts=3,
        backoff_seconds=1,
        sleep=lambda _seconds: pytest.fail("permanent must not sleep"),
    )
    assert result.outcome == SendOutcome.PERMANENT_FAILURE
    assert result.attempts == 1
    assert result.error_code == "UNREGISTERED"
    assert result.invalid_token is True


def test_unknown_codes_are_retried_but_never_prune() -> None:
    """Ambiguity costs a bounded retry; it must never destroy a device.

    MT-5.4-04 prunes only ``invalid_token`` results — an unclassified
    code therefore stays in the retry bucket, not the pruning one.
    """
    transient, invalid = classify_fcm_error("SOME_FUTURE_CODE")
    assert (transient, invalid) == (True, False)
    assert classify_fcm_error(None) == (True, False)
    assert classify_fcm_error("UNAVAILABLE") == (True, False)
    assert classify_fcm_error("QUOTA_EXCEEDED") == (True, False)
    assert classify_fcm_error("INTERNAL") == (True, False)
    assert classify_fcm_error("UNREGISTERED") == (False, True)
    assert classify_fcm_error("INVALID_ARGUMENT") == (False, True)
    assert classify_fcm_error("SENDER_ID_MISMATCH") == (False, True)


def test_unknown_code_with_budget_returns_transient_failure() -> None:
    """A retried unknown code reports transient — never permanent."""
    transport = FakeTransport(_transient(code="SOME_FUTURE_CODE"))
    result = send_to_token(
        "token-a", {"task_id": "t"}, transport=transport, max_attempts=1, sleep=lambda _s: None
    )
    assert result.outcome == SendOutcome.TRANSIENT_FAILURE
    assert result.invalid_token is False


def test_transport_seam_overrides_and_clears() -> None:
    """The process-default transport is injectable and clearable (tests)."""
    fake = FakeTransport()
    set_fcm_transport(fake)
    assert get_fcm_transport() is fake
    set_fcm_transport(None)


def test_disabled_push_has_no_transport_and_fails_fast() -> None:
    """Push-disabled: asking for the production transport is a config error."""
    with override_settings(PUSH_ENABLED=False):
        with pytest.raises(ImproperlyConfigured) as caught:
            get_fcm_transport()
    assert "ORCHESTRATOR_PUSH_ENABLED" in str(caught.value)


# --- job wiring (escalation event → fan-out → sender) -------------------------


def _make_exhausted(project: Project, index: int = 1) -> Task:
    """An ``in_progress`` row at the retry ceiling (T9's premises)."""
    task = make_task(project, index, state=TaskState.IN_PROGRESS, failure_retry_count=3)
    task.worker_agent_id = "claude-code-session-98b2"
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = ClaimedRole.CODER
    task.lease_acquired_at = timezone.now()
    task.lease_expires_at = timezone.now()
    task.save()
    return task


def _register_device(user: Any, *, push_token: str, revoked: bool = False) -> Device:
    """One device row with its device-bound token (WP-5.3's shape)."""
    token_row = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        user=user,
        hash=hash_token(f"credential-{user.pk}-{push_token}"),
        project_id=None,
    )
    device = Device.objects.create(
        user=user, platform="android", push_token=push_token, token=token_row
    )
    if revoked:
        device.revoked_at = timezone.now()
        device.save()
    return device


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the default policy."""
    return make_project(name="WP-5.4 sender")


def test_escalation_trigger_reaches_the_job_only_after_commit(
    project: Project, django_capture_on_commit_callbacks: Any, monkeypatch: Any
) -> None:
    """Section 9.8's entry trigger enqueues the worker job post-commit."""
    from apps.tasks.state_machine import hooks as sm_hooks

    task = _make_exhausted(project)

    delivered: list[dict[str, Any]] = []

    class _StubTask:
        @staticmethod
        def delay(trigger: dict[str, Any]) -> None:
            delivered.append(trigger)

    monkeypatch.setattr(dispatch_module, "dispatch_push_task", _StubTask())
    sm_hooks.set_review_push_hook(dispatch_module.enqueue_push_dispatch)

    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        dispatch_transition(
            task_id=task.pk, trigger="retry_exhausted", actor_type="system", actor_ref="sweeper"
        )
        assert delivered == [], "the worker must not see an uncommitted trigger"

    assert callbacks, "the enqueue registered a post-commit callback"
    assert len(delivered) == 1
    task.refresh_from_db()  # the dispatch bumped the version (dedupe key half)
    trigger = delivered[0]
    assert trigger["event_type"]
    assert trigger["project_id"] == project.pk
    assert trigger["task_id"] == task.pk
    assert trigger["state_version"] == task.version


def test_job_fans_out_to_active_devices_and_reports_summary(project: Project) -> None:
    """Active devices get one send each; revoked and empty-token rows don't."""
    task = make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW, title="Banner title")
    user = User.objects.create_user("wp54-fanout", None, "pw-wp54-fanout-123456")
    _register_device(user, push_token="token-live-1")
    _register_device(user, push_token="token-revoked", revoked=True)
    _register_device(user, push_token="")  # never a valid destination
    _register_device(user, push_token="token-live-2")

    # One acceptance and a fully-scripted transient exhaustion (three
    # attempts); backoff zeroed so the retry loop costs no wall time.
    transport = FakeTransport(
        None,
        _transient(),  # exhausts the 3-attempt budget (Section 9.10 default)
        _transient(),
        _transient(),
    )
    set_fcm_transport(transport)

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        summary = dispatch_module.dispatch_push(
            {
                "event_type": "merge_failed",
                "project_id": project.pk,
                "task_id": task.pk,
                "state_version": 3,
                "reason_code": "merge_conflict",
            }
        )

    assert summary == {
        "accepted": 1,
        "transient_failed": 1,
        "permanent_failed": 0,
        "suppressed": 0,
    }
    # Every call went to a live token only; the retried device appears
    # once per attempt (three here — the exhausted transient budget).
    assert {token for token, _data in transport.calls} == {"token-live-1", "token-live-2"}
    assert [token for token, _data in transport.calls].count("token-live-2") == 3
    payload = transport.calls[0][1]
    assert payload == {
        "event_type": "merge_failed",
        "project_id": project.pk,
        "task_id": task.pk,
        "task_version": "3",
        "title": "Banner title",  # MT-5.4-02's allowlist builder fetched it
    }


def test_ensure_wiring_skips_the_unit_layer_and_disabled_push(monkeypatch: Any) -> None:
    """Both documented gates: test settings and push-disabled deployments."""
    assert dispatch_module.ensure_push_dispatch_wired() is False  # .test settings

    monkeypatch.setenv("DJANGO_SETTINGS_MODULE", "apps.core.settings.dev")
    with override_settings(PUSH_ENABLED=False):
        assert dispatch_module.ensure_push_dispatch_wired() is False
    with override_settings(PUSH_ENABLED=True):
        assert dispatch_module.ensure_push_dispatch_wired() is True
        # The seam now routes into the enqueue (post-commit, not inline).
        from apps.tasks.state_machine import hooks as sm_hooks

        delivered: list[dict[str, Any]] = []

        class _StubTask:
            @staticmethod
            def delay(trigger: dict[str, Any]) -> None:
                delivered.append(trigger)

        monkeypatch.setattr(dispatch_module, "dispatch_push_task", _StubTask())
        sm_hooks.trigger_review_push({"event_type": "x", "project_id": "p", "task_id": "t"})
        assert delivered == [], "enqueue defers to transaction.on_commit"
