"""MT-3.6-01 / MT-3.6-04 — the review decision endpoint (T15/T16) on the real API.

The executable half of WP-3.6's acceptance criteria (FR-AUD-05; Sections
9.2, 8.2, 11.5, 12.2, 12.5, 14.2):

* all three decisions end to end — approve (T15: ``merge_status =
  pending`` + record), request_changes (T16: note → ``latest_feedback``,
  attempt preserved, worker cleared, back to ``pending``), reassign
  (T16: back to ``pending``, worker cleared);
* the T16 note guard (``VALIDATION_ERROR`` with hint) and the T15
  resolution guard (approve without a resolution is rejected);
* Section 12.2 authorization: Owner and Device only; agent tokens of
  every role answer ``ROLE_NOT_PERMITTED``, a foreign-project agent
  answers ``AUTH_FORBIDDEN_PROJECT`` (scope-first), anonymous
  ``AUTH_REQUIRED``;
* Section 8.2 rules: one Transition row + one ``review.decided`` event
  row per accepted decision, in one transaction; stale ``version`` →
  ``VERSION_CONFLICT``; illegal state → ``TASK_STATE_CONFLICT``;
* MT-3.6-04 approve safety (Section 14.2): the approval is bound to the
  ``resolution_id`` the reviewer saw — an outdated id is refused with
  **zero** side effects; only approve is resolution-bound.

Run with ``pytest backend/tests -k review_endpoint -q``.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import ReviewDecision, ReviewDecisionValue, ReviewVia
from apps.events.models import Event
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import (
    ClaimedRole,
    MergeStatus,
    Task,
    TaskResolution,
    TaskState,
    TaskTransition,
)

from .wp15_helpers import make_project, make_task
from .wp16_helpers import restore_lease_registry  # noqa: F401  (autouse: T4/T6 wiring)
from .wp33_helpers import (  # noqa: F401  (autouse: registry restore)
    JsonAPIClient,
    agent_client,
    issue_agent_token,
    login_owner_client,
    restore_audit_registry,
)

REVIEW_URL = "/api/v1/tasks/{task_id}/review"
PASSWORD = "wp36-tests-1!"  # pragma: allowlist secret

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the review suites."""
    return make_project(name="WP-3.6 review")


def _resolution(task: Task, session: str = "sess_wp36_coder") -> TaskResolution:
    """The task's current-attempt submission (the binding input)."""
    resolution: TaskResolution = TaskResolution.objects.create(
        task=task,
        attempt_number=task.attempt_number,
        branch_name=f"feat/{task.pk}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="wp36 seed submission",
        submitted_by_session=session,
    )
    return resolution


def _review_task(project: Project, index: int = 1, *, worker: bool = False) -> Task:
    """A task sitting in ``in_human_review`` with its current resolution.

    ``worker=True`` stages the coder-lease columns a T9-escalated row
    could carry so T16's "clear worker" side effect is observable
    (Section 8.3 invariant 1 still holds after the clear).
    """
    task = make_task(project, index, state=TaskState.IN_HUMAN_REVIEW, attempt_number=1)
    if worker:
        task.worker_agent_id = "claude-code-session-98b2"
        task.worker_session_id = "sess_7f3c91d0a2b44e"
        task.claimed_role = ClaimedRole.CODER
        task.lease_acquired_at = timezone.now()
        task.lease_expires_at = timezone.now() + timedelta(minutes=45)
        task.save()
    _resolution(task)
    return task


def _approve_body(task: Task, **overrides: Any) -> dict[str, Any]:
    """An approve body bound to the task's current resolution and version."""
    current = TaskResolution.objects.filter(task=task).order_by("-submitted_at").first()
    body: dict[str, Any] = {
        "decision": "approve",
        "resolution_id": str(current.pk) if current else None,
        "version": task.version,
        "note": "ship it",
    }
    body.update(overrides)
    return body


# --- the three decisions end to end (MT-3.6-01) ------------------------------


