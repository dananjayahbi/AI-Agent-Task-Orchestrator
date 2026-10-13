"""MT-3.3-05 — the audit verdict endpoint (Section 9.2 Audit row; §10.5).

Run with ``pytest backend/tests -k audit_verdict -q``:

* **Validation matrix** — the Section 10.5 contract exactly: verdict in
  ``pass``/``flag_risk``/``fail``, confidence 1-5, required ``evidence``
  with its required structure, ``task_id`` equal to the path; anything
  else answers ``VALIDATION_ERROR`` with field details (20.4 item 5).
* **Ownership** — only the current auditor lease owner submits
  (``ROLE_NOT_PERMITTED`` / ``LEASE_NOT_OWNED`` / ``LEASE_EXPIRED`` /
  ``TASK_STATE_CONFLICT``), anonymous 401; catalog codes only.
* **Persistence** — a successful POST stores the Audit Report with
  ``proposed_verdict``, evidence, confidence, notes and the
  resolution/auditor identity (MT-3.3-04).
* **Outcome** — the endpoint never approves (invariant 8.3.4): the
  decision seam decides, fail-closed to T14 escalate until MT-3.4-07
  installs the engine; an installed approving hook is the only path to
  T13 merge-pending.
* **Idempotency** — a replayed ``Idempotency-Key`` returns the stored
  201 with no second report and no second transition; an unkeyed retry
  dies at the state gate (Section 9.2 rule).
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.audit.decision import AuditDecision, set_audit_decision_hook
from apps.audit.models import AuditReport
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp33_helpers import (
    JsonAPIClient,
    active_policy_project,
    agent_client,
    auditable_task,
    claim_as_auditor,
    clean_throttle_cache,  # noqa: F401  (autouse)
    install_event_recorder,
    issue_agent_token,
    login_owner_client,
    make_task,
    restore_audit_registry,  # noqa: F401  (autouse)
    verdict_body,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (Section 9.2's owner-only rows)."""
    return login_owner_client()


def _error(response: Any) -> tuple[int, str]:
    """(status, catalog code) with the five-field envelope asserted."""
    error = response.json()["error"]
    assert set(error) == {"code", "message", "retryable", "correlation_id", "details"}
    return response.status_code, str(error["code"])


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _claimed(
    owner_client: APIClient, project: Project, *, index: int = 1
) -> tuple[Task, APIClient]:
    """A ``to_be_audited`` task held by an independent auditor lease."""
    task = auditable_task(project, index, coder_session="sess_wp33_coder")
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    claimed = claim_as_auditor(auditor, task.pk)
    assert claimed.status_code == 200, claimed.content
    return task, auditor


# --- validation: the Section 10.5 contract ----------------------------------


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        (lambda body: body.pop("task_id"), "task_id"),
        (lambda body: body.update(task_id="PID00001-T999"), "task_id"),
        (lambda body: body.update(verdict="maybe"), "verdict"),
        (lambda body: body.update(confidence=0), "confidence"),
        (lambda body: body.update(confidence=6), "confidence"),
        (lambda body: body.pop("evidence"), "evidence"),
        (lambda body: body.update(evidence=["not", "an", "object"]), "evidence"),
        (lambda body: body.update(evidence={"lint_clean": True}), "evidence"),
        (
            lambda body: body.update(evidence={"commands": [{"label": "t", "command": "t"}]}),
            "evidence",
        ),
        (
            lambda body: body.update(
                evidence={"commands": [{"label": "t", "command": "t", "exit_code": "zero"}]}
            ),
            "evidence",
        ),
        (
            lambda body: body.update(
                evidence={
                    "commands": [{"label": "t", "command": "t", "exit_code": 0}],
                    "lint_clean": "yes",
                }
            ),
            "evidence",
        ),
        (
            lambda body: body.update(acceptance_criteria_results=[{"criterion": "c"}]),
            "acceptance_criteria_results",
        ),
        (lambda body: body.pop("session_id"), "session_id"),
        (lambda body: body.pop("lease_generation"), "lease_generation"),
        (lambda body: body.update(surprise="field"), "surprise"),
    ],
)
def test_validation_matrix_answers_validation_error(
    owner_client: APIClient, project: Project, mutate: Any, field: str
) -> None:
    """Bad input → 400 VALIDATION_ERROR naming the field (20.4 item 5)."""
    task = auditable_task(project, 1)
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    body = verdict_body(task.pk)
    mutate(body)

    response = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", body)

    status_code, code = _error(response)
    assert status_code == 400, response.content
    assert code == "VALIDATION_ERROR"
    assert field in str(response.json()["error"]["details"])
    assert AuditReport.objects.count() == 0, "validation never persists"


