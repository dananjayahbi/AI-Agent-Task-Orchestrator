"""MT-5.4-04 — Delivery tracking and invalid-token pruning.

Section 9.8 verbatim: "Delivery status tracked; invalid push tokens are
pruned"; Section 17: push success rate metric, push-failure alert.
This suite pins the tracking contract in the dispatch path:

* every send records a delivery row — device, Section 9.8 event key,
  outcome, attempts, FCM error classification — and **no payload
  content** (Section 12.4: tracking is not a leak channel);
* a definitive invalid-token response (the sender's ``invalid_token``
  flag — FCM's documented UNREGISTERED/INVALID_ARGUMENT/
  SENDER_ID_MISMATCH set) prunes the token: subsequent dispatches skip
  the device without error, and only ``push_token`` changes — never
  revocation/auth/registration state (WP-5.3 owns those);
* transient failures record their attempts and remain retryable
  within MT-5.4-01's budget; permanent non-token failures record once
  and stop (no endless retry);
* an ambiguous FCM code never prunes (the risk note: misclassifying a
  transient as permanent silently drops a working device);
* push success rate and failure counts are queryable
  (``push_success_stats``) for Section 17's metric/alert wiring;
* pruning cannot resurrect a suppressed send — dedupe rows are
  untouched, a pruned device's claimed keys stay claimed.

Run with ``pytest backend/tests -k push_delivery_tracking -q``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.accounts.models import ApiToken, Device, TokenKind, User
from apps.accounts.services.tokens import hash_token
from apps.notifications import dispatch as dispatch_module
from apps.notifications.dedupe import claim_dedupe
from apps.notifications.models import DeliveryOutcome, PushDeliveryRecord
from apps.notifications.sender import FcmTransportError, set_fcm_transport
from apps.notifications.tracking import (
    DELIVERY_RECORD_RETENTION_DAYS,
    prune_dedupe_records,
    prune_delivery_records,
    prune_invalid_token,
    push_success_stats,
    record_delivery,
)
from apps.projects.models import Project
from apps.tasks.models import TaskState
from tests.test_fcm_sender import FakeTransport, _permanent, _transient
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
    return make_project(name="WP-5.4 tracking")


@pytest.fixture
def task(project: Project) -> Any:
    """A review-state row the trigger names (the banner title source)."""
    return make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW, title="Tracked task")


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
def phone(db: None) -> Device:
    """One live phone."""
    user = User.objects.create_user("wp54-track", None, "pw-wp54-track-123456")
    return _register_device(user, push_token="phone-track")


# --- recording through the job -------------------------------------------------


def test_accepted_send_records_a_delivery_row(project: Project, task: Any, phone: Device) -> None:
    """Section 9.8 "Delivery status tracked": accepted is recorded."""
    set_fcm_transport(FakeTransport(None))
    dispatch_module.dispatch_push(_TRIGGER)

    record = PushDeliveryRecord.objects.get()
    assert record.device == phone
    assert record.outcome == DeliveryOutcome.ACCEPTED
    assert record.attempts == 1
    assert record.error_code == ""
    assert (
        record.event_type,
        record.task_id,
        record.state_version,
    ) == ("review.requested", "PID00001-T001", 4)


def test_transient_failure_records_attempts_and_stays_retryable(
    project: Project, task: Any, phone: Device
) -> None:
    """The exhausted transient budget is recorded with its attempt count."""
    set_fcm_transport(FakeTransport(*([_transient()] * 3)))
    from django.test import override_settings

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        summary = dispatch_module.dispatch_push(_TRIGGER)

    assert summary["transient_failed"] == 1
    record = PushDeliveryRecord.objects.get()
    assert record.outcome == DeliveryOutcome.TRANSIENT_FAILURE
    assert record.attempts == 3  # MT-5.4-01's budget, evidenced
    assert record.error_code == "UNAVAILABLE"
    assert record.invalid_token is False


def test_permanent_non_token_failure_records_once_without_endless_retry(
    project: Project, task: Any, phone: Device
) -> None:
    """A permanent auth error: one attempt, recorded, never retried."""
    set_fcm_transport(FakeTransport(_permanent(code="THIRD_PARTY_AUTH_ERROR", invalid_token=False)))
    from django.test import override_settings

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        summary = dispatch_module.dispatch_push(_TRIGGER)

    assert summary["permanent_failed"] == 1
    record = PushDeliveryRecord.objects.get()
    assert record.outcome == DeliveryOutcome.PERMANENT_FAILURE
    assert record.attempts == 1
    assert record.error_code == "THIRD_PARTY_AUTH_ERROR"
    assert record.invalid_token is False
    device = Device.objects.get(pk=phone.pk)
    assert device.push_token == "phone-track"  # non-token permanent: token kept


def test_tracking_rows_carry_no_payload_content(project: Project, task: Any, phone: Device) -> None:
    """Section 12.4: ids and verdicts only — never banner or event text."""
    set_fcm_transport(FakeTransport(None))
    dispatch_module.dispatch_push(_TRIGGER)

    record = PushDeliveryRecord.objects.get()
    fields = {field.name for field in PushDeliveryRecord._meta.concrete_fields}
    assert "title" not in fields and "payload" not in fields and "data" not in fields
    row_values = {name: getattr(record, name) for name in fields}
    assert "Tracked task" not in repr(row_values)


# --- pruning -------------------------------------------------------------------


def test_invalid_token_response_prunes_and_subsequent_dispatches_skip(
    project: Project, task: Any, phone: Device
) -> None:
    """Section 9.8 "invalid push tokens are pruned" — the dead-token path."""
    transport = FakeTransport(_permanent())  # UNREGISTERED, invalid_token=True
    set_fcm_transport(transport)
    from django.test import override_settings

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        summary = dispatch_module.dispatch_push(_TRIGGER)
        second = dispatch_module.dispatch_push(_TRIGGER)

    assert summary["permanent_failed"] == 1
    device = Device.objects.get(pk=phone.pk)
    assert device.push_token == ""  # pruned: active_devices now skips it
    assert second == {
        "accepted": 0,
        "transient_failed": 0,
        "permanent_failed": 0,
        "suppressed": 0,  # the device never reaches the claim — no error
    }
    assert len(transport.calls) == 1  # exactly one send attempt, ever
    record = PushDeliveryRecord.objects.get()
    assert record.invalid_token is True
    assert record.error_code == "UNREGISTERED"


def test_pruning_touches_only_the_token_never_device_state(project: Project, phone: Device) -> None:
    """WP-5.3 remains the revocation/registration owner."""
    phone.last_seen_at = timezone.now()
    phone.biometric_bound = True
    phone.save()
    token_pk = phone.token_id
    user_pk = phone.user_id

    assert prune_invalid_token(phone) is True

    device = Device.objects.get(pk=phone.pk)
    assert device.push_token == ""
    assert device.revoked_at is None  # not revoked — merely tokenless
    assert device.biometric_bound is True
    assert device.last_seen_at is not None
    assert device.token_id == token_pk  # the device credential survives
    assert device.user_id == user_pk
    assert device.is_active() is True
    assert prune_invalid_token(device) is False  # idempotent on a pruned row


def test_ambiguous_failure_never_prunes(project: Project, task: Any, phone: Device) -> None:
    """The risk note: ambiguity retries bounded, never destroys a device."""
    ambiguous = FcmTransportError("mystery", code="MYSTERY_CODE", transient=True)
    set_fcm_transport(FakeTransport(ambiguous, ambiguous, ambiguous))
    from django.test import override_settings

    with override_settings(PUSH_RETRY_BACKOFF_SECONDS=0):
        dispatch_module.dispatch_push(_TRIGGER)

    device = Device.objects.get(pk=phone.pk)
    assert device.push_token == "phone-track"  # intact — transient, not invalid
    record = PushDeliveryRecord.objects.get()
    assert record.invalid_token is False


def test_pruning_does_not_resurrect_a_suppressed_send(
    project: Project, task: Any, phone: Device
) -> None:
    """Dedupe interplay: pruning touches the token only — claims stay."""
    assert claim_dedupe(
        phone, event_type="review.requested", task_id="PID00001-T001", state_version=4
    )
    assert prune_invalid_token(phone) is True

    set_fcm_transport(FakeTransport(None))
    summary = dispatch_module.dispatch_push(_TRIGGER)  # device skipped pre-claim

    assert summary["suppressed"] == 0  # never even claimed again
    # A *new* state version on a re-registered token still notifies.
    Device.objects.filter(pk=phone.pk).update(push_token="phone-new")
    second = dispatch_module.dispatch_push({**_TRIGGER, "state_version": 5})
    assert second["accepted"] == 1


# --- Section 17 metric interface ------------------------------------------------


def test_success_stats_expose_the_numerator_denominator_and_failures(
    project: Project, task: Any, phone: Device
) -> None:
    """One query interface for the push success-rate metric and alert."""
    record_delivery(
        phone,
        event_type="review.requested",
        task_id="t1",
        state_version=1,
        outcome=DeliveryOutcome.ACCEPTED,
        attempts=1,
    )
    record_delivery(
        phone,
        event_type="review.requested",
        task_id="t2",
        state_version=1,
        outcome=DeliveryOutcome.TRANSIENT_FAILURE,
        attempts=3,
        error_code="UNAVAILABLE",
    )
    record_delivery(
        phone,
        event_type="merge_failed",
        task_id="t3",
        state_version=1,
        outcome=DeliveryOutcome.PERMANENT_FAILURE,
        attempts=1,
        error_code="THIRD_PARTY_AUTH_ERROR",
    )

    stats = push_success_stats()
    assert stats == {
        "total": 3,
        "accepted": 1,
        "transient_failures": 1,
        "permanent_failures": 1,
    }
    # The window filter works for the future alert's lookback: a row
    # older than the cutoff drops out of both numerator and denominator.
    PushDeliveryRecord.objects.filter(task_id="t1").update(
        created_at=timezone.now() - timedelta(days=DELIVERY_RECORD_RETENTION_DAYS + 2)
    )
    windowed = push_success_stats()
    assert windowed == {
        "total": 2,
        "accepted": 0,
        "transient_failures": 1,
        "permanent_failures": 1,
    }
    wide = push_success_stats(since=timedelta(days=DELIVERY_RECORD_RETENTION_DAYS * 2))
    assert wide["total"] == 3


def test_retention_entry_points_prune_by_created_at(phone: Device) -> None:
    """The recorded 90-day choice: both tables prune on created_at."""
    old = timezone.now() - timedelta(days=DELIVERY_RECORD_RETENTION_DAYS + 1)
    fresh_delivery = record_delivery(
        phone,
        event_type="e",
        task_id="t",
        state_version=1,
        outcome=DeliveryOutcome.ACCEPTED,
        attempts=1,
    )
    PushDeliveryRecord.objects.filter(pk=fresh_delivery.pk).update(created_at=old)
    stale_delivery = record_delivery(
        phone,
        event_type="e",
        task_id="t",
        state_version=2,
        outcome=DeliveryOutcome.ACCEPTED,
        attempts=1,
    )

    assert prune_delivery_records() == 1
    assert PushDeliveryRecord.objects.filter(pk=stale_delivery.pk).exists()

    from apps.notifications.models import PushDedupeRecord

    old_dedupe = PushDedupeRecord.objects.create(
        device=phone, event_type="e", task_id="t", state_version=1
    )
    PushDedupeRecord.objects.filter(pk=old_dedupe.pk).update(created_at=old)
    fresh_dedupe = PushDedupeRecord.objects.create(
        device=phone, event_type="e", task_id="t", state_version=2
    )

    assert prune_dedupe_records() == 1
    assert PushDedupeRecord.objects.filter(pk=fresh_dedupe.pk).exists()
