"""MT-3.8-01 — the decomposer role permission (draft-only), enforced server-side.

UC-10 / G-19 / Section 12.2: the Decomposer column of the authorization
matrix is executable here — one case per printed cell, against the real
routes with a real ``decomposer``-scoped agent token:

* **Create draft tasks — Yes**: the decomposer causes T1 only; the
  created row lands in ``draft`` with its server-allocated id and the
  ``task.created`` event (Section 8.2 T1; Section 19 WP-3.8 acceptance
  "created tasks appear as draft");
* every **No** cell that has a real endpoint answers
  ``ROLE_NOT_PERMITTED`` (403, catalog-closed): publish's class is
  exercised by the matrix probe row, both claims, submit resolution,
  submit verdict, review decisions and PATCH are refused on their live
  routes here; the merge-queue routes land with WP-3.7 (their class
  cell is walked in ``test_authorization_matrix.py``);
* the Owner / coder / auditor columns are unchanged (regressions
  asserted alongside).

The permission is the **backend** half (Section 12.2 is enforced where
tokens are validated) — the bridge's ``create_draft_task`` tool is
MT-3.8-02's separate layer over this same route.

Run with ``pytest backend/tests -k decomposer_permissions -q``.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState

from .wp15_helpers import make_project, make_task
from .wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from .wp33_helpers import (  # noqa: F401  (autouse: registry restore)
    JsonAPIClient,
    agent_client,
    issue_agent_token,
    login_owner_client,
    restore_audit_registry,
)

pytestmark = pytest.mark.django_db

CREATE_URL = "/api/v1/projects/{pid}/tasks"
CLAIM_URL = "/api/v1/tasks/{task_id}/claim"
RESOLUTION_URL = "/api/v1/tasks/{task_id}/resolution"
VERDICT_URL = "/api/v1/tasks/{task_id}/audit-verdict"
REVIEW_URL = "/api/v1/tasks/{task_id}/review"
DETAIL_URL = "/api/v1/tasks/{task_id}"

DENIED_CODE = "ROLE_NOT_PERMITTED"
PASSWORD = "wp38-tests-1!"  # pragma: allowlist secret


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the decomposer suites."""
    return make_project(name="WP-3.8 decomposer")


def _decomposer(owner_client: JsonAPIClient, project: Project) -> JsonAPIClient:
    """A project-scoped agent token carrying only the decomposer role."""
    token = issue_agent_token(owner_client, project.pk, "decomposer")
    return agent_client(token)


def _code(response: Any) -> str:
    """The catalog code of one standard envelope."""
    error = response.json()["error"]
    assert error["code"] in {
        "AUTH_REQUIRED",
        "AUTH_FORBIDDEN_PROJECT",
        "ROLE_NOT_PERMITTED",
        "VALIDATION_ERROR",
    }
    return str(error["code"])


# --- the one Yes cell: create draft tasks (T1) --------------------------------


