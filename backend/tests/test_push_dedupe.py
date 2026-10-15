"""MT-5.4-03 — Per-device dedupe keys (event type, task id, state version).

Section 9.8 verbatim: "per-device dedupe key `(event type, task id,
state version)` prevents duplicates on retries"; WP-5.4's acceptance:
"escalation produces one push within 10 s; retried event does not
duplicate." This suite pins the dedupe contract in the dispatch path:

* same key twice → one send per device (the retry/re-delivery case —
  asserted through the **job**, not only the claim helper);
* a different state version for the same task/event type notifies
  again (the version is part of the key, not a filter);
* per-device independence — multi-device fan-out dedupes per device,
  never globally;
* atomic check-and-record — two interleaved workers lose/win on the
  unique constraint, never both send (the Section 18 concurrency
  posture; SQLite runs the real constraint race deterministically —
  the true two-process race belongs to the integration layer);
* record-before-send — a worker crash between claim and send leaves
  the claim standing, so a re-delivered trigger after restart does not
  double-send.

Run with ``pytest backend/tests -k push_dedupe -q``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.services.tokens import hash_token
from apps.notifications import dispatch as dispatch_module
from apps.notifications.dedupe import claim_dedupe
from apps.notifications.models import PushDedupeRecord
from apps.notifications.sender import set_fcm_transport
from apps.projects.models import Project
from apps.tasks.models import TaskState
from tests.test_fcm_sender import FakeTransport, _transient  # scripted transport
from tests.wp15_helpers import make_project, make_task, reset_hooks
from tests.wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)

pytestmark = pytest.mark.django_db

_TRIGGER: dict[str, Any] = {
    "event_type": "review.requested",
    "project_id": "PID00001",
    "task_id": "PID00001-T001",
    "state_version": 4,
}


@pytest.fixture(autouse=True)
def clean_seams() -> Iterator[None]:
    """The push seams and the process transport start clean per test."""
    yield
    reset_hooks()
    set_fcm_transport(None)


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the default policy."""
    return make_project(name="WP-5.4 dedupe")


@pytest.fixture
def task(project: Project) -> Any:
    """A review-state row the trigger names (the banner title source)."""
    return make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW, title="Dedupe task")


def _register_device(user: User, *, push_token: str) -> Device:
    """One active device row (WP-5.3's shape)."""
    token_row = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        user=user,
        hash=hash_token(f"credential-{user.pk}-{push_token}"),
        project_id=None,
    )
    return Device.objects.create(
        user=user, platform="android", push_token=push_token, token=token_row
    )


@pytest.fixture
def devices(db: None) -> tuple[Device, Device]:
    """Two live phones on one owner — the per-device independence pair."""
    user = User.objects.create_user("wp54-dedupe", None, "pw-wp54-dedupe-123456")
    return (
        _register_device(user, push_token="phone-a"),
        _register_device(user, push_token="phone-b"),
    )


# --- the claim primitive ------------------------------------------------------


def test_claim_wins_once_then_loses(devices: tuple[Device, Device]) -> None:
    """First claim owns the key; an identical second claim is refused."""
    phone_a, _phone_b = devices
    assert claim_dedupe(phone_a, event_type="e", task_id="t", state_version=1) is True
    assert claim_dedupe(phone_a, event_type="e", task_id="t", state_version=1) is False


def test_claim_is_scoped_per_device(devices: tuple[Device, Device]) -> None:
    """Two phones claim the same key independently (never a global key)."""
    phone_a, phone_b = devices
    assert claim_dedupe(phone_a, event_type="e", task_id="t", state_version=1) is True
    assert claim_dedupe(phone_b, event_type="e", task_id="t", state_version=1) is True
    assert PushDedupeRecord.objects.count() == 2


def test_claim_treats_state_version_as_part_of_the_key(
    devices: tuple[Device, Device],
) -> None:
    """A later escalation (newer version) is a fresh key — it notifies."""
    phone_a, _phone_b = devices
    assert claim_dedupe(phone_a, event_type="e", task_id="t", state_version=1) is True
    assert claim_dedupe(phone_a, event_type="e", task_id="t", state_version=2) is True


def test_unique_constraint_is_the_atomic_mechanism(devices: tuple[Device, Device]) -> None:
    """The raw duplicate insert raises IntegrityError — the DB decides the
    race; ``claim_dedupe`` maps that error to a lost claim (never a crash)."""
    phone_a, _phone_b = devices
    PushDedupeRecord.objects.create(device=phone_a, event_type="e", task_id="t", state_version=1)
    with pytest.raises(IntegrityError):
        PushDedupeRecord.objects.create(
            device=phone_a, event_type="e", task_id="t", state_version=1
        )


