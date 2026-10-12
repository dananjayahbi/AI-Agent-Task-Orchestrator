"""MT-1.5-02 — owner transitions T2 (publish), T3 (unpublish), T19 (archive).

Run with ``pytest backend/tests -k owner_transitions -q``. Each row of
Section 8.2 with Actor **O** gets its happy path, its guard failures
(canonical catalog codes only — Section 20.4 item 5), and the FR-TSK-04
history assertions (actor, from/to, reason, timestamp on every row).

Recorded readings asserted here (see ``transitions_owner``'s module
docstring for the full rationale):

* T2 "dependencies exist" = exists **and completed** — an unmet
  dependency refuses with ``DEPENDENCY_UNMET`` (409), a completed one
  passes (the MT's own acceptance names that code);
* T2 "attachments ready (or override)" is vacuous until WP-1.11 — no
  attachment model exists, and publish must not fail because of that;
* T2 "required fields valid" = non-blank title → ``VALIDATION_ERROR``;
* T3 "no active lease" reads lease/worker *records* — even an expired
  but not-yet-swept claim refuses (the sweeper, T5, clears it);
* T19 is a flag: state never changes, ``archived_at`` is the marker,
  ``completed`` refuses, and re-archiving never re-stamps the marker.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError

from apps.core.errors import DEPENDENCY_UNMET, ROLE_NOT_PERMITTED, TASK_STATE_CONFLICT
from apps.projects.models import Project
from apps.tasks.exceptions import DependencyUnmet, TaskStateConflict, TransitionActorForbidden
from apps.tasks.models import Task, TaskState, TaskTransition
from apps.tasks.services.dependencies import set_dependencies
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp15_helpers import (
    install_event_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)


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
    """One project row for the owner-transition tests."""
    return make_project(name="Owner transitions")


def _dispatch(task: Task, trigger: str, **kwargs: Any) -> Task:
    """Dispatch *trigger* as the Owner (Section 8.2 actor O)."""
    payload: dict[str, Any] = {"actor_type": "owner", "actor_ref": "user:7"}
    payload.update(kwargs)
    return dispatch_transition(task_id=task.pk, trigger=trigger, **payload)


def _history(task: Task) -> list[TaskTransition]:
    return list(TaskTransition.objects.filter(task=task).order_by("timestamp", "id"))


# --- T2: publish (draft -> pending) ------------------------------------------


def test_publish_moves_draft_to_pending_with_history_and_event(project: Project) -> None:
    """T2 happy path: state, version, one history row, one event."""
    events = install_event_recorder()
    task = make_task(project, 1)

    result = _dispatch(task, "publish", note="ready for agents")

    assert result.state == TaskState.PENDING  # "Visible to agents" = the state itself
    assert result.version == 2
    row = _history(task)[0]
    assert (
        row.from_state,
        row.to_state,
        row.actor_type,
        row.actor_ref,
        row.reason_code,
        row.note,
    ) == ("draft", "pending", "owner", "user:7", "publish", "ready for agents")
    assert row.timestamp is not None, "FR-TSK-04: who, when, from, to, reason"
    assert [event["type"] for event in events] == ["task.transitioned"]


def test_publish_refuses_unmet_dependencies_with_dependency_unmet(project: Project) -> None:
    """T2's dependency guard surfaces the canonical DEPENDENCY_UNMET (409)."""
    events = install_event_recorder()
    blocker = make_task(project, 1, state=TaskState.PENDING)
    task = make_task(project, 2)
    set_dependencies(task=task, dependency_ids=[blocker.pk])

    with pytest.raises(DependencyUnmet) as caught:
        _dispatch(task, "publish")

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert caught.value.default_code == DEPENDENCY_UNMET
    assert task.pk in str(caught.value), "the refusal names the waiting task"
    task.refresh_from_db()
    assert task.state == TaskState.DRAFT and task.version == 1
    assert _history(task) == [] and events == []

    blocker.state = TaskState.COMPLETED
    blocker.version += 1
    blocker.save()

    published = _dispatch(task, "publish")
    assert published.state == TaskState.PENDING
    assert len(_history(task)) == 1, "the recorded reading: exists AND completed passes"


def test_publish_passes_vacuously_without_dependencies_or_attachments(project: Project) -> None:
    """No attachments exist until WP-1.11 — publish must not fail because of it."""
    task = make_task(project, 1)

    published = _dispatch(task, "publish")

    assert published.state == TaskState.PENDING


def test_publish_refuses_a_blank_title_with_validation_error(project: Project) -> None:
    """T2's required-fields guard: VALIDATION_ERROR is the catalog code."""
    from apps.core.exceptions import orchestrator_exception_handler  # local: envelope check

    task = make_task(project, 1, title="")

    with pytest.raises(ValidationError) as caught:
        _dispatch(task, "publish")

    # The envelope handler maps DRF ValidationError to VALIDATION_ERROR
    # (apps.core.exceptions._CODE_BY_EXCEPTION_TYPE) — asserted here so the
    # guard's wire code is pinned to the closed catalog, not just raised.
    response = orchestrator_exception_handler(
        caught.value, {"view": None, "args": (), "kwargs": {}}
    )
    assert response is not None
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    task.refresh_from_db()
    assert task.state == TaskState.DRAFT and task.version == 1