def test_decomposer_creates_a_draft_task(owner_client: JsonAPIClient, project: Project) -> None:
    """UC-10: the decomposer's T1 — draft state, server id, task.created."""
    response = _decomposer(owner_client, project).post(
        CREATE_URL.format(pid=project.pk),
        {
            "title": "Split the report builder",
            "description": "High-level slice from the goal decomposition.",
            "acceptance_criteria": ["report renders", "tests pass"],
            "target_scope": ["src/reports/**"],
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    payload = response.json()
    assert payload["state"] == TaskState.DRAFT, "Section 19 WP-3.8: created tasks are draft"
    assert payload["version"] == 1
    assert payload["project_id"] == project.pk, "the URL decides the project (G-07)"
    assert payload["id"].startswith(f"{project.pk}-T")

    assert Event.objects.filter(task_id=payload["id"], type="task.created").exists(), (
        "T1 emits task.created (Section 8.2)"
    )


def test_decomposer_cannot_address_another_project(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """ADR-004 zero-bleed holds for the newly granted cell."""
    other = Project.objects.create(
        id="PID00098",
        name="Other",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    response = _decomposer(owner_client, project).post(
        CREATE_URL.format(pid=other.pk), {"title": "Foreign draft"}, format="json"
    )
    assert response.status_code == 403
    assert _code(response) == "AUTH_FORBIDDEN_PROJECT"


# --- every No cell with a real endpoint ---------------------------------------


def test_decomposer_is_rejected_from_every_no_cell(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 12.2's Decomposer column, one live route per printed cell."""
    decomposer = _decomposer(owner_client, project)
    pending = make_task(project, 1, state=TaskState.PENDING)
    audited = make_task(project, 2, state=TaskState.TO_BE_AUDITED, attempt_number=1)
    reviewing = make_task(project, 3, state=TaskState.IN_HUMAN_REVIEW)

    body: dict[str, Any]

    # Claim `pending` (T4) — coder cell only.
    body = {"session_id": "sess-decomposer", "worker_agent_id": "decomposer-agent"}
    response = decomposer.post(CLAIM_URL.format(task_id=pending.pk), body, format="json")
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # Claim `to_be_audited` (T11) — auditor cell only.
    body = {
        "session_id": "sess-decomposer",
        "worker_agent_id": "decomposer-agent",
        "role": "auditor",
    }
    response = decomposer.post(CLAIM_URL.format(task_id=audited.pk), body, format="json")
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # Submit resolution (T7) — coder cell only.
    body = {
        "session_id": "sess-decomposer",
        "lease_generation": 1,
        "git_branch": "feat/decomposer",
        "commit_sha": "0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        "execution_summary": "should never land",
        "patch": "",
    }
    response = decomposer.post(RESOLUTION_URL.format(task_id=pending.pk), body, format="json")
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # Submit verdict — auditor cell only.
    body = {
        "session_id": "sess-decomposer",
        "lease_generation": 1,
        "task_id": audited.pk,
        "verdict": "pass",
        "confidence": 5,
        "evidence": {"commands": [{"label": "tests", "command": "pytest -q", "exit_code": 0}]},
    }
    response = decomposer.post(VERDICT_URL.format(task_id=audited.pk), body, format="json")
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # Review decisions (WP-3.6's route) — Owner/Device cells only.
    body = {"decision": "reassign", "version": reviewing.version}
    response = decomposer.post(REVIEW_URL.format(task_id=reviewing.pk), body, format="json")
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # PATCH /tasks/{id} (publish-adjacent edits) — Owner-only write cell.
    response = decomposer.patch(
        DETAIL_URL.format(task_id=pending.pk),
        {"title": "renamed", "version": pending.version},
        format="json",
    )
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE

    # Publish/unpublish (T2/T3) and the merge queue keep their matrix
    # class cells in test_authorization_matrix.py (their routes land
    # with WP-1.5 wiring/WP-3.7); the decomposer scope is absent from
    # every granting class, so the probe rows answer 403 there.

    # Nothing above touched a row.
    for task in (pending, audited, reviewing):
        task.refresh_from_db()
        assert task.version == 1
    assert Task.objects.filter(pk=pending.pk, state=TaskState.PENDING).exists()
    assert Task.objects.filter(pk=reviewing.pk, state=TaskState.IN_HUMAN_REVIEW).exists()


# --- the other columns are unchanged (regressions) ----------------------------


def test_other_roles_keep_their_create_draft_answers(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Owner yes, coder/auditor no — the non-decomposer cells stay put."""
    create = CREATE_URL.format(pid=project.pk)

    owner_view = owner_client.post(create, {"title": "Owner draft"}, format="json")
    assert owner_view.status_code == 201, owner_view.content
    assert owner_view.json()["state"] == TaskState.DRAFT

    for role in ("coder", "auditor"):
        token = issue_agent_token(owner_client, project.pk, role)
        response = agent_client(token).post(create, {"title": f"{role} draft"}, format="json")
        assert response.status_code == 403, role
        assert _code(response) == DENIED_CODE, role

    anonymous = APIClient().post(create, {"title": "anon draft"}, format="json")
    assert anonymous.status_code == 401


def test_a_coder_token_without_the_decomposer_scope_stays_out(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The grant is the *scope*, not the token kind — never trusted free text."""
    token = issue_agent_token(owner_client, project.pk, "coder")
    response = agent_client(token).post(
        CREATE_URL.format(pid=project.pk),
        {"title": "claimed coder", "description": "role intent cannot widen a scope"},
        format="json",
    )
    assert response.status_code == 403
    assert _code(response) == DENIED_CODE
