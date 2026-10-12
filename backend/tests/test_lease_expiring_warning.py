"""MT-1.7-04 — the lease-expiring warning at 80% of lease (Sections 9.6, 9.9).

Run with ``pytest backend/tests -k lease_expiring_warning -q``: the 80%
threshold, exactly-once-per-window emission, no warning for expired or
swept leases, and the documented re-arm rule (a checkpoint extension
redefines ``lease_expires_at`` and therefore the window — the warning
re-arms at 80% of the new window; the generation is part of the dedupe
key).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.models import Event, EventQuerySet, EventType
from apps.leases.extension import extend_lease
from apps.leases.notifier import notify_lease_expiring
from apps.leases.release import release_task
from apps.leases.sweeper import sweep_expired_leases
from apps.tasks.models import Task, TaskState

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db

WINDOW = timedelta(minutes=45)  # the Section 7.2 default duration


def _held_task_with_window(*, elapsed: timedelta, window: timedelta = WINDOW) -> Task:
    """A claimed task whose lease window started *elapsed* ago (model time)."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_holder")
    now = timezone.now()
    acquired = now - elapsed
    Task.objects.filter(pk=task.pk).update(
        lease_acquired_at=acquired, lease_expires_at=acquired + window
    )
    task.refresh_from_db()
    return task


def _warning_events(task: Task) -> EventQuerySet:
    queryset: EventQuerySet = Event.objects.filter(
        type=EventType.TASK_LEASE_EXPIRING, task_id=task.pk
    )
    return queryset


def test_sub_80_percent_of_the_window_produces_no_event() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=30))  # 30 < 36 = 80% of 45

    report = notify_lease_expiring()

    assert report.warned == 0
    assert report.already_warned == 0
    assert _warning_events(task).count() == 0


def test_crossing_80_percent_emits_exactly_one_catalog_event() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=37))  # 37 > 36

    report = notify_lease_expiring()

    task.refresh_from_db()
    assert report.warned == 1
    events = _warning_events(task)
    assert events.count() == 1
    event = events.get()
    # Section 9.6 envelope: catalog type, project/task ids, system actor.
    assert event.type == "task.lease_expiring"
    assert event.project_id == task.project_id
    assert event.task_id == task.pk
    assert event.actor_type == "system"
    assert event.actor_ref == "lease-expiring-notifier"
    # Payload data: what consumers need to act (task id, expiry, generation).
    assert event.data["task_id"] == task.pk
    assert event.data["lease_generation"] == task.lease_generation
    assert task.lease_expires_at is not None
    assert event.data["lease_expires_at"] == task.lease_expires_at.isoformat()
    assert event.correlation_id == report.correlation_id


def test_repeated_runs_within_one_window_never_duplicate() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=37))

    first = notify_lease_expiring()
    second = notify_lease_expiring()

    assert first.warned == 1
    assert second.warned == 0
    assert second.already_warned == 1
    assert _warning_events(task).count() == 1


def test_no_warning_for_an_expired_lease_sweep_takes_over() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=50))  # past the window

    warning = notify_lease_expiring()
    sweep = sweep_expired_leases()
    task.refresh_from_db()

    assert warning.warned == 0
    assert _warning_events(task).count() == 0
    # T5's task.lease_expired stays the sole expiry event.
    assert sweep.reclaimed == 1
    assert task.state == TaskState.PENDING
    assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk).count() == 1


def test_checkpoint_extension_rearms_the_warning_in_a_new_window() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=37))
    assert notify_lease_expiring().warned == 1

    # A valid checkpoint extension (MT-1.6-03's driver) redefines the expiry:
    # the warning re-arms at 80% of the *new* window, not immediately.
    extension = extend_lease(
        task_id=task.pk, session_id="sess_holder", lease_generation=task.lease_generation
    )
    task.refresh_from_db()
    assert extension.lease_expires_at == task.lease_expires_at
    assert notify_lease_expiring().warned == 0  # new 80% point is still ahead

    # Model time: push the new window past its own 80% point (same generation).
    now = timezone.now()
    Task.objects.filter(pk=task.pk).update(
        lease_acquired_at=now - timedelta(minutes=60),
        lease_expires_at=now + timedelta(minutes=5),
    )
    task.refresh_from_db()
    assert notify_lease_expiring().warned == 1

    # Two windows, two warnings — deduped per (generation, expiry), not per task.
    events = _warning_events(task).order_by("id")
    assert events.count() == 2
    last = events.last()
    assert last is not None
    assert task.lease_expires_at is not None
    assert last.data["lease_expires_at"] == task.lease_expires_at.isoformat()
    assert last.data["lease_generation"] == task.lease_generation


def test_a_new_claim_generation_starts_a_new_window() -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=37))
    assert notify_lease_expiring().warned == 1
    old_generation = task.lease_generation

    release_task(
        task_id=task.pk,
        session_id="sess_holder",
        lease_generation=task.lease_generation,
        actor_type="agent",
        actor_ref="sess_holder",
    )
    claim(task, session_id="sess_holder_again")
    now = timezone.now()
    acquired = now - timedelta(minutes=40)  # 40 > 36 = 80% of the 45-minute window
    Task.objects.filter(pk=task.pk).update(
        lease_acquired_at=acquired, lease_expires_at=acquired + WINDOW
    )
    task.refresh_from_db()
    assert task.lease_generation == old_generation + 1

    report = notify_lease_expiring()

    assert report.warned == 1
    last = _warning_events(task).order_by("id").last()
    assert last is not None
    assert last.data["lease_generation"] == old_generation + 1


@pytest.mark.parametrize(
    ("elapsed", "window"),
    [
        (timedelta(0), timedelta(0)),  # zero-length window — fail closed
        (timedelta(minutes=2), timedelta(minutes=-1)),  # negative window — fail closed
    ],
)
def test_degenerate_windows_fail_closed(elapsed: timedelta, window: timedelta) -> None:
    task = _held_task_with_window(elapsed=timedelta(minutes=1))
    now = timezone.now()
    Task.objects.filter(pk=task.pk).update(
        lease_acquired_at=now + elapsed, lease_expires_at=now + elapsed + window
    )

    report = notify_lease_expiring()

    assert report.warned == 0
    assert _warning_events(task).count() == 0


def test_invalid_batch_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        notify_lease_expiring(batch_size=0)