# --- ownership and state gates (catalog codes only) -------------------------


def test_only_the_current_auditor_lease_owner_submits(
    owner_client: APIClient, project: Project
) -> None:
    """Foreign session 403, stale generation 409, coder/owner/anon refused."""
    task, auditor = _claimed(owner_client, project)

    foreign = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, session_id="sess_wp33_intruder"),
    )
    assert _error(foreign) == (403, "LEASE_NOT_OWNED")

    stale = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, lease_generation=0),
    )
    assert _error(stale) == (409, "LEASE_EXPIRED")

    coder = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    coder_post = coder.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert _error(coder_post) == (403, "ROLE_NOT_PERMITTED")

    owner_post = owner_client.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert _error(owner_post) == (403, "ROLE_NOT_PERMITTED")

    anonymous = JsonAPIClient().post(
        f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk)
    )
    assert _error(anonymous) == (401, "AUTH_REQUIRED")

    # Nothing above moved or duplicated anything.
    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED
    assert AuditReport.objects.count() == 0


def test_verdict_without_a_lease_and_wrong_state_refuse(
    owner_client: APIClient, project: Project
) -> None:
    """Unclaimed → LEASE_EXPIRED (dead lease gate); other states → conflict."""
    unclaimed = auditable_task(project, 1, coder_session="sess_wp33_coder")
    auditor = agent_client(issue_agent_token(owner_client, project.pk, "auditor"))
    never_held = auditor.post(
        f"/api/v1/tasks/{unclaimed.pk}/audit-verdict",
        verdict_body(unclaimed.pk, lease_generation=0),
    )
    assert _error(never_held) == (409, "LEASE_EXPIRED")

    draft = make_task(project, 2, state=TaskState.DRAFT)
    wrong_state = auditor.post(f"/api/v1/tasks/{draft.pk}/audit-verdict", verdict_body(draft.pk))
    assert _error(wrong_state) == (409, "TASK_STATE_CONFLICT")


# --- persistence and outcome (fail closed; invariant 8.3.4) -----------------


def test_accepted_verdict_persists_the_report_and_escalates(
    owner_client: APIClient, project: Project
) -> None:
    """201: report row + T14 in_human_review — the endpoint never approves."""
    events = install_event_recorder()
    task, auditor = _claimed(owner_client, project)

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, confidence=5, notes="clean audit"),
    )

    assert response.status_code == 201, response.content
    body = response.json()
    assert body["trigger"] == "audit_verdict_escalated"
    assert body["decision"] == {"approve": False, "reason": "policy_forced_review"}
    assert body["task"]["state"] == TaskState.IN_HUMAN_REVIEW
    assert body["task"]["review_reason"] == "policy_forced_review"
    assert body["task"]["merge_status"] == "none", "no accidental merge-pending"

    report = AuditReport.objects.get(task=task)
    assert report.proposed_verdict == "pass"
    assert report.confidence == 5
    assert report.auditor_notes == "clean audit"
    assert report.auditor_session_id == "sess_wp33_auditor"
    assert report.policy_decision is None and report.policy_rule_results is None

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW, "T14 (the fail-closed branch)"
    assert task.merge_status == "none", "invariant 8.3.4: no approval without the engine"
    assert task.claimed_role is None, "the audit lease released with the verdict"
    assert task.lease_expires_at is None

    transition = TaskTransition.objects.filter(task=task).latest("timestamp")
    assert transition.from_state == TaskState.TO_BE_AUDITED
    assert transition.to_state == TaskState.IN_HUMAN_REVIEW
    assert transition.reason_code == "policy_forced_review"
    escalated = [record for record in events if record["type"] == "audit.escalated"]
    assert len(escalated) == 1, "Section 9.6 catalog event, exactly once"


def test_a_flagged_verdict_escalates_with_auditor_flagged(
    owner_client: APIClient, project: Project
) -> None:
    """Non-pass verdicts carry §8.4's auditor_flagged (R8's own reason)."""
    task, auditor = _claimed(owner_client, project)

    response = auditor.post(
        f"/api/v1/tasks/{task.pk}/audit-verdict",
        verdict_body(task.pk, verdict="fail", confidence=2),
    )

    assert response.status_code == 201, response.content
    assert response.json()["task"]["review_reason"] == "auditor_flagged"
    assert AuditReport.objects.get(task=task).proposed_verdict == "fail"


