"""MT-3.3-03 — audit lease acquire/extend and T12 expiry release.

Run with ``pytest backend/tests -k audit_lease -q``. Section 8.2 gives
auditors the same lease discipline as coders: **T11** sets the audit
lease ("same lease rules" — Section 8.6 acquire, policy duration, hard
cap, fencing generation), checkpoints extend through the *existing*
extension function (no parallel logic), and **T12** releases an expired
audit lease in the same 60 s sweeper cadence as T5 — incrementing
``audit_retry_count`` only, never leaving ``to_be_audited``, and never
touching the resolution (Section 19 WP-3.3 acceptance: "expiry releases
the audit claim without losing the resolution").
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.transitions import ensure_audit_wired
from apps.leases.extension import extend_lease
from apps.leases.sweeper import sweep_expired_leases
from apps.projects.models import Project
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import Task, TaskResolution, TaskState, TaskTransition
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp33_helpers import (
    active_policy_project,
    agent_client,
    auditable_task,
    claim_as_auditor,
    clean_throttle_cache,  # noqa: F401  (autouse)
    install_event_recorder,
    issue_agent_token,
    login_owner_client,
    restore_audit_registry,  # noqa: F401  (autouse)
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client() -> APIClient:
    """A logged-in owner session (Section 9.2's owner-only rows)."""
    return login_owner_client()


@pytest.fixture
def project() -> Project:
    """One active project (PID00001) with a tuned 30-minute audit lease."""
    return active_policy_project(lease_duration_minutes=30, lease_max_total_minutes=120)


def _auditor_client(owner_client: APIClient) -> APIClient:
    return agent_client(issue_agent_token(owner_client, "PID00001", "auditor"))


def _expire(task: Task) -> None:
    """Backdate the stored lease past now (the sweeper's input, honestly)."""
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    task.refresh_from_db()


# --- T11: acquire -----------------------------------------------------------


def test_t11_claim_sets_the_policy_shaped_audit_lease(
    owner_client: APIClient, project: Project
) -> None:
    """Duration from policy, generation +1, role auditor, attempt intact."""
    task = auditable_task(project, 1)

    response = claim_as_auditor(_auditor_client(owner_client), task.pk)

    assert response.status_code == 200, response.content
    lease = response.json()["lease"]
    task.refresh_from_db()
    assert task.claimed_role == "auditor"
    assert task.lease_acquired_at is not None and task.lease_expires_at is not None
    window = task.lease_expires_at - task.lease_acquired_at
    assert timedelta(minutes=29) <= window <= timedelta(minutes=31), "policy duration (30m)"
    assert task.lease_generation == 1, "Section 8.6 fencing: every claim increments"
    assert task.attempt_number == 1, "coder claims only bump the attempt (Section 7.2)"
    assert lease["role"] == "auditor"
    assert response.json()["task"]["claimed_role"] == "auditor"


def test_auditor_checkpoint_extension_reuses_the_shared_formula(
    owner_client: APIClient, project: Project
) -> None:
    """Section 8.6 extend: min(now+duration, acquired+cap) — capped flag."""
    task = auditable_task(project, 1)
    claimed = claim_as_auditor(_auditor_client(owner_client), task.pk)
    assert claimed.status_code == 200, claimed.content
    task.refresh_from_db()
    # Age the lease so the hard cap (120 min) clamps before now+30.
    aged = timezone.now() - timedelta(minutes=100)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=aged)
    task.refresh_from_db()

    extension = extend_lease(
        task_id=task.pk,
        session_id="sess_wp33_auditor",
        lease_generation=task.lease_generation,
    )

    cap = aged + timedelta(minutes=120)
    assert extension.lease_expires_at == cap, "hard cap wins over now + duration"
    assert extension.capped is True
    task.refresh_from_db()
    assert task.lease_expires_at == cap
    # A foreign session still dies at the shared fencing gate (no second
    # implementation — MT-1.6-05).
    from apps.leases.exceptions import LeaseNotOwned

    with pytest.raises(LeaseNotOwned):
        extend_lease(
            task_id=task.pk,
            session_id="sess_wp33_intruder",
            lease_generation=task.lease_generation,
        )


# --- T12: expiry release ----------------------------------------------------


