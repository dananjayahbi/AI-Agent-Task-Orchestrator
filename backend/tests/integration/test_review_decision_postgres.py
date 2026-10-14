"""MT-3.6-04 on **real Postgres** — the review-decision race (Section 18).

The concurrency half of WP-3.6's stale-protection acceptance, on the
integration layer the plan reserves for it (Section 18; the unit-layer
semantics live in ``tests/test_review_endpoint.py``):

* **exactly one winner** — two concurrent review decisions on the same
  ``in_human_review`` row and the same ``version`` produce one 201 and
  one catalog 409, one Review Decision record, one Transition row and
  one ``review.decided`` event — the Section 8.2 single-transaction
  rule holding under real row locks;
* **the stale binding loses cleanly** — an approval carrying an
  outdated ``resolution_id`` (the coder re-submitted into a new
  attempt while the reviewer looked away, Section 14.2) answers
  ``VERSION_CONFLICT`` with zero T15 side effects on Postgres too;
* **NFR-12's decision class** — MT-1.15-03 recorded the review
  endpoint's deferral; this file is its follow-through: sequential and
  concurrent same-``Idempotency-Key`` replays store exactly one record
  and one transition.

Skipped automatically outside the integration layer or when Postgres is
unreachable — the skip reason carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev
"""

from __future__ import annotations

from typing import Any

import pytest
from rest_framework.test import APIClient

from apps.audit.models import ReviewDecision
from apps.projects.models import Project
from apps.tasks.models import (
    MergeStatus,
    Task,
    TaskResolution,
    TaskState,
    TaskTransition,
)
from tests.integration.race_harness import duplicate_posts, race, skip_reason
from tests.wp16_helpers import active_policy_project  # noqa: F401  (fixture)
from tests.wp32_helpers import (  # noqa: F401  (autouse fixtures promoted)
    _code,
    clean_throttle_cache,
    login_owner,
    restore_submission_registry,
)

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(skip_reason() is not None, reason=skip_reason() or "unreachable"),
]

REVIEW_URL = "/api/v1/tasks/{task_id}/review"


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (cookie transport)."""
    return login_owner()


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with the default policy."""
    return active_policy_project()


def _review_task(project: Project, index: int = 1) -> Task:
    """An ``in_human_review`` row with its current-attempt resolution."""
    task = Task.objects.create(
        id=f"{project.pk}-T{index:03d}",
        project=project,
        title="Review race target",
        state=TaskState.IN_HUMAN_REVIEW,
        attempt_number=1,
    )
    TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name=f"feat/{task.pk}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="integration review race seed",
        submitted_by_session="sess-integration-review-coder",
    )
    return task


def _approve_body(task: Task, **overrides: Any) -> dict[str, Any]:
    """An approve bound to the task's current resolution and version."""
    current = TaskResolution.objects.filter(task=task).order_by("-submitted_at").first()
    assert current is not None
    body: dict[str, Any] = {
        "decision": "approve",
        "resolution_id": str(current.pk),
        "version": task.version,
        "note": "integration approve",
    }
    body.update(overrides)
    return body


def _session_cookie(owner_client: APIClient) -> str:
    """The owner session cookie value raced requests must carry."""
    morsel = owner_client.cookies["sessionid"]
    assert morsel.value, "login_owner established a session cookie"
    return f"sessionid={morsel.value}"


def _post_review(owner_client: APIClient, task: Task, body: dict[str, Any], **kwargs: Any) -> Any:
    """One review POST through the real route (fresh client per call)."""
    client = APIClient()
    client.cookies.update(owner_client.cookies)
    return client.post(REVIEW_URL.format(task_id=task.pk), body, format="json", **kwargs)


# --- exactly one winner (MT-3.6-04 acceptance; Section 18 concurrency row) ---


