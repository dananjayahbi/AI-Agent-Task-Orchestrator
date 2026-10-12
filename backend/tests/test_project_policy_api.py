"""MT-1.3-04 — policy read/patch endpoints (Sections 9.2, 7.2; FR-PRJ-05).

The MT's test command against the running API:

* ``GET`` equals the Section 7.2 defaults for a fresh project (the literal
  table, imported from ``test_project_models`` so there is one drift
  detector, not two);
* ``PATCH max_retries`` changes **only** that field (partial semantics —
  defaults are never silently rewritten);
* invalid enums/bounds/empties and unknown fields answer
  ``VALIDATION_ERROR`` — validated exactly as far as Section 7.2 states and
  no further (risk note: no invented hard policy);
* non-owner credentials answer ``ROLE_NOT_PERMITTED`` /
  ``AUTH_FORBIDDEN_PROJECT`` / ``AUTH_REQUIRED`` (Section 12.2, ADR-004).

Run with ``pytest backend/tests/test_project_policy_api.py`` (MT test
command).
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project
from tests.test_project_api import (  # shared API helpers (one definition)
    _create,
    _envelope,
    _issue_agent_token,
    _register_device,
)
from tests.test_project_models import POLICY_DEFAULTS

PASSWORD = "project-policy-tests-1!"  # pragma: allowlist secret


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("policy-owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "policy-owner", "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


@pytest.fixture
def client(db: None) -> APIClient:
    """An unauthenticated client (the `plain` caller)."""
    return APIClient()


def _policy_url(owner_client: APIClient, **overrides: str) -> str:
    """Create a project and return its policy path."""
    project = _create(owner_client, **overrides)
    return f"/api/v1/projects/{project['id']}/policy"


def _get(owner_client: APIClient, url: str) -> dict[str, Any]:
    response = owner_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.content
    return cast(dict[str, Any], response.json())


def _patch(owner_client: APIClient, url: str, body: dict[str, Any]) -> Any:
    # JSON bodies: the API's real content type — multipart silently drops
    # empty-list values, which would hide the allow_empty validation.
    return owner_client.patch(url, body, format="json")


# --- GET: full coverage of the Section 7.2 table ----------------------------


def test_get_returns_every_section_7_2_field_at_its_documented_default(
    owner_client: APIClient,
) -> None:
    """FR-PRJ-05 field coverage: the fresh-policy GET is the plan table."""
    url = _policy_url(owner_client)
    body = _get(owner_client, url)
    assert set(body) == set(POLICY_DEFAULTS), "no field added or dropped (7.2)"
    for name, expected in POLICY_DEFAULTS.items():
        assert body[name] == expected, name


# --- PATCH: partial semantics ------------------------------------------------


def test_patch_of_one_field_leaves_every_other_field_untouched(
    owner_client: APIClient,
) -> None:
    """Patching max_retries rewrites nothing else (MT AC: no silent reset)."""
    url = _policy_url(owner_client)
    before = _get(owner_client, url)

    response = _patch(owner_client, url, {"max_retries": 7})
    assert response.status_code == status.HTTP_200_OK, response.content

    after = _get(owner_client, url)
    changed = {key for key in before if before[key] != after[key]}
    assert changed == {"max_retries"}
    assert after["max_retries"] == 7


def test_patch_accepts_the_per_project_extension_mode_option(
    owner_client: APIClient,
) -> None:
    """OQ-04: checkpoint_and_liveness is accepted as a per-project value."""
    url = _policy_url(owner_client)
    response = _patch(owner_client, url, {"lease_extension_mode": "checkpoint_and_liveness"})
    assert response.status_code == status.HTTP_200_OK, response.content
    assert response.json()["lease_extension_mode"] == "checkpoint_and_liveness"
    assert response.json()["lease_extension_mode"] != "checkpoint_only"  # default


# --- PATCH: enums, bounds, empties, unknown keys ----------------------------


def test_patch_rejects_invalid_enum_values(owner_client: APIClient) -> None:
    """Closed vocabularies: anything outside Section 7.2 is a 400."""
    url = _policy_url(owner_client)
    for body in (
        {"merge_strategy": "rebase"},
        {"lease_extension_mode": "always"},
    ):
        response = _patch(owner_client, url, body)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, body
        assert _envelope(response)["code"] == "VALIDATION_ERROR", body


def test_patch_enforces_only_the_bounds_section_7_2_states(owner_client: APIClient) -> None:
    """Positive durations/retries/thresholds, confidence 1-5, concurrency >= 0."""
    url = _policy_url(owner_client)

    rejected: dict[str, Any] = {
        "lease_duration_minutes": 0,
        "lease_max_total_minutes": 0,
        "max_retries": 0,
        "autonomous_diff_threshold_lines": 0,
        "stalled_after_minutes": 0,
        "auditor_min_confidence": 0,
    }
    for field, value in rejected.items():
        response = _patch(owner_client, url, {field: value})
        assert response.status_code == status.HTTP_400_BAD_REQUEST, field
        assert _envelope(response)["code"] == "VALIDATION_ERROR", field

    above = _patch(owner_client, url, {"auditor_min_confidence": 6})
    assert above.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(above)["code"] == "VALIDATION_ERROR"

    # The endpoints of the stated ranges and G-26's >= 0 all pass.
    assert _patch(owner_client, url, {"auditor_min_confidence": 1}).status_code == 200
    assert _patch(owner_client, url, {"auditor_min_confidence": 5}).status_code == 200
    assert _patch(owner_client, url, {"max_concurrent_tasks": 0}).status_code == 200
    assert _patch(owner_client, url, {"max_concurrent_tasks": 1}).status_code == 200


def test_patch_rejects_unknown_fields_and_type_errors(owner_client: APIClient) -> None:
    """Unknown keys are rejected, never ignored; wrong types are 400s."""
    url = _policy_url(owner_client)
    before = _get(owner_client, url)

    unknown = _patch(owner_client, url, {"max_retrys": 9})
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"
    assert "max_retrys" in unknown.json()["error"]["details"]
    assert _get(owner_client, url) == before, "the rejected patch changed nothing"

    wrong_type = _patch(owner_client, url, {"max_retries": "many"})
    assert wrong_type.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(wrong_type)["code"] == "VALIDATION_ERROR"


def test_patch_requires_non_empty_prefix_and_glob_lists(owner_client: APIClient) -> None:
    """When supplied: prefix non-empty, each glob list non-empty, items non-blank."""
    url = _policy_url(owner_client)

    invalid_bodies: list[dict[str, Any]] = [
        {"branch_prefix": ""},
        {"critical_path_globs": []},
        {"critical_path_globs": [""]},
        {"migration_path_globs": []},
        {"sensitive_config_globs": []},
    ]
    for body in invalid_bodies:
        response = _patch(owner_client, url, body)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, body
        assert _envelope(response)["code"] == "VALIDATION_ERROR", body

    ok = _patch(
        owner_client,
        url,
        {"branch_prefix": "chore/{PID}-", "critical_path_globs": ["infra/*"]},
    )
    assert ok.status_code == status.HTTP_200_OK, ok.content
    assert ok.json()["branch_prefix"] == "chore/{PID}-"
    assert ok.json()["critical_path_globs"] == ["infra/*"]


# --- Section 12.2 callers + ADR-004 (MT AC) ---------------------------------


def test_policy_endpoint_is_owner_only_with_catalog_codes(
    owner_client: APIClient, client: APIClient
) -> None:
    """GET admits §9.2's agent read cell; PATCH stays Owner-only."""
    project_a = _create(owner_client, name="Policy A")
    project_b = _create(owner_client, name="Policy B")
    url_a = f"/api/v1/projects/{project_a['id']}/policy"
    url_b = f"/api/v1/projects/{project_b['id']}/policy"

    agent_token = _issue_agent_token(owner_client, project_a["id"])
    agent = {"Authorization": f"Bearer {agent_token}"}
    device = {"Authorization": f"Bearer {_register_device(owner_client)}"}

    # Scope matches → the caller cell decides: the agent reads its own
    # project's policy (§9.2 "agents read-only for own project"), while
    # every write still hits the Manage-projects Owner cell.
    read = client.get(url_a, headers=agent)
    assert read.status_code == status.HTTP_200_OK
    assert read.json()["branch_prefix"]  # the real Section 7.2 payload

    patch_denied = client.patch(url_a, {"max_retries": 9}, headers=agent, format="json")
    assert patch_denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(patch_denied)["code"] == "ROLE_NOT_PERMITTED"

    # Scope mismatch → zero-bleed outranks the role error (ADR-004).
    cross = client.get(url_b, headers=agent)
    assert cross.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(cross)["code"] == "AUTH_FORBIDDEN_PROJECT"

    # Devices are not in the read cell.
    device_denied = client.get(url_a, headers=device)
    assert device_denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(device_denied)["code"] == "ROLE_NOT_PERMITTED"

    anonymous = client.get(url_a)
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"


def test_policy_route_shares_the_project_pid_boundary_answers(
    owner_client: APIClient,
) -> None:
    """Malformed and unknown pid: the same catalog answer as the CRUD routes."""
    malformed = owner_client.get("/api/v1/projects/PID12/policy")
    assert malformed.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(malformed)["code"] == "VALIDATION_ERROR"

    unknown = owner_client.get("/api/v1/projects/PID99999/policy")
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"


def test_patches_persist_across_requests(owner_client: APIClient) -> None:
    """The write path is durable: later GET and ORM reads see the values."""
    project = _create(owner_client)
    url = f"/api/v1/projects/{project['id']}/policy"
    _patch(owner_client, url, {"max_retries": 5, "auto_complete_enabled": False})

    body = _get(owner_client, url)
    assert body["max_retries"] == 5
    assert body["auto_complete_enabled"] is False

    stored = Project.objects.get(pk=project["id"]).agent_policy
    assert stored.max_retries == 5
    assert stored.auto_complete_enabled is False
    assert stored.branch_prefix == "feat/{PID}-"  # untouched default (G-09)
