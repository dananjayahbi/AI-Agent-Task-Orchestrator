"""MT-1.6-06 — per-project max_concurrent_tasks at claim time (FR-LEA-08; G-26).

Run with ``pytest backend/tests -k concurrency_limit -q``. The check
itself lives in the wired T4 guard (inside the claim transaction, after
the row lock — Section 9.3 step 4); the simultaneous-at-the-boundary
proof runs on real Postgres in
``tests/integration/test_claim_race_postgres.py``.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.leases.claim import claim_task
from apps.leases.exceptions import ConcurrencyLimitReached
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import ClaimedRole, Task, TaskState, TaskTransition

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    install_event_recorder,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def test_claim_at_the_limit_is_concurrency_limit_reached() -> None:
    """Default limit 1: with one task running, the next claim is refused."""
    project = active_policy_project()  # max_concurrent_tasks default 1
    running = make_pending_task(project, 1)
    claim(running, session_id="sess_first")
    candidate = make_pending_task(project, 2)
    events = install_event_recorder()

    with pytest.raises(ConcurrencyLimitReached) as caught:
        claim(candidate, session_id="sess_second")

    assert caught.value.status_code == 409
    assert caught.value.limit == 1
    fresh = Task.objects.get(pk=candidate.pk)
    assert fresh.state == TaskState.PENDING, "refused claim leaves the row alone"
    assert fresh.version == 1 and fresh.lease_generation == 0
    assert not TaskTransition.objects.filter(task=fresh).exists()
    assert events == [], "no event fires for a refused claim"


def test_claim_below_the_limit_succeeds() -> None:
    """n-1 running: the boundary claim is admitted."""
    project = active_policy_project(max_concurrent_tasks=2)
    running = make_pending_task(project, 1)
    claim(running, session_id="sess_first")

    candidate = make_pending_task(project, 2)
    assert claim(candidate, session_id="sess_second").state == TaskState.IN_PROGRESS

    third = make_pending_task(project, 3)
    with pytest.raises(ConcurrencyLimitReached):
        claim(third, session_id="sess_third")


def test_raising_the_policy_admits_more_without_code_changes() -> None:
    """ADR-013: the limit is data (policy), not a constant."""
    project = active_policy_project()
    first = make_pending_task(project, 1)
    claim(first, session_id="sess_a")
    second = make_pending_task(project, 2)

    with pytest.raises(ConcurrencyLimitReached):
        claim(second, session_id="sess_b")

    project.agent_policy.max_concurrent_tasks = 2
    project.agent_policy.save(update_fields=["max_concurrent_tasks"])
    assert claim(second, session_id="sess_b").state == TaskState.IN_PROGRESS


def test_paused_project_fails_the_project_active_guard_first() -> None:
    """MT-1.6-06: the earlier guard answers, not CONCURRENCY_LIMIT_REACHED."""
    project = active_policy_project()
    running = make_pending_task(project, 1)
    claim(running, session_id="sess_first")
    type(project).objects.filter(pk=project.pk).update(active_status="paused")
    candidate = make_pending_task(project, 2)

    with pytest.raises(TaskStateConflict) as caught:
        claim(candidate, session_id="sess_second")

    assert "paused" in str(caught.value)


def test_count_is_coder_only() -> None:
    """Section 7.2 wording: the limit counts in_progress *coder* leases.

    A simulated future audit claim (``claimed_role=auditor`` — WP-3.3's
    T11 shape) does not consume the coder budget (recorded reading, the
    MT's risk note default).
    """
    project = active_policy_project()
    audit_side = make_pending_task(project, 1)
    Task.objects.filter(pk=audit_side.pk).update(
        state=TaskState.TO_BE_AUDITED,
        claimed_role=ClaimedRole.AUDITOR,
        worker_agent_id="sess-auditor-label",
        worker_session_id="sess_auditor",
        lease_acquired_at=timezone.now(),
        lease_expires_at=timezone.now() + timedelta(minutes=45),
    )

    candidate = make_pending_task(project, 2)
    assert claim(candidate, session_id="sess_coder").state == TaskState.IN_PROGRESS


def test_the_check_runs_on_the_locked_path() -> None:
    """Section 9.3 step 4: same transaction as the lock (single service call).

    The refusal happens inside ``claim_task``'s atomic block — proven by
    the full rollback asserted above (no lease, no history, no event,
    version untouched); a pre-lock count would leave partial writes.
    """
    project = active_policy_project()
    running = make_pending_task(project, 1)
    claim(running, session_id="sess_first")
    candidate = make_pending_task(project, 2)

    with pytest.raises(ConcurrencyLimitReached):
        claim_task(
            task_id=candidate.pk,
            session_id="sess_x",
            worker_agent_id="label",
            caller_project_id=project.pk,
        )

    fresh = Task.objects.get(pk=candidate.pk)
    assert (fresh.state, fresh.version, fresh.lease_generation) == (
        TaskState.PENDING,
        1,
        0,
    )