# --- through the job ----------------------------------------------------------


def test_retried_trigger_sends_once_per_device(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """The same trigger processed twice yields one send per device."""
    transport = FakeTransport(*([None] * 8))
    set_fcm_transport(transport)

    first = dispatch_module.dispatch_push(_TRIGGER)
    second = dispatch_module.dispatch_push(_TRIGGER)

    assert first["accepted"] == 2 and first["suppressed"] == 0
    assert second["accepted"] == 0 and second["suppressed"] == 2
    assert {token for token, _data in transport.calls} == {"phone-a", "phone-b"}


def test_newer_state_version_notifies_again(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """Same task, same event type, newer version → a second push."""
    transport = FakeTransport(*([None] * 8))
    set_fcm_transport(transport)

    dispatch_module.dispatch_push(_TRIGGER)
    summary = dispatch_module.dispatch_push({**_TRIGGER, "state_version": 5})

    assert summary["accepted"] == 2 and summary["suppressed"] == 0
    assert len(transport.calls) == 4  # two per device, two versions


def test_fan_out_dedupes_per_device_not_globally(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """One phone suppressed never silences the other (multi-device owners)."""
    phone_a, phone_b = devices
    transport = FakeTransport(*([None] * 8))
    set_fcm_transport(transport)

    # phone_a already got this key (a previous partial dispatch).
    assert claim_dedupe(phone_a, **_key(_TRIGGER)) is True

    summary = dispatch_module.dispatch_push(_TRIGGER)

    assert summary == {
        "accepted": 1,
        "transient_failed": 0,
        "permanent_failed": 0,
        "suppressed": 1,
    }
    assert [token for token, _data in transport.calls] == ["phone-b"]


def _key(trigger: dict[str, Any]) -> dict[str, Any]:
    """The Section 9.8 key kwargs for the claim helper."""
    return {
        "event_type": str(trigger["event_type"]),
        "task_id": str(trigger["task_id"]),
        "state_version": int(trigger["state_version"]),
    }


def test_worker_restart_mid_dispatch_does_not_double_send(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """Record-before-send: a crash after the claim leaves it standing —
    the re-delivered trigger after restart loses the claim and sends nothing."""
    phone_a, phone_b = devices
    # Simulate the crashed worker: claims recorded, sender never reached.
    assert claim_dedupe(phone_a, **_key(_TRIGGER)) is True
    assert claim_dedupe(phone_b, **_key(_TRIGGER)) is True

    transport = FakeTransport()
    set_fcm_transport(transport)

    summary = dispatch_module.dispatch_push(_TRIGGER)  # the redelivery

    assert summary["accepted"] == 0 and summary["suppressed"] == 2
    assert transport.calls == []


def test_transient_failure_is_not_retried_by_a_redelivered_trigger(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """The claim stands even when the send exhausts its retry budget.

    The dedupe key suppresses *duplicates*, not FCM-level retries —
    MT-5.4-01's in-send backoff owns those; a redelivered trigger after
    an exhausted send does not fan out again (the acceptance's
    "retried event does not duplicate").
    """
    phone_a, _phone_b = devices
    transport = FakeTransport(
        # Three scripted transients per device (budget 3 each) — both
        # budgets exhaust; nothing accepts.
        *([_transient()] * 6),
    )
    set_fcm_transport(transport)

    from django.test import override_settings

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        first = dispatch_module.dispatch_push(_TRIGGER)
        second = dispatch_module.dispatch_push(_TRIGGER)

    assert first["transient_failed"] == 2  # both devices exhausted their budgets
    assert second["suppressed"] == 2 and second["accepted"] == 0
    assert [token for token, _data in transport.calls].count("phone-a") == 3


def test_records_carry_the_documented_retention_anchor(
    project: Project, task: Any, devices: tuple[Device, Device]
) -> None:
    """created_at is the retention anchor (the TTL choice in the changelog)."""
    before = timezone.now()
    set_fcm_transport(FakeTransport(*([None] * 4)))
    dispatch_module.dispatch_push(_TRIGGER)
    record = PushDedupeRecord.objects.first()
    assert record is not None
    assert record.created_at is not None
    assert record.created_at >= before
