"""MT-1.6-07 — claim, release and work endpoints (Section 9.2 "Agent work" row).

Run with ``pytest backend/tests -k claim_release_endpoints -q``. Every
case runs against the **real** routes with real credentials: success
shapes (task + Section 8.6 lease record + Section 10.6 rules block),
the full catalog-error matrix, ``Idempotency-Key`` replay (NFR-12),
and the Section 12.2 permission cells the authorization matrix rows
exercise.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.projects.models import Project
from apps.tasks.models import Task, TaskState, TaskTransition
from apps.tasks.services.dependencies import set_dependencies

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    PASSWORD,
    active_policy_project,
    make_pending_task,
    make_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db

LEASE_FIELDS = {
    "task_id",
    "assigned_agent",
    "session_id",
    "role",
    "lease_generation",
    "lease_acquired_at",
    "lease_expires_at",
    "lease_hard_cap_at",
    "last_checkpoint",
    "failure_retry_count",
}


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — fresh budget per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport)."""
    User.objects.create_user("owner-wp16", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner-wp16", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def issue_agent_token(owner_client: APIClient, project_id: str, *scopes: str) -> dict[str, Any]:
    """Mint a project-scoped agent token through the real Owner API."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": list(scopes)}
    )
    assert response.status_code == 201, response.content
    payload: dict[str, Any] = response.json()
    return payload


def agent_client(token_payload: dict[str, Any]) -> APIClient:
    """A plain client carrying one agent bearer token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['token']}")
    return client


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


def claim_payload(session_id: str = "sess_ep_claim", label: str = "ep-coder") -> dict[str, Any]:
    """The ClaimRequest body (session id + worker label)."""
    return {"session_id": session_id, "worker_agent_id": label}


# --- claim: success shape ----------------------------------------------------


def test_claim_returns_task_lease_and_rules_block(
    owner_client: APIClient, project: Project
) -> None:
    """200 body: task details, the Section 8.6 lease JSON, Section 10.6 rules."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    response = client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {"task", "lease", "rules_block"}
    assert body["task"]["state"] == TaskState.IN_PROGRESS
    lease = body["lease"]
    assert set(lease) == LEASE_FIELDS, "Section 8.6 example JSON, field for field"
    assert lease["lease_generation"] == 1
    assert lease["session_id"] == "sess_ep_claim"
    assert lease["role"] == "coder"
    assert lease["assigned_agent"] == "ep-coder"
    assert lease["lease_hard_cap_at"] is not None
    rules = body["rules_block"]
    assert set(rules) == {"standard_rules", "project_rules"}
    assert len(rules["standard_rules"]) == 8, "Section 10.6's eight standard rules"
    assert rules["project_rules"] == project.system_prompt_rules


def test_claim_persists_the_lease_on_the_row(owner_client: APIClient, project: Project) -> None:
    """The response mirrors committed state, not optimistic memory."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    fresh = Task.objects.get(pk=task.pk)
    assert fresh.state == TaskState.IN_PROGRESS
    assert fresh.worker_session_id == "sess_ep_claim"
    acquired = fresh.lease_acquired_at
    assert acquired is not None
    assert fresh.lease_expires_at == acquired + timedelta(
        minutes=project.agent_policy.lease_duration_minutes
    )


# --- claim: authentication and authorization --------------------------------


def test_claim_anonymous_is_auth_required(owner_client: APIClient, project: Project) -> None:
    """401 + AUTH_REQUIRED in the standard envelope (Section 9.2)."""
    task = make_pending_task(project, 1)
    response = APIClient().post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())
    assert response.status_code == 401
    assert _code(response) == "AUTH_REQUIRED"


def test_claim_non_coder_roles_are_role_not_permitted(
    owner_client: APIClient, project: Project
) -> None:
    """Section 12.2: only the coder cell may claim pending work."""
    task = make_pending_task(project, 1)
    for role in ("auditor", "decomposer", "merge_executor"):
        client = agent_client(issue_agent_token(owner_client, project.pk, role))
        response = client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())
        assert response.status_code == 403, (role, response.content)
        assert _code(response) == "ROLE_NOT_PERMITTED"

    owner_response = owner_client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())
    assert owner_response.status_code == 403
    assert _code(owner_response) == "ROLE_NOT_PERMITTED"


