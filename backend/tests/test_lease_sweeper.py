"""MT-1.7-02 — the lease sweeper job (Sections 6.5 Flow B, 8.6, 9.9).

Run with ``pytest backend/tests -k lease_sweeper -q``: reclaim side effects,
unexpired/empty no-ops, sequential double-sweep idempotency and the
post-sweep ``LEASE_EXPIRED`` shape for the former owner. The concurrent
double-sweeper, chaos and PG lock proofs live in
``tests/integration/test_sweeper_chaos_postgres.py`` (MT-1.7-05).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.events.models import Event, EventType
from apps.leases.exceptions import LeaseExpired
from apps.leases.extension import extend_lease
from apps.leases.release import release_task
from apps.leases.sweeper import sweep_expired_leases
from apps.tasks.models import Task, TaskState, TaskTransition

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _expire(task: Task) -> Task:
    """Model time instead of waiting: push the lease into the past."""
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    task.refresh_from_db()
    return task


def _held_expired_task(**policy_fields: Any) -> tuple[Task, int]:
    """A claimed task whose lease has passed; returns (task, generation)."""
    project = active_policy_project(**policy_fields)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_dead_worker")
    task.refresh_from_db()
    generation = task.lease_generation
    return _expire(task), generation


def test_expired_lease_reclaimed_to_pending_with_side_effects() -> None:
    task, generation = _held_expired_task()

    report = sweep_expired_leases()

    task.refresh_from_db()
    assert report.reclaimed == 1
    assert report.escalated == 0
    assert report.skipped == 0
    # T5 side effects: pending, failure_retry_count + 1, worker lease cleared,
    # generation untouched (T5 never decrements — Section 8.6 fencing).
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1
    assert task.worker_agent_id is None
    assert task.worker_session_id is None
    assert task.lease_acquired_at is None
    assert task.lease_expires_at is None
    assert task.lease_generation == generation
    # Exactly one history row and one catalog event, written in-transaction.
    assert (
        TaskTransition.objects.filter(
            task_id=task.pk, from_state=TaskState.IN_PROGRESS, to_state=TaskState.PENDING
        ).count()
        == 1
    )
    events = Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk)
    assert events.count() == 1
    assert events.get().actor_ref == "lease-sweeper"
    # The run's correlation id (WP-0.5-03) scopes every event it wrote.
    assert events.get().correlation_id == report.correlation_id
    assert report.correlation_id != ""


def test_unexpired_lease_is_untouched() -> None:
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_alive")
    task.refresh_from_db()
    assert task.lease_expires_at is not None
    assert task.lease_expires_at > timezone.now()

    report = sweep_expired_leases()

    task.refresh_from_db()
    assert report.processed == 0
    assert task.state == TaskState.IN_PROGRESS
    assert task.failure_retry_count == 0
    assert TaskTransition.objects.filter(task_id=task.pk).count() == 1  # T4 only
    assert not Event.objects.filter(task_id=task.pk, type=EventType.TASK_LEASE_EXPIRED).exists()


def test_empty_sweep_is_clean_noop() -> None:
    project = active_policy_project()
    make_pending_task(project, 1)  # pending rows are never sweep candidates

    report = sweep_expired_leases()

    assert report.processed == 0
    assert report.correlation_id != ""
    assert not Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED).exists()
    assert TaskTransition.objects.count() == 0


def test_sequential_second_sweep_is_a_noop() -> None:
    task, _generation = _held_expired_task()

    first = sweep_expired_leases()
    second = sweep_expired_leases()

    assert first.reclaimed == 1
    assert second.processed == 0
    assert (
        TaskTransition.objects.filter(
            task_id=task.pk, from_state=TaskState.IN_PROGRESS, to_state=TaskState.PENDING
        ).count()
        == 1
    )
    assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk).count() == 1


def test_batches_repeat_until_no_candidates_remain() -> None:
    project = active_policy_project(max_concurrent_tasks=3)
    tasks = []
    for index in (1, 2, 3):
        task = make_pending_task(project, index)
        claim(task, session_id=f"sess_dead_{index}")
        tasks.append(_expire(task))

    report = sweep_expired_leases(batch_size=2)

    assert report.reclaimed == 3
    for task in tasks:
        task.refresh_from_db()
        assert task.state == TaskState.PENDING
    assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED).count() == 3


def test_old_owner_mutations_after_sweep_fail_lease_expired() -> None:
    task, generation = _held_expired_task()
    sweep_expired_leases()
    task.refresh_from_db()

    # The late owner's checkpoint-equivalent (extension driver, Section 8.6)
    # and its release both refuse with LEASE_EXPIRED — no resurrection.
    with pytest.raises(LeaseExpired):
        extend_lease(task_id=task.pk, session_id="sess_dead_worker", lease_generation=generation)
    with pytest.raises(LeaseExpired):
        release_task(
            task_id=task.pk,
            session_id="sess_dead_worker",
            lease_generation=generation,
            actor_type="agent",
            actor_ref="sess_dead_worker",
        )

    task.refresh_from_db()
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1
    assert task.worker_agent_id is None
    assert task.lease_expires_at is None


def test_invalid_batch_size_is_rejected() -> None:
    with pytest.raises(ValueError):
        sweep_expired_leases(batch_size=0)
