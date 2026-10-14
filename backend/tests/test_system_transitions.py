"""MT-1.5-03 — system transitions T5 (lease expired), T9 (retry exhausted).

Run with ``pytest backend/tests -k system_transitions -q``. The system
actor (**S**) rows of Section 8.2: guards against the clock and the
policy's ``max_retries``, the exact side-effect sets, the Section 9.6
event, and the Section 9.8 push trigger.

Asserted here per the acceptance criteria:

* T5 exactly as the table: guard ``lease_expires_at`` < now,
  ``failure_retry_count`` + 1, clear worker fields, emit
  ``task.lease_expired`` — a Section 9.6 catalog event;
* T9 exactly as the table: guard ``failure_retry_count`` >=
  ``max_retries`` (project policy, default 3), ``review_reason`` =
  ``retry_exhausted`` (canonical Section 8.4 member), push on entry;
* both refuse from every state but ``in_progress`` with
  ``TASK_STATE_CONFLICT`` (409);
* the boundary: ``max_retries - 1`` still allows T5 and still refuses
  T9; at ``max_retries`` the escalation path applies;
* Transition rows carry ``actor_type`` ``system`` with a sweeper
  ``actor_ref`` (FR-TSK-04).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework import status

from apps.core.errors import ROLE_NOT_PERMITTED, TASK_STATE_CONFLICT
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict, TransitionActorForbidden
from apps.tasks.models import ReviewReason, Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp15_helpers import (
    SECTION_9_6_EVENTS,
    install_event_recorder,
    install_push_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)

SWEEPER = "lease-sweeper"  # the Section 9.6 actor ref example


@pytest.fixture(autouse=True)
def registry_guard() -> Iterator[None]:
    """No registrations happen in this suite; keep the default rows stable."""
    with registered_registry():
        yield


@pytest.fixture(autouse=True)
def clean_hooks() -> Iterator[None]:
    """Default no-op seams unless a test installs a recorder."""
    reset_hooks()
    yield
    reset_hooks()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the system-transition tests (policy defaults)."""
    return make_project(name="System transitions")


def _make_claimed(project: Project, index: int, *, retry_count: int = 0) -> Task:
    """An ``in_progress`` task with worker, session and a live-looking lease."""
    task = make_task(project, index, state=TaskState.IN_PROGRESS)
    task.worker_agent_id = "claude-code-session-98b2"
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = "coder"
    task.lease_acquired_at = timezone.now() - timedelta(minutes=10)
    task.lease_expires_at = timezone.now() + timedelta(minutes=35)
    task.failure_retry_count = retry_count
    task.save()
    return task


def _dispatch(task: Task, trigger: str, **kwargs: Any) -> Task:
    """Dispatch *trigger* as the system sweeper (Section 8.2 actor S)."""
    payload: dict[str, Any] = {"actor_type": "system", "actor_ref": SWEEPER}
    payload.update(kwargs)
    return dispatch_transition(task_id=task.pk, trigger=trigger, **payload)


def _history(task: Task) -> list[TaskTransition]:
    return list(TaskTransition.objects.filter(task=task).order_by("timestamp", "id"))


# --- T5: lease expired (in_progress -> pending) ------------------------------


def test_lease_expired_returns_task_to_pending_with_all_side_effects(
    project: Project,
) -> None:
    """T5 verbatim: +1 failure, cleared worker, task.lease_expired event."""
    events = install_event_recorder()
    pushes = install_push_recorder()
    task = _make_claimed(project, 1)
    task.lease_expires_at = timezone.now() - timedelta(minutes=1)
    task.save()

    result = _dispatch(task, "lease_expired")

    assert result.state == TaskState.PENDING
    assert result.failure_retry_count == 1, "Section 8.2 T5: failure_retry_count+1"
    assert result.worker_agent_id is None
    assert result.worker_session_id is None
    assert result.claimed_role is None, "Section 8.3 rule 1: no coder lease outside in_progress"
    assert result.lease_acquired_at is None and result.lease_expires_at is None
    assert result.version == 2

    assert [event["type"] for event in events] == ["task.lease_expired"]
    assert events[0]["type"] in SECTION_9_6_EVENTS, "Section 9.6 catalog (20.4 item 6)"
    assert events[0]["_in_atomic_block"] is True
    assert pushes == [], "T5 is not an in_human_review entry (Section 9.8)"

    row = _history(task)[0]
    assert (
        row.actor_type,
        row.actor_ref,
        row.from_state,
        row.to_state,
        row.reason_code,
    ) == ("system", SWEEPER, "in_progress", "pending", "lease_expired")


