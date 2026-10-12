"""MT-1.6-05 — lease fencing generation (Section 8.6; ADR-012; GOAL-2).

Run with ``pytest backend/tests -k lease_fencing -q``: strictly
increasing generations across claim→expire→reclaim cycles, the single
shared fencing helper's refusals, and no-write-on-reject.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.leases.exceptions import LeaseExpired, LeaseNotOwned
from apps.leases.fencing import require_current_lease
from apps.leases.release import release_task
from apps.tasks.models import Task, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    active_policy_project,
    claim,
    install_event_recorder,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def test_every_claim_increments_the_generation_by_exactly_one() -> None:
    """Section 8.6: 0 → 1 on first claim; +1 per subsequent claim."""
    project = active_policy_project()
    task = make_pending_task(project, 1)

    assert task.lease_generation == 0
    first = claim(task, session_id="sess_a")
    assert first.lease_generation == 1

    release = release_task(
        task_id=first.pk,
        session_id="sess_a",
        lease_generation=1,
        actor_type="agent",
        actor_ref="sess_a",
        caller_project_id=project.pk,
    )
    assert release.lease_generation == 1, "release does not bump (Section 8.6)"

    second = claim(release, session_id="sess_b")
    assert second.lease_generation == 2, "strictly increasing (GOAL-2)"


def test_generation_is_returned_in_the_lease_record() -> None:
    """Section 8.6's lease JSON carries ``lease_generation``."""
    from apps.leases.serializers import lease_record_payload

    project = active_policy_project()
    task = make_pending_task(project, 1)
    claimed = claim(task, session_id="sess_a")

    payload = lease_record_payload(claimed)

    assert payload["lease_generation"] == 1
    assert payload["session_id"] == "sess_a"
    assert payload["role"] == "coder"


def test_reclaim_after_expiry_yields_strictly_increasing_generations() -> None:
    """claim → expire (T5) → claim: 1, then 2 — never a reused value."""
    project = active_policy_project()
    task = make_pending_task(project, 1)

    first = claim(task, session_id="sess_a")
    Task.objects.filter(pk=first.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    swept = dispatch_transition(
        task_id=first.pk,
        trigger="lease_expired",
        actor_type="system",
        actor_ref="sweeper-sim",
    )
    assert swept.state == TaskState.PENDING
    assert swept.worker_session_id is None

    second = claim(swept, session_id="sess_b")
    assert second.lease_generation == 2
    assert first.lease_generation == 1  # the stale holder's view never moves


def test_stale_generation_is_rejected_without_writes() -> None:
    """A request carrying the previous generation after reclaim changes nothing."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    first = claim(task, session_id="sess_a")
    Task.objects.filter(pk=first.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    dispatch_transition(
        task_id=first.pk, trigger="lease_expired", actor_type="system", actor_ref="sweep"
    )
    reclaimed = claim(Task.objects.get(pk=first.pk), session_id="sess_b")  # gen 2
    events = install_event_recorder()
    version_before = reclaimed.version

    with pytest.raises(LeaseExpired):
        release_task(
            task_id=reclaimed.pk,
            session_id="sess_a",
            lease_generation=1,  # stale: current is 2
            actor_type="agent",
            actor_ref="sess_a",
            caller_project_id=project.pk,
        )

    fresh = Task.objects.get(pk=reclaimed.pk)
    assert fresh.version == version_before
    assert fresh.worker_session_id == "sess_b", "the new holder stands"
    assert events == [], "a refused mutation emits nothing"
    transitions = TaskTransition.objects.filter(task=reclaimed).count()
    assert transitions == 3, "claim, T5, reclaim only — the refusal added none"


def test_helper_accepts_the_live_owner() -> None:
    """The one fencing helper stays silent for the current holder."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claimed = claim(task, session_id="sess_owner")

    # No raise: the holder's current pair passes (the helper returns None).
    require_current_lease(
        claimed, session_id="sess_owner", lease_generation=claimed.lease_generation
    )


def test_helper_refusals_use_only_catalog_lease_errors() -> None:
    """Missing pair → NOT_OWNED; stale fence → EXPIRED; foreign → NOT_OWNED."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claimed = claim(task, session_id="sess_owner")

    with pytest.raises(LeaseNotOwned):
        require_current_lease(claimed, session_id=None, lease_generation=None)
    with pytest.raises(LeaseExpired):
        require_current_lease(
            claimed, session_id="sess_owner", lease_generation=claimed.lease_generation + 7
        )
    with pytest.raises(LeaseNotOwned):
        require_current_lease(
            claimed, session_id="sess_other", lease_generation=claimed.lease_generation
        )


def test_helper_refuses_a_dead_lease_even_for_the_holder() -> None:
    """Expired-but-unswept: the holder itself gets LEASE_EXPIRED (8.6)."""
    project = active_policy_project()
    task = make_pending_task(project, 1)
    claimed = claim(task, session_id="sess_owner")
    Task.objects.filter(pk=claimed.pk).update(
        lease_expires_at=timezone.now() - timedelta(minutes=1)
    )
    claimed.refresh_from_db()

    with pytest.raises(LeaseExpired):
        require_current_lease(
            claimed, session_id="sess_owner", lease_generation=claimed.lease_generation
        )
