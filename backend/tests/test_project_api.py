"""MT-1.3-03 — project CRUD endpoints (Sections 9.2, 7.2, 12.2; FR-PRJ-01/02/04).

The MT's test command, executed against the running API with real
credentials:

* ``POST /projects`` assigns a generated ``PID[0-9]{5}`` and the default
  policy pair; a client-supplied id is **rejected**, never honored;
* fetch/patch round-trips every FR-PRJ-02 field; ``active_status`` cycles
  through the three canonical values only;
* malformed and unknown ``{pid}`` both answer catalog codes (the recorded
  asymmetry: no ``PROJECT_NOT_FOUND`` exists, so both land on
  ``VALIDATION_ERROR``/400 — MT-1.3-03 risk note);
* non-owner callers answer ``ROLE_NOT_PERMITTED``/``AUTH_REQUIRED``, and an
  agent token aimed at another project answers ``AUTH_FORBIDDEN_PROJECT``
  (ADR-004 against real rows — the WP-1.2 probe/deferred assumption this
  WP replaces);
* list pagination follows the MT-0.5-04 cursor shape (envelope is exactly
  ``results`` + ``next_cursor``).

Run with ``pytest backend/tests/test_project_api.py`` (MT test command).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any, cast

import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.errors import CANONICAL_ERROR_CODES
from apps.projects.models import ProjectPolicy
from apps.projects.services.pids import PID_MAX
from tests.test_pid_generation import _set_sequence_value

PID_RE = re.compile(r"^PID[0-9]{5}$")
PASSWORD = "project-api-tests-1!"  # pragma: allowlist secret

VALID_CREATE = {
    "name": "Tea Factory ERP",
    "repo_path": "/srv/repos/tea-factory-erp",
    "default_branch": "main",
    "system_prompt_rules": "# Rules\n\nRun the tests.",
}


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
    assert error["code"] in CANONICAL_ERROR_CODES, "catalog-closed (20.4 item 5)"
    return cast(dict[str, Any], error)


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "owner", "password": PASSWORD})
    assert response.status_code == 200, response.content
    return api


@pytest.fixture
def client(db: None) -> APIClient:
    """An unauthenticated client (the `plain` caller)."""
    return APIClient()


def _create(owner_client: APIClient, **overrides: str) -> Any:
    """POST a valid project; return the parsed 201 body."""
    payload = {**VALID_CREATE, **overrides}
    response = owner_client.post("/api/v1/projects", payload)
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
        "/api/v1/devices", {"platform": "android", "push_token": "apns-project-api"}
    )
    assert response.status_code == status.HTTP_201_CREATED, response.content
    return cast(str, response.json()["token"])


# --- creation (FR-PRJ-01) ---------------------------------------------------


def test_create_assigns_a_generated_pid_and_the_default_policy_pair(
    owner_client: APIClient,
) -> None:
    """Server-assigned PID + Section 7.2 default policy created as a pair."""
    body = _create(owner_client)

    assert PID_RE.match(body["id"]), body["id"]
    assert body["name"] == VALID_CREATE["name"]
    assert body["repo_path"] == VALID_CREATE["repo_path"]
    assert body["default_branch"] == VALID_CREATE["default_branch"]
    assert body["system_prompt_rules"] == VALID_CREATE["system_prompt_rules"]
    assert body["active_status"] == "active"  # FR-PRJ-04 default
    assert body["task_counter"] == 0
    assert body["created_at"] <= body["updated_at"]

    policy = ProjectPolicy.objects.get(pk=body["agent_policy"])
    assert policy.lease_duration_minutes == 45  # Section 7.2 defaults
    assert policy.max_retries == 3
    assert policy.branch_prefix == "feat/{PID}-"  # G-09
    assert policy.audit_required_default is True
    assert policy.project.pk == body["id"]  # the 1:1 pair (Section 7.1)


def test_create_rejects_a_client_supplied_id(owner_client: APIClient) -> None:
    """FR-PRJ-01: the id is never client-chosen — unknown key, not ignored."""
    response = owner_client.post("/api/v1/projects", {**VALID_CREATE, "id": "PID99999"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"
    assert "id" in response.json()["error"]["details"]

    from apps.projects.models import Project

    assert not Project.objects.filter(pk="PID99999").exists()
    assert Project.objects.count() == 0, "the rejected request created nothing"


def test_create_requires_the_section_9_2_inputs(owner_client: APIClient) -> None:
    """Missing fields are catalog validation errors, not 500s."""
    response = owner_client.post("/api/v1/projects", {"name": "Only a name"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(response)["code"] == "VALIDATION_ERROR"


# --- read / patch round-trip (FR-PRJ-02) ------------------------------------


def test_fetch_round_trips_every_fr_prj_02_field(owner_client: APIClient) -> None:
    """GET returns the full Section 7.2 field set with the stored values."""
    created = _create(owner_client)
    response = owner_client.get(f"/api/v1/projects/{created['id']}")
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert set(body) == {
        "id",
        "name",
        "repo_path",
        "active_status",
        "default_branch",
        "system_prompt_rules",
        "agent_policy",
        "task_counter",
        "created_at",
        "updated_at",
    }
    for key in ("id", "name", "repo_path", "default_branch", "system_prompt_rules"):
        assert body[key] == created[key], key


def test_patch_updates_each_mutable_fr_prj_02_field(owner_client: APIClient) -> None:
    """PATCH round-trips every mutable field; server-managed ones hold."""
    created = _create(owner_client)
    updates = {
        "name": "Tea Factory ERP v2",
        "repo_path": "/srv/repos/tea-erp-moved",
        "default_branch": "develop",
        "system_prompt_rules": "# New rules",
    }
    response = owner_client.patch(f"/api/v1/projects/{created['id']}", updates)
    assert response.status_code == status.HTTP_200_OK, response.content
    body = response.json()
    for key, value in updates.items():
        assert body[key] == value, key
    assert body["id"] == created["id"]  # immutable (Section 7.3/7.4)
    assert body["task_counter"] == created["task_counter"]
    assert body["created_at"] == created["created_at"]
    assert body["updated_at"] >= created["updated_at"]

    # Partial: patching one field leaves the others at their current values.
    again = owner_client.patch(f"/api/v1/projects/{created['id']}", {"name": "Third name"})
    assert again.status_code == status.HTTP_200_OK
    assert again.json()["name"] == "Third name"
    assert again.json()["default_branch"] == "develop"


def test_status_cycles_through_all_three_canonical_values(owner_client: APIClient) -> None:
    """FR-PRJ-04: active → paused → archived → active; nothing else exists."""
    created = _create(owner_client)
    pid = created["id"]
    for value in ("paused", "archived", "active"):
        response = owner_client.patch(f"/api/v1/projects/{pid}", {"active_status": value})
        assert response.status_code == status.HTTP_200_OK, response.content
        assert response.json()["active_status"] == value

    rejected = owner_client.patch(f"/api/v1/projects/{pid}", {"active_status": "stopped"})
    assert rejected.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(rejected)["code"] == "VALIDATION_ERROR"


def test_patch_rejects_id_changes_and_unknown_fields(owner_client: APIClient) -> None:
    """Id immutability at the boundary: the key is rejected, not rewritten."""
    created = _create(owner_client)
    pid = created["id"]

    id_change = owner_client.patch(f"/api/v1/projects/{pid}", {"id": "PID99999"})
    assert id_change.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(id_change)["code"] == "VALIDATION_ERROR"

    typo = owner_client.patch(f"/api/v1/projects/{pid}", {"namee": "typo"})
    assert typo.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(typo)["code"] == "VALIDATION_ERROR"

    assert owner_client.get(f"/api/v1/projects/{pid}").json()["name"] == VALID_CREATE["name"]


# --- boundary ids (Section 7.3; MT-1.3-03 risk note) ------------------------


def test_malformed_and_unknown_pid_answer_catalog_codes(owner_client: APIClient) -> None:
    """Both land on VALIDATION_ERROR/400 — no PROJECT_NOT_FOUND exists."""
    malformed = owner_client.get("/api/v1/projects/PID12")
    assert malformed.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(malformed)["code"] == "VALIDATION_ERROR"
    assert "pid" in malformed.json()["error"]["details"]

    unknown = owner_client.get("/api/v1/projects/PID99999")
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"

    # Same answers on the addressed write path.
    patch_unknown = owner_client.patch("/api/v1/projects/PID99999", {"name": "x"})
    assert patch_unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(patch_unknown)["code"] == "VALIDATION_ERROR"


# --- Section 12.2 callers + ADR-004 against real rows -----------------------


def test_non_owner_credentials_receive_catalog_authorization_codes(
    owner_client: APIClient, client: APIClient
) -> None:
    """Owner-only: ROLE_NOT_PERMITTED for wrong roles, AUTH_REQUIRED for none."""
    created = _create(owner_client)
    pid = created["id"]
    agent_token = _issue_agent_token(owner_client, pid)
    device_token = _register_device(owner_client)
    agent = {"Authorization": f"Bearer {agent_token}"}
    device = {"Authorization": f"Bearer {device_token}"}

    # Scope matches (the token's own project) → role check decides.
    for path in ("/api/v1/projects", f"/api/v1/projects/{pid}"):
        denied = client.get(path, headers=agent)
        assert denied.status_code == status.HTTP_403_FORBIDDEN, path
        assert _envelope(denied)["code"] == "ROLE_NOT_PERMITTED", path

    device_denied = client.get(f"/api/v1/projects/{pid}", headers=device)
    assert device_denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(device_denied)["code"] == "ROLE_NOT_PERMITTED"

    agent_post = client.post("/api/v1/projects", VALID_CREATE, headers=agent)
    assert agent_post.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(agent_post)["code"] == "ROLE_NOT_PERMITTED"

    anonymous = client.get(f"/api/v1/projects/{pid}")
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"


def test_agent_token_for_one_project_is_forbidden_on_another(
    owner_client: APIClient, client: APIClient
) -> None:
    """ADR-004 zero-bleed on the real registry: PID-A token vs PID-B row."""
    project_a = _create(owner_client, name="Project A")
    project_b = _create(owner_client, name="Project B")
    agent_token = _issue_agent_token(owner_client, project_a["id"])
    agent = {"Authorization": f"Bearer {agent_token}"}

    own = client.get(f"/api/v1/projects/{project_a['id']}", headers=agent)
    assert own.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(own)["code"] == "ROLE_NOT_PERMITTED"

    other = client.get(f"/api/v1/projects/{project_b['id']}", headers=agent)
    assert other.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(other)["code"] == "AUTH_FORBIDDEN_PROJECT"


# --- list pagination (MT-0.5-04 / pagination.md) ----------------------------


def test_list_pagination_follows_the_cursor_envelope_shape(owner_client: APIClient) -> None:
    """Two-member envelope, canonical params, stable id-ascending order."""
    first = _create(owner_client, name="First")
    second = _create(owner_client, name="Second")
    third = _create(owner_client, name="Third")

    page_one = owner_client.get("/api/v1/projects", {"page_size": 2})
    assert page_one.status_code == status.HTTP_200_OK
    body_one = page_one.json()
    assert set(body_one) == {"results", "next_cursor"}, "pagination.md envelope"
    assert len(body_one["results"]) == 2
    assert body_one["next_cursor"], "more pages exist"
    ids_one = [row["id"] for row in body_one["results"]]
    assert ids_one == sorted(ids_one), "documented sort: project id ascending"
    assert {first["id"], second["id"], third["id"]} >= set(ids_one)

    page_two = owner_client.get(
        "/api/v1/projects",
        {"page_size": 2, "cursor": body_one["next_cursor"]},
    )
    assert page_two.status_code == status.HTTP_200_OK
    body_two = page_two.json()
    assert set(body_two) == {"results", "next_cursor"}
    assert len(body_two["results"]) == 1
    assert body_two["next_cursor"] is None, "end of list (null cursor)"
    assert body_two["results"][0]["id"] not in ids_one

    # Every listed row survives the full round of pages exactly once.
    listed = ids_one + [body_two["results"][0]["id"]]
    assert sorted(listed) == sorted([first["id"], second["id"], third["id"]])


def test_list_rejects_a_malformed_cursor_and_bad_page_size(owner_client: APIClient) -> None:
    """Cursor opacity: a hand-mangled cursor is a catalog validation error."""
    bad_cursor = owner_client.get("/api/v1/projects", {"cursor": "not-base64!!"})
    assert bad_cursor.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(bad_cursor)["code"] == "VALIDATION_ERROR"

    bad_size = owner_client.get("/api/v1/projects", {"page_size": 0})
    assert bad_size.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(bad_size)["code"] == "VALIDATION_ERROR"


# --- Section 7.3 exhaustion over the wire (declared 500 on POST) ------------


def test_sequence_exhaustion_answers_the_declared_catalog_500(
    owner_client: APIClient,
) -> None:
    """Capacity spent → PidSequenceExhausted renders SERVER_ERROR, 500."""
    _set_sequence_value(PID_MAX)
    response = owner_client.post("/api/v1/projects", VALID_CREATE)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    error = _envelope(response)
    assert error["code"] == "SERVER_ERROR"
    assert error["retryable"] is True  # 5xx rule (apps/core/exceptions.py)
    assert "99,999" in error["message"]
