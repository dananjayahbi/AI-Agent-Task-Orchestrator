"""MT-1.7-03 — retry-exhaustion escalation in the sweep cycle (G-10, FR-LEA-07).

Run with ``pytest backend/tests -k retry_exhaustion -q``: the escalation
boundary (below / exactly at / above the project's ``max_retries``), the
custom-policy path, the Section 9.8 push trigger with its dedupe key, and
the sweeper's no-touch guarantee once a task is in ``in_human_review``.

Recorded reading pinned by these tests (Section 6.5 Flow B vs the frozen
registry): T9's from-state is ``in_progress``, so the sweep dispatches T9
*instead of* T5 once ``failure_retry_count`` already meets ``max_retries``
— "the sweep following the increment" escalates; the increment itself is
the preceding T5. One transition per expired row, no
``pending`` ↔ ``in_progress`` loop (G-10).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.events.models import Event, EventType
from apps.leases.sweeper import sweep_expired_leases
from apps.tasks.models import ReviewReason, Task, TaskState, TaskTransition

from .wp15_helpers import install_push_recorder
from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    install_event_recorder,
    make_pending_task,
    reset_hooks,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _expire(task: Task) -> Task:
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    task.refresh_from_db()
    return task


def _dead_cycle(project_id: str, task: Task) -> Task:
    """Claim (if needed), expire the lease, and run one sweep."""
    task.refresh_from_db()
    if task.state != TaskState.IN_PROGRESS:
        claim(task, session_id=f"sess_attempt_{task.attempt_number + 1}")
    _expire(task)
    sweep_expired_leases()
    task.refresh_from_db()
    return task


def test_below_max_retries_the_task_returns_to_pending_and_stays_claimable() -> None:
    project = active_policy_project(max_retries=3)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_first")
    _expire(task)

    report = sweep_expired_leases()
    task.refresh_from_db()

    assert report.reclaimed == 1
    assert report.escalated == 0
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1
    assert task.review_reason is None
    # Still claimable — G-10 bounded retries, not immediate escalation.
    claim(task, session_id="sess_second")
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS


def test_exactly_at_max_retries_the_next_sweep_escalates() -> None:
    """count == max_retries on an expired lease escalates instead of requeues."""
    project = active_policy_project(max_retries=3)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_first")
    Task.objects.filter(pk=task.pk).update(failure_retry_count=3)
    _expire(task)

    report = sweep_expired_leases()
    task.refresh_from_db()

    assert report.reclaimed == 0
    assert report.escalated == 1
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == ReviewReason.RETRY_EXHAUSTED
    # T9 does not increment — the budget was already spent by prior T5s.
    assert task.failure_retry_count == 3
    assert task.worker_agent_id is None
    # Section 20.4 item 6: one history row, one catalog event for the T9.
    assert (
        TaskTransition.objects.filter(task_id=task.pk, to_state=TaskState.IN_HUMAN_REVIEW).count()
        == 1
    )
    assert (
        Event.objects.filter(
            type=EventType.TASK_TRANSITIONED,
            task_id=task.pk,
            data__to_state=TaskState.IN_HUMAN_REVIEW,
        ).count()
        == 1
    )


def test_escalation_fires_after_the_increment_that_reaches_max_retries() -> None:
    """The documented loop: requeue until the budget is spent, then escalate."""
    project = active_policy_project(max_retries=2)
    task = make_pending_task(project, 1)

    # Attempt 1: expiry -> T5 (count 1 < 2), task back to pending.
    _dead_cycle(project.pk, task)
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1

    # Attempt 2: expiry -> T5 (count 2 == 2), task back to pending.
    _dead_cycle(project.pk, task)
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 2

    # Attempt 3: expiry -> T9 escalation (budget already exhausted).
    _dead_cycle(project.pk, task)
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == ReviewReason.RETRY_EXHAUSTED
    assert task.failure_retry_count == 2


def test_custom_project_max_retries_is_honoured() -> None:
    project = active_policy_project(max_retries=1)
    task = make_pending_task(project, 1)

    _dead_cycle(project.pk, task)  # T5: count 1 == custom max
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1

    _dead_cycle(project.pk, task)  # T9: escalation at the project's own budget
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == ReviewReason.RETRY_EXHAUSTED


def test_push_trigger_fires_once_with_the_section_9_8_dedupe_key() -> None:
    project = active_policy_project(max_retries=1)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_first")
    Task.objects.filter(pk=task.pk).update(failure_retry_count=1)
    _expire(task)
    pushes = install_push_recorder()

    sweep_expired_leases()
    task.refresh_from_db()

    assert len(pushes) == 1
    payload = pushes[0]
    assert payload["event_type"] == "task.transitioned"
    assert payload["task_id"] == task.pk
    assert payload["project_id"] == project.pk
    assert payload["reason_code"] == "retry_exhausted"
    assert payload["state_version"] == task.version
    reset_hooks()


def test_escalation_dispatch_runs_inside_one_transaction() -> None:
    project = active_policy_project(max_retries=1)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_first")
    Task.objects.filter(pk=task.pk).update(failure_retry_count=1)
    _expire(task)
    records = install_event_recorder()

    sweep_expired_leases()
    task.refresh_from_db()

    # The event emission (and the history write sharing its transaction)
    # happened inside the dispatcher's atomic block (Section 20.4 item 6).
    transition_records = [r for r in records if r["data"]["to_state"] == TaskState.IN_HUMAN_REVIEW]
    assert len(transition_records) == 1
    assert transition_records[0]["_in_atomic_block"] is True
    assert (
        TaskTransition.objects.filter(task_id=task.pk, to_state=TaskState.IN_HUMAN_REVIEW).count()
        == 1
    )
    reset_hooks()


def test_sweeper_never_reprocesses_a_task_in_human_review() -> None:
    project = active_policy_project(max_retries=1)
    task = make_pending_task(project, 1)
    _dead_cycle(project.pk, task)
    _dead_cycle(project.pk, task)  # escalated
    assert task.state == TaskState.IN_HUMAN_REVIEW
    transitions_before = TaskTransition.objects.filter(task_id=task.pk).count()

    report = sweep_expired_leases()

    task.refresh_from_db()
    assert report.processed == 0
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == ReviewReason.RETRY_EXHAUSTED
    assert TaskTransition.objects.filter(task_id=task.pk).count() == transitions_before
