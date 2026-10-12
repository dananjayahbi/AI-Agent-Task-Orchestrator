"""MT-1.8-04 — ``GET /tasks/{id}/checkpoints`` (Section 9.2 Progress row;
WP-0.5-04 cursor conventions; FR-WEB-04 / FR-MOB-03 consumers).

Run with ``pytest backend/tests -k checkpoint_listing -q``. The suite
proves the MT's acceptance criteria against the real route:

* first-page shape and order — newest first, the Section 7.2 fields the
  Section 13.2 feed renders (percent, message, token usage);
* cursor continuation reaches **every row exactly once**, including
  under concurrent inserts between pages (stable ``(timestamp, id)``
  ordering — pagination.md rule 2);
* the documented page-size defaults: 25 default, 100 maximum (values
  above clamp), per pagination.md;
* the authorization cells: owner session and project-scoped agent token
  pass; cross-project tokens answer ``AUTH_FORBIDDEN_PROJECT``;
  devices and anonymous callers are refused; unknown task
  ``TASK_NOT_FOUND``; malformed cursors ``VALIDATION_ERROR``;
* an empty task returns an empty page, not an error.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import CheckpointKind, Task, TaskCheckpoint
from apps.tasks.services.checkpoints import store_checkpoint

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    PASSWORD,
    active_policy_project,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db

CHECKPOINT_FIELDS = {
    "id",
    "task_id",
    "attempt_number",
    "session_id",
    "timestamp",
    "message",
    "percent",
    "token_usage",
    "kind",
}


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — fresh budget per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (the GET row's Owner caller)."""
    User.objects.create_user("owner-wp18-list", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner-wp18-list", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def project() -> Project:
    """One active project (PID00001)."""
    return active_policy_project()


@pytest.fixture
def task(project: Project) -> Task:
    """One pending task (no lease needed for the read row)."""
    return make_pending_task(project, 1)


def agent_client(owner_client: APIClient, project_id: str) -> APIClient:
    """A plain client carrying one project-scoped agent bearer token."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": ["coder"]}
    )
    assert response.status_code == 201, response.content
    payload: dict[str, Any] = response.json()
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {payload['token']}")
    return client


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


def seed_history(task: Task, count: int) -> list[TaskCheckpoint]:
    """*count* checkpoints with strictly increasing timestamps, oldest first."""
    base = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    rows: list[TaskCheckpoint] = []
    for index in range(count):
        row = TaskCheckpoint.objects.create(
            task=task,
            attempt_number=0,
            session_id="sess_list",
            message=f"step {index}",
            percent=index,
            kind=CheckpointKind.PROGRESS,
            timestamp=base.replace(minute=index % 60, second=index % 60, microsecond=index),
        )
        rows.append(row)
    return rows


# --- first page: shape and newest-first order -------------------------------


def test_first_page_is_newest_first_with_section_7_2_fields(
    owner_client: APIClient, task: Task
) -> None:
    """results carry the §7.2 fields; the newest row leads (Section 13.2)."""
    seeded = seed_history(task, 5)

    response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {"results", "next_cursor"}, "pagination.md envelope"
    results = body["results"]
    assert len(results) == 5
    for row in results:
        assert set(row) == CHECKPOINT_FIELDS, "the feed renders these and no more"
    timestamps = [row["timestamp"] for row in results]
    assert timestamps == sorted(timestamps, reverse=True), "newest first"
    assert results[0]["message"] == "step 4", "the last-seeded row leads"
    assert results[-1]["message"] == "step 0"
    assert results[0]["id"] == str(seeded[4].pk)
    assert body["next_cursor"] is None, "one page fits — end of list"


def test_empty_task_returns_an_empty_page(owner_client: APIClient, task: Task) -> None:
    """An empty history is a 200 empty page, never an error (acceptance)."""
    response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 200
    body = response.json()
    assert body == {"results": [], "next_cursor": None}


# --- cursor continuation: every row exactly once ----------------------------


def test_cursor_continuation_reaches_every_row_exactly_once(
    owner_client: APIClient, task: Task
) -> None:
    """Paging with page_size=2 walks all 5 rows without gaps or repeats."""
    seeded = seed_history(task, 5)
    url = f"/api/v1/tasks/{task.pk}/checkpoints"

    seen: list[str] = []
    cursor: str | None = None
    for _ in range(10):  # hard stop against a cursor loop
        query = f"{url}?page_size=2" + (f"&cursor={cursor}" if cursor else "")
        response = owner_client.get(query)
        assert response.status_code == 200, response.content
        body = response.json()
        seen.extend(row["id"] for row in body["results"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    else:  # pragma: no cover - the loop must terminate via next_cursor
        pytest.fail("pagination did not terminate")

    assert seen == [str(row.pk) for row in reversed(seeded)], "newest-first, each once"
    assert len(seen) == len(set(seen)), "no duplicates across pages"


def test_concurrent_inserts_never_shift_or_duplicate_paging(
    owner_client: APIClient, task: Task
) -> None:
    """Inserts *during* paging cannot disturb the older pages (rule 2).

    The cursor carries the full ``(timestamp, id)`` key, so a newer row
    inserted after page 1 simply never appears in the continuation — the
    rows the first page already promised are delivered exactly once.
    """
    seeded = seed_history(task, 4)
    url = f"/api/v1/tasks/{task.pk}/checkpoints"

    first = owner_client.get(f"{url}?page_size=2")
    page_one = first.json()
    assert [row["id"] for row in page_one["results"]] == [
        str(seeded[3].pk),
        str(seeded[2].pk),
    ]

    # A concurrent writer lands two *newer* checkpoints mid-paging.
    late = TaskCheckpoint.objects.create(
        task=task,
        attempt_number=0,
        session_id="sess_late",
        message="late arrival",
        percent=99,
    )

    continuation = owner_client.get(f"{url}?page_size=2&cursor={page_one['next_cursor']}")
    body = continuation.json()
    assert [row["id"] for row in body["results"]] == [
        str(seeded[1].pk),
        str(seeded[0].pk),
    ], "the promised rows arrive exactly once; the late row does not shift them"
    assert str(late.pk) not in {row["id"] for row in body["results"]}
    assert body["next_cursor"] is None


def test_identical_timestamps_page_through_the_id_tiebreak(
    owner_client: APIClient, task: Task
) -> None:
    """Timestamp ties cannot skip or repeat rows (pagination.md rule 2)."""
    shared = datetime(2026, 3, 2, 9, 30, 0, tzinfo=UTC)
    tied = [
        TaskCheckpoint.objects.create(
            task=task,
            attempt_number=0,
            session_id="sess_tie",
            message=f"tie {index}",
            timestamp=shared,
        )
        for index in range(3)
    ]

    url = f"/api/v1/tasks/{task.pk}/checkpoints"
    seen: list[str] = []
    cursor: str | None = None
    for _ in range(5):
        query = f"{url}?page_size=1" + (f"&cursor={cursor}" if cursor else "")
        body = owner_client.get(query).json()
        seen.extend(row["id"] for row in body["results"])
        cursor = body["next_cursor"]
        if cursor is None:
            break

    assert sorted(seen) == sorted(str(row.pk) for row in tied), "each tied row once"
    assert len(seen) == 3


# --- page-size conventions (pagination.md) ----------------------------------


def test_default_page_size_is_twenty_five(owner_client: APIClient, task: Task) -> None:
    """26 rows: the first page carries 25 and a next_cursor."""
    seed_history(task, 26)

    response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    body = response.json()
    assert len(body["results"]) == 25
    assert body["next_cursor"] is not None


def test_page_size_above_the_maximum_clamps_to_one_hundred(
    owner_client: APIClient, task: Task
) -> None:
    """page_size=500 is a hint — the server clamps at 100 (RISK-13 cap)."""
    seed_history(task, 101)

    response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints?page_size=500")

    body = response.json()
    assert len(body["results"]) == 100, "the documented maximum"
    assert body["next_cursor"] is not None, "one row remains"


def test_malformed_cursor_answers_validation_error(owner_client: APIClient, task: Task) -> None:
    """A mangled cursor is a client error from the closed catalog (rule 1)."""
    for bad in ("not-base64~", "aGVsbG8", "aGVsbG8=d29ybGQ"):
        response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints?cursor={bad}")
        assert response.status_code == 400
        assert _code(response) == "VALIDATION_ERROR"


# --- authorization (Section 9.2/12.2 caller cells) --------------------------


def test_project_scoped_agent_token_may_read(
    owner_client: APIClient, project: Project, task: Task
) -> None:
    """The Agent half of the Progress row's GET cell."""
    seed_history(task, 1)
    client = agent_client(owner_client, project.pk)

    response = client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 200, response.content
    assert len(response.json()["results"]) == 1


def test_cross_project_agent_token_answers_auth_forbidden_project(
    owner_client: APIClient, project: Project, task: Task
) -> None:
    """ADR-004 Zero-Bleed on the read row: PID00002 cannot read PID00001."""
    other = active_policy_project(pid="PID00002")
    client = agent_client(owner_client, other.pk)

    response = client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"


def test_device_token_is_refused(owner_client: APIClient, project: Project, task: Task) -> None:
    """Devices are not in the GET cell's caller column (Section 9.2)."""
    from apps.accounts.models import ApiToken, Device, TokenKind
    from apps.accounts.services.tokens import hash_token

    plaintext = "wp18-device-credential"  # pragma: allowlist secret
    user = User.objects.create_user("device-wp18", None, PASSWORD)
    token_row = ApiToken.objects.create(
        kind=TokenKind.DEVICE,
        user=user,
        hash=hash_token(plaintext),
        project_id=project.pk,
    )
    Device.objects.create(
        user=user, platform="android", push_token="wp18-device-push", token=token_row
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {plaintext}")

    response = client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 403
    assert _code(response) == "ROLE_NOT_PERMITTED"


def test_anonymous_caller_is_refused(owner_client: APIClient, task: Task) -> None:
    """No credential: AUTH_REQUIRED (401)."""
    anonymous = APIClient()

    response = anonymous.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    assert response.status_code == 401
    assert _code(response) == "AUTH_REQUIRED"


def test_unknown_task_answers_task_not_found(owner_client: APIClient, project: Project) -> None:
    """Well-formed but unknown id: TASK_NOT_FOUND (404)."""
    response = owner_client.get(f"/api/v1/tasks/{project.pk}-T777/checkpoints")

    assert response.status_code == 404
    assert _code(response) == "TASK_NOT_FOUND"


def test_malformed_task_id_answers_validation_error(owner_client: APIClient) -> None:
    """The Section 7.3 boundary validates before the lookup."""
    response = owner_client.get("/api/v1/tasks/not-an-id/checkpoints")

    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"


# --- the listing only reads (no writes on GET) ------------------------------


def test_listing_never_writes(owner_client: APIClient, task: Task) -> None:
    """A GET leaves the row untouched — reads carry no lease semantics."""
    seed_history(task, 2)
    from apps.tasks.models import Task as TaskModel

    version_before = TaskModel.objects.get(pk=task.pk).version

    owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints")
    owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints?page_size=1")

    assert TaskModel.objects.get(pk=task.pk).version == version_before
    assert TaskCheckpoint.objects.filter(task=task).count() == 2


def test_history_survives_a_swept_lease(owner_client: APIClient, task: Task) -> None:
    """Checkpoints are history (P8): a swept lease does not remove them."""
    claimed = store_checkpoint(task, session_id="sess_gone", message="before the sweep")
    # The lease dies and the sweeper clears the worker fields (T5 outcome).
    from apps.tasks.models import TaskState

    Task.objects.filter(pk=task.pk).update(
        state=TaskState.PENDING, worker_session_id=None, lease_expires_at=None
    )

    response = owner_client.get(f"/api/v1/tasks/{task.pk}/checkpoints")

    body = response.json()
    assert [row["id"] for row in body["results"]] == [str(claimed.pk)], (
        "the checkpoint outlives the lease it reported on"
    )