def test_claim_cross_project_token_is_forbidden(owner_client: APIClient, project: Project) -> None:
    """ADR-004: a PID00002 token never touches PID00001 rows (403)."""
    other = active_policy_project(pid="PID00002")
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, other.pk, "coder"))

    response = client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"
    assert Task.objects.get(pk=task.pk).state == TaskState.PENDING


# --- claim: error catalog ----------------------------------------------------


def test_claim_unknown_and_malformed_ids(owner_client: APIClient, project: Project) -> None:
    """404 TASK_NOT_FOUND for well-formed unknown ids; 400 for malformed."""
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    unknown = client.post("/api/v1/tasks/PID00001-T999/claim", claim_payload())
    assert unknown.status_code == 404 and _code(unknown) == "TASK_NOT_FOUND"

    malformed = client.post("/api/v1/tasks/1/claim", claim_payload())
    assert malformed.status_code == 400 and _code(malformed) == "VALIDATION_ERROR"


def test_claim_already_claimed_is_409(owner_client: APIClient, project: Project) -> None:
    """The losing claimant reads TASK_ALREADY_CLAIMED with the envelope."""
    task = make_pending_task(project, 1)
    first = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    second = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    assert first.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload("sess_a")).status_code == 200

    response = second.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload("sess_b"))

    assert response.status_code == 409
    assert _code(response) == "TASK_ALREADY_CLAIMED"


def test_claim_state_dependency_and_concurrency_codes(
    owner_client: APIClient, project: Project
) -> None:
    """409 codes: TASK_STATE_CONFLICT, DEPENDENCY_UNMET, CONCURRENCY_LIMIT_REACHED."""
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    draft = make_task(project, 1, state=TaskState.DRAFT)
    response = client.post(f"/api/v1/tasks/{draft.pk}/claim", claim_payload())
    assert response.status_code == 409 and _code(response) == "TASK_STATE_CONFLICT"

    blocker = make_task(project, 2, state=TaskState.PENDING)
    waiting = make_pending_task(project, 3)
    set_dependencies(task=waiting, dependency_ids=[blocker.pk])
    response = client.post(f"/api/v1/tasks/{waiting.pk}/claim", claim_payload())
    assert response.status_code == 409 and _code(response) == "DEPENDENCY_UNMET"

    running = make_pending_task(project, 4)
    assert client.post(f"/api/v1/tasks/{running.pk}/claim", claim_payload()).status_code == 200
    capped = make_pending_task(project, 5)
    response = client.post(f"/api/v1/tasks/{capped.pk}/claim", claim_payload())
    assert response.status_code == 409 and _code(response) == "CONCURRENCY_LIMIT_REACHED"


# --- claim: idempotency (NFR-12; ADR-012) -----------------------------------


def test_claim_idempotency_key_replays_one_lease(owner_client: APIClient, project: Project) -> None:
    """Same key + same request → identical 200, exactly one lease."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    headers = {"Idempotency-Key": "claim-key-1"}

    first = client.post(
        f"/api/v1/tasks/{task.pk}/claim", claim_payload(), format="json", headers=headers
    )
    retry = client.post(
        f"/api/v1/tasks/{task.pk}/claim", claim_payload(), format="json", headers=headers
    )

    assert first.status_code == 200 and retry.status_code == 200
    assert first.json() == retry.json(), "the replay is byte-identical"
    assert Task.objects.get(pk=task.pk).lease_generation == 1, "one lease, one increment"
    assert TaskTransition.objects.filter(task=task).count() == 1


def test_claim_same_key_different_body_executes(owner_client: APIClient, project: Project) -> None:
    """headers.md open point: key reuse with a different request replays nothing."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    headers = {"Idempotency-Key": "claim-key-2"}

    assert (
        client.post(
            f"/api/v1/tasks/{task.pk}/claim",
            claim_payload("sess_a"),
            format="json",
            headers=headers,
        ).status_code
        == 200
    )
    response = client.post(
        f"/api/v1/tasks/{task.pk}/claim", claim_payload("sess_b"), format="json", headers=headers
    )
    assert response.status_code == 409, "different fingerprint → executed, not replayed"
    assert _code(response) == "TASK_ALREADY_CLAIMED"