@pytest.mark.parametrize(
    ("lease_delta_minutes",),
    [(35,), (5,)],
)
def test_lease_expired_guard_requires_a_strictly_past_lease(
    project: Project, lease_delta_minutes: int
) -> None:
    """Guard ``lease_expires_at`` < now — a future deadline refuses (409)."""
    task = _make_claimed(project, 1)
    task.lease_expires_at = timezone.now() + timedelta(minutes=lease_delta_minutes)
    task.save()

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "lease_expired")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS and task.version == 1
    assert _history(task) == []


def test_lease_expired_guard_treats_the_deadline_itself_as_not_expired(
    project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The table says ``< now`` — a lease expiring *exactly* now refuses.

    Frozen clock (the natural race in comparing against a live clock):
    ``lease_expires_at == now`` is not yet expired, so the sweeper waits
    for the next tick instead of reclaiming a live lease.
    """
    from apps.tasks.state_machine import transitions_system

    instant = timezone.now()
    task = _make_claimed(project, 1)
    task.lease_expires_at = instant
    task.save()

    class _FrozenClock:
        @staticmethod
        def now() -> Any:
            return instant

    monkeypatch.setattr(transitions_system, "timezone", _FrozenClock)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "lease_expired")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS and task.version == 1


def test_lease_expired_guard_refuses_a_task_without_a_lease(project: Project) -> None:
    """``None`` never satisfies ``< now`` — nothing to sweep answers 409."""
    task = make_task(project, 1, state=TaskState.IN_PROGRESS)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "lease_expired")

    assert caught.value.default_code == TASK_STATE_CONFLICT


def test_lease_expired_still_applies_at_the_retry_boundary(project: Project) -> None:
    """``max_retries - 1`` failures: T5 keeps working (the sweeper's requeue path)."""
    limit = project.agent_policy.max_retries  # Section 7.2 default: 3
    task = _make_claimed(project, 1, retry_count=limit - 1)
    task.lease_expires_at = timezone.now() - timedelta(minutes=1)
    task.save()

    result = _dispatch(task, "lease_expired")

    assert result.state == TaskState.PENDING
    assert result.failure_retry_count == limit, "still increments; escalation is T9's call"


@pytest.mark.parametrize(
    "state",
    [
        TaskState.DRAFT,
        TaskState.PENDING,
        TaskState.TO_BE_AUDITED,
        TaskState.IN_HUMAN_REVIEW,
        TaskState.COMPLETED,
    ],
)
def test_lease_expired_is_refused_outside_in_progress(project: Project, state: str) -> None:
    """T5's From column is exactly ``in_progress`` — anything else is a 409."""
    task = make_task(project, 1, state=state)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "lease_expired")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.version == 1 and _history(task) == []


def test_lease_expired_is_system_only(project: Project) -> None:
    """The Actor column: owner/agent may not sweep leases."""
    task = _make_claimed(project, 1)
    task.lease_expires_at = timezone.now() - timedelta(minutes=1)
    task.save()

    for actor in ("owner", "agent"):
        with pytest.raises(TransitionActorForbidden) as caught:
            _dispatch(task, "lease_expired", actor_type=actor, actor_ref="u")
        assert caught.value.default_code == ROLE_NOT_PERMITTED
        assert caught.value.status_code == status.HTTP_403_FORBIDDEN


# --- T9: retry exhausted (in_progress -> in_human_review) --------------------


def test_retry_exhausted_escalates_with_reason_worker_clearing_and_push(
    project: Project,
) -> None:
    """T9 verbatim + the recorded invariant-1 clearing + Section 9.8 push."""
    events = install_event_recorder()
    pushes = install_push_recorder()
    task = _make_claimed(project, 1, retry_count=project.agent_policy.max_retries)

    result = _dispatch(task, "retry_exhausted")

    assert result.state == TaskState.IN_HUMAN_REVIEW
    assert result.review_reason == ReviewReason.RETRY_EXHAUSTED
    assert result.worker_agent_id is None and result.claimed_role is None
    assert result.lease_expires_at is None, "Section 8.3 rule 1 (recorded reading)"
    assert result.version == 2

    # The row's own event, then the WP-3.9 review.requested entry event
    # (MT-3.9-02: one per in_human_review entry, in the same transaction).
    assert [event["type"] for event in events] == ["task.transitioned", "review.requested"]
    entry = events[1]
    assert entry["data"]["review_reason"] == ReviewReason.RETRY_EXHAUSTED
    assert entry["data"]["task_version"] == result.version
    assert len(pushes) == 1, "Section 9.8: push on in_human_review entry"
    push = pushes[0]
    assert push["task_id"] == task.pk
    assert push["state_version"] == 2, "dedupe key: (event type, task id, state version)"
    assert push["reason_code"] == "retry_exhausted"
    assert push["event_type"] in SECTION_9_6_EVENTS

    row = _history(task)[0]
    assert (
        row.actor_type,
        row.actor_ref,
        row.from_state,
        row.to_state,
        row.reason_code,
    ) == ("system", SWEEPER, "in_progress", "in_human_review", "retry_exhausted")


@pytest.mark.parametrize("retry_count", [0, 2])
def test_retry_exhausted_is_refused_below_max_retries(project: Project, retry_count: int) -> None:
    """The boundary's lower half: policy default max_retries = 3 (G-10)."""
    assert project.agent_policy.max_retries == 3, "Section 7.2 default"
    task = _make_claimed(project, 1, retry_count=retry_count)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "retry_exhausted")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.state == TaskState.IN_PROGRESS and task.version == 1
    assert _history(task) == []


