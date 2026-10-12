"""Lease-expiring warning notifier (Sections 9.6 ``task.lease_expiring``, 9.9).

MT-1.7-04 (FR-LEA-04, FR-LEA-05, NFR-03). Every 60 seconds the beat job finds
``in_progress`` tasks whose lease has passed 80% of its current window while
still valid and emits the catalog warning event through the WP-1.9
write/publish path, so SSE subscribers (boards, agents panel) see a lease
about to lapse *before* the sweeper applies T5 — silent expiry (RISK-02)
becomes a visible signal.

Exactly-once-per-window rule (recorded reading of Section 8.6, WP changelog):
one ``task.lease_expiring`` per ``(task, lease_generation,
lease_expires_at)`` window. The generation is part of the key and a
checkpoint extension (MT-1.6-03) redefines ``lease_expires_at``, i.e. starts
a new window — the warning re-arms at 80% of the new window; repeated
60-second runs within one window never duplicate. The append-only Event log
itself is the dedupe store, written in the same row-locked transaction as the
emission, so two concurrent beat instances cannot double-warn. Expired or
already-swept leases are never warned — T5's ``task.lease_expired`` stays the
sole expiry event.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.core.correlation import (
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from apps.events.models import Event, EventQuerySet, EventType
from apps.events.services import write_event
from apps.tasks.models import Task, TaskState

logger = logging.getLogger(__name__)

# actor_ref for every warning this job emits (Section 9.6 envelope).
NOTIFIER_ACTOR_REF = "lease-expiring-notifier"

# Section 9.6 catalog note for task.lease_expiring: "(sent at 80% of lease)".
LEASE_EXPIRING_FRACTION = 0.8

# Documented default (MT-1.7-02 pattern): bounds one run's candidate scan;
# the next 60-second beat run picks up any remainder.
DEFAULT_BATCH_SIZE = 100


@dataclass
class NotifyReport:
    """One notifier run's outcome (structured for logs and the Celery result)."""

    warned: int = 0
    already_warned: int = 0
    skipped: int = 0  # swept/expired/degenerate rows at lock time
    correlation_id: str = ""


def notify_lease_expiring(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    now: datetime | None = None,
) -> NotifyReport:
    """Emit ``task.lease_expiring`` for leases past 80% of their window.

    Idempotent: within one ``(generation, expiry)`` window the event log stops
    duplicates; a clean run over an empty or sub-80% set is a no-op. One
    correlation id scopes the whole run (WP-0.5-03).
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1 (got {batch_size})")
    token = set_correlation_id(new_correlation_id())
    report = NotifyReport(correlation_id=get_correlation_id())
    try:
        _scan_candidates(batch_size=batch_size, now=now or timezone.now(), report=report)
    finally:
        reset_correlation_id(token)
    logger.info(
        "lease-expiring scan complete",
        extra={
            "notifier_warned": report.warned,
            "notifier_already_warned": report.already_warned,
            "notifier_skipped": report.skipped,
        },
    )
    return report


def _scan_candidates(*, batch_size: int, now: datetime, report: NotifyReport) -> None:
    candidates = (
        Task.objects.filter(
            state=TaskState.IN_PROGRESS,
            lease_acquired_at__isnull=False,
            # Still-valid leases only: an expired lease is the sweeper's T5,
            # never a warning.
            lease_expires_at__gt=now,
        )
        .order_by("lease_expires_at")
        .values_list("pk", "lease_acquired_at", "lease_expires_at")[:batch_size]
    )
    for task_id, acquired_at, expires_at in candidates:
        if not _past_threshold(acquired_at=acquired_at, expires_at=expires_at, now=now):
            continue
        _warn_one(task_id=task_id, report=report)


def _past_threshold(
    *,
    acquired_at: datetime | None,
    expires_at: datetime | None,
    now: datetime,
) -> bool:
    """True when *now* has passed 80% of the (acquired, expires) window.

    Fails closed on degenerate or missing windows: a zero/negative window
    (policy validation is WP-1.3's job) never produces a warning.
    """
    if acquired_at is None or expires_at is None:
        return False
    window = expires_at - acquired_at
    if window <= timedelta(0):
        return False
    return now >= acquired_at + window * LEASE_EXPIRING_FRACTION


def _warn_one(*, task_id: str, report: NotifyReport) -> None:
    with transaction.atomic():
        # Re-read under the row lock so two concurrent notifiers serialize on
        # the task and the dedupe check sees the committed sibling emission.
        task = (
            Task.objects.select_for_update(skip_locked=True)
            .select_related("project")
            .filter(pk=task_id, state=TaskState.IN_PROGRESS)
            .first()
        )
        if task is None:
            report.skipped += 1  # swept or released between scan and lock
            return
        now = timezone.now()
        if not _past_threshold(
            acquired_at=task.lease_acquired_at, expires_at=task.lease_expires_at, now=now
        ):
            # Expired, extended past the threshold, or degenerate at lock time.
            report.skipped += 1
            return
        if _already_warned(task):
            report.already_warned += 1
            logger.debug(
                "lease-expiring warning already emitted for this window",
                extra={
                    "task_id": str(task.pk),
                    "lease_generation": task.lease_generation,
                    "lease_expires_at": task.lease_expires_at.isoformat()
                    if task.lease_expires_at
                    else None,
                },
            )
            return
        event = write_event(
            type=EventType.TASK_LEASE_EXPIRING,
            project_id=str(task.project_id),
            task_id=str(task.pk),
            actor_type="system",
            actor_ref=NOTIFIER_ACTOR_REF,
            data={
                "task_id": str(task.pk),
                "lease_generation": task.lease_generation,
                "lease_expires_at": task.lease_expires_at.isoformat()
                if task.lease_expires_at
                else None,
            },
        )
        report.warned += 1
        logger.info(
            "lease-expiring warning emitted",
            extra={
                "task_id": str(task.pk),
                "event_id": str(event.pk),
                "lease_generation": task.lease_generation,
                "lease_expires_at": task.lease_expires_at.isoformat()
                if task.lease_expires_at
                else None,
            },
        )


def _already_warned(task: Task) -> bool:
    """Dedupe on the (generation, window) key via the append-only Event log."""
    warnings: EventQuerySet = Event.objects.filter(
        type=EventType.TASK_LEASE_EXPIRING,
        task_id=str(task.pk),
        data__lease_generation=task.lease_generation,
        data__lease_expires_at=task.lease_expires_at.isoformat() if task.lease_expires_at else None,
    )
    return warnings.exists()
