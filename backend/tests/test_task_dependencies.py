"""MT-1.4-05 — TaskDependency relation, write validation, readiness (FR-TSK-07).

The MT's test command, executed against the running API:

* edge creation validation — missing target, malformed id, cross-project
  target (GOAL-2/ADR-004 zero-bleed), self-edge, two- and three-node
  cycles — every refusal a catalog ``VALIDATION_ERROR`` that persists
  **nothing** (task row, id counter and edges all roll back together);
* the ``depends_on`` payload shape recorded for this MT: a list of task
  ids on POST and PATCH, **replace-the-set** on PATCH (omit = unchanged,
  ``[]`` = clear), read back on every task representation; duplicates
  collapse to one edge;
* FR-TSK-06 still holds across the new write: a stale ``version`` refuses
  the dependency change with ``VERSION_CONFLICT`` and the set is intact;
* readiness: :func:`all_dependencies_completed` — no dependencies (ready),
  mixed states (not ready), all ``completed`` (ready) — the predicate
  WP-1.6's work selection and T4 claim guard will call;
* migration hygiene: ``0002`` applies and reverses standalone
  (Section 20.3) without dropping the ``0001`` task table.

Cycle prevention is a *reading* of the plan (FR-TSK-07's offer rule is
unsatisfiable in a cycle) — recorded as such in the WP changelog, flagged
for owner confirmation.

Run with ``pytest backend/tests/test_task_dependencies.py`` (MT test
command).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskDependency, TaskState
from apps.tasks.services.dependencies import all_dependencies_completed

PASSWORD = "task-dependency-tests-1!"  # pragma: allowlist secret


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
        name="Task dependency tests",
        repo_path="/srv/repos/task-deps",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _task(project: Project, index: int, *, state: str = TaskState.DRAFT) -> Task:
    """One task row with a deterministic id (direct ORM for fixtures).

    Direct creates bypass the allocator, so the project's counter is
    advanced to the fixture's index — a later POST must allocate
    ``T{index+1}``, never collide with a fixture row (Section 7.3).
    """
    task = Task.objects.create(
        id=f"{project.pk}-T{index:03d}",
        project=project,
        title=f"Task {index:03d}",
        state=state,
    )
    Project.objects.filter(pk=project.pk, task_counter__lt=index).update(task_counter=index)
    return task


def _patch(owner_client: APIClient, task_id: str, payload: dict[str, Any]) -> Any:
    """PATCH one task as **JSON**; return the raw response.

    JSON is the wire format real clients use (web, bridge, mobile). The
    DRF test client's multipart default would *drop* an empty list field
    entirely, making ``depends_on: []`` indistinguishable from an omitted
    key — transport noise, not API behavior.
    """
    return owner_client.patch(f"/api/v1/tasks/{task_id}", payload, format="json")


def _edges_of(task_id: str) -> list[str]:
    """The stored edge set, ordered (what the DB actually holds)."""
    return list(
        TaskDependency.objects.filter(task_id=task_id)
        .order_by("depends_on_id")
        .values_list("depends_on_id", flat=True)
    )


# --- write-side validation (structure → VALIDATION_ERROR) -------------------


def test_create_with_dependencies_records_the_edges(
    owner_client: APIClient, project: Project
) -> None:
    """POST accepts `depends_on` and lands one row per target (Section 7.1)."""
    first = _task(project, 1)
    response = owner_client.post(
        "/api/v1/projects/PID00001/tasks",
        {"title": "Second", "depends_on": [first.pk]},
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    created = response.json()
    assert created["id"] == "PID00001-T002"
    assert created["depends_on"] == ["PID00001-T001"]

    assert _edges_of("PID00001-T002") == ["PID00001-T001"]
    assert TaskDependency.objects.count() == 1


def test_create_without_depends_on_starts_with_no_edges(
    owner_client: APIClient, project: Project
) -> None:
    """Omitted `depends_on` is an empty set, not a required field."""
    response = owner_client.post("/api/v1/projects/PID00001/tasks", {"title": "Standalone"})
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["depends_on"] == []
    assert TaskDependency.objects.count() == 0


def test_missing_target_persists_nothing(owner_client: APIClient, project: Project) -> None:
    """Well-formed but unknown id → 400; task, counter and edges roll back."""
    response = owner_client.post(
        "/api/v1/projects/PID00001/tasks",
        {"title": "Orphan", "depends_on": ["PID00001-T999"]},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = _envelope(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert "PID00001-T999" in str(error["details"])

    assert Task.objects.count() == 0, "the task row rolled back with the edge"
    project.refresh_from_db()
    assert project.task_counter == 0, "the id allocation refunded too (7.3)"
    assert TaskDependency.objects.count() == 0


def test_malformed_dependency_id_is_a_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """Section 7.3 boundary: non-ids never reach the lookup layer."""
    response = owner_client.post(
        "/api/v1/projects/PID00001/tasks",
        {"title": "Bad edge", "depends_on": ["not-a-task-id"]},
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    assert TaskDependency.objects.count() == 0


def test_cross_project_dependency_is_rejected_on_both_writes(
    owner_client: APIClient, project: Project
) -> None:
    """Zero-Bleed (ADR-004): a dependency never leaves its project."""
    other = Project.objects.create(
        id="PID00002",
        name="Other project",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    foreign = _task(other, 1)
    own = _task(project, 1)

    create = owner_client.post(
        "/api/v1/projects/PID00001/tasks",
        {"title": "Bleed attempt", "depends_on": [foreign.pk]},
    )
    assert create.status_code == status.HTTP_400_BAD_REQUEST
    error = _envelope(create)
    assert error["code"] == "VALIDATION_ERROR"
    assert "same project" in str(error["details"]) or "project" in str(error["details"])
    assert Task.objects.filter(project=project).count() == 1, (
        "only the fixture row exists — the refused POST created nothing"
    )

    patch = _patch(owner_client, own.pk, {"version": 1, "depends_on": [foreign.pk]})
    assert patch.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(patch)["code"] == "VALIDATION_ERROR"
    assert _edges_of(own.pk) == [], "nothing written"
    assert own.version == 1, "no version bump on a refusal"


def test_self_dependency_is_rejected(owner_client: APIClient, project: Project) -> None:
    """DB check + service rule: a task never waits on itself."""
    task = _task(project, 1)
    response = _patch(owner_client, task.pk, {"version": 1, "depends_on": [task.pk]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    assert _edges_of(task.pk) == []
    assert task.version == 1


def test_two_node_cycle_is_rejected(owner_client: APIClient, project: Project) -> None:
    """A ↔ B would deadlock both tasks — the second write is refused."""
    first = _task(project, 1)
    second = _task(project, 2)

    forward = _patch(owner_client, first.pk, {"version": 1, "depends_on": [second.pk]})
    assert forward.status_code == status.HTTP_200_OK, forward.content
    assert forward.json()["depends_on"] == ["PID00001-T002"]

    reverse = _patch(owner_client, second.pk, {"version": 1, "depends_on": [first.pk]})
    assert reverse.status_code == status.HTTP_400_BAD_REQUEST
    error = _envelope(reverse)
    assert error["code"] == "VALIDATION_ERROR"
    assert "cycle" in str(error["details"])

    assert _edges_of(second.pk) == [], "the closing edge was never written"
    assert _edges_of(first.pk) == ["PID00001-T002"], "the accepted edge survives"
    assert second.version == 1, "no bump on a refusal"


def test_three_node_cycle_is_rejected(owner_client: APIClient, project: Project) -> None:
    """The walk follows the full chain T003 → T002 → T001 (not just 2 hops)."""
    first = _task(project, 1)
    second = _task(project, 2)
    third = _task(project, 3)

    assert (
        _patch(owner_client, first.pk, {"version": 1, "depends_on": [second.pk]}).status_code == 200
    )
    assert (
        _patch(owner_client, second.pk, {"version": 1, "depends_on": [third.pk]}).status_code == 200
    )

    closing = _patch(owner_client, third.pk, {"version": 1, "depends_on": [first.pk]})
    assert closing.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(closing)["code"] == "VALIDATION_ERROR"
    assert _edges_of(third.pk) == []


def test_patch_replaces_the_dependency_set(owner_client: APIClient, project: Project) -> None:
    """`depends_on` is declarative: the payload *is* the set (MT choice)."""
    first = _task(project, 1)
    second = _task(project, 2)
    third = _task(project, 3)

    both = _patch(
        owner_client,
        first.pk,
        {"version": 1, "depends_on": [second.pk, third.pk]},
    )
    assert both.status_code == status.HTTP_200_OK, both.content
    assert both.json()["depends_on"] == ["PID00001-T002", "PID00001-T003"]
    assert both.json()["version"] == 2

    shrunk = _patch(owner_client, first.pk, {"version": 2, "depends_on": [third.pk]})
    assert shrunk.status_code == status.HTTP_200_OK
    assert shrunk.json()["depends_on"] == ["PID00001-T003"]
    assert shrunk.json()["version"] == 3
    assert _edges_of(first.pk) == ["PID00001-T003"], "the dropped edge is gone"

    cleared = _patch(owner_client, first.pk, {"version": 3, "depends_on": []})
    assert cleared.status_code == status.HTTP_200_OK
    assert cleared.json()["depends_on"] == []
    assert cleared.json()["version"] == 4
    assert _edges_of(first.pk) == []


def test_patch_without_depends_on_leaves_edges_alone(
    owner_client: APIClient, project: Project
) -> None:
    """Omission means *unchanged* — a title edit never touches the set."""
    first = _task(project, 1)
    second = _task(project, 2)
    assert (
        _patch(owner_client, first.pk, {"version": 1, "depends_on": [second.pk]}).status_code == 200
    )

    renamed = _patch(owner_client, first.pk, {"version": 2, "title": "Renamed"})
    assert renamed.status_code == status.HTTP_200_OK, renamed.content
    assert renamed.json()["depends_on"] == ["PID00001-T002"]
    assert renamed.json()["version"] == 3
    assert _edges_of(first.pk) == ["PID00001-T002"]


def test_duplicate_dependency_ids_collapse_to_one_edge(
    owner_client: APIClient, project: Project
) -> None:
    """`[b, b]` is one edge — uniqueness is data, not an IntegrityError."""
    target = _task(project, 1)
    response = owner_client.post(
        "/api/v1/projects/PID00001/tasks",
        {"title": "Twin", "depends_on": [target.pk, target.pk]},
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    assert response.json()["depends_on"] == ["PID00001-T001"]
    assert TaskDependency.objects.count() == 1


def test_stale_version_blocks_a_dependency_write(owner_client: APIClient, project: Project) -> None:
    """FR-TSK-06 crosses the new write: stale → 409, set untouched."""
    first = _task(project, 1)
    second = _task(project, 2)

    bump = _patch(owner_client, first.pk, {"version": 1, "title": "Renamed"})
    assert bump.status_code == status.HTTP_200_OK

    stale = _patch(owner_client, first.pk, {"version": 1, "depends_on": [second.pk]})
    assert stale.status_code == status.HTTP_409_CONFLICT
    assert _envelope(stale)["code"] == "VERSION_CONFLICT"
    assert _edges_of(first.pk) == [], "the stale write changed nothing"


def test_detail_and_list_expose_the_dependency_set(
    owner_client: APIClient, project: Project
) -> None:
    """Read side: the relation rides every task representation (§9.2 shape)."""
    first = _task(project, 1)
    second = _task(project, 2)
    assert (
        _patch(owner_client, second.pk, {"version": 1, "depends_on": [first.pk]}).status_code == 200
    )

    detail = owner_client.get(f"/api/v1/tasks/{second.pk}")
    assert detail.status_code == status.HTTP_200_OK
    assert detail.json()["depends_on"] == ["PID00001-T001"]

    listed = owner_client.get("/api/v1/projects/PID00001/tasks")
    assert listed.status_code == status.HTTP_200_OK
    by_id = {row["id"]: row["depends_on"] for row in listed.json()["results"]}
    assert by_id == {
        "PID00001-T001": [],
        "PID00001-T002": ["PID00001-T001"],
    }, "prefetched edges, one query per page (NFR-09)"


# --- readiness (FR-TSK-07; the WP-1.6 contract) -----------------------------


def test_readiness_no_dependencies_is_ready(project: Project) -> None:
    """Vacuous truth: nothing to wait on → ready to offer."""
    task = _task(project, 1)
    assert all_dependencies_completed(task) is True


def test_readiness_mixed_states_is_not_ready(project: Project) -> None:
    """One completed, one pending → not ready (FR-TSK-07 is all-or-nothing)."""
    blocker = _task(project, 1)
    other = _task(project, 2)
    waiter = _task(project, 3)
    TaskDependency.objects.create(task=waiter, depends_on=blocker)
    TaskDependency.objects.create(task=waiter, depends_on=other)

    Task.objects.filter(pk=blocker.pk).update(state=TaskState.COMPLETED)
    assert all_dependencies_completed(waiter) is False

    # Finishing the last blocker flips readiness — the predicate tracks state.
    Task.objects.filter(pk=other.pk).update(state=TaskState.COMPLETED)
    assert all_dependencies_completed(waiter) is True


def test_readiness_all_dependencies_completed_is_ready(project: Project) -> None:
    """Every edge points at `completed` (G-01 canonical) → ready."""
    first = _task(project, 1, state=TaskState.COMPLETED)
    second = _task(project, 2, state=TaskState.COMPLETED)
    waiter = _task(project, 3)
    TaskDependency.objects.create(task=waiter, depends_on=first)
    TaskDependency.objects.create(task=waiter, depends_on=second)

    assert all_dependencies_completed(waiter) is True

    # A non-canonical neighbour state (in_progress) is *not* completed.
    Task.objects.filter(pk=first.pk).update(state=TaskState.IN_PROGRESS)
    assert all_dependencies_completed(waiter) is False


# --- migration hygiene (Section 18; Section 20.3 standalone relation) -------


def _table_exists(model: type[Task] | type[TaskDependency]) -> bool:
    """Whether *model*'s table is present (vendor-neutral name lookup)."""
    table = model._meta.db_table
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                [table],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
                [table],
            )
        row = cursor.fetchone()
        assert row is not None
        return int(row[0]) == 1


@pytest.mark.django_db(transaction=True)
def test_dependency_migration_applies_and_reverses_cleanly() -> None:
    """``0002`` is standalone: reversing it drops only the relation table."""
    assert _table_exists(TaskDependency)
    assert _table_exists(Task)

    call_command("migrate", "tasks", "0001_initial", verbosity=0)
    assert not _table_exists(TaskDependency), "reverse must drop the relation table"
    assert _table_exists(Task), "0001 must keep the task table"

    call_command("migrate", "tasks", verbosity=0)
    assert _table_exists(TaskDependency), "re-apply must recreate the relation table"
