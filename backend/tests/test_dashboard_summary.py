"""MT-1.15-06 — ``GET /dashboard/summary`` (Section 9.2 Dashboard row; FR-MOB-01).

The endpoint's test command, executed against the running API with real
credentials:

* payload shape — every project appears once in project-id order; each card
  carries exactly ``project_id``, ``name``, ``state_counts``, ``velocity``,
  ``active_agents``; ``state_counts`` always contains **all six canonical
  G-01 keys** (ADR-010), zero-filled, over **non-archived** tasks only (T19
  default board visibility);
* aggregation correctness — per-state counts, the 7-day velocity window
  against the append-only TaskTransition log (a completion older than the
  window does not count; ``in_human_review``/other states do not count as
  velocity), and active vs ended agent sessions (``ended_at`` null only);
* the caller matrix — owner session 200; coder/auditor/decomposer/
  merge-executor agent tokens and a device token 403 ``ROLE_NOT_PERMITTED``;
  anonymous 401 ``AUTH_REQUIRED`` — all with the five-field Section 9.2
  envelope, including the **cross-project isolation** proof that a
  PID-scoped agent token never receives any project's counts (the denial is
  envelope-only; ADR-004 zero-bleed in the no-data sense this row implies);
* no pagination — the body is the single-resource shape, not the
  pagination.md ``results``/``next_cursor`` envelope.

Run with ``uv run --directory backend pytest tests/test_dashboard_summary.py``
(MT test command); the file runs in CI's unit job alongside the deferred-entry
retirement it forced in ``tests/test_authorization_matrix.py``.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta
from typing import Any, cast

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.agents.models import AgentSession, SessionTransport
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState, TaskTransition

SUMMARY_URL = "/api/v1/dashboard/summary"
PASSWORD = "dashboard-summary-tests-1!"  # pragma: allowlist secret

#: The six canonical G-01/ADR-010 state keys — the payload must always
#: carry every one of them (the mobile card renders from these keys).
STATE_KEYS = (
    "draft",
    "pending",
    "in_progress",
    "to_be_audited",
    "in_human_review",
    "completed",
)

AGENT_ROLES = ("coder", "auditor", "decomposer", "merge_executor")


@pytest.fixture(autouse=True)
def clean_throttle_cache() -> Iterator[None]:
    """Throttle history is process state — keep budgets fresh across files."""
    cache.clear()
    yield
    cache.clear()


def _envelope(response: Any) -> dict[str, Any]:
    """Assert the five-field Section 9.2 envelope; return the error body."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    assert error["code"] in (
        "AUTH_REQUIRED",
        "ROLE_NOT_PERMITTED",
    ), "catalog-closed codes (Section 9.2; 20.4 item 5)"
    return cast(dict[str, Any], error)


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


@pytest.fixture
def client(db: None) -> APIClient:
    """An unauthenticated client (the `plain` caller)."""
    return APIClient()


def _make_project(pid: str, name: str) -> Project:
    """One project row with the Section 7.1 policy pair (deterministic id)."""
    return Project.objects.create(
        id=pid,
        name=name,
        repo_path=f"/srv/repos/{name.lower().replace(' ', '-')}",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _make_task(project: Project, index: int, state: str, **overrides: Any) -> Task:
    """One task row with a deterministic id; the counter stays honest."""
    payload: dict[str, Any] = {
        "id": f"{project.pk}-T{index:03d}",
        "project": project,
        "title": f"Task {index:03d}",
        "state": state,
    }
    payload.update(overrides)
    task = Task.objects.create(**payload)
    Project.objects.filter(pk=project.pk, task_counter__lt=index).update(task_counter=index)
    return task


def _complete(task: Task, *, age: timedelta = timedelta(0)) -> None:
    """Record the append-only completion row velocity reads (Section 7.2).

    ``age`` backdates the history row's timestamp so tests can pin the
    velocity window. ``auto_now_add`` owns the column on insert and the
    TransitionQuerySet refuses ``update()`` (P8 append-only), so the age
    is applied with one raw UPDATE — the guard covers the application
    role, not this test fixture deliberately aging its own history.
    """
    transition = TaskTransition.objects.create(
        task=task,
        from_state=TaskState.IN_HUMAN_REVIEW,
        to_state=TaskState.COMPLETED,
        actor_type="owner",
        actor_ref="1",
        # Names the Section 8.2 approve trigger the WP-3.x review flow
        # registers catalog-first; the column carries no DB check
        # constraint, and the completion rows velocity reads predate it.
        reason_code="approve",
    )
    if age:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks_tasktransition SET timestamp = %s WHERE id = %s",
                [timezone.now() - age, transition.pk],
            )


