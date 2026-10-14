"""MT-3.6-03 — ``latest_feedback`` travels from T16 to the next coder's details.

The closed loop WP-3.6 acceptance names: *"feedback appears in the next
coder's task details"*. Section 7.2 puts ``latest_feedback`` on the Task
(the fast read path); T16's side effect writes it (MT-3.6-01); the
bridge's ``get_task_details`` tool serves ``GET /tasks/{id}`` (Section
10.5; the backend payload half — the bridge tool itself is WP-2.4's
contract). This suite drives the real endpoint and the real read route:

* after an Owner request-changes the next read (owner **and** the bound
  coder agent token) carries the note as ``latest_feedback``;
* a newer T16 note overwrites the previous one ("latest wins" — no
  history invented, Section 7.2);
* tasks that never received feedback return the field empty without
  breaking existing consumers;
* reassign without a note leaves the previous feedback intact (the
  MT-3.6-03 recorded reading).

Run with ``pytest backend/tests -k latest_feedback -q``.
"""

from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState

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

REVIEW_URL = "/api/v1/tasks/{task_id}/review"
DETAILS_URL = "/api/v1/tasks/{task_id}"


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the feedback suites."""
    return make_project(name="WP-3.6 feedback")


def _review_task(project: Project, index: int = 1) -> Task:
    """A task in ``in_human_review`` with its current-attempt resolution."""
    task = make_task(project, index, state=TaskState.IN_HUMAN_REVIEW, attempt_number=1)
    TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name=f"feat/{task.pk}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="wp36 feedback seed submission",
        submitted_by_session="sess_wp36_feedback_coder",
    )
    return task


def _request_changes(owner_client: JsonAPIClient, task: Task, note: str) -> None:
    """One accepted request-changes through the real endpoint."""
    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "request_changes", "note": note, "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content


def test_request_changes_note_reaches_the_next_coder_details(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T16 → GET /tasks/{id}: the coder's orientation call sees the note."""
    task = _review_task(project)
    _request_changes(owner_client, task, "split the parser from the writer")

    coder_token = issue_agent_token(owner_client, project.pk, "coder")
    response = agent_client(coder_token).get(DETAILS_URL.format(task_id=task.pk))
    assert response.status_code == 200, response.content
    assert response.json()["latest_feedback"] == "split the parser from the writer"


def test_a_newer_note_overwrites_the_previous_one(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Section 7.2 "latest" semantics: one field, newest note wins."""
    task = _review_task(project)
    _request_changes(owner_client, task, "first note")
    # The card worked its way back to review for a second round.
    task.refresh_from_db()
    task.state = TaskState.IN_HUMAN_REVIEW
    task.save()
    _request_changes(owner_client, task, "second note")

    detail = owner_client.get(DETAILS_URL.format(task_id=task.pk))
    assert detail.status_code == 200
    assert detail.json()["latest_feedback"] == "second note"


def test_reassign_without_a_note_keeps_the_prior_feedback(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A note-less reassign never wipes what a reviewer already wrote."""
    task = _review_task(project)
    _request_changes(owner_client, task, "keep this context")
    task.refresh_from_db()
    task.state = TaskState.IN_HUMAN_REVIEW
    task.save()

    response = owner_client.post(
        REVIEW_URL.format(task_id=task.pk),
        {"decision": "reassign", "version": task.version},
        format="json",
    )
    assert response.status_code == 201, response.content
    detail = owner_client.get(DETAILS_URL.format(task_id=task.pk))
    assert detail.json()["latest_feedback"] == "keep this context"


def test_tasks_without_feedback_return_an_empty_field(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Empty-state safety: the field is always present, never null-shaped."""
    task = make_task(project, 7, state=TaskState.PENDING)
    coder_token = issue_agent_token(owner_client, project.pk, "coder")
    response = agent_client(coder_token).get(DETAILS_URL.format(task_id=task.pk))
    assert response.status_code == 200
    payload = response.json()
    assert payload["latest_feedback"] == ""
    assert payload["id"] == task.pk  # the rest of the payload is intact


def test_feedback_is_visible_to_owner_and_bound_agent_only(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The read cell of GET /tasks/{id} is unchanged by the new field."""
    task = _review_task(project)
    _request_changes(owner_client, task, "auditor context")

    owner_view = owner_client.get(DETAILS_URL.format(task_id=task.pk))
    assert owner_view.status_code == 200
    assert owner_view.json()["latest_feedback"] == "auditor context"

    auditor_token = issue_agent_token(owner_client, project.pk, "auditor")
    auditor_view = agent_client(auditor_token).get(DETAILS_URL.format(task_id=task.pk))
    assert auditor_view.status_code == 200
    assert auditor_view.json()["latest_feedback"] == "auditor context"

    device_client = APIClient()
    device_view = device_client.get(DETAILS_URL.format(task_id=task.pk))
    assert device_view.status_code == 401, "anonymous stays outside the read cell"
