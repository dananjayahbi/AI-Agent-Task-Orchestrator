"""MT-3.2-02 — patch artifact storage with the 5 MB cap (Sections 7.2/9.7/9.10).

Run with ``pytest backend/tests -k patch_artifacts -q``:

* the round trip — store through the real submission, serve through
  ``GET /resolutions/{id}/patch``: byte-identical body, server-computed
  ``sha256``/``size_bytes`` (never trusted from the client), the
  content-derived key under the configured backend (Section 9.10 — the
  suite runs on a per-test ``MEDIA_ROOT``, nothing environment-specific
  committed);
* the **inclusive** cap boundary (MT-3.2-02 risk note's recorded
  reading): a patch of exactly 5 MB stores fully, one byte more takes
  the degraded path;
* the oversize path end to end — 201 (a degraded path, **not** an
  error), stats and file list still recorded from the received bytes,
  no body stored, and the Section 9.7 "diff too large" marker served
  by the patch GET (no new error codes anywhere — Section 20.4 item 5).
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.attachments.storage import get_storage
from apps.projects.models import Project
from apps.tasks.models import Task, TaskArtifact, TaskResolution, TaskState
from apps.tasks.services.resolutions import (
    DIFF_TOO_LARGE_MARKER,
    PATCH_MAX_BYTES,
    patch_storage_key,
    store_patch_artifact,
)

from .wp32_helpers import (  # noqa: F401  (autouse fixtures promoted)
    SAMPLE_PATCH,
    active_policy_project,
    agent_client,
    claimed_task,
    issue_agent_token,
    local_storage,
    login_owner,
    make_task,
    restore_submission_registry,
    submission_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport) for token minting."""
    return login_owner()


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _coder(owner_client: APIClient, project: Project) -> APIClient:
    return agent_client(issue_agent_token(owner_client, project.pk, "coder"))


def _submit(client: APIClient, task: Task, patch: str = SAMPLE_PATCH) -> Any:
    return client.post(
        f"/api/v1/tasks/{task.pk}/resolution",
        submission_body(patch=patch),
        format="json",
    )


# --- round trip: sha256, size, key, served bytes -----------------------------


def test_round_trip_stores_and_serves_the_exact_bytes(
    owner_client: APIClient, project: Project
) -> None:
    """Store → artifact row → serve: identical body, server-side digest."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(agent, task)
    assert response.status_code == 201, response.content
    resolution = TaskResolution.objects.get(pk=response.json()["resolution"]["id"])
    artifact = TaskArtifact.objects.get(resolution=resolution, kind="patch")

    expected_sha = hashlib.sha256(SAMPLE_PATCH.encode("utf-8")).hexdigest()
    assert artifact.sha256 == expected_sha, "server-computed over the stored bytes"
    assert artifact.size_bytes == len(SAMPLE_PATCH.encode("utf-8"))
    assert artifact.storage_key == patch_storage_key(expected_sha)
    assert artifact.storage_key.startswith(f"objects/{expected_sha[:2]}/")
    assert get_storage().exists(artifact.storage_key), "through the configured backend"

    served = agent.get(f"/api/v1/resolutions/{resolution.pk}/patch")
    assert served.status_code == 200
    body = served.json()
    assert body["sha256"] == expected_sha
    assert body["size_bytes"] == artifact.size_bytes
    assert body["diff_too_large"] is False
    assert body["marker"] is None
    assert body["patch"].encode("utf-8") == SAMPLE_PATCH.encode("utf-8")


def test_artifact_row_matches_the_section_7_2_field_set(
    owner_client: APIClient, project: Project
) -> None:
    """id, resolution_id, kind, storage_key, size_bytes, sha256 — no extras."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**", "docs/**"])

    response = _submit(agent, task)
    artifact = TaskArtifact.objects.get(resolution__pk=response.json()["resolution"]["id"])
    fields = {field.name for field in TaskArtifact._meta.get_fields()}
    assert {"resolution", "kind", "storage_key", "size_bytes", "sha256"} <= fields
    assert artifact.kind == "patch"