def test_retry_exhausted_applies_at_and_above_max_retries(project: Project) -> None:
    """The boundary's upper half: >= max_retries escalates (exact + over)."""
    pushes = install_push_recorder()
    for index, retry_count in enumerate(
        (project.agent_policy.max_retries, project.agent_policy.max_retries + 1), start=1
    ):
        task = _make_claimed(project, index, retry_count=retry_count)

        result = _dispatch(task, "retry_exhausted")

        assert result.state == TaskState.IN_HUMAN_REVIEW
        assert result.review_reason == ReviewReason.RETRY_EXHAUSTED
    assert len(pushes) == 2


def test_retry_exhausted_reads_the_project_policy(project: Project) -> None:
    """``max_retries`` is per policy — a policy of 1 shifts the boundary."""
    policy = project.agent_policy
    policy.max_retries = 1
    policy.save()

    below = _make_claimed(project, 1, retry_count=0)
    with pytest.raises(TaskStateConflict):
        _dispatch(below, "retry_exhausted")

    at_limit = _make_claimed(project, 2, retry_count=1)
    result = _dispatch(at_limit, "retry_exhausted")
    assert result.state == TaskState.IN_HUMAN_REVIEW


@pytest.mark.parametrize(
    "state",
    [
        TaskState.DRAFT,
        TaskState.PENDING,
        TaskState.TO_BE_AUDITED,
        TaskState.IN_HUMAN_REVIEW,
        TaskState.COMPLETED,
    ],
)
def test_retry_exhausted_is_refused_outside_in_progress(project: Project, state: str) -> None:
    """T9's From column is exactly ``in_progress`` — anything else is a 409."""
    task = make_task(project, 1, state=state, failure_retry_count=3)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "retry_exhausted")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.version == 1 and _history(task) == []


def test_retry_exhausted_is_system_only(project: Project) -> None:
    """The Actor column: only the sweeper escalates retries."""
    task = _make_claimed(project, 1, retry_count=3)

    for actor in ("owner", "agent"):
        with pytest.raises(TransitionActorForbidden):
            _dispatch(task, "retry_exhausted", actor_type=actor, actor_ref="u")
