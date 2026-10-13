"""MT-3.3-01 — auditor role gating on work listing and claim (Section 9.2/10.5).

Run with ``pytest backend/tests -k auditor_role_gating -q``. Every case
runs against the **real** routes with real credentials:

* ``GET /projects/{pid}/work`` — ``role=coder`` (default) lists unblocked
  ``pending`` only, ``role=auditor`` lists ``to_be_audited`` only, never a
  mixed or wrong-state listing; an invalid role answers
  ``VALIDATION_ERROR`` (Section 10.5; FR-AUD-01).
* ``POST /tasks/{id}/claim`` — the Section 12.2 claim matrix with the
  Section 10.5 ``role`` input: token scopes answer first (the permission
  cells), then the declared role is validated against the state inside
  the lock (``ROLE_NOT_PERMITTED`` for the other role's claimable state,
  ``TASK_STATE_CONFLICT`` for any other state); a successful auditor
  claim records ``claimed_role = auditor`` with the Section 8.6 audit
  lease and leaves ``attempt_number`` at the coder's value (T11).
* The coder path (T4) stays byte-identical: the default body claims
  ``pending`` exactly as before WP-3.3 (regression guard).
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.tasks.models import TaskState

from .wp33_helpers import (
    active_policy_project,
    agent_client,
    auditable_task,
    claim_as_auditor,
    clean_throttle_cache,  # noqa: F401  (autouse)
    issue_agent_token,
    login_owner_client,
    make_pending_task,
    make_task,
    restore_audit_registry,  # noqa: F401  (autouse)
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (Section 9.2's owner-only rows)."""
    return login_owner_client()


def _code(response: Any) -> str:
    """The catalog code of one standard envelope (five fields, asserted)."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return str(error["code"])


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


# --- work listing: role selects exactly one state (Section 10.5) -------------


def test_work_listing_role_is_an_exact_state_filter(
    owner_client: APIClient, project: Project
) -> None:
    """coder → unblocked pending only; auditor → to_be_audited only."""
    pending = make_pending_task(project, 1)
    waiting = make_task(project, 2, state=TaskState.DRAFT)  # never offered to either
    audit_row = auditable_task(project, 3)
    blocked = make_pending_task(project, 4)
    blocker = make_task(project, 5, state=TaskState.PENDING)
    from apps.tasks.services.dependencies import set_dependencies

    set_dependencies(task=blocked, dependency_ids=[blocker.pk])
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder", "auditor"))

    coder = client.get(f"/api/v1/projects/{project.pk}/work")
    assert coder.status_code == 200, coder.content
    coder_ids = {row["id"] for row in coder.json()["results"]}
    assert pending.pk in coder_ids
    assert audit_row.pk not in coder_ids, "never a mixed listing (Section 10.5)"
    assert waiting.pk not in coder_ids
    assert blocked.pk not in coder_ids, "dependencies must be completed"

    auditor = client.get(f"/api/v1/projects/{project.pk}/work", {"role": "auditor"})
    assert auditor.status_code == 200, auditor.content
    auditor_ids = {row["id"] for row in auditor.json()["results"]}
    assert auditor_ids == {audit_row.pk}, "auditor sees exactly to_be_audited"


def test_work_listing_rejects_an_invalid_role(owner_client: APIClient, project: Project) -> None:
    """Invalid role → VALIDATION_ERROR (400), not a silent coder default."""
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    response = client.get(f"/api/v1/projects/{project.pk}/work", {"role": "owner"})
    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"


# --- claim: a successful auditor claim (T11's claim half) --------------------


def test_auditor_claim_sets_role_and_lease_without_bumping_attempt(
    owner_client: APIClient, project: Project
) -> None:
    """200: claimed_role auditor, Section 8.6 audit lease, attempt intact."""
    task = auditable_task(project, 1)
    assert task.attempt_number == 1
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    response = claim_as_auditor(client, task.pk)

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["task"]["state"] == TaskState.TO_BE_AUDITED, "T11 never moves the state"
    assert body["task"]["claimed_role"] == "auditor"
    assert body["task"]["attempt_number"] == 1, "attempt_number increments on coder claims only"
    lease = body["lease"]
    assert lease["role"] == "auditor"
    assert lease["session_id"] == "sess_wp33_auditor"
    assert lease["assigned_agent"] == "wp33-auditor"
    assert lease["lease_generation"] == 1
    assert lease["lease_acquired_at"] and lease["lease_expires_at"]
    assert lease["lease_hard_cap_at"] is not None
    assert set(body) == {"task", "lease", "rules_block"}, "Section 9.3 step 6 shape"

    task.refresh_from_db()
    assert task.claimed_role == "auditor"
    assert task.worker_session_id == "sess_wp33_auditor"
    assert task.attempt_number == 1
    assert task.lease_expires_at is not None


# --- claim: the Section 12.2 matrix, scopes first then declared role --------


def test_claim_matrix_token_scopes_answer_first(owner_client: APIClient, project: Project) -> None:
    """Cross-role *tokens* die at the permission gate (ROLE_NOT_PERMITTED)."""
    pending = make_pending_task(project, 1)
    audit_row = auditable_task(project, 2)
    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    # Claim pending is coder-only: an auditor token is refused …
    denied = auditor.post(
        f"/api/v1/tasks/{pending.pk}/claim",
        {"session_id": "sess_x_0001", "worker_agent_id": "x"},
    )
    assert denied.status_code == 403
    assert _code(denied) == "ROLE_NOT_PERMITTED"

    # … and claim to_be_audited is auditor-only: a coder token is refused
    # even when it *declares* role=auditor (the scope answers first).
    denied_audit = coder.post(
        f"/api/v1/tasks/{audit_row.pk}/claim",
        {"session_id": "sess_x_0002", "worker_agent_id": "x", "role": "auditor"},
    )
    assert denied_audit.status_code == 403
    assert _code(denied_audit) == "ROLE_NOT_PERMITTED"


def test_claim_matrix_declared_role_is_validated_against_the_state(
    owner_client: APIClient, project: Project
) -> None:
    """A dual-scope token's *intent* still faces the claim cells (403)."""
    pending = make_pending_task(project, 1)
    audit_row = auditable_task(project, 2)
    dual = agent_client(issue_agent_token(owner_client, project.pk, "coder", "auditor"))

    # role=auditor on pending: the auditor role may not act there.
    on_pending = dual.post(
        f"/api/v1/tasks/{pending.pk}/claim",
        {"session_id": "sess_wp33_dual1", "worker_agent_id": "dual", "role": "auditor"},
    )
    assert on_pending.status_code == 403
    assert _code(on_pending) == "ROLE_NOT_PERMITTED"
    pending.refresh_from_db()
    assert pending.state == TaskState.PENDING, "no lease, no side effect on refusal"

    # role=coder on to_be_audited: the coder role may not act there.
    on_audit = dual.post(
        f"/api/v1/tasks/{audit_row.pk}/claim",
        {"session_id": "sess_wp33_dual2", "worker_agent_id": "dual", "role": "coder"},
    )
    assert on_audit.status_code == 403
    assert _code(on_audit) == "ROLE_NOT_PERMITTED"
    audit_row.refresh_from_db()
    assert audit_row.claimed_role is None


