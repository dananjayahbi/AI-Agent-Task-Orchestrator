"""MT-3.7-01 — the merge queue API (pending / start / result) on the real API.

The executable half of WP-3.7's first acceptance slice (FR-AUD-06;
Sections 9.2, 8.1, 8.2, 7.2, 12.2, 9.6, 9.8, ADR-008, ADR-012):

* ``GET /merge/pending`` — the FIFO queue of ``merge_status = pending``
  carriers, the canonical ``{results, next_cursor}`` envelope, project
  scoping (an agent token sees only its project; the Owner sees all);
* ``POST /merge/{task}/start`` — pending → ``merging`` + the
  ``merge.started`` event in one transaction; wrong sub-status or wrong
  state → ``TASK_STATE_CONFLICT`` (409); optional ``version`` CAS;
* ``POST /merge/{task}/result`` — ``succeeded`` dispatches T17 exactly
  once (``completed`` + ``merged`` + ``merge.succeeded`` carrying the
  sha in payload/note/event); ``conflict``/``failed`` dispatch T18
  (``in_human_review`` + ``review_reason = merge_conflict`` +
  ``merge.failed`` + the Section 9.8 push and ``review.requested`` —
  WP-3.9's hook rule);
* Section 12.2 authorization: Merge Executor writes, Owner reads;
  every other agent role and devices answer ``ROLE_NOT_PERMITTED``,
  cross-project answers ``AUTH_FORBIDDEN_PROJECT`` (scope first),
  anonymous ``AUTH_REQUIRED``;
* ADR-012: a replayed ``Idempotency-Key`` re-applies nothing; a repeat
  result on an exited task answers ``TASK_STATE_CONFLICT`` (T17/T18
  fire exactly once).

Run with ``pytest backend/tests -k merge_queue -q``.
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.events.models import Event
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import MergeStatus, Task, TaskResolution, TaskState, TaskTransition

from .wp15_helpers import (  # noqa: F401  (autouse: push recorder factory available)
    install_push_recorder,
    make_project,
    make_task,
)
from .wp33_helpers import (  # noqa: F401  (autouse: registry restore + throttle cache)
    JsonAPIClient,
    agent_client,
    issue_agent_token,
    login_owner_client,
    restore_audit_registry,
)

PENDING_URL = "/api/v1/merge/pending"
START_URL = "/api/v1/merge/{task_id}/start"
RESULT_URL = "/api/v1/merge/{task_id}/result"
PASSWORD = "wp37-tests-1!"  # pragma: allowlist secret

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the merge queue suites."""
    return make_project(name="WP-3.7 merge queue")


def _merge_pending_task(
    project: Project,
    index: int = 1,
    *,
    state: str = TaskState.IN_HUMAN_REVIEW,
) -> Task:
    """A merge-pending carrier (T15's approve outcome) with its resolution.

    ``state=TO_BE_AUDITED`` builds the engine-approved T10/T13 carrier
    instead — both are Section 8.1's sub-status carriers the queue lists.
    """
    task = make_task(
        project,
        index,
        state=state,
        merge_status=MergeStatus.PENDING,
        attempt_number=1,
    )
    TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name=f"feat/{project.pk}-T{index:03d}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="wp37 seed submission",
        submitted_by_session="sess_wp37_coder",
    )
    return task


def _executor(owner_client: JsonAPIClient, project: Project) -> JsonAPIClient:
    """A merge-executor agent client scoped to *project*."""
    token = issue_agent_token(owner_client, project.pk, "merge_executor")
    return agent_client(token)


def _start_body(task: Task, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"version": task.version}
    body.update(overrides)
    return body


def _result_body(task: Task, result: str = "succeeded", **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"result": result, "version": task.version}
    if result == "succeeded":
        body["sha"] = "aaaabbbbccccddddeeeeffff0000111122223333"  # pragma: allowlist secret
    body.update(overrides)
    return body


# --- GET /merge/pending (Section 9.2) ----------------------------------------


