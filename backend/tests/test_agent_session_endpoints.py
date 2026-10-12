"""MT-1.6-09 — agent session open/end endpoints (Section 9.2 Sessions row).

Run with ``pytest backend/tests -k agent_session -q``: the Section 7.2
field contract, ADR-004 project binding (project from the token, never
the body), idempotent end, duplicate/unknown-id refusals, and the
Bridge-caller permission cells.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.agents.models import AgentSession, SessionCapability, SessionTransport
from apps.projects.models import Project

from .wp16_helpers import PASSWORD, active_policy_project

pytestmark = pytest.mark.django_db

SESSION_FIELDS = {
    "id",
    "project_id",
    "token_id",
    "agent_label",
    "client_name",
    "capability",
    "transport",
    "started_at",
    "last_seen_at",
    "ended_at",
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
    User.objects.create_user("owner-sessions", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner-sessions", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def project() -> Project:
    """One active project."""
    return active_policy_project()


def issue_agent_token(owner_client: APIClient, project_id: str) -> dict[str, Any]:
    """Mint a project-scoped coder token through the real Owner API."""
    response = owner_client.post(
        "/api/v1/tokens/agent", {"project_id": project_id, "scopes": ["coder"]}
    )
    assert response.status_code == 201, response.content
    payload: dict[str, Any] = response.json()
    return payload


def agent_client(token_payload: dict[str, Any]) -> APIClient:
    """A plain client carrying one agent bearer token."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_payload['token']}")
    return client


def open_body(session_id: str = "sess_lifecycle_1", **extra: Any) -> dict[str, Any]:
    """The AgentSessionCreate body (bridge-issued id + declared shape)."""
    body = {"id": session_id, "transport": SessionTransport.STDIO}
    body.update(extra)
    return body


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


# --- open --------------------------------------------------------------------


