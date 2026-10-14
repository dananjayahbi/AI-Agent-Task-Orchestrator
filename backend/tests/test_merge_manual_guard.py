"""MT-3.7-04 — the queue-side ``manual`` guard (OQ-06) on the real API.

Scope line of the MT: "implement the queue-side guard so an accidentally
enqueued manual task is resolved without performing a merge, and
coordinate with the WP-3.6 approval path" — acceptance: ``manual`` tasks
never trigger an executor merge (Section 8.3 invariant 2's recorded
exception; OQ-06 decided 2026-10-11).

* ``GET /merge/pending`` resolves a ``merge_status = pending`` carrier
  of a ``merge_strategy = manual`` project through the wired **T20
  ``merge_manual``** transition — ``completed`` + ``merge_status =
  none`` + one history row + the cataloged ``task.transitioned`` event
  — and never returns it to the caller: no merge attempt is possible;
* executable-strategy projects are untouched by the guard (role-scoped:
  squash/merge_commit/fast_forward_only entries still list);
* T20 itself refuses a non-manual project and a non-carrier state
  (TASK_STATE_CONFLICT) so the exception can never widen.

Recorded reading (flagged in the WP changelog): OQ-06's fourth value
``manual`` is accepted at the DB/state-machine layer — the plan's §7.2
table lists only the three executable values, so
``apps.projects.models.MergeStrategy.choices`` (outside this WP's touch
area) has not been widened; the policy PATCH serializer gains the value
with the policy-form work (WP-4.10-03). Direct policy-row writes set it
here, exactly as OQ-06 describes.

Run with ``pytest backend/tests -k merge_manual -q``.
"""

from __future__ import annotations

import pytest

from apps.events.models import Event
from apps.merge.transitions import ensure_merge_wired
from apps.projects.models import Project, ProjectPolicy
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import MergeStatus, Task, TaskResolution, TaskState, TaskTransition
from apps.tasks.models.transitions import TransitionReason
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp15_helpers import make_project, make_task
from .wp16_helpers import restore_lease_registry  # noqa: F401  (autouse)
from .wp33_helpers import (  # noqa: F401  (autouse: registry restore + throttle cache)
    JsonAPIClient,
    login_owner_client,
    restore_audit_registry,
)

PENDING_URL = "/api/v1/merge/pending"

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> JsonAPIClient:
    """A logged-in owner session (cookie transport), fresh per test."""
    return login_owner_client()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the manual-guard suites."""
    return make_project(name="WP-3.7 manual guard")


def _set_strategy(project: Project, value: str) -> None:
    """Write ``merge_strategy`` on the policy row (no serializer in the way)."""
    policy: ProjectPolicy = project.agent_policy
    policy.merge_strategy = value
    policy.save(update_fields=["merge_strategy"])
    project.refresh_from_db()


def _merge_pending_task(project: Project, index: int = 1) -> Task:
    """A merge-pending carrier (T15's approve outcome) with its resolution."""
    task = make_task(
        project,
        index,
        state=TaskState.IN_HUMAN_REVIEW,
        merge_status=MergeStatus.PENDING,
        attempt_number=1,
    )
    TaskResolution.objects.create(
        task=task,
        attempt_number=1,
        branch_name=f"feat/{project.pk}-T{index:03d}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="wp37 manual guard seed",
        submitted_by_session="sess_wp37_coder",
    )
    return task


# --- the queue-side guard: resolved without a merge ---------------------------


def test_pending_listing_resolves_a_manual_entry_without_a_merge(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """OQ-06: the accidentally enqueued manual task completes, never lists."""
    _set_strategy(project, "manual")
    task = _merge_pending_task(project)

    response = owner_client.get(PENDING_URL)
    assert response.status_code == 200, response.content
    assert task.pk not in {row["id"] for row in response.json()["results"]}, (
        "a manual entry must never reach the executor"
    )

    task.refresh_from_db()
    assert task.state == TaskState.COMPLETED
    assert task.merge_status == MergeStatus.NONE, "no merge step happened (OQ-06)"
    assert task.version == 2, "exactly one transition, no extra writes"

    assert TaskTransition.objects.filter(
        task=task, reason_code=TransitionReason.MERGE_MANUAL
    ).exists(), "T20 wrote its FR-TSK-04 history row"
    assert Event.objects.filter(task_id=task.pk, type="task.transitioned").exists()
    assert not Event.objects.filter(
        task_id=task.pk, type__in=("merge.succeeded", "merge.failed")
    ).exists(), "no merge event may be fabricated for a manual completion"


def test_pending_listing_still_offers_executable_strategy_entries(
    owner_client: JsonAPIClient, project: Project
) -> None:
    """The guard is strategy-scoped: squash entries list unchanged."""
    task = _merge_pending_task(project)

    response = owner_client.get(PENDING_URL)
    assert response.status_code == 200, response.content
    assert task.pk in {row["id"] for row in response.json()["results"]}

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.merge_status == MergeStatus.PENDING
    assert task.version == 1, "an executable project's carrier is never auto-completed"


# --- T20 itself: the exception never widens -----------------------------------


def test_t20_completes_a_manual_carrier_with_history_and_event(project: Project) -> None:
    """The service-level transition behind the queue guard."""
    ensure_merge_wired()
    _set_strategy(project, "manual")
    task = _merge_pending_task(project)

    dispatched = dispatch_transition(
        task_id=task.pk,
        trigger="merge_manual",
        actor_type="agent",
        actor_ref="merge-queue",
    )
    assert dispatched.state == TaskState.COMPLETED

    task.refresh_from_db()
    assert task.merge_status == MergeStatus.NONE
    row = TaskTransition.objects.get(task=task, reason_code=TransitionReason.MERGE_MANUAL)
    assert row.from_state == TaskState.IN_HUMAN_REVIEW
    assert row.to_state == TaskState.COMPLETED
    assert row.actor_type == "agent"


def test_t20_refuses_executable_projects_and_non_carrier_states(project: Project) -> None:
    """Both guards answer TASK_STATE_CONFLICT (never a silent completion)."""
    ensure_merge_wired()

    executable = _merge_pending_task(project, 1)
    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=executable.pk,
            trigger="merge_manual",
            actor_type="agent",
            actor_ref="merge-queue",
        )
    executable.refresh_from_db()
    assert executable.state == TaskState.IN_HUMAN_REVIEW
    assert executable.merge_status == MergeStatus.PENDING

    _set_strategy(project, "manual")
    draft_carrier = make_task(
        project,
        2,
        state=TaskState.PENDING,
        merge_status=MergeStatus.PENDING,
    )
    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=draft_carrier.pk,
            trigger="merge_manual",
            actor_type="agent",
            actor_ref="merge-queue",
        )
    draft_carrier.refresh_from_db()
    assert draft_carrier.state == TaskState.PENDING
