"""MT-1.6-01 — the atomic claim transaction (Section 9.3; FR-LEA-01/02).

Run with ``pytest backend/tests -k claim_transaction -q`` (WP test
command) — the unit layer exercises the six Section 9.3 steps, both
follow-up-read error paths, the FR-LEA-02 lease record and the atomic
Transition/Event writes sequentially on SQLite; the two-connection and
50-claimant contention proofs live on real Postgres in
``tests/integration/test_claim_race_postgres.py`` (Section 18: skip-
locked semantics are that layer's scope).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.leases.claim import claim_task
from apps.leases.exceptions import TaskAlreadyClaimed
from apps.projects.models import ProjectPolicy
from apps.tasks.exceptions import DependencyUnmet, TaskNotFound, TaskStateConflict
from apps.tasks.models import ClaimedRole, Task, TaskState, TaskTransition
from apps.tasks.services.dependencies import set_dependencies

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    install_event_recorder,
    make_pending_task,
    make_project,
    make_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def test_claim_writes_the_full_lease_record() -> None:
    """FR-LEA-02 verbatim: worker, session, role, start, expiry (+45)."""
    project = active_policy_project()
    task = make_pending_task(project, 1)

    before = timezone.now()
    claimed = claim(task, session_id="sess_claim_a", worker_agent_id="claude-code-98b2")
    after = timezone.now()

    assert claimed.state == TaskState.IN_PROGRESS
    assert claimed.worker_agent_id == "claude-code-98b2"
    assert claimed.worker_session_id == "sess_claim_a"
    assert claimed.claimed_role == ClaimedRole.CODER
    assert claimed.lease_acquired_at is not None and before <= claimed.lease_acquired_at <= after
    assert claimed.lease_expires_at == claimed.lease_acquired_at + timedelta(minutes=45)
    assert claimed.lease_generation == 1  # first claim: 0 -> 1 (Section 8.6)
    assert claimed.attempt_number == 1  # Section 8.2 T4 side effect
    assert claimed.version == 2  # dispatcher's single bump per dispatch


def test_claim_writes_transition_and_event_atomically() -> None:
    """One T4 row + one ``task.claimed`` hook inside the open transaction."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    events = install_event_recorder()

    claimed = claim(task)

    rows = list(TaskTransition.objects.filter(task=claimed))
    assert len(rows) == 1
    assert (rows[0].from_state, rows[0].to_state) == (
        TaskState.PENDING,
        TaskState.IN_PROGRESS,
    )
    assert rows[0].actor_type == "agent"
    assert rows[0].actor_ref == "sess_wp16_claimant"
    assert rows[0].reason_code == "claim"
    assert len(events) == 1, "exactly one event per transition (Section 20.4 item 6)"
    assert events[0]["type"] == "task.claimed"
    assert events[0]["_in_atomic_block"] is True  # written in the same transaction


def test_second_claimant_reports_task_already_claimed() -> None:
    """Contended claim: the loser answers TASK_ALREADY_CLAIMED (409)."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_winner")

    with pytest.raises(TaskAlreadyClaimed) as caught:
        claim(task, session_id="sess_loser")

    assert caught.value.status_code == 409
    winner = Task.objects.get(pk=task.pk)
    assert winner.worker_session_id == "sess_winner", "the winner's lease stands"
    assert winner.lease_generation == 1, "no second increment on a refused claim"


def test_unknown_task_reports_task_not_found() -> None:
    """Well-formed but absent id → TASK_NOT_FOUND (404), catalog only."""
    active_policy_project()
    with pytest.raises(TaskNotFound) as caught:
        claim_task(
            task_id="PID00001-T999",
            session_id="sess_x",
            worker_agent_id="label",
            caller_project_id="PID00001",
        )
    assert caught.value.status_code == 404


def test_malformed_task_id_is_validation_error() -> None:
    """Section 7.3 boundary: a malformed id never reaches the lock."""
    active_policy_project()
    with pytest.raises(ValidationError):
        claim_task(
            task_id="1",
            session_id="sess_x",
            worker_agent_id="label",
            caller_project_id="PID00001",
        )


def test_foreign_project_caller_reports_auth_forbidden_project() -> None:
    """ADR-004 / G-07: the token's project is the boundary (403)."""
    project = active_policy_project()
    other = make_project(pid="PID00002")
    task = make_pending_task(project, 1)

    with pytest.raises(AuthForbiddenProject) as caught:
        claim(task, caller_project_id=other.pk)

    assert caught.value.status_code == 403
    assert Task.objects.get(pk=task.pk).state == TaskState.PENDING, "no writes"