def test_open_creates_the_section_7_2_row(owner_client: APIClient, project: Project) -> None:
    """201 returns every Section 7.2 field; project/token come from the token."""
    token = issue_agent_token(owner_client, project.pk)
    client = agent_client(token)

    response = client.post(
        "/api/v1/agent-sessions",
        open_body(agent_label="claude-code", client_name="claude/1.0"),
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert set(body) == SESSION_FIELDS
    assert body["id"] == "sess_lifecycle_1"
    assert body["project_id"] == project.pk, "the project is the token's (ADR-004)"
    assert body["token_id"] == token["id"]
    assert body["agent_label"] == "claude-code"
    assert body["client_name"] == "claude/1.0"
    assert body["capability"] == SessionCapability.UNKNOWN, "Section 10.4 default"
    assert body["transport"] == SessionTransport.STDIO
    assert body["started_at"] == body["last_seen_at"], "no heartbeat invented (OQ-04)"
    assert body["ended_at"] is None
    row = AgentSession.objects.get(pk="sess_lifecycle_1")
    assert row.project_id == project.pk


def test_open_rejects_a_body_supplied_project(owner_client: APIClient, project: Project) -> None:
    """ADR-004 executable: unknown field → VALIDATION_ERROR, row never made."""
    client = agent_client(issue_agent_token(owner_client, project.pk))

    response = client.post("/api/v1/agent-sessions", open_body(project_id="PID00002"))

    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"
    assert not AgentSession.objects.filter(pk="sess_lifecycle_1").exists()


def test_open_validates_the_id_and_transport(owner_client: APIClient, project: Project) -> None:
    """Shape validation at the boundary (G-18 unguessable id, 10.2 modes)."""
    client = agent_client(issue_agent_token(owner_client, project.pk))

    short_id = client.post("/api/v1/agent-sessions", open_body(session_id="ab"))
    assert short_id.status_code == 400 and _code(short_id) == "VALIDATION_ERROR"

    bad_transport = client.post(
        "/api/v1/agent-sessions", {"id": "sess_lifecycle_2", "transport": "carrier-pigeon"}
    )
    assert bad_transport.status_code == 400 and _code(bad_transport) == "VALIDATION_ERROR"


def test_open_duplicate_id_is_refused(owner_client: APIClient, project: Project) -> None:
    """Same id twice (no key) → VALIDATION_ERROR, never a second row."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    assert client.post("/api/v1/agent-sessions", open_body()).status_code == 201

    response = client.post("/api/v1/agent-sessions", open_body())

    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"
    assert AgentSession.objects.filter(project=project).count() == 1


def test_open_idempotency_key_replays_one_row(owner_client: APIClient, project: Project) -> None:
    """NFR-12: a retried open replays the original 201 — one row."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    headers = {"Idempotency-Key": "session-open-1"}

    first = client.post("/api/v1/agent-sessions", open_body(), format="json", headers=headers)
    retry = client.post("/api/v1/agent-sessions", open_body(), format="json", headers=headers)

    assert first.status_code == 201 and retry.status_code == 201
    assert first.json() == retry.json()
    assert AgentSession.objects.count() == 1


def test_open_permission_cells(owner_client: APIClient, project: Project) -> None:
    """Sessions row caller Bridge: anon 401; owner/device-role 403; agent 201."""
    assert APIClient().post("/api/v1/agent-sessions", open_body()).status_code == 401

    owner_response = owner_client.post("/api/v1/agent-sessions", open_body())
    assert owner_response.status_code == 403
    assert _code(owner_response) == "ROLE_NOT_PERMITTED"

    client = agent_client(issue_agent_token(owner_client, project.pk))
    assert client.post("/api/v1/agent-sessions", open_body()).status_code == 201


def test_open_cross_project_token_binds_its_own_project(
    owner_client: APIClient, project: Project
) -> None:
    """A token can only open sessions for the project it is scoped to."""
    other = active_policy_project(pid="PID00002")
    client = agent_client(issue_agent_token(owner_client, other.pk))

    response = client.post("/api/v1/agent-sessions", open_body())

    assert response.status_code == 201
    assert response.json()["project_id"] == other.pk


# --- end ---------------------------------------------------------------------


def test_end_sets_ended_at_exactly_once(owner_client: APIClient, project: Project) -> None:
    """200 sets the stamp; a second end replays without a second write."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    client.post("/api/v1/agent-sessions", open_body())

    first = client.post("/api/v1/agent-sessions/sess_lifecycle_1/end")
    second = client.post("/api/v1/agent-sessions/sess_lifecycle_1/end")

    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json(), "the repeat changes nothing"
    assert first.json()["ended_at"] is not None
    assert AgentSession.objects.get(pk="sess_lifecycle_1").ended_at is not None


def test_end_unknown_id_is_the_no_catalog_code_mapping(
    owner_client: APIClient, project: Project
) -> None:
    """No SESSION_NOT_FOUND exists — core's documented 400 mapping answers."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    response = client.post("/api/v1/agent-sessions/sess_no_such_one/end")
    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"


def test_end_cross_project_token_is_forbidden(owner_client: APIClient, project: Project) -> None:
    """ADR-004: ending another project's session → AUTH_FORBIDDEN_PROJECT."""
    other = active_policy_project(pid="PID00002")
    owner_of_other = agent_client(issue_agent_token(owner_client, project.pk))
    assert owner_of_other.post("/api/v1/agent-sessions", open_body()).status_code == 201

    foreign_client = agent_client(issue_agent_token(owner_client, other.pk))
    response = foreign_client.post("/api/v1/agent-sessions/sess_lifecycle_1/end")

    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"
    assert AgentSession.objects.get(pk="sess_lifecycle_1").ended_at is None


def test_end_permission_cells(owner_client: APIClient, project: Project) -> None:
    """Anonymous 401, owner 403 — Bridge-only caller column."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    client.post("/api/v1/agent-sessions", open_body())

    assert APIClient().post("/api/v1/agent-sessions/sess_lifecycle_1/end").status_code == 401
    owner_response = owner_client.post("/api/v1/agent-sessions/sess_lifecycle_1/end")
    assert owner_response.status_code == 403
    assert _code(owner_response) == "ROLE_NOT_PERMITTED"
    assert AgentSession.objects.get(pk="sess_lifecycle_1").ended_at is None


def test_end_idempotency_key_replay(owner_client: APIClient, project: Project) -> None:
    """Retried end with the same key replays the stored 200."""
    client = agent_client(issue_agent_token(owner_client, project.pk))
    client.post("/api/v1/agent-sessions", open_body())
    headers = {"Idempotency-Key": "session-end-1"}

    first = client.post("/api/v1/agent-sessions/sess_lifecycle_1/end", headers=headers)
    retry = client.post("/api/v1/agent-sessions/sess_lifecycle_1/end", headers=headers)

    assert first.status_code == 200 and retry.status_code == 200
    assert first.json() == retry.json()


def test_open_and_end_carry_the_agent_throttle(owner_client: APIClient) -> None:
    """FR-SEC-05: both Sessions routes name AgentEndpointThrottle."""
    from apps.agents.views import AgentSessionEndView, AgentSessionOpenView
    from apps.core.throttling import AgentEndpointThrottle

    assert AgentEndpointThrottle in AgentSessionOpenView.throttle_classes
    assert AgentEndpointThrottle in AgentSessionEndView.throttle_classes
