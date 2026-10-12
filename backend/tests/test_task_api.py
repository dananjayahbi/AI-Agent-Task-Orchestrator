"""MT-1.4-03 — task CRUD endpoints (Sections 9.2, 7.2, 7.3, 8.2, 12.2/12.3).

The MT's test command, executed against the running API with real
credentials:

* create returns an allocated ``{PID}-T{index}`` id in ``draft`` with
  ``version`` 1 (T1's model-level step; FR-TSK-01/02/06) and copies the
  policy's ``audit_required``;
* read round-trips the FR-TSK-02 field set; malformed and unknown ids
  answer catalog codes (``VALIDATION_ERROR`` / ``TASK_NOT_FOUND``);
* matching-version PATCH increments ``version``; a stale-version PATCH
  returns ``VERSION_CONFLICT`` in the five-field envelope — the
  **WP-1.4 acceptance**;
* the writable-field allowlist holds: ``state``/``version``-as-data/
  lease/merge fields are rejected as unknown, so PATCH cannot bypass
  WP-1.5's state machine (MT risk note);
* ``target_scope`` globs are validated on creation (Section 12.3);
* ``Idempotency-Key`` replays a retried create without a second row
  (ADR-012; headers.md);
* non-Owner callers answer ``ROLE_NOT_PERMITTED``/``AUTH_REQUIRED``, and
  an agent token aimed at another project answers
  ``AUTH_FORBIDDEN_PROJECT`` on the **real** task routes (ADR-004).

Run with ``pytest backend/tests/test_task_api.py`` (MT test command).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.errors import CANONICAL_ERROR_CODES
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task

TASK_ID_RE = re.compile(r"^PID00001-T[0-9]{3,}$")
PASSWORD = "task-api-tests-1!"  # pragma: allowlist secret

VALID_CREATE = {
    "title": "Wire the orchestrator bridge",
    "description": "# Bridge\n\nRun `pytest` after wiring.",
    "acceptance_criteria": ["bridge starts", "tools register"],
    "target_scope": ["bridge/**", "docs/*.md"],
    "test_command": "pytest bridge",
    "priority": "high",
}


def _envelope(response: Any) -> dict[str, Any]:
    """Assert the five-field Section 9.2 envelope; return the error body."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    assert error["correlation_id"], "the envelope carries this exchange's id"
    return cast(dict[str, Any], error)


@pytest.fixture(autouse=True)
def clear_replay_cache() -> Iterator[None]:
    """The idempotency store is LocMem process state — never leak it across tests."""
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
def client(db: None) -> APIClient:
    """An unauthenticated client (the `anonymous` caller)."""
    return APIClient()