def test_installed_engine_hook_is_the_only_approval_path(
    owner_client: APIClient, project: Project
) -> None:
    """Hook approves → T13 merge-pending; hook escalates → its §8.4 reason."""
    task, auditor = _claimed(owner_client, project, index=1)

    def _approve(task_: Task, resolution: Any, report: AuditReport) -> AuditDecision:
        return AuditDecision(approve=True)

    set_audit_decision_hook(_approve)
    approved = auditor.post(f"/api/v1/tasks/{task.pk}/audit-verdict", verdict_body(task.pk))
    assert approved.status_code == 201, approved.content
    body = approved.json()
    assert body["trigger"] == "audit_verdict_pass"
    assert body["decision"]["approve"] is True
    assert body["task"]["state"] == TaskState.TO_BE_AUDITED, "still to_be_audited until merge"
    assert body["task"]["merge_status"] == "pending"
    assert body["task"]["review_reason"] is None
    task.refresh_from_db()
    assert task.merge_status == "pending"
    assert task.claimed_role is None, "T13 concludes the audit claim"

    # Second task, engine escalates with its own enumerated reason.
    def _escalate(task_: Task, resolution: Any, report: AuditReport) -> AuditDecision:
        return AuditDecision(approve=False, reason="low_confidence")

    set_audit_decision_hook(_escalate)
    second, second_auditor = _claimed(owner_client, project, index=2)
    escalated = second_auditor.post(
        f"/api/v1/tasks/{second.pk}/audit-verdict", verdict_body(second.pk, confidence=1)
    )
    assert escalated.status_code == 201, escalated.content
    assert escalated.json()["task"]["review_reason"] == "low_confidence"
    assert escalated.json()["decision"] == {"approve": False, "reason": "low_confidence"}


def test_engine_hook_cannot_approve_via_the_escalation_row(
    owner_client: APIClient, project: Project
) -> None:
    """Structural guard: the T14 side effect refuses an approving engine."""
    from apps.audit.transitions import ensure_audit_wired

    task, auditor = _claimed(owner_client, project)

    def _approve(task_: Task, resolution: Any, report: AuditReport) -> AuditDecision:
        return AuditDecision(approve=True)

    set_audit_decision_hook(_approve)
    # The service picks T13 when the hook approves, so T14's refusal needs
    # a direct dispatch — proving the row itself cannot approve by stealth.
    ensure_audit_wired()
    resolution = task.resolutions.get(attempt_number=task.attempt_number)
    report = AuditReport.objects.create(
        task=task,
        resolution=resolution,
        auditor_session_id="sess_wp33_auditor",
        evidence={"commands": []},
        confidence=4,
        proposed_verdict="pass",
    )
    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=task.pk,
            trigger="audit_verdict_escalated",
            actor_type="agent",
            actor_ref="sess_wp33_auditor",
            extra={
                "session_id": "sess_wp33_auditor",
                "lease_generation": 1,
                "resolution": resolution,
                "report": report,
            },
        )


# --- idempotency (Section 9.2; NFR-12) --------------------------------------


def test_idempotent_key_replay_never_double_applies(
    owner_client: APIClient, project: Project
) -> None:
    """Same key + body → the stored 201; one report, one transition."""
    task, auditor = _claimed(owner_client, project)
    headers = {"Idempotency-Key": "verdict-key-1"}
    url = f"/api/v1/tasks/{task.pk}/audit-verdict"
    body = verdict_body(task.pk)

    first = auditor.post(url, body, headers=headers)
    second = auditor.post(url, body, headers=headers)

    assert first.status_code == 201, first.content
    assert second.status_code == 201, second.content
    assert second.json() == first.json(), "replay returns the original outcome"
    assert AuditReport.objects.count() == 1
    # T11 claim + T14 verdict = exactly two history rows, replay included.
    assert TaskTransition.objects.filter(task=task).count() == 2


def test_unkeyed_retry_dies_at_the_state_gate(owner_client: APIClient, project: Project) -> None:
    """No key: the second POST is a conflict — no second report, no row."""
    task, auditor = _claimed(owner_client, project)
    url = f"/api/v1/tasks/{task.pk}/audit-verdict"

    first = auditor.post(url, verdict_body(task.pk))
    retry = auditor.post(url, verdict_body(task.pk))

    assert first.status_code == 201, first.content
    assert _error(retry) == (409, "TASK_STATE_CONFLICT")
    assert AuditReport.objects.count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 2
