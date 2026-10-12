"""MT-1.4-06 — soft archive and read-only `completed` (FR-TSK-08; ADR-008).

The MT's test command, covering the acceptance criteria:

* **Recorded catalog choice:** *both* write refusals — `PATCH` on a
  `completed` row (Section 8.2 T17 side effect; Section 7.4 rule 3) and
  `PATCH` on an archived row — answer `TASK_STATE_CONFLICT` (409). The
  catalog has no `TASK_ARCHIVED`/`READ_ONLY` code and a 20th is
  forbidden (Section 20.4 item 5); `VALIDATION_ERROR` would blame a
  valid payload when the *resource* refuses. The payload's `version` is
  still checked first (stale clients get `VERSION_CONFLICT`, the check
  ordering pinned by a test);
* reads keep serving both kinds of row — by id and in lists (archived
  hidden by default, `include_archived=true` restores them — the flag
  MT-1.4-04 confirmed);
* **no DELETE exists** on task resources (Section 7.3 "deleting a task
  is not supported"): the view classes define no `delete`, and live
  DELETE attempts hit the recorded `MethodNotAllowed` →
  `VALIDATION_ERROR` (400) mapping with the row intact;
* `archive_task()` is the setter contract handed to WP-1.5's T19
  (MT-1.5-02): server-clock marker + version bump under the row lock,
  optional CAS, idempotent re-archive; state gating stays with the
  transition registry (the documented boundary).

Run with ``pytest backend/tests/test_task_archive.py`` (MT test
command).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.urls import resolve
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import CANONICAL_ERROR_CODES, TASK_STATE_CONFLICT, VERSION_CONFLICT
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.exceptions import TaskStateConflict, VersionConflict
from apps.tasks.models import Task, TaskDependency, TaskState
from apps.tasks.services.tasks import archive_task
from apps.tasks.views.tasks import TaskDetailView, TaskListCreateView

PASSWORD = "task-archive-tests-1!"  # pragma: allowlist secret


def _envelope(response: Any) -> dict[str, Any]:
    """Assert the five-field Section 9.2 envelope; return the error body."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    return cast(dict[str, Any], error)


