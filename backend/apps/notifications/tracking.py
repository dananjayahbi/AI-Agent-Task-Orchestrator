"""Delivery tracking services and invalid-token pruning (MT-5.4-04).

Section 9.8: "Delivery status tracked; invalid push tokens are pruned";
Section 17 makes push operations observable (push success rate metric,
push-failure alert). This module is the service layer over
:class:`apps.notifications.models.PushDeliveryRecord` — the data side
only; the dashboard and alert *delivery* are WP-6.4's, wired against
:func:`push_success_stats`.

* :func:`record_delivery` — the dispatch job's per-send recorder
  (ids, outcome, attempts, FCM error classification; never payload).
* :func:`prune_invalid_token` — on a *definitively* invalid-token
  response (the sender's ``invalid_token`` flag — FCM's documented
  UNREGISTERED / INVALID_ARGUMENT / SENDER_ID_MISMATCH set, never an
  ambiguous code, per the MT's risk note), blank the device's push
  token so :func:`apps.notifications.dispatch.active_devices` skips it
  forever after. Touches **only** ``push_token`` — never ``revoked_at``
  or any auth/registration state (device revocation stays WP-5.3's
  owner-initiated action; a re-registered token arrives through
  WP-5.3's registration path and reactivates dispatch naturally).
* :func:`push_success_stats` — the Section 17 numerator/denominator
  and failure counts, one query interface.
* :func:`prune_delivery_records` / :func:`prune_dedupe_records` — the
  retention entry points (the recorded 90-day choice, flagged for
  owner confirmation; scheduled by WP-6.4's ops cadence).

Pruning and dedupe interplay (the MT's dependency note): pruning
touches only the device token — the dedupe rows are untouched, so a
pruned device's already-claimed keys stay claimed; pruning can never
*resurrect* a suppressed send.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Count, Q
from django.utils import timezone

from apps.accounts.models import Device

from .models import DeliveryOutcome, PushDedupeRecord, PushDeliveryRecord

#: Operational-data retention (Section 12.4/OQ-10 posture): long enough
#: to cover every retry/restart window with orders of magnitude of
#: slack, short enough that the table cannot grow without bound.
#: Flagged for owner confirmation in the WP changelog.
DELIVERY_RECORD_RETENTION_DAYS = 90


def record_delivery(
    device: Device,
    *,
    event_type: str,
    task_id: str,
    state_version: int,
    outcome: str,
    attempts: int,
    error_code: str | None = None,
    invalid_token: bool = False,
) -> PushDeliveryRecord:
    """Persist one send's verdict (ids and outcome — nothing else)."""
    return PushDeliveryRecord.objects.create(
        device=device,
        event_type=event_type,
        task_id=task_id,
        state_version=state_version,
        outcome=outcome,
        attempts=attempts,
        error_code=error_code or "",
        invalid_token=invalid_token,
    )


def prune_invalid_token(device: Device) -> bool:
    """Blank the device's push token on a definitive invalid-token signal.

    Returns whether a token was cleared. Only ``push_token`` changes:
    the dispatch query excludes empty-token rows, so future sends skip
    this device without error; registration, auth and revocation state
    are untouched (WP-5.3 remains their owner).
    """
    if not device.push_token:
        return False
    Device.objects.filter(pk=device.pk).exclude(push_token="").update(push_token="")
    device.push_token = ""
    return True


def push_success_stats(*, since: timedelta | None = None) -> dict[str, int]:
    """Section 17's push metrics over the retention window, one query.

    Returns ``accepted`` (numerator), ``total`` (denominator),
    ``transient_failures`` and ``permanent_failures`` — the clean
    interface the WP-6.4 metric/alert wiring consumes.
    """
    cutoff = timezone.now() - (since or timedelta(days=DELIVERY_RECORD_RETENTION_DAYS))
    row: dict[str, Any] = PushDeliveryRecord.objects.filter(created_at__gte=cutoff).aggregate(
        total=Count("id"),
        accepted=Count("id", filter=Q(outcome=DeliveryOutcome.ACCEPTED)),
        transient_failures=Count("id", filter=Q(outcome=DeliveryOutcome.TRANSIENT_FAILURE)),
        permanent_failures=Count("id", filter=Q(outcome=DeliveryOutcome.PERMANENT_FAILURE)),
    )
    return {key: int(value or 0) for key, value in row.items()}


def prune_delivery_records(*, older_than_days: int = DELIVERY_RECORD_RETENTION_DAYS) -> int:
    """Retention enforcement for delivery rows (the recorded 90-day choice).

    Returns the number of expired rows deleted.
    """
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = PushDeliveryRecord.objects.filter(created_at__lt=cutoff).delete()
    return int(deleted)


def prune_dedupe_records(*, older_than_days: int = DELIVERY_RECORD_RETENTION_DAYS) -> int:
    """Retention enforcement for dedupe rows (same window and anchor).

    Deleting a dedupe row is safe only beyond every retry window — the
    90-day default is orders of magnitude past MT-5.4-01's seconds-long
    backoff and any realistic queue redelivery, which is exactly the
    "safely beyond the retry/restart window" the MT-5.4-03 risk note
    asks for.
    """
    cutoff = timezone.now() - timedelta(days=older_than_days)
    deleted, _ = PushDedupeRecord.objects.filter(created_at__lt=cutoff).delete()
    return int(deleted)


__all__ = [
    "DELIVERY_RECORD_RETENTION_DAYS",
    "prune_delivery_records",
    "prune_dedupe_records",
    "prune_invalid_token",
    "push_success_stats",
    "record_delivery",
]
