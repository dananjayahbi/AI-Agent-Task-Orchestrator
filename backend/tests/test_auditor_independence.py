"""MT-3.3-02 — auditor independence rule, ``AUDITOR_SAME_AS_CODER`` (G-20).

Run with ``pytest backend/tests -k auditor_independence -q``. The rule
(Section 8.3 invariant 3; Section 12.1 self-approval mitigation;
Section 19 WP-3.3 acceptance "same session or same label cannot audit")
is enforced **server-side and attempt-scoped**:

* same session as the current attempt's coder → refused;
* same agent label (via the coder session's Section 7.2 AgentSession
  row) → refused;
* no current-attempt resolution → refused (independence unprovable —
  fail closed, never assumed);
* a historical attempt's coder never blocks a later independent
  auditor (the "for one attempt" wording);
* and the *verdict* path re-runs the same function (MT-3.3-05's
  recheck — the rule's tests live here per the MT's out-of-scope note).

Every rejection is the closed catalog ``AUDITOR_SAME_AS_CODER`` (409)
and leaves the task in ``to_be_audited`` with no audit lease.
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
    register_session,
    restore_audit_registry,  # noqa: F401  (autouse)
    verdict_body,
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
    assert error["code"] in ("AUDITOR_SAME_AS_CODER",), error["code"]
    return str(error["code"])


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _assert_refused_clean(response: Any, task_id: str) -> None:
    """409 AUDITOR_SAME_AS_CODER, state untouched, no lease set."""
    assert response.status_code == 409, response.content
    assert _code(response) == "AUDITOR_SAME_AS_CODER"
    from apps.tasks.models import Task

    task = Task.objects.get(pk=task_id)
    assert task.state == TaskState.TO_BE_AUDITED, "the claim refusal changes nothing"
    assert task.claimed_role is None
    assert task.lease_expires_at is None
    assert task.lease_generation == 0, "no fencing increment on refusal"


# --- claim-time enforcement (inside the T11 guard) ---------------------------


def test_same_session_as_coder_is_refused(owner_client: APIClient, project: Project) -> None:
    """The auditor session *is* the submitting coder's session (G-20)."""
    task = auditable_task(project, 1, coder_session="sess_wp33_coder")
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    response = claim_as_auditor(client, task.pk, session_id="sess_wp33_coder")

    _assert_refused_clean(response, task.pk)


def test_same_agent_label_as_coder_is_refused(owner_client: APIClient, project: Project) -> None:
    """Different sessions, identical label — G-20's label half blocks."""
    task = auditable_task(
        project, 1, coder_session="sess_wp33_coder", coder_label="shared-opencode"
    )
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    response = claim_as_auditor(
        client, task.pk, session_id="sess_wp33_other", label="shared-opencode"
    )

    _assert_refused_clean(response, task.pk)


def test_distinct_session_and_label_claims_successfully(
    owner_client: APIClient, project: Project
) -> None:
    """The independent auditor proceeds (T11's lease lands)."""
    task = auditable_task(project, 1, coder_session="sess_wp33_coder", coder_label="coder-label")
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    response = claim_as_auditor(
        client, task.pk, session_id="sess_wp33_auditor", label="auditor-label"
    )

    assert response.status_code == 200, response.content
    assert response.json()["task"]["claimed_role"] == "auditor"


def test_missing_agent_session_row_keeps_the_session_gate(
    owner_client: APIClient, project: Project
) -> None:
    """Recorded reading: no label input → the session half still gates."""
    task = auditable_task(project, 1, coder_session="sess_wp33_coder")  # no AgentSession row
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    refused = claim_as_auditor(client, task.pk, session_id="sess_wp33_coder")
    _assert_refused_clean(refused, task.pk)

    allowed = claim_as_auditor(client, task.pk, session_id="sess_wp33_new_aud")
    assert allowed.status_code == 200, allowed.content


def test_unprovable_independence_fails_closed(owner_client: APIClient, project: Project) -> None:
    """A ``to_be_audited`` row without a current-attempt resolution: refuse."""
    from apps.tasks.models import Task

    from .wp33_helpers import make_task

    task = make_task(project, 1, state=TaskState.TO_BE_AUDITED, attempt_number=1)
    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))

    response = claim_as_auditor(client, task.pk)

    _assert_refused_clean(response, task.pk)
    assert Task.objects.get(pk=task.pk).state == TaskState.TO_BE_AUDITED


def test_historical_attempt_coder_does_not_block_a_later_auditor(
    owner_client: APIClient, project: Project
) -> None:
    """Attempt-scoped: only the *current* attempt's coder is compared."""
    task = auditable_task(
        project,
        1,
        coder_session="sess_wp33_old_cr",
        coder_label="old-coder-label",
        attempt=2,
    )
    # The attempt-1 coder (session + label) is historical history only.
    from apps.tasks.models import TaskResolution

    TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name="feat/PID00001-T001",
        commit_sha="abcdef0123456789abcdef0123456789abcdef01",  # pragma: allowlist secret
        execution_summary="first attempt",
        submitted_by_session="sess_wp33_hist",
    )
    register_session(project, "sess_wp33_hist", "historic-label")

    client = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    # Reusing the *historical* session and label is fine: the current
    # attempt's coder is sess_wp33_old_cr / old-coder-label.
    response = claim_as_auditor(
        client, task.pk, session_id="sess_wp33_hist", label="historic-label"
    )

    assert response.status_code == 200, response.content


# --- verdict-time recheck (MT-3.3-05 reuses this function; tests live here) --


def test_verdict_path_rechecks_independence(
    owner_client: APIClient, project: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verdict service calls the same function — a raised check refuses
    the POST with AUDITOR_SAME_AS_CODER and stores no report."""
    from apps.audit import services as audit_services
    from apps.audit.exceptions import AuditorSameAsCoder

    task = auditable_task(project, 1, coder_session="sess_wp33_coder")
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    claimed = claim_as_auditor(auditor, task.pk)
    assert claimed.status_code == 200, claimed.content

    def _refuse(*args: Any, **kwargs: Any) -> Any:
        raise AuditorSameAsCoder("PID00001-T001", reason="recheck fixture")

    monkeypatch.setattr(audit_services, "assert_auditor_independent", _refuse)
    response = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "AUDITOR_SAME_AS_CODER"

    from apps.audit.models import AuditReport

    assert AuditReport.objects.count() == 0, "the refused verdict persists nothing"
    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED, "and dispatches nothing"
    assert task.lease_expires_at is not None, "the audit lease it already holds stands"