def test_invalid_declared_role_value_is_validation_error(
    owner_client: APIClient, project: Project
) -> None:
    """Section 20.4 item 5: bad input → VALIDATION_ERROR, never a 500."""
    audit_row = auditable_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    response = client.post(
        f"/api/v1/tasks/{audit_row.pk}/claim",
        {"session_id": "sess_wp33_bad", "worker_agent_id": "x", "role": "owner"},
    )
    assert response.status_code == 400
    assert _code(response) == "VALIDATION_ERROR"


def test_auditor_role_meets_the_other_states_with_catalog_codes(
    owner_client: APIClient, project: Project
) -> None:
    """role=auditor: held → TASK_ALREADY_CLAIMED; anything else → conflict."""
    draft = make_task(project, 1, state=TaskState.DRAFT)
    claimed = make_pending_task(project, 2)
    review = make_task(project, 3, state=TaskState.IN_HUMAN_REVIEW)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder", "auditor"))

    held = client.post(
        f"/api/v1/tasks/{claimed.pk}/claim",
        {"session_id": "sess_wp33_hold", "worker_agent_id": "h"},
    )
    assert held.status_code == 200, held.content

    for task in (draft, review):
        response = client.post(
            f"/api/v1/tasks/{task.pk}/claim",
            {"session_id": "sess_wp33_other", "worker_agent_id": "x", "role": "auditor"},
        )
        assert response.status_code == 409, (task.pk, response.content)
        assert _code(response) == "TASK_STATE_CONFLICT"

    again = client.post(
        f"/api/v1/tasks/{claimed.pk}/claim",
        {"session_id": "sess_wp33_again", "worker_agent_id": "x", "role": "auditor"},
    )
    assert again.status_code == 409
    assert _code(again) == "TASK_ALREADY_CLAIMED"


# --- regression: the coder path (T4) is untouched ----------------------------


def test_coder_default_claim_path_is_unchanged(owner_client: APIClient, project: Project) -> None:
    """No role field → coder intent → pending claimed exactly as before."""
    task = make_pending_task(project, 1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))

    response = client.post(
        f"/api/v1/tasks/{task.pk}/claim",
        {"session_id": "sess_wp33_coderapi", "worker_agent_id": "wp33-coder"},
    )

    assert response.status_code == 200, response.content
    body = response.json()
    assert body["task"]["state"] == TaskState.IN_PROGRESS
    assert body["task"]["claimed_role"] == "coder"
    assert body["task"]["attempt_number"] == 1, "T4 still bumps the attempt"
    assert body["lease"]["role"] == "coder"
    assert body["lease"]["lease_generation"] == 1

    # The same claim against an auditor-only state with the default role
    # is a role refusal — the omitted parameter is "coder", never "any".
    audit_row = auditable_task(project, 2)
    denied = client.post(
        f"/api/v1/tasks/{audit_row.pk}/claim",
        {"session_id": "sess_wp33_coderapi", "worker_agent_id": "wp33-coder"},
    )
    assert denied.status_code == 403
    assert _code(denied) == "ROLE_NOT_PERMITTED"