def test_approve_lands_merge_pending_and_records_the_decision(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T15: merge_status pending, the record, the history row, the event."""
    task = _review_task(project)

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk), _approve_body(task), format="json"
    )
    assert response.status_code == 201, response.content

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.PENDING, "Section 8.1 merge-pending sub-status"
    assert task.state == TaskState.IN_HUMAN_REVIEW, "sub-status, never a seventh state"
    assert task.version == 2

    payload = response.json()
    assert payload["decision"]["decision"] == "approve"
    assert payload["decision"]["decided_via"] == ReviewVia.WEB
    assert payload["decision"]["resolution_id"] is not None
    assert payload["task"]["merge_status"] == MergeStatus.PENDING

    row = ReviewDecision.objects.get(task=task)
    assert row.decision == ReviewDecisionValue.APPROVE
    assert row.note == "ship it"
    assert row.resolution is not None
    assert row.decided_by  # the owner user id (Section 7.2)

    transition = TaskTransition.objects.get(task=task)
    assert transition.from_state == TaskState.IN_HUMAN_REVIEW
    assert transition.to_state == TaskState.IN_HUMAN_REVIEW  # flag-only row
    assert transition.reason_code == "approve"
    assert transition.actor_type == "owner"

    event = Event.objects.get(task_id=task.pk, type="review.decided")
    assert event.data["from_state"] == TaskState.IN_HUMAN_REVIEW
    assert event.data["reason_code"] == "approve"
    assert event.data["task_version"] == 2


def test_request_changes_sets_feedback_and_returns_to_pending(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T16: note → latest_feedback, attempt preserved, worker cleared."""
    task = _review_task(project, worker=True)

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "request_changes", "note": "tighten the scope", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content

    task.refresh_from_db()
    assert task.state == TaskState.PENDING
    assert task.latest_feedback == "tighten the scope"
    assert task.attempt_number == 1, "T16 preserves attempt_number (Section 8.2)"
    assert task.worker_agent_id is None and task.claimed_role is None, "clear worker"
    assert task.merge_status == MergeStatus.NONE

    row = ReviewDecision.objects.get(task=task)
    assert row.decision == ReviewDecisionValue.REQUEST_CHANGES
    assert row.note == "tighten the scope"
    assert row.resolution is not None, "bound to the reviewed submission"

    event = Event.objects.get(task_id=task.pk, type="review.decided")
    assert event.data["to_state"] == TaskState.PENDING
    assert event.data["reason_code"] == "request_changes"


def test_reassign_returns_to_pending_without_a_note(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T16 reassign: pending + worker cleared; no note → no feedback wipe."""
    task = _review_task(project, worker=True)
    Task.objects.filter(pk=task.pk).update(latest_feedback="earlier reviewer note")

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "reassign", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content

    task.refresh_from_db()
    assert task.state == TaskState.PENDING
    assert task.worker_agent_id is None and task.claimed_role is None
    assert task.latest_feedback == "earlier reviewer note", (
        "reassign without a note leaves the prior feedback intact (MT-3.6-03 recorded reading)"
    )
    row = ReviewDecision.objects.get(task=task)
    assert row.decision == ReviewDecisionValue.REASSIGN


def test_reassign_with_a_note_updates_feedback(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A supplied reassign note follows T16's latest_feedback side effect."""
    task = _review_task(project)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "reassign", "note": "needs a fresh pair of eyes", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content
    task.refresh_from_db()
    assert task.latest_feedback == "needs a fresh pair of eyes"


# --- guards and rejections ----------------------------------------------------


def test_request_changes_without_a_note_is_rejected_with_a_hint(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T16 guard: VALIDATION_ERROR (400) with the note hint; nothing written."""
    task = _review_task(project)

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "request_changes", "version": task.version},
        format="json",
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "note" in error["details"]

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.version == 1
    assert not ReviewDecision.objects.filter(task=task).exists()
    assert not TaskTransition.objects.filter(task=task).exists()
    assert not Event.objects.filter(task_id=task.pk, type="review.decided").exists()


def test_approve_without_a_resolution_id_is_rejected(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The approve binding's input half (MT-3.6-04; Section 14.2)."""
    task = _review_task(project)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "approve", "version": task.version},
        format="json",
    )
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "resolution_id" in error["details"]


def test_approve_without_any_resolution_is_refused_by_the_guard(
    project: Project,
) -> None:
    """T15's guard answers TASK_STATE_CONFLICT for a dispatch with no submission.

    The endpoint's serializer catches the missing binding first, so this
    is the direct-dispatcher-caller half (MT-1.5-04 contract: guards are
    honest without the service in front of them).
    """
    from apps.tasks.exceptions import TaskStateConflict
    from apps.tasks.state_machine.dispatcher import dispatch_transition

    task = make_task(project, 9, state=TaskState.IN_HUMAN_REVIEW, attempt_number=1)
    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=task.pk,
            trigger="approve",
            actor_type="owner",
            actor_ref="owner-1",
            extra={
                "resolution": None,
                "note": "",
                "decided_by": "owner-1",
                "decided_via": "web",
            },
        )
    task.refresh_from_db()
    assert task.version == 1
    assert not ReviewDecision.objects.filter(task=task).exists()


