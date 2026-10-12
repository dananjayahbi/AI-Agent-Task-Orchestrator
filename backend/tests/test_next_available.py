"""MT-1.6-02 — next-available selection (Section 9.3 last paragraph; FR-TSK-05).

Run with ``pytest backend/tests -k next_available -q``. Ordering,
eligibility filters and empty results run on the unit layer; the
concurrent-selector disjointness proof needs real skip-locked semantics
and lives in ``tests/integration/test_claim_race_postgres.py``.
"""

from __future__ import annotations

import pytest
from django.db.models import QuerySet
from django.utils import timezone

from apps.leases.claim import claim_next_available, eligible_work_queryset
from apps.tasks.models import Task, TaskState
from apps.tasks.services.dependencies import set_dependencies

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    make_pending_task,
    make_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _ids(queryset: QuerySet[Task]) -> list[str]:
    """Row ids of one offer query, in query order."""
    return [row.pk for row in queryset]


def test_ordering_is_priority_then_creation() -> None:
    """FR-TSK-05 + Section 9.3: urgent beats low; FIFO inside one priority."""
    project = active_policy_project()
    low = make_pending_task(project, 1, priority="low")
    urgent = make_pending_task(project, 2, priority="urgent")
    medium_a = make_pending_task(project, 3, priority="medium")
    medium_b = make_pending_task(project, 4, priority="medium")

    # Creates are sequential, so medium_a predates medium_b (FIFO tie-break).
    assert _ids(eligible_work_queryset(project, role="coder")) == [
        urgent.pk,
        medium_a.pk,
        medium_b.pk,
        low.pk,
    ]


def test_unmet_dependencies_are_not_offered() -> None:
    """FR-TSK-07: only completed-dependency tasks appear in the offer.

    The blocker itself stays pending and free, so it remains offerable —
    what must vanish is *waiting*, whose dependency is open.
    """
    project = active_policy_project()
    blocker = make_task(project, 1, state=TaskState.PENDING)
    waiting = make_pending_task(project, 2)
    ready = make_pending_task(project, 3)
    set_dependencies(task=waiting, dependency_ids=[blocker.pk])

    offered = _ids(eligible_work_queryset(project, role="coder"))

    assert waiting.pk not in offered, "unmet dependencies are never offered"
    assert offered == [blocker.pk, ready.pk]


def test_archived_and_non_pending_rows_are_excluded() -> None:
    """T19 default visibility + role state scope."""
    project = active_policy_project()
    archived = make_pending_task(project, 1, archived_at=timezone.now())
    draft = make_task(project, 2, state=TaskState.DRAFT)
    offerable = make_pending_task(project, 3)
    audit_row = make_task(project, 4, state=TaskState.TO_BE_AUDITED)

    coder = _ids(eligible_work_queryset(project, role="coder"))
    auditor = _ids(eligible_work_queryset(project, role="auditor"))

    assert coder == [offerable.pk]
    assert audit_row.pk in auditor
    assert archived.pk not in coder and draft.pk not in coder


def test_priority_filter_is_surfaced() -> None:
    """Section 9.2 "filters" — the priority half MT-1.6-02 must surface."""
    project = active_policy_project()
    low = make_pending_task(project, 1, priority="low")
    urgent = make_pending_task(project, 2, priority="urgent")

    assert _ids(eligible_work_queryset(project, role="coder", priority="urgent")) == [urgent.pk]
    assert _ids(eligible_work_queryset(project, role="coder", priority="low")) == [low.pk]


def test_next_available_claims_the_top_candidate() -> None:
    """Selection and claim are one operation (single round trip)."""
    project = active_policy_project()
    make_pending_task(project, 1, priority="low")
    top = make_pending_task(project, 2, priority="urgent")

    claimed = claim_next_available(
        caller_project_id=project.pk,
        session_id="sess_next_1",
        worker_agent_id="label-1",
    )

    assert claimed is not None and claimed.pk == top.pk
    assert claimed.state == TaskState.IN_PROGRESS
    assert claimed.lease_generation == 1


def test_next_available_returns_none_when_nothing_is_offerable() -> None:
    """Empty result, never an error (the bridge maps it to no-work)."""
    project = active_policy_project()
    make_task(project, 1, state=TaskState.DRAFT)

    assert (
        claim_next_available(
            caller_project_id=project.pk,
            session_id="sess_next",
            worker_agent_id="label",
        )
        is None
    )


def test_non_active_project_offers_no_work() -> None:
    """FR-PRJ-04: paused → empty offer, no claim attempted."""
    project = active_policy_project()
    type(project).objects.filter(pk=project.pk).update(active_status="paused")
    make_pending_task(project, 1)

    assert (
        claim_next_available(
            caller_project_id=project.pk,
            session_id="sess_next",
            worker_agent_id="label",
        )
        is None
    )


def test_consecutive_selections_receive_different_tasks() -> None:
    """Section 9.3: concurrent (here sequential) selectors never collide."""
    project = active_policy_project(max_concurrent_tasks=2)
    first = make_pending_task(project, 1, priority="urgent")
    second = make_pending_task(project, 2, priority="urgent")

    a = claim_next_available(
        caller_project_id=project.pk, session_id="sess_a", worker_agent_id="la"
    )
    b = claim_next_available(
        caller_project_id=project.pk, session_id="sess_b", worker_agent_id="lb"
    )

    assert a is not None and b is not None
    assert {a.pk, b.pk} == {first.pk, second.pk}
    assert a.pk != b.pk
