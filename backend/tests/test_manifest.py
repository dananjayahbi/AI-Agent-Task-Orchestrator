"""MT-1.3-05 — manifest schema, renderer and endpoint (Sections 10.3, 9.2).

WP-1.3 acceptance, executable: **generated manifests pass validation
against the published schema** — for a fresh *and* a customized project —
the output carries exactly the Section 10.3 allowlisted keys (FR-SEC-04:
no secret can fit, and the schema itself would reject an injected key),
rendered values come from their plan sources (`auto_branch_prefix` from
policy/G-09, `orchestrator_api` from configuration/NFR-06,
`audit_required_default` from policy), and `GET /projects/{pid}/manifest`
is Owner-only with catalog codes.

Run with ``pytest backend/tests/test_manifest.py`` (MT test command).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import jsonschema
import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project, ProjectPolicy
from apps.projects.services.manifest import render_manifest, resolve_branch_prefix
from tests.test_project_api import (  # shared API helpers (one definition)
    _create,
    _envelope,
    _issue_agent_token,
    _register_device,
)

# The published schema (repository-local reference — MT-1.3-05 records the
# filename choice `schemas/manifest.v1.json`, matching the plan's URL path).
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "manifest.v1.json"

# The Section 10.3 example, key for key — the allowlist a rendered manifest
# must equal exactly (FR-SEC-04; written independently of both the renderer
# and the schema so it detects drift in either).
SECTION_10_3_KEYS = frozenset(
    {
        "$schema",
        "schema_version",
        "project_id",
        "project_name",
        "orchestrator_api",
        "default_branch",
        "auto_branch_prefix",
        "audit_required_default",
        "agent_hints",
    }
)

# The required subset the plan states (MT: "nothing required beyond it").
SECTION_10_3_REQUIRED = (
    "schema_version",
    "project_id",
    "project_name",
    "orchestrator_api",
    "default_branch",
    "auto_branch_prefix",
    "audit_required_default",
)

PASSWORD = "manifest-tests-1!"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def manifest_schema() -> dict[str, Any]:
    """The published schemas/manifest.v1.json document."""
    assert SCHEMA_PATH.is_file(), f"manifest schema must be published at {SCHEMA_PATH}"
    return cast(dict[str, Any], json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def _make_project(
    pid: str = "PID00007",
    name: str = "Tea Factory ERP",
    **policy_overrides: Any,
) -> Project:
    """A registry row with explicit id (never the sequence) + policy."""
    policy = ProjectPolicy.objects.create(**policy_overrides)
    return Project.objects.create(
        id=pid,
        name=name,
        repo_path="/srv/repos/tea-factory-erp",
        default_branch="main",
        agent_policy=policy,
    )


# --- the published schema (MT AC: matches Section 10.3 key-for-key) ---------


def test_published_schema_matches_the_section_10_3_contract(
    manifest_schema: dict[str, Any],
) -> None:
    """Required keys, types and the no-extra-keys guarantee — nothing more."""
    assert manifest_schema["type"] == "object"
    assert tuple(manifest_schema["required"]) == SECTION_10_3_REQUIRED
    assert manifest_schema["additionalProperties"] is False, "FR-SEC-04 allowlist"
    assert set(manifest_schema["properties"]) == SECTION_10_3_KEYS
    assert manifest_schema["properties"]["schema_version"]["const"] == 1
    assert manifest_schema["properties"]["project_id"]["pattern"] == "^PID[0-9]{5}$"

    hints = manifest_schema["properties"]["agent_hints"]
    assert hints["additionalProperties"] is False
    assert set(hints["properties"]) == {"test_command_default", "worktree_mode"}
    assert manifest_schema["$id"].endswith("/schemas/manifest.v1.json")


# --- the renderer (WP-1.3 acceptance: generated manifest validates) ---------


def test_manifest_for_a_fresh_project_validates_against_the_schema(
    db: None, manifest_schema: dict[str, Any]
) -> None:
    """The Section 10.3 example's own project shape (PID00007)."""
    document = render_manifest(_make_project())
    jsonschema.validate(instance=document, schema=manifest_schema)
    assert document["schema_version"] == 1
    assert document["project_id"] == "PID00007"
    assert document["project_name"] == "Tea Factory ERP"
    assert document["auto_branch_prefix"] == "feat/PID00007-"  # G-09, resolved


def test_manifest_for_a_customized_project_validates_and_carries_policy(
    db: None, manifest_schema: dict[str, Any]
) -> None:
    """Policy edits flow through: prefix, audit default, project fields."""
    project = _make_project(
        pid="PID00042",
        name="Customized",
        branch_prefix="chore/{PID}-",
        audit_required_default=False,
    )
    project.default_branch = "develop"
    project.save()

    document = render_manifest(project)
    jsonschema.validate(instance=document, schema=manifest_schema)
    assert document["project_name"] == "Customized"
    assert document["default_branch"] == "develop"
    assert document["auto_branch_prefix"] == "chore/PID00042-"
    assert document["audit_required_default"] is False


def test_manifest_keys_equal_the_section_10_3_allowlist(db: None) -> None:
    """FR-SEC-04: the output contains only the documented keys."""
    for document in (
        render_manifest(_make_project(pid="PID00001")),
        render_manifest(
            _make_project(pid="PID00002", branch_prefix="release-", auto_complete_enabled=False)
        ),
    ):
        assert frozenset(document) == SECTION_10_3_KEYS
        assert set(document["agent_hints"]) == {"test_command_default", "worktree_mode"}