def _session(pid: str, session_id: str, *, ended: bool = False) -> AgentSession:
    """One agent session row (open by default — the active-agent signal)."""
    return AgentSession.objects.create(
        id=session_id,
        project_id=pid,
        token_id=1,
        transport=SessionTransport.STDIO,
        ended_at=timezone.now() if ended else None,
    )


def _issue_agent_token(owner_client: APIClient, project_id: str, role: str) -> str:
    """Mint an agent bearer token scoped to *project_id* (plaintext back)."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": [role]}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


def _register_device(owner_client: APIClient) -> str:
    """Mint a device bearer token (plaintext back)."""
    response = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-dashboard-summary"}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


# --- payload shape (FR-MOB-01; the WP-5.6 recommendation contract) ----------


def test_owner_gets_one_card_per_project_in_id_order(
    owner_client: APIClient,
) -> None:
    """Every registered project appears once, ordered by project id."""
    _make_project("PID00002", "Website")
    _make_project("PID00001", "Orchestrator")

    response = owner_client.get(SUMMARY_URL)
    assert response.status_code == status.HTTP_200_OK, response.content

    projects = response.json()["projects"]
    assert [card["project_id"] for card in projects] == ["PID00001", "PID00002"]
    assert [card["name"] for card in projects] == ["Orchestrator", "Website"]


def test_every_card_carries_exactly_the_documented_fields(
    owner_client: APIClient,
) -> None:
    """The WP-5.6 card contract: five keys, no invented fields."""
    _make_project("PID00001", "Orchestrator")

    body = owner_client.get(SUMMARY_URL).json()
    assert set(body) == {"projects"}
    card = body["projects"][0]
    assert set(card) == {"project_id", "name", "state_counts", "velocity", "active_agents"}


def test_state_counts_always_carry_all_six_g01_keys_zero_filled(
    owner_client: APIClient,
) -> None:
    """A project with no tasks still reports every state as 0 (ADR-010)."""
    _make_project("PID00001", "Quiet")

    card = owner_client.get(SUMMARY_URL).json()["projects"][0]
    assert card["state_counts"] == {key: 0 for key in STATE_KEYS}
    assert card["velocity"] == 0
    assert card["active_agents"] == 0


def test_state_counts_aggregate_states_and_exclude_archived_tasks(
    owner_client: APIClient,
) -> None:
    """Counts are per-state over non-archived tasks (T19 visibility)."""
    project = _make_project("PID00001", "Orchestrator")
    _make_task(project, 1, TaskState.DRAFT)
    _make_task(project, 2, TaskState.DRAFT)
    _make_task(project, 3, TaskState.IN_PROGRESS)
    _make_task(project, 4, TaskState.IN_HUMAN_REVIEW)
    # Archived: hidden from the board, hidden from the counts (T19).
    _make_task(project, 5, TaskState.PENDING, archived_at=timezone.now())

    card = owner_client.get(SUMMARY_URL).json()["projects"][0]
    assert card["state_counts"] == {
        "draft": 2,
        "pending": 0,
        "in_progress": 1,
        "to_be_audited": 0,
        "in_human_review": 1,
        "completed": 0,
    }


def test_counts_never_leak_across_projects(owner_client: APIClient) -> None:
    """One project's tasks never appear in another's card."""
    first = _make_project("PID00001", "Orchestrator")
    second = _make_project("PID00002", "Website")
    _make_task(first, 1, TaskState.IN_PROGRESS)
    _make_task(second, 1, TaskState.DRAFT)
    _make_task(second, 2, TaskState.DRAFT)

    cards = {card["project_id"]: card for card in owner_client.get(SUMMARY_URL).json()["projects"]}
    assert cards["PID00001"]["state_counts"]["draft"] == 0
    assert cards["PID00001"]["state_counts"]["in_progress"] == 1
    assert cards["PID00002"]["state_counts"]["draft"] == 2
    assert cards["PID00002"]["state_counts"]["in_progress"] == 0


# --- velocity (documented default: 7-day completion window) -----------------


def test_velocity_counts_only_completions_inside_the_window(
    owner_client: APIClient,
) -> None:
    """The transition log's last 7 days (server clock); older rows excluded."""
    project = _make_project("PID00001", "Orchestrator")
    fresh = _make_task(project, 1, TaskState.COMPLETED)
    stale = _make_task(project, 2, TaskState.COMPLETED)
    _complete(fresh)
    _complete(stale, age=timedelta(days=8))

    card = owner_client.get(SUMMARY_URL).json()["projects"][0]
    assert card["velocity"] == 1