# --- release -----------------------------------------------------------------


def test_release_endpoint_clears_the_lease(owner_client: APIClient, project: Project) -> None:
    """Agent release with the fencing pair → 200, task back to pending."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    claimed = client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload()).json()

    response = client.post(
        f"/api/v1/tasks/{task.pk}/release",
        {"session_id": "sess_ep_claim", "lease_generation": 1, "reason": "done"},
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["state"] == TaskState.PENDING
    assert body["worker_session_id"] is None
    assert body["attempt_number"] == claimed["task"]["attempt_number"], "attempt preserved"
    row = TaskTransition.objects.filter(task=task).latest("timestamp")
    assert row.note == "done", "the reason lands on the Transition note"
    assert row.reason_code == "voluntary_release"


def test_release_requires_the_fencing_pair_for_agents(
    owner_client: APIClient, project: Project
) -> None:
    """ADR-012 presence: {} from an agent is VALIDATION_ERROR, not a wildcard."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    response = client.post(f"/api/v1/tasks/{task.pk}/release", {})

    assert response.status_code == 400 and _code(response) == "VALIDATION_ERROR"
    assert Task.objects.get(pk=task.pk).state == TaskState.IN_PROGRESS


def test_release_foreign_session_and_expired_lease(
    owner_client: APIClient, project: Project
) -> None:
    """403 LEASE_NOT_OWNED (wrong session); 409 LEASE_EXPIRED (dead lease)."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    foreign = client.post(
        f"/api/v1/tasks/{task.pk}/release",
        {"session_id": "sess_someone_else", "lease_generation": 1},
    )
    assert foreign.status_code == 403 and _code(foreign) == "LEASE_NOT_OWNED"

    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    stale = client.post(
        f"/api/v1/tasks/{task.pk}/release",
        {"session_id": "sess_ep_claim", "lease_generation": 1},
    )
    assert stale.status_code == 409 and _code(stale) == "LEASE_EXPIRED"
    assert Task.objects.get(pk=task.pk).state == TaskState.IN_PROGRESS


def test_release_owner_override(owner_client: APIClient, project: Project) -> None:
    """Section 8.2 T6 actors (C, O): an owner session releases without a pair."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())

    response = owner_client.post(f"/api/v1/tasks/{task.pk}/release", {})

    assert response.status_code == 200, response.content
    assert response.json()["state"] == TaskState.PENDING
    row = TaskTransition.objects.filter(task=task).latest("timestamp")
    assert row.actor_type == "owner", "the override is auditable"


def test_release_permission_cells(owner_client: APIClient, project: Project) -> None:
    """Anonymous 401; non-coder agent roles 403 ROLE_NOT_PERMITTED."""
    task = make_pending_task(project, 1)
    assert APIClient().post(f"/api/v1/tasks/{task.pk}/release", {}).status_code == 401

    for role in ("auditor", "decomposer", "merge_executor"):
        client = agent_client(issue_agent_token(owner_client, project.pk, role))
        response = client.post(f"/api/v1/tasks/{task.pk}/release", {})
        assert response.status_code == 403, (role, response.content)
        assert _code(response) == "ROLE_NOT_PERMITTED"