def test_t12_expiry_releases_only_the_audit_side(owner_client: APIClient, project: Project) -> None:
    """Sweeper dispatches T12: lease cleared, audit_retry_count + 1, state
    held, resolution intact, coder counters untouched (8.2 / 19)."""
    events = install_event_recorder()
    task = auditable_task(project, 1)
    resolution = TaskResolution.objects.get(task=task, attempt_number=1)
    claimed = claim_as_auditor(_auditor_client(owner_client), task.pk)
    assert claimed.status_code == 200, claimed.content
    task.refresh_from_db()
    assert task.lease_expires_at is not None
    _expire(task)

    report = sweep_expired_leases()

    assert report.audit_released == 1, report
    assert report.reclaimed == 0 and report.escalated == 0, report
    task.refresh_from_db()
    assert task.state == TaskState.TO_BE_AUDITED, "T12 never leaves the state"
    assert task.worker_session_id is None
    assert task.worker_agent_id is None
    assert task.claimed_role is None
    assert task.lease_acquired_at is None and task.lease_expires_at is None
    assert task.audit_retry_count == 1, "the audit retry counter increments"
    assert task.failure_retry_count == 0, "the coder budget is untouched (8.3 invariant 1)"
    assert task.attempt_number == 1, "attempt_number is coder history"
    assert task.version == 3, "T11 claim +1 and T12 release +1 (two dispatches)"
    # The resolution and its identity survive verbatim.
    resolution.refresh_from_db()
    assert resolution.submitted_by_session == "sess_wp33_coder"
    transition = TaskTransition.objects.filter(task=task).latest("timestamp")
    assert transition.from_state == TaskState.TO_BE_AUDITED
    assert transition.to_state == TaskState.TO_BE_AUDITED
    assert transition.reason_code == "lease_expired"
    assert transition.actor_type == "system"
    expiry_events = [record for record in events if record["type"] == "task.lease_expired"]
    assert len(expiry_events) == 1, "Section 9.6: the existing catalog event, once"
    assert expiry_events[0]["data"]["to_state"] == TaskState.TO_BE_AUDITED


def test_a_new_independent_auditor_can_claim_after_t12(
    owner_client: APIClient, project: Project
) -> None:
    """Re-claim works (subject to MT-3.3-02) with a fresh generation."""
    task = auditable_task(project, 1, coder_session="sess_wp33_coder")
    first = claim_as_auditor(_auditor_client(owner_client), task.pk, session_id="sess_wp33_aud_one")
    assert first.status_code == 200, first.content
    task.refresh_from_db()
    _expire(task)

    sweep_expired_leases()

    second = claim_as_auditor(
        _auditor_client(owner_client), task.pk, session_id="sess_wp33_aud_two"
    )
    assert second.status_code == 200, second.content
    task.refresh_from_db()
    assert task.claimed_role == "auditor"
    assert task.lease_generation == 2, "each claim increments the fencing generation"
    assert task.audit_retry_count == 1, "the T12 release stays on the record"


def test_t12_dispatch_on_an_active_lease_is_refused(
    owner_client: APIClient, project: Project
) -> None:
    """The guard re-checks under the lock (defensive; 409 family)."""
    task = auditable_task(project, 1)
    claimed = claim_as_auditor(_auditor_client(owner_client), task.pk)
    assert claimed.status_code == 200, claimed.content

    ensure_audit_wired()
    with pytest.raises(TaskStateConflict):
        dispatch_transition(
            task_id=task.pk,
            trigger="audit_lease_expired",
            actor_type="system",
            actor_ref="lease-sweeper",
        )
    task.refresh_from_db()
    assert task.claimed_role == "auditor", "the live lease stands"


def test_one_sweep_runs_both_coder_and_audit_branches(
    owner_client: APIClient, project: Project
) -> None:
    """T5 and T12 side by side — one sweeper, two selection branches."""
    # The coder half: claim a pending task through the real service.
    from .wp33_helpers import make_pending_task

    coder_task = make_pending_task(project, 1)
    coder_client = agent_client(issue_agent_token(owner_client, project.pk, "coder"))
    coder_claim = coder_client.post(
        f"/api/v1/tasks/{coder_task.pk}/claim",
        {"session_id": "sess_wp33_coder1", "worker_agent_id": "wp33-coder"},
    )
    assert coder_claim.status_code == 200, coder_claim.content

    audit_task = auditable_task(project, 2)
    audit_claim = claim_as_auditor(_auditor_client(owner_client), audit_task.pk)
    assert audit_claim.status_code == 200, audit_claim.content

    _expire(coder_task)
    _expire(audit_task)

    report = sweep_expired_leases()

    assert report.reclaimed == 1, report
    assert report.audit_released == 1, report
    assert report.escalated == 0 and report.skipped == 0, report
    coder_task.refresh_from_db()
    assert coder_task.state == TaskState.PENDING, "T5 unchanged (Section 8.3 invariant 1)"
    assert coder_task.failure_retry_count == 1
    assert coder_task.audit_retry_count == 0, "the audit counter is not the coder's"
    audit_task.refresh_from_db()
    assert audit_task.state == TaskState.TO_BE_AUDITED
    assert audit_task.audit_retry_count == 1
    assert audit_task.failure_retry_count == 0


def test_an_unexpired_audit_lease_is_left_alone(owner_client: APIClient, project: Project) -> None:
    """A run of nothing to do is a clean no-op (idempotent sweep)."""
    task = auditable_task(project, 1)
    assert claim_as_auditor(_auditor_client(owner_client), task.pk).status_code == 200

    report = sweep_expired_leases()

    assert report.processed == 0, report
    task.refresh_from_db()
    assert task.claimed_role == "auditor"
