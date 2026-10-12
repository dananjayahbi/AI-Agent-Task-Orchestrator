"""MT-1.6-04 — voluntary release, T6 (Section 8.2; FR-LEA-06).

Run with ``pytest backend/tests -k voluntary_release -q``: the no-
failure-increment rule, ownership refusals, the Owner override, and the
late-owner shape; the endpoint wiring (idempotency, permissions) is
``test_claim_release_endpoints.py``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.leases.exceptions import LeaseExpired, LeaseNotOwned
from apps.leases.release import release_task
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict, VersionConflict
from apps.tasks.models import Task, TaskState, TaskTransition

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    install_event_recorder,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _held_task(**policy_fields: Any) -> tuple[Project, Task]:
    """A claimed task held by sess_owner (claim bumps attempt to 1)."""
    project = active_policy_project(**policy_fields)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_owner")
    task.refresh_from_db()
    return project, task


def _release(
    task: Task,
    *,
    session_id: str | None = "sess_owner",
    generation: int | None = None,
    actor_type: str = "agent",
    owner_override: bool = False,
    reason: str = "",
    expected_version: int | None = None,
) -> Task:
    return release_task(
        task_id=task.pk,
        session_id=session_id,
        lease_generation=task.lease_generation if generation is None else generation,
        actor_type=actor_type,
        actor_ref=session_id or "owner-ref",
        owner_override=owner_override,
        reason=reason,
        expected_version=expected_version,
        caller_project_id=task.project_id,
    )


def test_owner_release_clears_the_lease_without_failure_increment() -> None:
    """FR-LEA-06: pending again, workers cleared, counters untouched."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    Task.objects.filter(pk=task.pk).update(failure_retry_count=2)  # prior T5 history
    events = install_event_recorder()
    claim(task, session_id="sess_owner")
    task.refresh_from_db()

    released = _release(task, reason="handing back")

    assert released.state == TaskState.PENDING
    assert released.worker_agent_id is None
    assert released.worker_session_id is None
    assert released.claimed_role is None
    assert released.lease_acquired_at is None and released.lease_expires_at is None
    assert released.failure_retry_count == 2, "no failure increment (FR-LEA-06)"
    assert released.attempt_number == 1, "attempt preserved (T16 comparison)"
    assert released.lease_generation == 1, "release does not bump the generation"
    assert released.version == 3  # claim bumped to 2, release to 3

    rows = list(TaskTransition.objects.filter(task=released))
    assert len(rows) == 2
    last = rows[-1]
    assert (last.from_state, last.to_state) == (TaskState.IN_PROGRESS, TaskState.PENDING)
    assert last.actor_type == "agent" and last.reason_code == "voluntary_release"
    assert last.note == "handing back"
    assert [event["type"] for event in events] == ["task.claimed", "task.released"]


def test_foreign_session_is_lease_not_owned() -> None:
    """Ownership guard: another session on a live lease → LEASE_NOT_OWNED."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    events = install_event_recorder()
    claim(task, session_id="sess_owner")
    task.refresh_from_db()

    with pytest.raises(LeaseNotOwned) as caught:
        _release(task, session_id="sess_intruder")

    assert caught.value.status_code == 403
    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.IN_PROGRESS, "nothing changed"
    assert fresh.version == 2
    assert not TaskTransition.objects.filter(task=task, reason_code="voluntary_release").exists()
    assert [event["type"] for event in events] == ["task.claimed"], "the refusal emits nothing"


def test_expired_lease_release_is_lease_expired() -> None:
    """An expired lease is the sweeper's to reclaim — LEASE_EXPIRED (409)."""
    _, task = _held_task()
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    task.refresh_from_db()

    with pytest.raises(LeaseExpired) as caught:
        _release(task)

    assert caught.value.status_code == 409
    assert Task.objects.get(pk=task.pk).state == TaskState.IN_PROGRESS, "T6 not applied"


def test_release_of_non_claimed_task_is_state_conflict() -> None:
    """Wrong from-state → the registry's TASK_STATE_CONFLICT (409)."""
    project = active_policy_project()
    pending = make_pending_task(project, 1)

    with pytest.raises(TaskStateConflict):
        _release(pending)


def test_late_owner_after_sweep_gets_lease_expired() -> None:
    """WP-1.6 acceptance: late owner call after reclaim → LEASE_EXPIRED."""
    project, task = _held_task()
    # Simulate T5's outcome: lease expired, task back to pending, worker cleared.
    Task.objects.filter(pk=task.pk).update(
        state=TaskState.PENDING,
        worker_agent_id=None,
        worker_session_id=None,
        claimed_role=None,
        lease_acquired_at=None,
        lease_expires_at=None,
    )
    task.refresh_from_db()
    version_before = task.version

    with pytest.raises(LeaseExpired) as caught:
        _release(task)  # same session, same generation — the lease is gone

    assert caught.value.status_code == 409
    assert Task.objects.get(pk=task.pk).version == version_before, "zero writes"


def test_owner_override_releases_anyone_lease() -> None:
    """Section 8.2 T6 "(or Owner override)" — actors C, O both admitted."""
    _, task = _held_task()

    released = _release(
        task,
        session_id=None,
        generation=None,
        actor_type="owner",
        owner_override=True,
        reason="owner reassigned the work",
    )

    assert released.state == TaskState.PENDING
    last = TaskTransition.objects.filter(task=released).latest("timestamp")
    assert last.actor_type == "owner", "the override is auditable (Section 12.5)"
    assert last.note == "owner reassigned the work"


def test_owner_override_skips_the_fencing_pair() -> None:
    """An owner release without session/generation still applies (override)."""
    _, task = _held_task()
    released = _release(
        task,
        session_id=None,
        generation=None,
        actor_type="owner",
        owner_override=True,
    )
    assert released.state == TaskState.PENDING


def test_agent_release_without_fencing_pair_is_validation_error() -> None:
    """ADR-012: presence is enforced — an omitted generation is not a wildcard."""
    _, task = _held_task()

    with pytest.raises(ValidationError):
        release_task(
            task_id=task.pk,
            session_id=None,
            lease_generation=None,
            actor_type="agent",
            actor_ref="sess_owner",
            caller_project_id=task.project_id,
        )


def test_stale_version_is_version_conflict() -> None:
    """Optional FR-TSK-06 check on release (MT-1.6-04 risk note)."""
    _, task = _held_task()

    with pytest.raises(VersionConflict) as caught:
        _release(task, expected_version=1)  # claim already moved it to 2

    assert caught.value.status_code == 409
    assert Task.objects.get(pk=task.pk).state == TaskState.IN_PROGRESS


def test_double_release_reports_lease_expired() -> None:
    """A second T6 without an idempotency replay: the lease is already gone.

    Indistinguishable from the swept-late-owner shape (pending + current
    generation) — one documented refusal serves both; a *retried* release
    with the same ``Idempotency-Key`` replays the original 200 instead
    (endpoint suite).
    """
    _, task = _held_task()
    _release(task)
    with pytest.raises(LeaseExpired):
        _release(task)