def test_claim_without_project_scope_fails_closed() -> None:
    """An agent token without a project offers nothing (fail closed)."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    with pytest.raises(AuthForbiddenProject):
        claim_task(
            task_id=task.pk,
            session_id="sess_x",
            worker_agent_id="label",
            caller_project_id=None,
        )


def test_non_pending_state_is_task_state_conflict() -> None:
    """Draft (and every other from-state) → TASK_STATE_CONFLICT (409)."""
    project = active_policy_project()
    task = make_task(project, 1, state=TaskState.DRAFT)
    events = install_event_recorder()

    with pytest.raises(TaskStateConflict) as caught:
        claim(task)

    assert caught.value.status_code == 409
    draft = Task.objects.get(pk=task.pk)
    assert draft.state == TaskState.DRAFT and draft.version == 1
    assert not TaskTransition.objects.filter(task=draft).exists()
    assert events == [], "a refused claim emits nothing"


def test_unmet_dependency_reports_dependency_unmet() -> None:
    """T4 guard (dependencies completed) → DEPENDENCY_UNMET (409)."""
    project = active_policy_project()
    blocker = make_task(project, 1, state=TaskState.PENDING)
    task = make_pending_task(project, 2)
    set_dependencies(task=task, dependency_ids=[blocker.pk])

    with pytest.raises(DependencyUnmet) as caught:
        claim(task)

    assert caught.value.status_code == 409
    assert Task.objects.get(pk=task.pk).state == TaskState.PENDING


def test_completed_dependency_allows_the_claim() -> None:
    """FR-TSK-07's other half: completed dependencies clear the guard."""
    project = active_policy_project()
    blocker = make_task(project, 1, state=TaskState.COMPLETED)
    task = make_pending_task(project, 2)
    set_dependencies(task=task, dependency_ids=[blocker.pk])

    assert claim(task).state == TaskState.IN_PROGRESS


def test_archived_task_is_refused() -> None:
    """T19 default visibility + MT-1.4-06's archived-write family (409)."""
    project = active_policy_project()
    task = make_pending_task(project, 1, archived_at=timezone.now())

    with pytest.raises(TaskStateConflict) as caught:
        claim(task)

    assert "archived" in str(caught.value)


def test_non_active_project_is_refused_at_the_guard() -> None:
    """T4's "Project active" guard (FR-PRJ-04) — separate from concurrency."""
    project = active_policy_project()
    type(project).objects.filter(pk=project.pk).update(active_status="paused")
    task = make_pending_task(project, 1)

    with pytest.raises(TaskStateConflict) as caught:
        claim(task)

    assert "paused" in str(caught.value)
    assert Task.objects.get(pk=task.pk).state == TaskState.PENDING


def test_policy_duration_drives_the_lease_expiry() -> None:
    """Section 7.2 lease_duration_minutes is read, never hardcoded."""
    project = active_policy_project(lease_duration_minutes=10)
    assert isinstance(project.agent_policy, ProjectPolicy)
    task = make_pending_task(project, 1)

    claimed = claim(task)

    acquired = claimed.lease_acquired_at
    assert acquired is not None
    assert claimed.lease_expires_at == acquired + timedelta(minutes=10)


def test_policy_default_is_forty_five_minutes() -> None:
    """Section 7.2 default honored when the policy row is untouched."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claimed = claim(task)
    acquired = claimed.lease_acquired_at
    assert acquired is not None
    assert claimed.lease_expires_at == acquired + timedelta(
        minutes=project.agent_policy.lease_duration_minutes
    )
    assert project.agent_policy.lease_duration_minutes == 45