@pytest.fixture(autouse=True)
def clear_replay_cache() -> Iterator[None]:
    """LocMem is process state — keep idempotency/throttle history isolated."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the Section 7.1 policy pair."""
    return Project.objects.create(
        id="PID00001",
        name="Task archive tests",
        repo_path="/srv/repos/task-archive",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _task(
    project: Project,
    index: int,
    *,
    state: str = TaskState.DRAFT,
    archived: bool = False,
    title: str | None = None,
) -> Task:
    """One task row with a deterministic id; counter kept allocator-honest."""
    task = Task.objects.create(
        id=f"{project.pk}-T{index:03d}",
        project=project,
        title=title or f"Task {index:03d}",
        state=state,
        archived_at=timezone.now() if archived else None,
    )
    Project.objects.filter(pk=project.pk, task_counter__lt=index).update(task_counter=index)
    return task


def _patch(owner_client: APIClient, task_id: str, payload: dict[str, Any]) -> Any:
    """PATCH one task as JSON (the real wire format)."""
    return owner_client.patch(f"/api/v1/tasks/{task_id}", payload, format="json")


# --- read-only completed (FR-TSK-08; Section 7.4 rule 3) -------------------


def test_patch_on_completed_task_is_refused(owner_client: APIClient, project: Project) -> None:
    """`completed` is read-only: 409 TASK_STATE_CONFLICT, nothing changes."""
    task = _task(project, 1, state=TaskState.COMPLETED, title="Original")

    response = _patch(owner_client, task.pk, {"version": 1, "title": "Renamed"})
    assert response.status_code == status.HTTP_409_CONFLICT, response.content
    assert _envelope(response)["code"] == "TASK_STATE_CONFLICT"

    task.refresh_from_db()
    assert task.title == "Original", "the refusal persisted nothing"
    assert task.version == 1, "no bump on a refusal"


def test_completed_task_stays_fully_readable(owner_client: APIClient, project: Project) -> None:
    """Read-only means *reads allowed*: by id and in the default list."""
    _task(project, 1, state=TaskState.COMPLETED, title="Finished work")

    detail = owner_client.get("/api/v1/tasks/PID00001-T001")
    assert detail.status_code == status.HTTP_200_OK
    body = detail.json()
    assert body["state"] == "completed"
    assert body["title"] == "Finished work"

    listed = owner_client.get("/api/v1/projects/PID00001/tasks")
    assert listed.status_code == status.HTTP_200_OK
    assert [row["id"] for row in listed.json()["results"]] == ["PID00001-T001"]


def test_stale_version_is_still_the_version_conflict(
    owner_client: APIClient, project: Project
) -> None:
    """Check ordering pinned: CAS runs before the lifecycle refusal."""
    task = _task(project, 1, state=TaskState.COMPLETED)

    response = _patch(owner_client, task.pk, {"version": 99, "title": "Renamed"})
    assert response.status_code == status.HTTP_409_CONFLICT
    assert _envelope(response)["code"] == "VERSION_CONFLICT"


# --- soft archive (Section 7.3; Section 8.2 T19 default) -------------------


def test_patch_on_archived_task_is_refused(owner_client: APIClient, project: Project) -> None:
    """Archived rows are historical records: same code, same cleanliness."""
    task = _task(project, 1, archived=True, title="History")

    response = _patch(owner_client, task.pk, {"version": 1, "title": "Rewritten"})
    assert response.status_code == status.HTTP_409_CONFLICT, response.content
    assert _envelope(response)["code"] == "TASK_STATE_CONFLICT"

    task.refresh_from_db()
    assert task.title == "History"
    assert task.version == 1
    assert task.archived_at is not None, "the marker was not cleared"


def test_archived_task_stays_readable_by_id(owner_client: APIClient, project: Project) -> None:
    """Id continuity (Section 7.3): the archived row still answers GET."""
    _task(project, 1, archived=True)

    detail = owner_client.get("/api/v1/tasks/PID00001-T001")
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["archived_at"] is not None


def test_list_default_excludes_archived_and_include_flag_restores(
    owner_client: APIClient, project: Project
) -> None:
    """T19 "hidden from boards by default"; completed rows stay visible."""
    _task(project, 1)  # plain draft — listed
    _task(project, 2, archived=True)  # archived — hidden by default
    _task(project, 3, state=TaskState.COMPLETED)  # completed — listed

    default = owner_client.get("/api/v1/projects/PID00001/tasks")
    assert default.status_code == status.HTTP_200_OK
    assert [row["id"] for row in default.json()["results"]] == [
        "PID00001-T001",
        "PID00001-T003",
    ]

    restored = owner_client.get("/api/v1/projects/PID00001/tasks", {"include_archived": "true"})
    assert restored.status_code == status.HTTP_200_OK
    assert [row["id"] for row in restored.json()["results"]] == [
        "PID00001-T001",
        "PID00001-T002",
        "PID00001-T003",
    ]


# --- no deletion (Section 7.3; Section 9.2 surface) ------------------------


def test_no_delete_handler_exists_on_task_views(project: Project) -> None:
    """Route table: neither task view defines DELETE (deletion unsupported)."""
    assert not hasattr(TaskListCreateView, "delete"), "list/create has no DELETE"
    assert not hasattr(TaskDetailView, "delete"), "detail has no DELETE"

    detail = resolve("/api/v1/tasks/PID00001-T001")
    listing = resolve("/api/v1/projects/PID00001/tasks")
    assert getattr(detail.func, "cls", None) is TaskDetailView
    assert getattr(listing.func, "cls", None) is TaskListCreateView


def test_live_delete_attempts_are_refused_and_nothing_is_removed(
    owner_client: APIClient, project: Project
) -> None:
    """405 → the recorded MethodNotAllowed mapping; the row survives."""
    task = _task(project, 1)

    detail_delete = owner_client.delete("/api/v1/tasks/PID00001-T001")
    assert detail_delete.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(detail_delete)["code"] == "VALIDATION_ERROR"

    list_delete = owner_client.delete("/api/v1/projects/PID00001/tasks")
    assert list_delete.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(list_delete)["code"] == "VALIDATION_ERROR"

    assert Task.objects.filter(pk=task.pk).exists(), "no hard delete happened"
    assert TaskDependency.objects.filter(task=task).count() == 0  # pre-state


# --- the archive setter contract for WP-1.5 (MT-1.5-02 / T19) --------------


def test_archive_task_sets_the_marker_and_bumps_version(project: Project) -> None:
    """Server-clock marker + version bump under the row lock, one txn."""
    task = _task(project, 1)

    archived = archive_task(task=task, expected_version=1)
    assert archived.archived_at is not None
    assert archived.version == 2, "the archive is a change (Section 7.2)"

    reloaded = Task.objects.get(pk=task.pk)
    assert reloaded.archived_at == archived.archived_at
    assert reloaded.version == 2


def test_archive_task_is_idempotent(project: Project) -> None:
    """First timestamp wins — a re-archive never re-stamps or double-bumps."""
    task = _task(project, 1)

    first = archive_task(task=task, expected_version=1)
    second = archive_task(task=first, expected_version=2)
    assert second.archived_at == first.archived_at, "the original marker stands"
    assert second.version == 2, "no second bump"

    reloaded = Task.objects.get(pk=task.pk)
    assert reloaded.version == 2
    assert reloaded.archived_at == first.archived_at


def test_archive_task_stale_version_is_a_version_conflict(project: Project) -> None:
    """The optional CAS behaves exactly like PATCH (FR-TSK-06)."""
    task = _task(project, 1)

    with pytest.raises(VersionConflict) as caught:
        archive_task(task=task, expected_version=99)
    assert caught.value.default_code == VERSION_CONFLICT
    assert caught.value.status_code == status.HTTP_409_CONFLICT
    task.refresh_from_db()
    assert task.archived_at is None, "the stale call archived nothing"


def test_state_conflict_is_a_catalog_code_with_409() -> None:
    """AC: refusals use only Section 9.2 codes — recorded mapping pinned."""
    assert TaskStateConflict.default_code == TASK_STATE_CONFLICT
    assert TaskStateConflict.status_code == status.HTTP_409_CONFLICT
    assert TaskStateConflict.default_code in CANONICAL_ERROR_CODES