def test_exact_cap_boundary_stores_fully(project: Project) -> None:
    """Exactly 5 MB (inclusive) stores its body — the recorded reading."""
    task = make_task(project, 99, state=TaskState.IN_PROGRESS)
    resolution = TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name="feat/boundary",
        commit_sha="b" * 40,
        execution_summary="boundary",
    )
    patch = "a" * PATCH_MAX_BYTES

    artifact = store_patch_artifact(resolution, patch)

    assert artifact.size_bytes == PATCH_MAX_BYTES
    assert artifact.storage_key, "at the cap the body is stored"
    assert get_storage().exists(artifact.storage_key)
    assert get_storage().get(artifact.storage_key) == patch.encode("utf-8")


def test_one_byte_over_the_cap_takes_the_degraded_path(project: Project) -> None:
    """5 MB + 1: no body, no error — the marker path MT-3.2-02 records."""
    task = make_task(project, 98, state=TaskState.IN_PROGRESS)
    resolution = TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name="feat/oversize",
        commit_sha="c" * 40,
        execution_summary="oversize",
    )
    patch = "a" * (PATCH_MAX_BYTES + 1)

    artifact = store_patch_artifact(resolution, patch)

    assert artifact.size_bytes == PATCH_MAX_BYTES + 1
    assert artifact.storage_key == "", "no body is stored"
    assert get_storage().exists(patch_storage_key(artifact.sha256)) is False


# --- oversize end to end through the API -------------------------------------

OVERSIZE_PREFIX = (
    "diff --git a/src/big.py b/src/big.py\n"
    "--- a/src/big.py\n"
    "+++ b/src/big.py\n"
    "@@ -1,1 +1,3 @@\n"
    " keep\n"
    "+new line\n"
    "+"
)


def _oversize_patch() -> str:
    """A parseable diff whose body exceeds the Section 9.7 cap."""
    return OVERSIZE_PREFIX + "y" * (PATCH_MAX_BYTES + 16) + "\n"


def test_oversize_submission_is_degraded_not_an_error(
    owner_client: APIClient, project: Project
) -> None:
    """201 with stats/file list recorded; no body, marker on the GET."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**"])
    patch = _oversize_patch()

    response = _submit(agent, task, patch=patch)
    assert response.status_code == 201, response.content
    resolution_payload = response.json()["resolution"]
    # Stats and file list survived the degraded path (Section 9.7).
    assert resolution_payload["changed_files"] == ["src/big.py"]
    assert resolution_payload["diff_summary"] == {
        "files": 1,
        "insertions": 2,
        "deletions": 0,
    }

    resolution = TaskResolution.objects.get(pk=resolution_payload["id"])
    artifact = TaskArtifact.objects.get(resolution=resolution, kind="patch")
    assert artifact.size_bytes > PATCH_MAX_BYTES
    assert artifact.storage_key == ""
    assert artifact.sha256 == hashlib.sha256(patch.encode("utf-8")).hexdigest()

    served = agent.get(f"/api/v1/resolutions/{resolution.pk}/patch")
    assert served.status_code == 200, "the marker is a served state, not an error"
    body = served.json()
    assert body["diff_too_large"] is True
    assert body["patch"] is None
    assert body["marker"] == DIFF_TOO_LARGE_MARKER == "diff too large"
    assert body["size_bytes"] == artifact.size_bytes
    assert body["sha256"] == artifact.sha256


def test_oversize_introduces_no_new_error_codes(owner_client: APIClient, project: Project) -> None:
    """Section 20.4 item 5: the degraded path answers 201, catalog untouched."""
    agent = _coder(owner_client, project)
    task = claimed_task(project, 1, target_scope=["src/**"])
    response = _submit(agent, task, patch=_oversize_patch())
    assert response.status_code == 201
    assert set(response.json()) == {
        "resolution",
        "task",
        "trigger",
        "scope_violations",
    }