@pytest.fixture
def project(db: None) -> Project:
    """One project row with the Section 7.1 policy pair (direct, explicit id)."""
    return Project.objects.create(
        id="PID00001",
        name="Task API tests",
        repo_path="/srv/repos/task-api",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _create(owner_client: APIClient, pid: str = "PID00001", **overrides: Any) -> Any:
    """POST a valid task; return the parsed 201 body."""
    response = owner_client.post(f"/api/v1/projects/{pid}/tasks", {**VALID_CREATE, **overrides})
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return response.json()


def _issue_agent_token(owner_client: APIClient, project_id: str, role: str = "coder") -> str:
    """Mint an agent bearer token scoped to *project_id* (plaintext back)."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": [role]}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


def _register_device(owner_client: APIClient) -> str:
    """Mint a device bearer token (plaintext back)."""
    response = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-task-api"}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


# --- create (Section 8.2 T1; FR-TSK-01/02) ---------------------------------


def test_create_returns_an_allocated_draft_task_with_version_one(
    owner_client: APIClient, project: Project
) -> None:
    """T1's model-level step: allocated id, ``draft``, ``version`` 1."""
    body = _create(owner_client)

    assert TASK_ID_RE.match(body["id"]), body["id"]
    assert body["state"] == "draft"
    assert body["version"] == 1
    assert body["project_id"] == "PID00001"
    assert body["priority"] == "high"
    assert body["merge_status"] == "none"
    assert body["archived_at"] is None
    assert body["created_at"] and body["updated_at"]

    owner = User.objects.get(username="owner")
    assert body["created_by"] == str(owner.pk), "actor ref recorded (Section 7.2)"

    project.refresh_from_db()
    assert project.task_counter == 1, "the Section 7.3 counter advanced once"


def test_create_copies_the_policy_audit_required_default(
    owner_client: APIClient, project: Project
) -> None:
    """Section 7.2: audit_required defaults from the project policy."""
    assert project.agent_policy.audit_required_default is True  # Section 7.2 default
    assert _create(owner_client)["audit_required"] is True

    project.agent_policy.audit_required_default = False
    project.agent_policy.save()
    assert _create(owner_client, title="No audit")["audit_required"] is False


def test_create_round_trips_the_fr_tsk_02_fields(owner_client: APIClient, project: Project) -> None:
    """Read back exactly what FR-TSK-02 lets a client set."""
    created = _create(owner_client)
    fetched = owner_client.get(f"/api/v1/tasks/{created['id']}")
    assert fetched.status_code == 200, fetched.content

    body = fetched.json()
    for field in (
        "title",
        "description",
        "acceptance_criteria",
        "target_scope",
        "test_command",
        "priority",
    ):
        assert body[field] == VALID_CREATE[field], field


@pytest.mark.parametrize(
    "server_owned",
    [
        {"state": "completed"},
        {"version": 2},
        {"id": "PID00001-T999"},
        {"project_id": "PID00002"},
        {"lease_expires_at": "2030-01-01T00:00:00Z"},
        {"merge_status": "merged"},
        {"archived_at": "2030-01-01T00:00:00Z"},
        {"unknown_field": True},
    ],
)
def test_create_rejects_server_owned_or_unknown_fields(
    owner_client: APIClient, project: Project, server_owned: dict[str, Any]
) -> None:
    """The strict allowlist: server-owned keys are errors, never honored."""
    response = owner_client.post(
        "/api/v1/projects/PID00001/tasks", {**VALID_CREATE, **server_owned}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    key = next(iter(server_owned))
    assert key in response.json()["error"]["details"]
    assert Task.objects.count() == 0, "the rejected request created nothing"


def test_create_requires_title(owner_client: APIClient, project: Project) -> None:
    """Missing FR-TSK-02 title is a catalog validation error, not a 500."""
    response = owner_client.post("/api/v1/projects/PID00001/tasks", {})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = _envelope(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert "title" in error["details"]


def test_create_rejects_target_scope_globs_that_escape_the_repo(
    owner_client: APIClient, project: Project
) -> None:
    """Section 12.3: traversal / absolute / backslash globs never persist."""
    for bad_glob in ("../etc/*", "/abs/path/*", "C:\\repos\\*", "src\\*"):
        response = owner_client.post(
            "/api/v1/projects/PID00001/tasks",
            {**VALID_CREATE, "target_scope": [bad_glob]},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST, bad_glob
        error = _envelope(response)
        assert error["code"] == "VALIDATION_ERROR"
        assert "target_scope" in error["details"], bad_glob

    assert Task.objects.count() == 0

    good = _create(owner_client, target_scope=["src/**", "docs/*.md"])
    assert good["target_scope"] == ["src/**", "docs/*.md"]


def test_create_on_an_unknown_or_malformed_project_answers_catalog_codes(
    owner_client: APIClient, client: APIClient
) -> None:
    """Boundary rules for ``{pid}`` on the task route (Section 7.3)."""
    unknown = owner_client.post("/api/v1/projects/PID00042/tasks", VALID_CREATE)
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"  # no PROJECT_NOT_FOUND

    malformed = owner_client.post("/api/v1/projects/PID1/tasks", VALID_CREATE)
    assert malformed.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(malformed)["code"] == "VALIDATION_ERROR"


# --- read (Section 9.2 GET /tasks/{id}) -------------------------------------


def test_read_resolves_a_task_by_canonical_id(owner_client: APIClient, project: Project) -> None:
    """GET returns the row; every Section 7.2 field is present."""
    created = _create(owner_client)
    response = owner_client.get(f"/api/v1/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_read_malformed_task_id_answers_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """Section 7.3: every boundary validates — short ids never reach the DB."""
    response = owner_client.get("/api/v1/tasks/1")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"


def test_read_unknown_task_answers_task_not_found(
    owner_client: APIClient, project: Project
) -> None:
    """Well-formed but absent id → TASK_NOT_FOUND (404), catalog only."""
    response = owner_client.get("/api/v1/tasks/PID00001-T999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    error = _envelope(response)
    assert error["code"] == "TASK_NOT_FOUND"
    assert error["retryable"] is False


# --- update + optimistic concurrency (FR-TSK-06; WP-1.4 acceptance) --------


def test_matching_version_patch_applies_and_increments_version(
    owner_client: APIClient, project: Project
) -> None:
    """The happy path of FR-TSK-06: one change, one increment."""
    created = _create(owner_client)
    assert created["version"] == 1

    response = owner_client.patch(
        f"/api/v1/tasks/{created['id']}",
        {"version": 1, "title": "Renamed", "priority": "urgent"},
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["version"] == 2, "incremented on every change (Section 7.2)"
    assert body["title"] == "Renamed"
    assert body["priority"] == "urgent"

    # ...and a second round-trip continues the sequence.
    again = owner_client.patch(
        f"/api/v1/tasks/{created['id']}", {"version": 2, "description": "now with docs"}
    )
    assert again.status_code == 200
    assert again.json()["version"] == 3
    assert again.json()["title"] == "Renamed", "partial update left siblings alone"


def test_stale_version_patch_returns_version_conflict(
    owner_client: APIClient, project: Project
) -> None:
    """**WP-1.4 acceptance**: stale version → VERSION_CONFLICT, no overwrite."""
    created = _create(owner_client)
    task_url = f"/api/v1/tasks/{created['id']}"

    first = owner_client.patch(task_url, {"version": 1, "title": "Writer one"})
    assert first.status_code == 200

    stale = owner_client.patch(task_url, {"version": 1, "title": "Writer two"})
    assert stale.status_code == status.HTTP_409_CONFLICT
    error = _envelope(stale)
    assert error["code"] == "VERSION_CONFLICT"
    assert error["retryable"] is False, "a stale write cannot succeed on retry"

    current = owner_client.get(task_url).json()
    assert current["title"] == "Writer one", "the stale writer changed nothing"
    assert current["version"] == 2


def test_patch_without_the_version_field_is_a_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """FR-TSK-06 makes the CAS token mandatory — silently latest-wins is banned."""
    created = _create(owner_client)
    response = owner_client.patch(f"/api/v1/tasks/{created['id']}", {"title": "No version sent"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    error = _envelope(response)
    assert error["code"] == "VALIDATION_ERROR"
    assert "version" in error["details"]


@pytest.mark.parametrize(
    "server_owned",
    [
        {"state": "completed"},
        {"worker_agent_id": "claude-code"},
        {"lease_expires_at": "2030-01-01T00:00:00Z"},
        {"merge_status": "merged"},
        {"archived_at": "2030-01-01T00:00:00Z"},
        {"attempt_number": 9},
        {"created_by": "someone"},
    ],
)
def test_patch_enforces_the_writable_field_allowlist(
    owner_client: APIClient, project: Project, server_owned: dict[str, Any]
) -> None:
    """MT risk note: PATCH is not a state-changing backdoor (tested)."""
    created = _create(owner_client)
    response = owner_client.patch(f"/api/v1/tasks/{created['id']}", {"version": 1, **server_owned})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    key = next(iter(server_owned))
    assert key in _envelope(response)["details"]

    row = Task.objects.get(pk=created["id"])
    assert row.version == 1, "the rejected PATCH changed nothing"
    assert row.state == "draft"


# --- idempotency (Section 9.2 rule; ADR-012; headers.md) -------------------


def test_create_replays_with_the_same_idempotency_key(
    owner_client: APIClient, project: Project
) -> None:
    """Retry with one key → one task, the original outcome replayed."""
    headers = {"Idempotency-Key": "create-bridge-task-1"}
    url = "/api/v1/projects/PID00001/tasks"

    first = owner_client.post(url, VALID_CREATE, headers=headers)
    assert first.status_code == status.HTTP_201_CREATED

    retry = owner_client.post(url, VALID_CREATE, headers=headers)
    assert retry.status_code == status.HTTP_201_CREATED
    assert retry.json() == first.json(), "the original outcome is replayed verbatim"

    assert Task.objects.count() == 1, "the retry did not duplicate the task"


def test_create_without_an_idempotency_key_creates_normally(
    owner_client: APIClient, project: Project
) -> None:
    """The header is optional: two identical posts are two tasks by default."""
    url = "/api/v1/projects/PID00001/tasks"
    assert owner_client.post(url, VALID_CREATE).status_code == 201
    assert owner_client.post(url, VALID_CREATE).status_code == 201

    assert Task.objects.count() == 2


def test_same_key_with_a_different_request_is_not_replayed(
    owner_client: APIClient, project: Project
) -> None:
    """Recorded reading of the headers.md open point: mismatch executes.

    headers.md marks key-reuse-with-a-different-request an open point and
    invents no behavior; this store simply declines to replay (the
    fingerprints differ) and runs the new request normally.
    """
    headers = {"Idempotency-Key": "reused-key"}
    url = "/api/v1/projects/PID00001/tasks"

    first = owner_client.post(url, VALID_CREATE, headers=headers)
    assert first.status_code == 201

    other = owner_client.post(url, {**VALID_CREATE, "title": "Different"}, headers=headers)
    assert other.status_code == 201
    assert other.json()["id"] != first.json()["id"], "no replay happened"

    assert Task.objects.count() == 2


def test_patch_replays_with_the_same_idempotency_key(
    owner_client: APIClient, project: Project
) -> None:
    """A retried PATCH replays the original body — ``version`` does not drift."""
    created = _create(owner_client)
    url = f"/api/v1/tasks/{created['id']}"
    headers = {"Idempotency-Key": "patch-bridge-1"}
    payload = {"version": 1, "title": "Replayed"}

    first = owner_client.patch(url, payload, headers=headers)
    assert first.status_code == 200
    assert first.json()["version"] == 2

    retry = owner_client.patch(url, payload, headers=headers)
    assert retry.status_code == 200
    assert retry.json() == first.json(), "replayed, not re-executed"

    current = owner_client.get(url).json()
    assert current["version"] == 2, "the replay did not bump the version again"


# --- authorization (Section 12.2 cells on the real routes; ADR-004) --------


def test_anonymous_callers_get_auth_required(client: APIClient, project: Project) -> None:
    """No credential → AUTH_REQUIRED (401) on both task routes."""
    for method, url in (
        ("post", "/api/v1/projects/PID00001/tasks"),
        ("get", "/api/v1/tasks/PID00001-T001"),
        ("patch", "/api/v1/tasks/PID00001-T001"),
    ):
        response = getattr(client, method)(url, {}, format="json")
        assert response.status_code == 401, url
        assert _envelope(response)["code"] == "AUTH_REQUIRED"


@pytest.mark.parametrize("role", ["coder", "decomposer", "merge_executor"])
def test_agent_tokens_are_refused_creates_but_read_detail(
    owner_client: APIClient, project: Project, role: str
) -> None:
    """Owner-only create; §9.2/§10.5's agent read cell on the detail GET.

    The Decomposer/Device cells of Section 12.2's "Create draft tasks"
    row are deferred to WP-2.x/M5 (MT-1.4-03 risk note) — recorded
    explicitly in the authorization-matrix suite, asserted here on the
    real route. The detail read is the activated WP-2.x read cell: a
    token scoped to the task's project reads the row (the bridge's
    `get_task_details`), while the write half stays Owner-only.
    """
    Task.objects.create(id="PID00001-T001", project=project, title="Detail read")
    token = _issue_agent_token(owner_client, "PID00001", role=role)
    headers = {"Authorization": f"Bearer {token}"}

    create = APIClient().post("/api/v1/projects/PID00001/tasks", VALID_CREATE, headers=headers)
    assert create.status_code == 403
    assert _envelope(create)["code"] == "ROLE_NOT_PERMITTED"

    detail = APIClient().get("/api/v1/tasks/PID00001-T001", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == "PID00001-T001"

    patched = APIClient().patch(
        "/api/v1/tasks/PID00001-T001",
        {"title": "Nope", "version": 1},
        headers=headers,
        format="json",
    )
    assert patched.status_code == 403
    assert _envelope(patched)["code"] == "ROLE_NOT_PERMITTED"


def test_device_tokens_get_role_not_permitted(owner_client: APIClient, project: Project) -> None:
    """The Device cell of "Create draft tasks" is deferred with Decomposer."""
    token = _register_device(owner_client)
    headers = {"Authorization": f"Bearer {token}"}

    response = APIClient().post("/api/v1/projects/PID00001/tasks", VALID_CREATE, headers=headers)
    assert response.status_code == 403
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"


def test_pid00001_agent_token_is_forbidden_on_pid00002_tasks(
    owner_client: APIClient, project: Project
) -> None:
    """WP-1.2 acceptance on the real task routes (ADR-004 zero-bleed)."""
    Task.objects.create(id="PID00001-T001", project=project, title="Own project task")
    Project.objects.create(
        id="PID00002",
        name="Other project",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    token = _issue_agent_token(owner_client, "PID00001", role="decomposer")
    headers = {"Authorization": f"Bearer {token}"}
    api = APIClient()

    # Project-addressed create: scope mismatch outranks the role error.
    create_other = api.post("/api/v1/projects/PID00002/tasks", VALID_CREATE, headers=headers)
    assert create_other.status_code == 403
    assert _envelope(create_other)["code"] == "AUTH_FORBIDDEN_PROJECT"

    # Task-addressed detail: the PID rides inside the task id (Section 7.3).
    detail_other = api.get("/api/v1/tasks/PID00002-T001", headers=headers)
    assert detail_other.status_code == 403
    assert _envelope(detail_other)["code"] == "AUTH_FORBIDDEN_PROJECT"

    # ...while the own-project task id passes scope and hits the §9.2
    # agent read cell (the activated WP-2.x read — 200).
    detail_own = api.get("/api/v1/tasks/PID00001-T001", headers=headers)
    assert detail_own.status_code == 200
    assert detail_own.json()["id"] == "PID00001-T001"
