"""MT-1.4-04 — list filters and priority/FIFO ordering (Sections 9.2, 7.2).

The MT's test command, executed against the running API:

* default order is FR-TSK-05 canonical — `urgent > high > medium > low`,
  then oldest `created_at` (FIFO), with same-timestamp ties broken by the
  task id's **generation order** (`T999` before `T1000` — pagination.md
  rule 2's explicit warning against raw lexicographic ids);
* `state` (repeatable) and `priority` filters return exactly the matching
  sets; unknown values answer `VALIDATION_ERROR`;
* archived tasks are excluded by default and restored by
  `include_archived=true` (the flag name this MT confirms — T19 default
  visibility, MT-1.4-06 owns the behavior);
* cursor pagination follows MT-0.5-04: envelope is exactly
  `{results, next_cursor}`, a full walk skips/duplicates nothing (alone
  and under filters), and a mangled cursor is a catalog error;
* results never cross the path project, and the Owner-only caller keeps
  agent tokens out (scope first, then role — MT-1.2-05);
* ordering/filtering run in the database (NFR-09: plan/explain evidence
  plus the declared composite indexes).

Run with ``pytest backend/tests/test_task_list.py`` (MT test command).
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task
from apps.tasks.services.tasks import (
    FR_TSK_05_ORDER,
    TaskCursorKey,
    filter_beyond_cursor,
    task_list_queryset,
)

PASSWORD = "task-list-tests-1!"  # pragma: allowlist secret
T_BASE = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)


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
        name="Task list tests",
        repo_path="/srv/repos/task-list",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _task(
    project: Project,
    index: int,
    *,
    priority: str = "medium",
    state: str = "draft",
    created_at: datetime | None = None,
    archived: bool = False,
    **extra: Any,
) -> Task:
    """One task row with a deterministic id and (optionally) created_at."""
    task = Task.objects.create(
        id=f"{project.pk}-T{index:03d}",
        project=project,
        title=f"Task {index:03d}",
        priority=priority,
        state=state,
        archived_at=created_at if archived else None,
        **extra,
    )
    if created_at is not None or archived:
        # queryset.update bypasses auto_now — exact FIFO timestamps for the
        # ordering tests (and archived_at rides along when set above).
        updates: dict[str, Any] = {}
        if created_at is not None:
            updates["created_at"] = created_at
        if archived:
            updates["archived_at"] = created_at or T_BASE
        Task.objects.filter(pk=task.pk).update(**updates)
        task.refresh_from_db()
    return task


def _list(owner_client: APIClient, pid: str = "PID00001", **params: Any) -> Any:
    """GET the list endpoint; return the parsed 200 body."""
    response = owner_client.get(f"/api/v1/projects/{pid}/tasks", params)
    assert response.status_code == status.HTTP_200_OK, response.content
    body = response.json()
    assert set(body) == {"results", "next_cursor"}, "pagination.md envelope"
    return cast(dict[str, Any], body)


def _ids(body: dict[str, Any]) -> list[str]:
    return [row["id"] for row in body["results"]]


def _issue_agent_token(owner_client: APIClient, project_id: str, role: str = "coder") -> str:
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": [role]}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


# --- canonical ordering (FR-TSK-05; Section 9.3 precedent) ------------------


def test_default_order_is_priority_then_fifo_then_id(
    owner_client: APIClient, project: Project
) -> None:
    """urgent > high > medium > low; FIFO inside a priority; id ties last."""
    _task(project, 1, priority="urgent", created_at=T_BASE - timedelta(minutes=5))
    _task(project, 2, priority="urgent", created_at=T_BASE)
    _task(project, 3, priority="high", created_at=T_BASE)
    _task(project, 4, priority="medium", created_at=T_BASE)
    _task(project, 5, priority="low", created_at=T_BASE)
    _task(project, 6, priority="urgent", created_at=T_BASE)

    body = _list(owner_client)
    # T001 wins on FIFO among urgent; T002 before T006 on the id tie-break
    # at identical timestamps; then high, medium, low.
    assert _ids(body) == [
        "PID00001-T001",
        "PID00001-T002",
        "PID00001-T006",
        "PID00001-T003",
        "PID00001-T004",
        "PID00001-T005",
    ]
    assert body["next_cursor"] is None, "single page — end of list signal"


def test_id_tie_break_follows_generation_order_past_three_digits(
    owner_client: APIClient, project: Project
) -> None:
    """pagination.md rule 2: T1000 must sort AFTER T999, never before."""
    _task(project, 999, priority="urgent", created_at=T_BASE)
    _task(project, 1000, priority="urgent", created_at=T_BASE)
    # Same priority, same timestamp — the id is the final stable key, and
    # raw lexicographic order would wrongly put "T1000" first.
    assert _ids(_list(owner_client)) == ["PID00001-T999", "PID00001-T1000"]


# --- filters (FR-TSK-05; Section 7.2 fields) --------------------------------


def test_state_filter_returns_exactly_the_matching_set(
    owner_client: APIClient, project: Project
) -> None:
    """Repeatable `state` param; two canonical states, nothing else."""
    _task(project, 1, state="draft")
    _task(project, 2, state="pending")
    _task(project, 3, state="in_progress")
    _task(project, 4, state="completed")

    both = _list(owner_client, state=["draft", "pending"])
    assert sorted(_ids(both)) == ["PID00001-T001", "PID00001-T002"]

    single = _list(owner_client, state=["in_progress"])
    assert _ids(single) == ["PID00001-T003"]


def test_priority_filter_returns_exactly_the_matching_set(
    owner_client: APIClient, project: Project
) -> None:
    """Single-valued FR-TSK-05 filter."""
    _task(project, 1, priority="urgent")
    _task(project, 2, priority="high")
    _task(project, 3, priority="urgent")

    urgent = _list(owner_client, priority="urgent")
    assert _ids(urgent) == ["PID00001-T001", "PID00001-T003"]  # already in order


@pytest.mark.parametrize("bad_value", ["bogus", "PENDING", "urgent,high"])
def test_unknown_filter_values_are_validation_errors(
    owner_client: APIClient, project: Project, bad_value: str
) -> None:
    """Catalog-only answers for malformed filter input (item 5)."""
    _task(project, 1)
    response = owner_client.get("/api/v1/projects/PID00001/tasks", {"state": [bad_value]})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"


def test_archived_tasks_are_hidden_by_default_and_restored_by_the_flag(
    owner_client: APIClient, project: Project
) -> None:
    """T19 default visibility: archived off the board, `include_archived` back."""
    _task(project, 1)
    _task(project, 2, archived=True, created_at=T_BASE)

    default = _list(owner_client)
    assert _ids(default) == ["PID00001-T001"]

    with_archived = _list(owner_client, include_archived="true")
    assert sorted(_ids(with_archived)) == ["PID00001-T001", "PID00001-T002"]


# --- cursor pagination (MT-0.5-04; pagination.md) ---------------------------


def test_cursor_walk_skips_and_duplicates_nothing(
    owner_client: APIClient, project: Project
) -> None:
    """A full page_size=2 walk visits every row exactly once, then ends."""
    for index in (1, 2, 3, 4, 5):
        _task(
            project,
            index,
            priority=("urgent", "high", "medium", "low", "urgent")[index - 1],
            created_at=T_BASE,
        )

    seen: list[str] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {"page_size": 2}
        if cursor is not None:
            params["cursor"] = cursor
        body = _list(owner_client, **params)
        seen.extend(_ids(body))
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
        assert pages < 10, "cursor never reached the end of the list"

    assert pages == 3, "5 rows at page_size 2 = 2 + 2 + 1"
    assert len(seen) == len(set(seen)) == 5, "no duplicates, no skips"
    assert set(seen) == {f"PID00001-T{i:03d}" for i in range(1, 6)}


def test_cursor_walk_resumes_consistently_under_a_filter(
    owner_client: APIClient, project: Project
) -> None:
    """pagination.md rule 1 in action: cursor + the filter it was issued with."""
    _task(project, 1, state="draft")
    _task(project, 2, state="pending")
    _task(project, 3, state="draft")
    _task(project, 4, state="pending")
    _task(project, 5, state="draft")

    seen: list[str] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": 2, "state": ["draft"]}
        if cursor is not None:
            params["cursor"] = cursor
        body = _list(owner_client, **params)
        seen.extend(_ids(body))
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == ["PID00001-T001", "PID00001-T003", "PID00001-T005"]


@pytest.mark.parametrize(
    "cursor",
    [
        "%%%not-base64%%%",
        "Z3JhY2U",  # valid base64, but the payload is not a cursor
        base64.urlsafe_b64encode(b"2|nonsense|101|PID00001-T001")
        .decode("ascii")
        .rstrip("="),  # four parts, unparseable timestamp
    ],
)
def test_mangled_cursors_are_validation_errors(
    owner_client: APIClient, project: Project, cursor: str
) -> None:
    """Cursors are opaque: a broken one is a client error, not a 500."""
    _task(project, 1)
    response = owner_client.get("/api/v1/projects/PID00001/tasks", {"cursor": cursor})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"


def test_page_size_above_the_maximum_is_clamped(owner_client: APIClient, project: Project) -> None:
    """pagination.md documented default: values over 100 clamp, never burst."""
    Task.objects.bulk_create(
        Task(
            id=f"PID00001-T{index:03d}",
            project=project,
            title=f"Bulk {index}",
        )
        for index in range(1, 102)
    )
    body = _list(owner_client, page_size=500)
    assert len(body["results"]) == 100, "the documented RISK-13 cap"
    assert body["next_cursor"] is not None, "more rows remain"


# --- isolation and authorization (Section 12.2; MT-1.2-05) ------------------


def test_results_never_cross_project_boundaries(owner_client: APIClient, project: Project) -> None:
    """Path-project scope: another project's tasks never appear."""
    Project.objects.create(
        id="PID00002",
        name="Other project",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    _task(project, 1)
    other = Project.objects.get(pk="PID00002")
    Task.objects.create(id="PID00002-T001", project=other, title="Other task")

    assert _ids(_list(owner_client)) == ["PID00001-T001"]
    assert _ids(_list(owner_client, pid="PID00002")) == ["PID00002-T001"]


def test_list_is_owner_only_with_scope_first(owner_client: APIClient, project: Project) -> None:
    """Agent tokens: own project → role denial, foreign → scope denial."""
    Project.objects.create(
        id="PID00002",
        name="Other project",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    token = _issue_agent_token(owner_client, "PID00001")
    headers = {"Authorization": f"Bearer {token}"}
    api = APIClient()

    own = api.get("/api/v1/projects/PID00001/tasks", headers=headers)
    assert own.status_code == 403
    assert _envelope(own)["code"] == "ROLE_NOT_PERMITTED"

    foreign = api.get("/api/v1/projects/PID00002/tasks", headers=headers)
    assert foreign.status_code == 403
    assert _envelope(foreign)["code"] == "AUTH_FORBIDDEN_PROJECT"

    anonymous = APIClient().get("/api/v1/projects/PID00001/tasks")
    assert anonymous.status_code == 401
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"


def test_malformed_or_unknown_project_answers_validation_error(owner_client: APIClient) -> None:
    """Boundary validation for the list route's {pid} (Section 7.3)."""
    for pid in ("PID1", "PID00042"):
        response = owner_client.get(f"/api/v1/projects/{pid}/tasks")
        assert response.status_code == status.HTTP_400_BAD_REQUEST, pid
        assert _envelope(response)["code"] == "VALIDATION_ERROR"


# --- NFR-09: the database does the work ------------------------------------


def test_ordering_and_filtering_happen_in_the_database(project: Project) -> None:
    """Queryset-level sort + the declared composite indexes (10k-task intent)."""
    queryset = task_list_queryset(project, states=["draft", "pending"], priority="high")

    # FR-TSK-05 canonical *priority* order — urgent > high > medium > low
    # (the state catalog is a separate §8.4 list); alphabetical enum order
    # would be wrong, and the sort key below must not inherit it.
    assert FR_TSK_05_ORDER == ("urgent", "high", "medium", "low")
    assert FR_TSK_05_ORDER != tuple(sorted(FR_TSK_05_ORDER)), "not alphabetical"

    # The sort lives in the SQL: order_by carries the four canonical keys
    # (the priority-rank annotation first — alphabetical enum order would
    # be wrong), and the compiled statement holds the actual expressions.
    order = tuple(str(entry) for entry in queryset.query.order_by)
    assert order == ("priority_rank", "created_at", "id_length", "id"), order

    sql, _parameters = queryset.query.sql_with_params()
    assert "CASE" in sql.upper(), sql  # priority rank expression, not enum alpha
    assert "LENGTH" in sql.upper(), sql  # id generation order (pagination rule 2)

    # Index backing: the model declares (project, priority, created_at) and
    # (project, state); the planner uses an index for the project-scoped
    # equality that dominates the query (plan/explain evidence for NFR-09).
    index_names = {index.name for index in Task._meta.indexes}
    assert {"task_proj_prio_created", "task_proj_state"} <= index_names

    plan = queryset.explain()
    assert "INDEX" in plan.upper(), plan  # SQLite: SEARCH ... USING INDEX ...


def test_cursor_filtering_keeps_the_canonical_order(project: Project) -> None:
    """filter_beyond_cursor narrows rows without disturbing the sort."""
    queryset = task_list_queryset(project)
    narrowed = filter_beyond_cursor(
        queryset,
        TaskCursorKey(
            rank=1,
            created_at=T_BASE,
            id_length=len("PID00001-T001"),
            task_id="PID00001-T001",
        ),
    )
    base_order = [str(entry) for entry in queryset.query.order_by]
    narrow_order = [str(entry) for entry in narrowed.query.order_by]
    assert narrow_order == base_order, "same four canonical keys after narrowing"