def test_concurrent_approvals_have_exactly_one_winner(
    owner_client: APIClient, project: Project
) -> None:
    """Same task, same version, two approvals → one 201, one 409, one row."""
    task = _review_task(project)
    body = _approve_body(task)

    outcomes = race(2, lambda _index: _post_review(owner_client, task, body))

    statuses = sorted(response.status_code for response in outcomes)
    assert statuses == [201, 409], [response.content for response in outcomes]
    losers = [response for response in outcomes if response.status_code == 409]
    assert _code(losers[0]) in {"VERSION_CONFLICT", "TASK_STATE_CONFLICT"}

    assert ReviewDecision.objects.filter(task=task).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1
    task.refresh_from_db()
    assert task.merge_status == MergeStatus.PENDING, "the winner's single T15"


def test_concurrent_approve_and_request_changes_have_exactly_one_winner(
    owner_client: APIClient, project: Project
) -> None:
    """T15 vs T16 on one row: one decision lands, the loser 409s."""
    task = _review_task(project)
    approve = _approve_body(task)
    request_changes = {
        "decision": "request_changes",
        "note": "not so fast",
        "version": task.version,
    }

    outcomes = race(
        2,
        lambda index: _post_review(owner_client, task, approve if index == 0 else request_changes),
    )

    statuses = sorted(response.status_code for response in outcomes)
    assert statuses == [201, 409], [response.content for response in outcomes]
    assert ReviewDecision.objects.filter(task=task).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1


# --- the stale binding loses cleanly on Postgres ------------------------------


def test_outdated_resolution_approval_is_rejected_on_postgres(
    owner_client: APIClient, project: Project
) -> None:
    """Section 14.2 approve safety, pinned on the integration layer."""
    task = _review_task(project)
    stale = TaskResolution.objects.filter(task=task).first()
    assert stale is not None
    # The coder re-submitted: a new attempt now answers the row.
    Task.objects.filter(pk=task.pk).update(attempt_number=2)
    TaskResolution.objects.create(
        task=task,
        attempt_number=2,
        branch_name=f"feat/{task.pk}-v2",
        commit_sha="fedcba9876543210fedcba9876543210fedcba98",  # pragma: allowlist secret
        execution_summary="integration re-submission",
        submitted_by_session="sess-integration-review-coder-2",
    )
    task.refresh_from_db()

    response = _post_review(owner_client, task, _approve_body(task, resolution_id=str(stale.pk)))
    assert response.status_code == 409
    assert _code(response) == "VERSION_CONFLICT"

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.NONE, "zero T15 side effects"
    assert not ReviewDecision.objects.filter(task=task).exists()
    assert not TaskTransition.objects.filter(task=task).exists()


# --- NFR-12's decision class (MT-1.15-03's recorded follow-through) ----------


def test_review_decision_sequential_same_key_replay(
    owner_client: APIClient, project: Project
) -> None:
    """One record + one transition across a sequential retry (ADR-012)."""
    task = _review_task(project)
    headers: dict[str, Any] = {"HTTP_IDEMPOTENCY_KEY": "integration-review-key-1"}
    body = _approve_body(task)

    first = _post_review(owner_client, task, body, **headers)
    assert first.status_code == 201, first.content
    replay = _post_review(owner_client, task, body, **headers)
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert ReviewDecision.objects.filter(task=task).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1


def test_review_decision_concurrent_same_key_storm(
    owner_client: APIClient, project: Project
) -> None:
    """Byte-identical same-key POSTs: one stored decision, one transition."""
    task = _review_task(project)
    headers = {
        "HTTP_IDEMPOTENCY_KEY": "integration-review-key-2",
        "Cookie": _session_cookie(owner_client),
    }

    outcomes = duplicate_posts(6, REVIEW_URL.format(task_id=task.pk), _approve_body(task), headers)
    statuses = [response.status_code for response in outcomes]
    assert statuses.count(201) >= 1, statuses
    assert set(statuses) <= {201, 409}, statuses
    assert ReviewDecision.objects.filter(task=task).count() == 1
    assert TaskTransition.objects.filter(task=task).count() == 1