def test_pending_listing_returns_the_queue_in_fifo_order(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Both carriers list with the canonical envelope and their branches."""
    first = _merge_pending_task(project, 1)
    second = _merge_pending_task(project, 2, state=TaskState.TO_BE_AUDITED)
    # Not queue material: a plain pending task (never approved) must not appear.
    make_task(project, 3, state=TaskState.PENDING)

    response = owner_client.get(PENDING_URL)
    assert response.status_code == 200, response.content
    payload = response.json()
    assert set(payload) == {"results", "next_cursor"}, "pagination.md envelope"
    assert payload["next_cursor"] is None
    assert [row["id"] for row in payload["results"]] == [first.pk, second.pk]
    by_id = {row["id"]: row for row in payload["results"]}
    assert by_id[first.pk]["merge_status"] == MergeStatus.PENDING
    assert by_id[first.pk]["branch_name"] == f"feat/{project.pk}-T001"
    assert by_id[first.pk]["state"] == TaskState.IN_HUMAN_REVIEW
    assert by_id[second.pk]["state"] == TaskState.TO_BE_AUDITED
    assert by_id[first.pk]["version"] == first.version


def test_pending_listing_pages_with_the_cursor(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """page_size + opaque cursor page the queue without dropping rows."""
    tasks = [_merge_pending_task(project, index) for index in range(1, 4)]

    first_page = owner_client.get(PENDING_URL, {"page_size": 2})
    assert first_page.status_code == 200, first_page.content
    first_payload = first_page.json()
    assert [row["id"] for row in first_payload["results"]] == [tasks[0].pk, tasks[1].pk]
    assert first_payload["next_cursor"] is not None

    second_page = owner_client.get(
        PENDING_URL, {"page_size": 2, "cursor": first_payload["next_cursor"]}
    )
    assert second_page.status_code == 200, second_page.content
    second_payload = second_page.json()
    assert [row["id"] for row in second_payload["results"]] == [tasks[2].pk]
    assert second_payload["next_cursor"] is None


def test_pending_listing_scopes_agent_tokens_to_their_project(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """ADR-004 zero-bleed: the executor sees only its own project's queue."""
    other = Project.objects.create(
        id="PID00007",
        name="Other",
        repo_path="/srv/repos/other",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    own = _merge_pending_task(project, 1)
    _merge_pending_task(other, 1)

    executor = _executor(owner_client, project)
    response = executor.get(PENDING_URL)
    assert response.status_code == 200, response.content
    assert [row["id"] for row in response.json()["results"]] == [own.pk]

    owner_view = owner_client.get(PENDING_URL)
    assert len(owner_view.json()["results"]) == 2, "the Owner's Read cell spans projects"


def test_pending_listing_rejects_non_queue_roles(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Coder/auditor/decomposer and devices answer ROLE_NOT_PERMITTED."""
    _merge_pending_task(project, 1)
    for role in ("coder", "auditor", "decomposer"):
        token = issue_agent_token(owner_client, project.pk, role)
        response = agent_client(token).get(PENDING_URL)
        assert response.status_code == 403, role
        assert response.json()["error"]["code"] == "ROLE_NOT_PERMITTED", role

    registration = owner_client.post(
        "/api/v1/devices", {"platform": "android", "push_token": "apns-wp37"}
    )
    assert registration.status_code == 201, registration.content
    device_client = JsonAPIClient()
    device_client.credentials(HTTP_AUTHORIZATION="Bearer " + str(registration.json()["token"]))
    response = device_client.get(PENDING_URL)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_NOT_PERMITTED"

    anonymous = APIClient().get(PENDING_URL)
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTH_REQUIRED"


# --- POST /merge/{task}/start (Section 9.2) ----------------------------------


def test_start_marks_merging_and_emits_merge_started(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """pending → merging, version bump, ``merge.started`` in one transaction."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)

    response = executor.post(START_URL.format(task_id=task.pk), _start_body(task), format="json")
    assert response.status_code == 200, response.content

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.MERGING
    assert task.version == 2
    assert task.state == TaskState.IN_HUMAN_REVIEW, "sub-status only — never a state move"

    payload = response.json()["task"]
    assert payload["id"] == task.pk
    assert payload["merge_status"] == MergeStatus.MERGING
    assert payload["version"] == 2
    assert payload["state"] == TaskState.IN_HUMAN_REVIEW

    event = Event.objects.get(task_id=task.pk, type="merge.started")
    assert event.data["from_merge_status"] == MergeStatus.PENDING
    assert event.data["to_merge_status"] == MergeStatus.MERGING
    assert event.data["task_version"] == 2
    assert event.actor_type == "agent"
    assert event.actor_ref  # Section 12.5 records the executor
    # start is not a dispatch — no Section 8.2 row exists for it.
    assert not TaskTransition.objects.filter(task=task).exists()


def test_start_rejects_a_task_that_is_not_pending(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Wrong sub-status (already merging / never queued) → 409, nothing written."""
    claimed = _merge_pending_task(project, 1)
    unqueued = make_task(project, 2, state=TaskState.IN_HUMAN_REVIEW)  # merge_status none
    executor = _executor(owner_client, project)

    first = executor.post(START_URL.format(task_id=claimed.pk), _start_body(claimed), format="json")
    assert first.status_code == 200, first.content
    second = executor.post(
        START_URL.format(task_id=claimed.pk), _start_body(claimed), format="json"
    )
    assert second.status_code == 409, second.content
    assert second.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    assert Event.objects.filter(task_id=claimed.pk, type="merge.started").count() == 1

    refused = executor.post(START_URL.format(task_id=unqueued.pk), {}, format="json")
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    unqueued.refresh_from_db()
    assert unqueued.version == 1, "a refusal changes nothing"


def test_start_rejects_a_state_that_cannot_carry_the_sub_status(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A stray ``pending`` sub-status outside the carriers is refused (409)."""
    stray = make_task(project, 1, state=TaskState.PENDING, merge_status=MergeStatus.PENDING)
    executor = _executor(owner_client, project)

    response = executor.post(START_URL.format(task_id=stray.pk), {}, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    stray.refresh_from_db()
    assert stray.merge_status == MergeStatus.PENDING  # untouched
    assert stray.version == 1


def test_start_honors_a_stale_version_without_claiming(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """FR-TSK-06 CAS: a stale ``version`` answers VERSION_CONFLICT (409)."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)

    response = executor.post(
        START_URL.format(task_id=task.pk), _start_body(task, version=99), format="json"
    )
    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
    task.refresh_from_db()
    assert task.merge_status == MergeStatus.PENDING
    assert task.version == 1


def test_start_rejects_foreign_and_forbidden_callers(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Scope first (AUTH_FORBIDDEN_PROJECT), then role, then anonymous."""
    task = _merge_pending_task(project, 1)

    other = Project.objects.create(
        id="PID00008",
        name="Other",
        repo_path="/srv/repos/other-8",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    foreign_token = issue_agent_token(owner_client, other.pk, "merge_executor")
    foreign = agent_client(foreign_token).post(START_URL.format(task_id=task.pk), {}, format="json")
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "AUTH_FORBIDDEN_PROJECT"

    for role in ("coder", "auditor", "decomposer"):
        token = issue_agent_token(owner_client, project.pk, role)
        refused = agent_client(token).post(START_URL.format(task_id=task.pk), {}, format="json")
        assert refused.status_code == 403, role
        assert refused.json()["error"]["code"] == "ROLE_NOT_PERMITTED", role

    # Section 12.2's Owner cell is *Read* — an owner POST is refused too.
    owner_post = owner_client.post(START_URL.format(task_id=task.pk), {}, format="json")
    assert owner_post.status_code == 403
    assert owner_post.json()["error"]["code"] == "ROLE_NOT_PERMITTED"

    anonymous = APIClient().post(START_URL.format(task_id=task.pk), {}, format="json")
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTH_REQUIRED"


def test_start_idempotency_key_replays_without_a_second_claim(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """ADR-012: a retried claim with the same key changes nothing twice."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    headers: dict[str, Any] = {"HTTP_IDEMPOTENCY_KEY": "wp37-start-1"}

    first = executor.post(
        START_URL.format(task_id=task.pk), _start_body(task), format="json", **headers
    )
    assert first.status_code == 200, first.content
    replay = executor.post(
        START_URL.format(task_id=task.pk), _start_body(task), format="json", **headers
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    task.refresh_from_db()
    assert task.merge_status == MergeStatus.MERGING
    assert task.version == 2, "the replay never re-applied the claim"
    assert Event.objects.filter(task_id=task.pk, type="merge.started").count() == 1


# --- POST /merge/{task}/result (Section 9.2; T17/T18) ------------------------


def test_success_result_applies_t17_completed_with_merge_succeeded(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T17: completed + merged, one history row, sha in note and event data."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    sha = "aaaabbbbccccddddeeeeffff0000111122223333"  # pragma: allowlist secret
    response = executor.post(
        RESULT_URL.format(task_id=task.pk),
        _result_body(task, version=2, sha=sha, details="fast-forwarded"),
        format="json",
    )
    assert response.status_code == 200, response.content

    task.refresh_from_db()
    assert task.state == TaskState.COMPLETED, "ADR-008: only after the reported merge"
    assert task.merge_status == MergeStatus.MERGED, "Section 8.3 rule 2 precondition"
    assert task.version == 3

    payload = response.json()
    assert payload["result"] == "succeeded"
    assert payload["sha"] == sha
    assert payload["task"]["state"] == TaskState.COMPLETED
    assert payload["task"]["merge_status"] == MergeStatus.MERGED

    transitions = TaskTransition.objects.filter(task=task)
    assert transitions.count() == 1
    transition = transitions.get()
    assert transition.from_state == TaskState.IN_HUMAN_REVIEW
    assert transition.to_state == TaskState.COMPLETED
    assert transition.reason_code == "merge_succeeded"
    assert transition.actor_type == "agent"
    assert sha in transition.note, "the sha rides the history note (risk note)"

    event = Event.objects.get(task_id=task.pk, type="merge.succeeded")
    assert event.data["from_state"] == TaskState.IN_HUMAN_REVIEW
    assert event.data["to_state"] == TaskState.COMPLETED
    assert event.data["reason_code"] == "merge_succeeded"
    assert event.data["task_version"] == 3
    assert event.data["merge_sha"] == sha, "and the event payload (risk note)"


def test_success_result_works_from_the_to_be_audited_carrier(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T17 also fires from the engine-approved T10/T13 carrier state."""
    task = _merge_pending_task(project, state=TaskState.TO_BE_AUDITED)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    response = executor.post(
        RESULT_URL.format(task_id=task.pk), _result_body(task, version=2), format="json"
    )
    assert response.status_code == 200, response.content
    task.refresh_from_db()
    assert task.state == TaskState.COMPLETED
    assert task.merge_status == MergeStatus.MERGED


def test_failure_result_applies_t18_back_to_review_with_merge_conflict(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T18: in_human_review + merge_conflict + merge.failed + push (9.8)."""
    pushes = install_push_recorder()
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    response = executor.post(
        RESULT_URL.format(task_id=task.pk),
        _result_body(task, result="conflict", version=2, details="a.txt conflicts"),
        format="json",
    )
    assert response.status_code == 200, response.content

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW, "Section 8.2 row T18"
    assert task.merge_status == MergeStatus.CONFLICT
    assert task.review_reason == "merge_conflict", "Section 8.4 canonical member"
    assert task.version == 3

    payload = response.json()
    assert payload["result"] == "conflict"
    assert payload["sha"] is None

    transition = TaskTransition.objects.get(task=task)
    assert transition.to_state == TaskState.IN_HUMAN_REVIEW
    assert transition.reason_code == "merge_failed"
    assert "a.txt conflicts" in transition.note

    event = Event.objects.get(task_id=task.pk, type="merge.failed")
    assert event.data["to_state"] == TaskState.IN_HUMAN_REVIEW
    assert event.data["merge_status"] == "conflict"
    assert event.data["details"] == "a.txt conflicts"

    # WP-3.9's hook: exactly one review.requested on the entry, with the
    # reason and no rule details (T18 never consulted the engine).
    review = Event.objects.get(task_id=task.pk, type="review.requested")
    assert review.data["review_reason"] == "merge_conflict"
    assert review.data["task_version"] == 3
    assert "policy_rule_results" not in review.data

    # Section 9.8 push fired on the entry, carrying the dedupe key.
    assert len(pushes) == 1, "exactly one Section 9.8 trigger per entry"
    push = pushes[0]
    assert push["event_type"] == "merge.failed"
    assert push["task_id"] == task.pk
    assert push["state_version"] == task.version
    assert push["reason_code"] == "merge_failed"


def test_failure_result_triggers_the_section_9_8_push(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The T18 entry push fires for the executor's reported ``failed`` flavor."""
    pushes = install_push_recorder()
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )
    response = executor.post(
        RESULT_URL.format(task_id=task.pk),
        _result_body(task, result="failed", version=2),
        format="json",
    )
    assert response.status_code == 200, response.content

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.FAILED, "the executor's reported flavor"
    assert len(pushes) == 1, "exactly one Section 9.8 trigger per entry"
    push = pushes[0]
    assert push["event_type"] == "merge.failed"
    assert push["task_id"] == task.pk
    assert push["state_version"] == task.version
    assert push["reason_code"] == "merge_failed"


def test_success_result_without_a_sha_is_rejected(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T17's Guard column: a success report must carry the resulting sha."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)

    response = executor.post(
        RESULT_URL.format(task_id=task.pk),
        {"result": "succeeded", "version": task.version},
        format="json",
    )
    assert response.status_code == 400, response.content
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.merge_status == MergeStatus.PENDING
    assert task.version == 1, "a refused report applies nothing"
    assert not Event.objects.filter(task_id=task.pk).exclude(type="merge.started").exists()


def test_result_applies_exactly_once_and_a_repeat_conflicts(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """T17 fires once; a second report answers TASK_STATE_CONFLICT (409)."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    first = executor.post(
        RESULT_URL.format(task_id=task.pk), _result_body(task, version=2), format="json"
    )
    assert first.status_code == 200, first.content
    repeat = executor.post(
        RESULT_URL.format(task_id=task.pk), _result_body(task, version=3), format="json"
    )
    assert repeat.status_code == 409, repeat.content
    assert repeat.json()["error"]["code"] == "TASK_STATE_CONFLICT"

    assert TaskTransition.objects.filter(task=task).count() == 1
    assert Event.objects.filter(task_id=task.pk, type="merge.succeeded").count() == 1


def test_result_on_an_unqueued_task_conflicts(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """A result without a start (merge_status none) is refused (409)."""
    task = make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW)
    executor = _executor(owner_client, project)

    response = executor.post(
        RESULT_URL.format(task_id=task.pk),
        {"result": "succeeded", "sha": "deadbeef" * 5},
        format="json",
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "TASK_STATE_CONFLICT"
    assert not TaskTransition.objects.filter(task=task).exists()


def test_result_honors_a_stale_version_without_applying(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """FR-TSK-06 CAS on the result half too."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    response = executor.post(
        RESULT_URL.format(task_id=task.pk), _result_body(task, version=1), format="json"
    )
    assert response.status_code == 409, response.content
    assert response.json()["error"]["code"] == "VERSION_CONFLICT"
    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.merge_status == MergeStatus.MERGING, "nothing applied"
    assert task.version == 2


def test_result_idempotency_key_replays_without_a_second_transition(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """ADR-012: a retried report with the same key replays the outcome."""
    task = _merge_pending_task(project)
    executor = _executor(owner_client, project)
    assert (
        executor.post(
            START_URL.format(task_id=task.pk), _start_body(task), format="json"
        ).status_code
        == 200
    )

    headers: dict[str, Any] = {"HTTP_IDEMPOTENCY_KEY": "wp37-result-1"}
    body = _result_body(task, version=2)
    first = executor.post(RESULT_URL.format(task_id=task.pk), body, format="json", **headers)
    assert first.status_code == 200, first.content
    replay = executor.post(RESULT_URL.format(task_id=task.pk), body, format="json", **headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert TaskTransition.objects.filter(task=task).count() == 1
    assert Event.objects.filter(task_id=task.pk, type="merge.succeeded").count() == 1


def test_result_rejects_foreign_and_forbidden_callers(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Scope first, then the executor-only cell, then anonymous."""
    task = _merge_pending_task(project, 1)

    other = Project.objects.create(
        id="PID00006",
        name="Other",
        repo_path="/srv/repos/other-6",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )
    foreign_token = issue_agent_token(owner_client, other.pk, "merge_executor")
    foreign = agent_client(foreign_token).post(
        RESULT_URL.format(task_id=task.pk), _result_body(task), format="json"
    )
    assert foreign.status_code == 403
    assert foreign.json()["error"]["code"] == "AUTH_FORBIDDEN_PROJECT"

    token = issue_agent_token(owner_client, project.pk, "coder")
    refused = agent_client(token).post(
        RESULT_URL.format(task_id=task.pk), _result_body(task), format="json"
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "ROLE_NOT_PERMITTED"

    owner_post = owner_client.post(
        RESULT_URL.format(task_id=task.pk), _result_body(task), format="json"
    )
    assert owner_post.status_code == 403, "Section 12.2: Owner cell is Read only"
    assert owner_post.json()["error"]["code"] == "ROLE_NOT_PERMITTED"

    anonymous = APIClient().post(
        RESULT_URL.format(task_id=task.pk), _result_body(task), format="json"
    )
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTH_REQUIRED"

    # And nothing moved: the queue entry is untouched by every refusal.
    task.refresh_from_db()
    assert task.merge_status == MergeStatus.PENDING
    assert task.version == 1


def test_unknown_task_answers_task_not_found(owner_client: JsonAPIClient) -> None:
    """A well-formed but unknown id answers TASK_NOT_FOUND (404)."""
    executor_client = JsonAPIClient()
    token = issue_agent_token(owner_client, "PID00001", "merge_executor")
    executor_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token['token']}")
    for url, body in (
        (START_URL.format(task_id="PID00001-T999"), {}),
        (RESULT_URL.format(task_id="PID00001-T999"), {"result": "conflict"}),
    ):
        response = executor_client.post(url, body, format="json")
        assert response.status_code == 404, url
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND", url


def test_malformed_task_id_is_a_validation_error(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """Boundary validation (Section 7.3) answers VALIDATION_ERROR (400)."""
    executor = _executor(owner_client, project)
    response = executor.post(START_URL.format(task_id="not-a-task"), {}, format="json")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