def test_velocity_ignores_non_completed_transitions(
    owner_client: APIClient,
) -> None:
    """Only ``to_state=completed`` feeds velocity (the pinned definition)."""
    project = _make_project("PID00001", "Orchestrator")
    task = _make_task(project, 1, TaskState.IN_PROGRESS)
    TaskTransition.objects.create(
        task=task,
        from_state=TaskState.PENDING,
        to_state=TaskState.IN_PROGRESS,
        actor_type="agent",
        actor_ref="sess_dashboard_1",
        reason_code="claim",
    )

    card = owner_client.get(SUMMARY_URL).json()["projects"][0]
    assert card["velocity"] == 0


# --- active agents (ended_at null only) -------------------------------------


def test_active_agents_count_open_sessions_only(
    owner_client: APIClient,
) -> None:
    """`active_agents` = AgentSession rows with ended_at null (Section 7.2)."""
    project = _make_project("PID00001", "Orchestrator")
    _make_task(project, 1, TaskState.DRAFT)  # unrelated, keeps the card non-vacuous
    _session("PID00001", "sess_dashboard_open_1")
    _session("PID00001", "sess_dashboard_open_2")
    _session("PID00001", "sess_dashboard_ended", ended=True)

    card = owner_client.get(SUMMARY_URL).json()["projects"][0]
    assert card["active_agents"] == 2


# --- callers: Owner only, catalog codes, envelope (Sections 9.2/12.2) ------


def test_anonymous_answers_auth_required_with_the_envelope(
    client: APIClient,
) -> None:
    """No credential → 401 AUTH_REQUIRED (the five-field envelope)."""
    response = client.get(SUMMARY_URL)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert _envelope(response)["code"] == "AUTH_REQUIRED"


def test_every_agent_role_is_refused_with_role_not_permitted(
    owner_client: APIClient, client: APIClient
) -> None:
    """No Section 12.2 row grants agents the dashboard — every role 403."""
    _make_project("PID00001", "Orchestrator")
    for role in AGENT_ROLES:
        token = _issue_agent_token(owner_client, "PID00001", role)
        response = client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_403_FORBIDDEN, (role, response.content)
        assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED", role


def test_device_token_is_refused(owner_client: APIClient, client: APIClient) -> None:
    """§9.2 names Owner and §12.2 prints no device cell — device 403."""
    token = _register_device(owner_client)
    response = client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"


def test_cross_project_agent_token_receives_no_counts(
    owner_client: APIClient, client: APIClient
) -> None:
    """ADR-004 isolation: the PID-scoped agent sees no project's data.

    The summary spans every project, which no agent token may read — the
    denial body is the error envelope **only**, never a card fragment.
    """
    first = _make_project("PID00001", "Orchestrator")
    second = _make_project("PID00002", "Website")
    _make_task(first, 1, TaskState.IN_PROGRESS)
    _make_task(second, 1, TaskState.DRAFT)
    _session("PID00002", "sess_dashboard_foreign_1")

    token = _issue_agent_token(owner_client, "PID00001", "coder")
    response = client.get(SUMMARY_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == status.HTTP_403_FORBIDDEN
    body = response.content.decode("utf-8")
    assert _envelope(response)["code"] == "ROLE_NOT_PERMITTED"
    for leaked in ("PID00001", "PID00002", "state_counts", "velocity", "Orchestrator"):
        assert leaked not in body, f"denial leaked {leaked!r}: {body}"


# --- single-resource GET: no pagination (pagination.md) ---------------------


def test_body_is_the_single_resource_shape_not_a_cursor_envelope(
    owner_client: APIClient,
) -> None:
    """No results/next_cursor: dashboard summary is not a list endpoint."""
    _make_project("PID00001", "Orchestrator")
    body = owner_client.get(SUMMARY_URL).json()
    assert "results" not in body
    assert "next_cursor" not in body