def test_release_idempotency_key_replays_one_transition(
    owner_client: APIClient, project: Project
) -> None:
    """A retried release replays 200 — never a second T6 row."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    client.post(f"/api/v1/tasks/{task.pk}/claim", claim_payload())
    payload = {"session_id": "sess_ep_claim", "lease_generation": 1}
    headers = {"Idempotency-Key": "release-key-1"}

    first = client.post(f"/api/v1/tasks/{task.pk}/release", payload, format="json", headers=headers)
    retry = client.post(f"/api/v1/tasks/{task.pk}/release", payload, format="json", headers=headers)

    assert first.status_code == 200 and retry.status_code == 200
    assert first.json() == retry.json()
    t6_rows = TaskTransition.objects.filter(task=task, reason_code="voluntary_release")
    assert t6_rows.count() == 1


# --- GET /projects/{pid}/work ------------------------------------------------


def test_work_list_lists_offerable_tasks(owner_client: APIClient, project: Project) -> None:
    """Coder role: pending, dependency-complete, canonical order, envelope shape."""
    low = make_pending_task(project, 1, priority="low")
    urgent = make_pending_task(project, 2, priority="urgent")
    blocker = make_task(project, 3, state=TaskState.PENDING)
    waiting = make_pending_task(project, 4)
    set_dependencies(task=waiting, dependency_ids=[blocker.pk])
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    response = client.get(f"/api/v1/projects/{project.pk}/work")

    assert response.status_code == 200, response.content
    body = response.json()
    assert set(body) == {"results", "next_cursor"}
    ids = [row["id"] for row in body["results"]]
    assert ids == [urgent.pk, blocker.pk, low.pk], "waiting excluded (FR-TSK-07); FIFO held"
    assert body["next_cursor"] is None


def test_work_list_requires_agent_and_scope(owner_client: APIClient, project: Project) -> None:
    """Caller Agent (Section 9.2): anonymous 401, owner 403, foreign pid 403."""
    make_pending_task(project, 1)
    assert APIClient().get(f"/api/v1/projects/{project.pk}/work").status_code == 401
    assert owner_client.get(f"/api/v1/projects/{project.pk}/work").status_code == 403

    other = active_policy_project(pid="PID00002")
    client = agent_client(issue_agent_token(owner_client, other.pk, "coder"))
    response = client.get(f"/api/v1/projects/{project.pk}/work")
    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"


def test_work_list_is_empty_for_a_paused_project(owner_client: APIClient, project: Project) -> None:
    """FR-PRJ-04: paused offers no work — an empty list, not an error."""
    make_pending_task(project, 1)
    type(project).objects.filter(pk=project.pk).update(active_status="paused")
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    response = client.get(f"/api/v1/projects/{project.pk}/work")

    assert response.status_code == 200
    assert response.json() == {"results": [], "next_cursor": None}


def test_work_list_auditor_role_and_priority_filter(
    owner_client: APIClient, project: Project
) -> None:
    """role=auditor lists to_be_audited; ?priority= filters (Section 9.2)."""
    make_pending_task(project, 1, priority="urgent")
    audit_row = make_task(project, 2, state=TaskState.TO_BE_AUDITED)
    low = make_pending_task(project, 3, priority="low")
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor", "coder"))

    auditor = client.get(f"/api/v1/projects/{project.pk}/work", {"role": "auditor"})
    assert [row["id"] for row in auditor.json()["results"]] == [audit_row.pk]

    lows = client.get(f"/api/v1/projects/{project.pk}/work", {"priority": "low"})
    assert [row["id"] for row in lows.json()["results"]] == [low.pk]


def test_work_list_cursor_pagination(owner_client: APIClient, project: Project) -> None:
    """pagination.md envelope: page_size=1 yields a cursor to the next page."""
    first = make_pending_task(project, 1, priority="urgent")
    second = make_pending_task(project, 2, priority="urgent")
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    page_one = client.get(f"/api/v1/projects/{project.pk}/work", {"page_size": 1})
    body = page_one.json()
    assert [row["id"] for row in body["results"]] == [first.pk]
    assert body["next_cursor"]

    page_two = client.get(
        f"/api/v1/projects/{project.pk}/work",
        {"page_size": 1, "cursor": body["next_cursor"]},
    )
    assert [row["id"] for row in page_two.json()["results"]] == [second.pk]
    assert page_two.json()["next_cursor"] is None