def test_the_schema_would_reject_any_key_beyond_the_allowlist(
    manifest_schema: dict[str, Any],
) -> None:
    """Proof the no-secrets guarantee is structural, not just conventional."""
    smuggled = {
        "$schema": "https://orchestrator.local/schemas/manifest.v1.json",
        "schema_version": 1,
        "project_id": "PID00007",
        "project_name": "Tea Factory ERP",
        "orchestrator_api": "http://localhost:8000/api/v1",
        "default_branch": "main",
        "auto_branch_prefix": "feat/PID00007-",
        "audit_required_default": True,
        "agent_token": "smuggled-secret",  # not in the contract
    }
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=smuggled, schema=manifest_schema)


# --- rendered values come from the plan's sources ---------------------------


def test_orchestrator_api_comes_from_configuration_not_code(
    db: None, manifest_schema: dict[str, Any]
) -> None:
    """NFR-06 / MT risk note: the value follows the environment."""
    project = _make_project(pid="PID00003")
    with override_settings(ORCHESTRATOR_API_BASE_URL="https://api.example.com/api/v1"):
        document = render_manifest(project)
        assert document["orchestrator_api"] == "https://api.example.com/api/v1"
        jsonschema.validate(instance=document, schema=manifest_schema)


def test_branch_prefix_token_resolution_helper() -> None:
    """G-09: `{PID}` resolves; a token-free prefix passes through."""
    assert resolve_branch_prefix("feat/{PID}-", "PID00007") == "feat/PID00007-"
    assert resolve_branch_prefix("release-", "PID00007") == "release-"


def test_no_secret_material_appears_in_a_rendered_manifest(db: None) -> None:
    """FR-SEC-04: the allowlist leaves no room for credentials."""
    from django.conf import settings

    document = render_manifest(_make_project(pid="PID00004"))
    serialized = json.dumps(document)
    assert frozenset(document) == SECTION_10_3_KEYS
    if settings.SECRET_KEY:
        assert settings.SECRET_KEY not in serialized
    assert "Bearer" not in serialized  # never a token credential either


# --- the endpoint (Section 9.2 caller: Owner) -------------------------------


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("manifest-owner", None, PASSWORD)
    api = APIClient()
    response = api.post("/api/v1/auth/login", {"username": "manifest-owner", "password": PASSWORD})
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


@pytest.fixture
def client(db: None) -> APIClient:
    """An unauthenticated client (the `plain` caller)."""
    return APIClient()


def test_manifest_endpoint_downloads_a_schema_valid_document(
    owner_client: APIClient, manifest_schema: dict[str, Any]
) -> None:
    """Owner GET: attachment headers + body that validates against $schema."""
    project = _create(owner_client)
    response = owner_client.get(f"/api/v1/projects/{project['id']}/manifest")
    assert response.status_code == status.HTTP_200_OK, response.content
    disposition = response["Content-Disposition"]
    assert disposition.startswith("attachment")
    assert "orchestrator.json" in disposition

    document = cast(dict[str, Any], response.json())
    jsonschema.validate(instance=document, schema=manifest_schema)
    assert document["project_id"] == project["id"]
    assert document["project_name"] == project["name"]
    assert document["orchestrator_api"]  # configuration-backed, non-empty


def test_manifest_endpoint_is_owner_only_with_catalog_codes(
    owner_client: APIClient, client: APIClient
) -> None:
    """ROLE_NOT_PERMITTED / AUTH_FORBIDDEN_PROJECT / AUTH_REQUIRED only."""
    project_a = _create(owner_client, name="Manifest A")
    project_b = _create(owner_client, name="Manifest B")
    url_a = f"/api/v1/projects/{project_a['id']}/manifest"
    url_b = f"/api/v1/projects/{project_b['id']}/manifest"

    agent_token = _issue_agent_token(owner_client, project_a["id"])
    device_token = _register_device(owner_client)
    agent = {"Authorization": f"Bearer {agent_token}"}
    device = {"Authorization": f"Bearer {device_token}"}

    role_denied = client.get(url_a, headers=agent)
    assert role_denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(role_denied)["code"] == "ROLE_NOT_PERMITTED"

    cross = client.get(url_b, headers=agent)
    assert cross.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(cross)["code"] == "AUTH_FORBIDDEN_PROJECT"

    device_denied = client.get(url_a, headers=device)
    assert device_denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(device_denied)["code"] == "ROLE_NOT_PERMITTED"

    anonymous = client.get(url_a)
    assert anonymous.status_code == status.HTTP_401_UNAUTHORIZED
    assert _envelope(anonymous)["code"] == "AUTH_REQUIRED"


def test_manifest_endpoint_shares_the_pid_boundary_answers(owner_client: APIClient) -> None:
    """Malformed and unknown pid: the documented VALIDATION_ERROR pair."""
    malformed = owner_client.get("/api/v1/projects/PID12/manifest")
    assert malformed.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(malformed)["code"] == "VALIDATION_ERROR"

    unknown = owner_client.get("/api/v1/projects/PID99999/manifest")
    assert unknown.status_code == status.HTTP_400_BAD_REQUEST
    assert _envelope(unknown)["code"] == "VALIDATION_ERROR"