def test_unknown_decision_value_is_rejected(owner_client: JsonAPIClient, project: Project) -> None:
    """Only the three Section 9.2 values — anything else is VALIDATION_ERROR."""
    task = _review_task(project)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "reject", "note": "nope", "version": task.version},
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_stale_version_conflicts_and_changes_nothing(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 8.2 rule 3: the version the UI saw, or VERSION_CONFLICT."""
    task = _review_task(project)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        _approve_body(task, version=task.version + 7),  # plausible but stale
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
    task.refresh_from_db()
    assert task.merge_status == MergeStatus.NONE
    assert not ReviewDecision.objects.filter(task=task).exists()


def test_illegal_state_decision_conflicts(owner_client: JsonAPIClient, project: Project) -> None:
    """Approve outside in_human_review answers TASK_STATE_CONFLICT (409)."""
    task = make_task(project, 5, state=TaskState.PENDING)
    resolution = _resolution(task)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        _approve_body(task, resolution_id=str(resolution.pk)),
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"


def test_unknown_task_answers_task_not_found(owner_client: JsonAPIClient) -> None:
    """Well-formed but absent id → TASK_NOT_FOUND (404)."""
    response = owner_client.post(
        REVIEW_URL.format(task_id="PID00001-T999"),
        {"decision": "reassign", "version": 1},
        format="json",
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


# --- MT-3.6-04: stale-resolution protection -----------------------------------


def test_approve_with_an_outdated_resolution_is_rejected_with_zero_side_effects(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 14.2: a newer submission invalidates a stale approval."""
    task = _review_task(project)
    stale = TaskResolution.objects.filter(task=task).first()
    assert stale is not None
    # The coder re-submitted while the reviewer looked away: a new
    # attempt (T4 claim bump + T7 submission) replaced the evidence the
    # reviewer had open.
    task.attempt_number = 2
    task.save()
    newer = _resolution(task, session="sess_wp36_coder_retry")

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        _approve_body(task, resolution_id=str(stale.pk)),
        format="json",
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "VERSION_CONFLICT"
    assert "refresh" in error["message"].lower()

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.NONE, "zero T15 side effects"
    assert not ReviewDecision.objects.filter(task=task).exists()
    assert not Event.objects.filter(task_id=task.pk, type="review.decided").exists()
    assert newer.attempt_number == 2  # the fixture really replaced the binding


def test_approve_with_the_current_resolution_proceeds(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The positive half: the current id sails through T15."""
    task = _review_task(project)
    current = TaskResolution.objects.filter(task=task).order_by("-submitted_at").first()
    assert current is not None
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        _approve_body(task, resolution_id=str(current.pk)),
        format="json",
    )
    assert response.status_code == 201, response.content


def test_approve_with_another_tasks_resolution_is_rejected(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A foreign resolution id is malformed input, not a stale binding."""
    task = _review_task(project)
    other = _review_task(project, index=2)
    foreign = TaskResolution.objects.filter(task=other).first()
    assert foreign is not None
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        _approve_body(task, resolution_id=str(foreign.pk)),
        format="json",
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_note_actions_are_not_resolution_bound(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 14.2 names approve alone — request_changes needs no binding."""
    # A T9-style review: the task never had a submission to bind.
    task = make_task(project, 8, state=TaskState.IN_HUMAN_REVIEW, attempt_number=1)
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "request_changes", "note": "try again", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content
    row = ReviewDecision.objects.get(task=task)
    assert row.resolution_id is None


# --- Section 12.2 authorization -----------------------------------------------


def test_agent_roles_are_refused_with_catalog_codes(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Review decisions are Owner/Device — every agent role answers 403."""
    task = _review_task(project)
    for role in ("coder", "auditor", "decomposer", "merge_executor"):
        token = issue_agent_token(owner_client, project.pk, role)
        response = agent_client(token).post(
            REVIEW_URL.format(task_id=task.pk), _approve_body(task), format="json"
        )
        assert response.status_code == 403, role
        assert response.json()["error"]["code"] == "ROLE_NOT_PERMITTED", role


def test_foreign_project_agent_token_is_forbidden_before_role_logic(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """ADR-004 zero-bleed: scope outranks role on the review route too."""
    other_project = Project.objects.create(
        id="PID00009",
        name="Other",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    task = _review_task(project)
    token = issue_agent_token(owner_client, other_project.pk, "coder")
    response = agent_client(token).post(
        REVIEW_URL.format(task_id=task.pk), _approve_body(task), format="json"
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_FORBIDDEN_PROJECT"


def test_anonymous_is_unauthorized(owner_client: JsonAPIClient, project: Project) -> None:
    """No credential → AUTH_REQUIRED (401), catalog-closed."""
    task = _review_task(project)
    response = APIClient().post(
        REVIEW_URL.format(task_id=task.pk), _approve_body(task), format="json"
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_device_decides_as_mobile(owner_client: JsonAPIClient, project: Project) -> None:
    """The device token is the mobile channel: decided_via mobile + device id."""
    registration = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-wp36"}
    )
    assert registration.status_code == 201, registration.content
    device = registration.json()

    device_client = JsonAPIClient()
    token_value = str(device["token"])
    device_client.credentials(HTTP_AUTHORIZATION="Bearer " + token_value)
    task = _review_task(project)
    response = device_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "reassign", "note": "needs the mobile reviewer", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content
    row = ReviewDecision.objects.get(task=task)
    assert row.decided_via == ReviewVia.MOBILE
    assert row.decided_by == str(device["id"])


# --- idempotency (Section 9.2) -------------------------------------------------


def test_idempotency_key_replays_without_a_second_decision(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A retried POST with the same key replays the stored outcome (ADR-012)."""
    task = _review_task(project)
    headers: dict[str, Any] = {"HTTP_IDEMPOTENCY_KEY": "wp36-review-1"}
    body = _approve_body(task)

    first = owner_client.post(REVIEW_URL.format(task_id=task.pk), body, format="json", **headers)
    assert first.status_code == 201, first.content
    replay = owner_client.post(REVIEW_URL.format(task_id=task.pk), body, format="json", **headers)
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert ReviewDecision.objects.filter(task=task).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1