def test_publish_refuses_any_state_but_draft(project: Project) -> None:
    """Wrong from-state is the Section 8.2 rule-1 family: TASK_STATE_CONFLICT."""
    task = make_task(project, 1, state=TaskState.PENDING)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "publish")

    assert caught.value.status_code == status.HTTP_409_CONFLICT
    assert caught.value.default_code == TASK_STATE_CONFLICT


def test_publish_refuses_non_owner_actors(project: Project) -> None:
    """The Actor column: agents and system may not publish (Section 8.2)."""
    task = make_task(project, 1)

    for actor in ("agent", "system"):
        with pytest.raises(TransitionActorForbidden) as caught:
            _dispatch(task, "publish", actor_type=actor, actor_ref="sess_x")
        assert caught.value.default_code == ROLE_NOT_PERMITTED
        assert caught.value.status_code == status.HTTP_403_FORBIDDEN

    task.refresh_from_db()
    assert task.state == TaskState.DRAFT and task.version == 1


# --- T3: unpublish (pending -> draft) ----------------------------------------


def test_unpublish_moves_pending_back_to_draft(project: Project) -> None:
    """T3 happy path with the FR-TSK-04 history row."""
    task = make_task(project, 1, state=TaskState.PENDING)

    result = _dispatch(task, "unpublish")

    assert result.state == TaskState.DRAFT
    assert result.version == 2
    row = _history(task)[0]
    assert (row.from_state, row.to_state, row.reason_code) == ("pending", "draft", "unpublish")
    assert row.actor_type == "owner" and row.actor_ref == "user:7"


@pytest.mark.parametrize(
    ("worker", "lease_delta_minutes"),
    [
        ("claude-code-session-98b2", 45),  # live lease
        ("claude-code-session-98b2", -5),  # expired-but-unswept claim still records a worker
    ],
)
def test_unpublish_refuses_while_a_lease_record_exists(
    project: Project, worker: str, lease_delta_minutes: int
) -> None:
    """T3 guard "No active lease" reads records — the sweeper clears them, not unpublish."""
    task = make_task(project, 1, state=TaskState.PENDING)
    task.worker_agent_id = worker
    task.worker_session_id = "sess_7f3c91d0a2b44e"
    task.claimed_role = "coder"
    task.lease_acquired_at = timezone.now() - timedelta(minutes=60)
    task.lease_expires_at = timezone.now() + timedelta(minutes=lease_delta_minutes)
    task.save()

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "unpublish")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.state == TaskState.PENDING and task.version == 1
    assert _history(task) == []


def test_unpublish_refuses_any_state_but_pending(project: Project) -> None:
    """draft/ in_progress/ ... cannot fire T3 (table From column)."""
    task = make_task(project, 1, state=TaskState.DRAFT)

    with pytest.raises(TaskStateConflict):
        _dispatch(task, "unpublish")


# --- T19: archive (any non-completed -> archived flag) -----------------------


@pytest.mark.parametrize(
    "state",
    [
        TaskState.DRAFT,
        TaskState.PENDING,
        TaskState.IN_PROGRESS,
        TaskState.TO_BE_AUDITED,
        TaskState.IN_HUMAN_REVIEW,
    ],
)
def test_archive_sets_the_flag_from_any_non_completed_state(project: Project, state: str) -> None:
    """T19: no guards, state unchanged (flag, never a seventh state)."""
    events = install_event_recorder()
    task = make_task(project, 1, state=state)
    if state == TaskState.IN_PROGRESS:  # Section 8.3 rule 1: in_progress carries a worker
        task.worker_agent_id = "claude-code-session-98b2"
        task.claimed_role = "coder"
        task.lease_expires_at = timezone.now() + timedelta(minutes=45)
        task.save()

    result = _dispatch(task, "archive")

    assert result.state == state, "T19 moves nothing (Section 8.1)"
    assert result.archived_at is not None
    assert result.version == 2
    row = _history(task)[0]
    assert (row.from_state, row.to_state, row.reason_code) == (state, state, "archive")
    assert row.actor_type == "owner"
    assert [event["type"] for event in events] == ["task.transitioned"]


def test_archive_refuses_completed_tasks(project: Project) -> None:
    """T19's From column is *any non-completed* — completed refuses."""
    task = make_task(project, 1, state=TaskState.COMPLETED)

    with pytest.raises(TaskStateConflict) as caught:
        _dispatch(task, "archive")

    assert caught.value.default_code == TASK_STATE_CONFLICT
    task.refresh_from_db()
    assert task.archived_at is None and task.version == 1
    assert _history(task) == []


def test_rearchive_never_restamps_the_marker(project: Project) -> None:
    """First timestamp wins (MT-1.4-06 contract); each dispatch still records."""
    task = make_task(project, 1)
    first = _dispatch(task, "archive")
    marker = first.archived_at
    assert marker is not None

    second = _dispatch(task, "archive")

    assert second.archived_at == marker, "the marker is a first-archive timestamp"
    assert second.version == 3, "each dispatch is a change (history appended)"
    assert len(_history(task)) == 2
