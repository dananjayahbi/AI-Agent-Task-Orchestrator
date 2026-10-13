"""MT-3.1-01 — the Section 7.2 policy table persists, round-trips, defaults stable (WP-3.1).

The MT's test battery (``pytest backend/tests -k project_policy`` runs
this file together with WP-1.3's ``test_project_policy_api``):

* every one of the Section 7.2 fields accepts a full-table PATCH round
  trip — no field added, dropped or renamed by WP-3.1 (the ``15`` fields
  the plan table enumerates; the MT text's "16" is a counting slip —
  the table is authoritative, recorded in the changelog);
* fresh policies keep the literal defaults, including the three glob
  triples — WP-3.1 widens validation, never the values (drift detector
  imported from ``test_project_models`` so there is one source, not two);
* ``lease_extension_mode`` stays ``checkpoint_only`` after unrelated
  edits (the MT AC's explicit callout);
* agent credentials stay read-only on the policy (GET yes, PATCH
  ``ROLE_NOT_PERMITTED``);
* a policy row constructed the way pre-WP-3.1 rows were (bare ORM create
  — the migration-backfill shape: model defaults applied to an existing
  project) renders the identical table through the API.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.projects.models import Project, ProjectPolicy
from apps.projects.models.policy import (
    CRITICAL_PATH_GLOBS_DEFAULT,
    MIGRATION_PATH_GLOBS_DEFAULT,
    SENSITIVE_CONFIG_GLOBS_DEFAULT,
)
from tests.test_project_api import _create, _envelope, _issue_agent_token
from tests.test_project_models import POLICY_DEFAULTS

PASSWORD = "project-policy-tests-1!"  # pragma: allowlist secret

# Every field set to a legal non-default value: the full-table round trip.
NON_DEFAULT_TABLE: dict[str, Any] = {
    "lease_duration_minutes": 30,
    "lease_max_total_minutes": 180,
    "lease_extension_mode": "checkpoint_and_liveness",
    "max_retries": 5,
    "max_concurrent_tasks": 2,
    "autonomous_diff_threshold_lines": 100,
    "auditor_min_confidence": 2,
    "critical_path_globs": ["infra/**"],
    "migration_path_globs": ["db/schema.rb"],
    "sensitive_config_globs": [".env*"],
    "auto_complete_enabled": False,
    "merge_strategy": "merge_commit",
    "branch_prefix": "chore/{PID}-",
    "audit_required_default": False,
    "stalled_after_minutes": 10,
}


@pytest.fixture
def owner_client(db: None) -> APIClient:
    """A logged-in owner session (cookie transport)."""
    from apps.accounts.models import User

    User.objects.create_user("policy-fields-owner", None, PASSWORD)
    api = APIClient()
    response = api.post(
        "/api/v1/auth/login",
        {"username": "policy-fields-owner", "password": PASSWORD},
    )
    assert response.status_code == status.HTTP_200_OK, response.content
    return api


def _get(owner_client: APIClient, url: str) -> dict[str, Any]:
    response = owner_client.get(url)
    assert response.status_code == status.HTTP_200_OK, response.content
    return cast(dict[str, Any], response.json())


def test_full_table_round_trips_through_patch_and_get(owner_client: APIClient) -> None:
    """All 15 fields accept a non-default write and read back verbatim."""
    project = _create(owner_client)
    url = f"/api/v1/projects/{project['id']}/policy"

    wrote = owner_client.patch(url, NON_DEFAULT_TABLE, format="json")
    assert wrote.status_code == status.HTTP_200_OK, wrote.content
    after_write = _get(owner_client, url)
    assert set(after_write) == set(POLICY_DEFAULTS), "no field added or dropped (7.2)"
    for name, expected in NON_DEFAULT_TABLE.items():
        assert after_write[name] == expected, name

    # And back: the stock table itself is a valid full-body patch, so the
    # defaults round-trip in the other direction too.
    restored = owner_client.patch(url, POLICY_DEFAULTS, format="json")
    assert restored.status_code == status.HTTP_200_OK, restored.content
    assert _get(owner_client, url) == POLICY_DEFAULTS


def test_fresh_policy_keeps_the_documented_defaults_including_globs(
    owner_client: APIClient,
) -> None:
    """WP-3.1 changes validation, never the default values (compat rule)."""
    project = _create(owner_client)
    body = _get(owner_client, f"/api/v1/projects/{project['id']}/policy")

    assert body == POLICY_DEFAULTS
    assert body["critical_path_globs"] == CRITICAL_PATH_GLOBS_DEFAULT
    assert body["migration_path_globs"] == MIGRATION_PATH_GLOBS_DEFAULT
    assert body["sensitive_config_globs"] == SENSITIVE_CONFIG_GLOBS_DEFAULT


def test_lease_extension_mode_stays_checkpoint_only(owner_client: APIClient) -> None:
    """MT AC: checkpoint_only is the default and survives unrelated edits."""
    project = _create(owner_client)
    url = f"/api/v1/projects/{project['id']}/policy"

    assert _get(owner_client, url)["lease_extension_mode"] == "checkpoint_only"
    patched = owner_client.patch(url, {"max_retries": 2}, format="json")
    assert patched.status_code == status.HTTP_200_OK, patched.content
    assert _get(owner_client, url)["lease_extension_mode"] == "checkpoint_only"


def test_agent_credentials_are_read_only_on_the_policy(owner_client: APIClient) -> None:
    """MT AC: agent tokens read their own project's policy; writes are refused."""
    project = _create(owner_client)
    url = f"/api/v1/projects/{project['id']}/policy"
    agent_token = _issue_agent_token(owner_client, project["id"])
    agent = {"Authorization": f"Bearer {agent_token}"}
    plain = APIClient()

    read = plain.get(url, headers=agent)
    assert read.status_code == status.HTTP_200_OK, read.content
    assert read.json()["lease_duration_minutes"] == 45

    denied = plain.patch(url, {"max_retries": 9}, headers=agent, format="json")
    assert denied.status_code == status.HTTP_403_FORBIDDEN
    assert _envelope(denied)["code"] == "ROLE_NOT_PERMITTED"


def test_backfilled_rows_render_the_same_defaults(owner_client: APIClient) -> None:
    """MT AC: rows from before WP-3.1 carry the defaults (migration shape).

    A bare ``ProjectPolicy.objects.create()`` is exactly what migration
    0002 wrote for pre-existing projects: model defaults, no WP-3.1 data
    fix-up needed because the fields and defaults are unchanged.
    """
    policy = ProjectPolicy.objects.create()
    project = Project.objects.create(
        id="PID00997",
        name="Backfilled",
        repo_path="/srv/repos/backfilled",
        default_branch="main",
        agent_policy=policy,
    )

    body = _get(owner_client, f"/api/v1/projects/{project.pk}/policy")
    assert body == POLICY_DEFAULTS
