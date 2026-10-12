"""MT-1.8-02 — lease ownership and fencing validation for checkpoints
(Section 8.6 Expire/Fencing; ADR-012; FR-LEA-03).

Run with ``pytest backend/tests -k checkpoint_ownership -q``. The gate
is :func:`apps.tasks.services.checkpoints.submit_checkpoint`, and the
suite proves every acceptance path of the MT:

* the current owner with the current generation and a live lease passes
  — row stored, ``last_checkpoint_at`` moved, lease extended, one
  ``task.checkpoint`` event written;
* a checkpoint **after expiry** is rejected ``LEASE_EXPIRED`` with
  **zero writes** — no row, no touch, no extension, no event (Section
  8.6: "must not resurrect the lease");
* a **stale generation** after reclamation answers ``LEASE_EXPIRED``
  (ADR-012) — same zero-write guarantee;
* a **foreign session** on a live lease answers ``LEASE_NOT_OWNED``
  (403), again with nothing written;
* the **sweeper race**: a reclaim landing between claim and checkpoint
  always wins — the old owner's late checkpoint fails cleanly (the gate
  re-runs under the row lock inside the same transaction as the insert,
  closing the TOCTOU the Section 18 race test targets);
* **kind gating** (OQ-04's recorded outcome): ``progress``/``system``
  extend the lease; ``liveness`` extends only under the project's
  ``checkpoint_and_liveness`` mode — the default ``checkpoint_only``
  stores the row and event but leaves the lease untouched.

The true parallel-interleaving race needs real Postgres (SQLite's
no-op ``select_for_update`` cannot race — the MT-1.6-06 recorded
caveat); this suite proves the *logic-level* interleavings every one of
those schedules reduces to, and the gate's placement inside the write
transaction makes each of them lose. WP-1.15's concurrency suite
re-proves the timing on Postgres.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.accounts.exceptions import AuthForbiddenProject
from apps.events.models import Event
from apps.leases.exceptions import LeaseExpired, LeaseNotOwned
from apps.projects.models import LeaseExtensionMode, Project
from apps.tasks.exceptions import TaskNotFound
from apps.tasks.models import CheckpointKind, Task, TaskCheckpoint
from apps.tasks.services.checkpoints import CheckpointSubmission, submit_checkpoint
from apps.tasks.services.ids import is_valid_task_id

from .wp16_helpers import (  # noqa: F401  (restore_lease_registry: autouse)
    PASSWORD,  # noqa: F401  (re-exported for suites)
    active_policy_project,
    claim,
    make_pending_task,
    restore_lease_registry,
)

pytestmark = pytest.mark.django_db


def _claimed(**policy_fields: Any) -> tuple[Project, Task]:
    """One project with tuned policy and one task claimed by sess_owner."""
    project = active_policy_project(**policy_fields)
    task = make_pending_task(project, 1)
    claim(task, session_id="sess_owner")
    task.refresh_from_db()
    return project, task


def _submit(
    task: Task,
    *,
    session_id: str = "sess_owner",
    generation: int | None = None,
    **fields: Any,
) -> CheckpointSubmission:
    """Checkpoint *task* as its holder (or a supplied fencing pair)."""
    return submit_checkpoint(
        task.pk,
        session_id=session_id,
        lease_generation=task.lease_generation if generation is None else generation,
        caller_project_id=task.project_id,
        **fields,
    )


def _assert_zero_writes(task: Task, *, before_version: int) -> None:
    """Nothing at all was written: no row, no touch, no extension, no event."""
    assert not TaskCheckpoint.objects.filter(task=task).exists(), "no row stored"
    assert not Event.objects.filter(type="task.checkpoint").exists(), "no event"
    task.refresh_from_db()
    assert task.last_checkpoint_at is None, "no touch point"
    assert task.version == before_version, "no version movement at all"


# --- the happy path: current owner, current generation ----------------------


def test_current_owner_checkpoint_passes_the_gate() -> None:
    """Row + touch + extension + event, all in one go (FR-LEA-03)."""
    project, task = _claimed()
    before = timezone.now()

    submission = _submit(task, message="halfway there", percent=50)

    assert submission.checkpoint.task_id == task.pk
    assert submission.checkpoint.session_id == "sess_owner"
    assert submission.checkpoint.attempt_number == task.attempt_number
    assert submission.lease_extended is True
    assert submission.lease_expires_at is not None, "an extending checkpoint returns an expiry"
    low = before + timedelta(minutes=project.agent_policy.lease_duration_minutes)
    assert submission.lease_expires_at >= low, "the Section 8.6 formula applied"
    task.refresh_from_db()
    assert task.last_checkpoint_at == submission.checkpoint.timestamp
    event = Event.objects.get(type="task.checkpoint")
    assert event.task_id == task.pk
    assert event.actor_ref == "sess_owner"


def test_checkpoint_extends_the_stored_lease() -> None:
    """The task row's expiry moves to the submission's value (Section 8.6)."""
    _, task = _claimed()
    task.refresh_from_db()
    # Windows' wall clock advances in ~15.6 ms ticks, so a claim and a
    # checkpoint inside one tick compute the same min(now + duration, cap)
    # and the "deadline moved" assertion would flake. Start the stored
    # expiry short of now + duration — a correct extension must still move
    # it strictly forward (the formula is asserted by
    # test_current_owner_checkpoint_passes_the_gate above).
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() + timedelta(minutes=1))
    task.refresh_from_db()
    before_expiry = task.lease_expires_at

    submission = _submit(task)

    task.refresh_from_db()
    assert task.lease_expires_at == submission.lease_expires_at
    assert before_expiry is not None, "a live claim always carries an expiry"
    assert task.lease_expires_at is not None
    assert task.lease_expires_at > before_expiry, "an extension moved the deadline"
    assert submission.capped is False


# --- rejections: zero writes, no resurrection (Section 8.6 "Expire") --------


def test_expired_lease_is_rejected_with_lease_expired_and_zero_writes() -> None:
    """WP-1.8 acceptance: checkpoint after expiry rejected, nothing written."""
    _, task = _claimed()
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    task.refresh_from_db()

    with pytest.raises(LeaseExpired) as caught:
        _submit(task, message="late report")

    assert caught.value.status_code == 409
    _assert_zero_writes(task, before_version=task.version)


def test_stale_generation_after_reclaim_is_rejected() -> None:
    """ADR-012: a previous generation answers LEASE_EXPIRED, never writes."""
    _, task = _claimed()
    stale = task.lease_generation - 1
    version_before = task.version

    with pytest.raises(LeaseExpired):
        _submit(task, generation=stale)

    task.refresh_from_db()
    assert task.version == version_before
    assert not TaskCheckpoint.objects.filter(task=task).exists()


def test_foreign_session_on_a_live_lease_is_rejected() -> None:
    """Ownership: only the holding session checkpoints — LEASE_NOT_OWNED."""
    _, task = _claimed()
    version_before = task.version

    with pytest.raises(LeaseNotOwned) as caught:
        _submit(task, session_id="sess_intruder")

    assert caught.value.status_code == 403
    _assert_zero_writes(task, before_version=version_before)


def test_empty_session_identity_is_refused() -> None:
    """An empty session can never act as the holder (the pair must match)."""
    _, task = _claimed()
    version_before = task.version

    with pytest.raises(LeaseNotOwned):
        _submit(task, session_id="")

    _assert_zero_writes(task, before_version=version_before)


def test_unknown_task_answers_task_not_found() -> None:
    """Well-formed but unknown id: TASK_NOT_FOUND (404), nothing written."""
    project = active_policy_project()
    ghost = f"{project.pk}-T777"
    assert is_valid_task_id(ghost)

    with pytest.raises(TaskNotFound):
        submit_checkpoint(
            ghost, session_id="sess_owner", lease_generation=1, caller_project_id=project.pk
        )


def test_malformed_task_id_is_a_validation_error() -> None:
    """The boundary validates before the gate (Section 7.3)."""
    from rest_framework.exceptions import ValidationError

    with pytest.raises(ValidationError):
        submit_checkpoint("not-an-id", session_id="sess_owner", lease_generation=1)


def test_foreign_project_caller_is_refused_before_any_write() -> None:
    """ADR-004: a scoped token of another project answers AUTH_FORBIDDEN_PROJECT."""
    _, task = _claimed()
    version_before = task.version

    with pytest.raises(AuthForbiddenProject):
        submit_checkpoint(
            task.pk,
            session_id="sess_owner",
            lease_generation=task.lease_generation,
            caller_project_id="PID99999",
        )

    _assert_zero_writes(task, before_version=version_before)


# --- the sweeper race: the reclaim always wins (Section 18) -----------------


def test_sweeper_reclaim_beats_a_late_checkpoint() -> None:
    """A reclaim landing before the checkpoint leaves the old owner refused.

    Simulates the losing interleaving of the checkpoint-vs-expiry race:
    the sweeper expires the lease (T5's outcome — the WP-1.7 sweeper
    applies it), then the old owner's late checkpoint arrives. The gate
    re-runs under the row lock inside the write transaction, so the
    loser observes the dead lease and writes nothing at all.
    """
    _, task = _claimed()
    version_before = task.version
    # T5's outcome, applied between the claim and the late checkpoint:
    # the lease is dead (expired then swept back to pending by the claim
    # of a new generation — here just expired, the minimal dead state).
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    task.refresh_from_db()

    with pytest.raises(LeaseExpired):
        _submit(task, message="racing the sweeper")

    _assert_zero_writes(task, before_version=version_before)


def test_reclaimed_and_reclaimed_task_refuses_the_middle_owner() -> None:
    """Generation ordering: the second claim's owner passes, the first cannot."""
    from apps.tasks.state_machine.dispatcher import dispatch_transition

    _, task = _claimed()
    first_session = task.worker_session_id
    first_generation = task.lease_generation
    # The sweeper hands the task on: T5 (the real sweep), then re-claim.
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(minutes=1))
    swept = dispatch_transition(
        task_id=task.pk,
        trigger="lease_expired",
        actor_type="system",
        actor_ref="sweeper-sim",
    )
    claim(swept, session_id="sess_second")
    task.refresh_from_db()
    second_generation = task.lease_generation
    assert second_generation > first_generation

    # The first owner's late checkpoint: stale generation + dead lease.
    with pytest.raises(LeaseExpired):
        _submit(task, session_id=str(first_session), generation=first_generation)

    assert not TaskCheckpoint.objects.filter(task=task).exists()

    # The current owner still passes — the gate is not a blanket refusal.
    submission = _submit(task, session_id="sess_second")
    assert submission.checkpoint.session_id == "sess_second"


# --- kind gating (OQ-04's recorded outcome) ---------------------------------


@pytest.mark.parametrize("kind", [CheckpointKind.PROGRESS, CheckpointKind.SYSTEM])
def test_progress_and_system_checkpoints_extend(kind: str) -> None:
    """The two extension-carrying kinds under the default mode (Section 8.6)."""
    _, task = _claimed()

    submission = _submit(task, kind=kind)

    assert submission.lease_extended is True
    assert submission.checkpoint.kind == kind
    task.refresh_from_db()
    assert task.lease_expires_at == submission.lease_expires_at


def test_liveness_checkpoint_does_not_extend_under_the_default_mode() -> None:
    """``checkpoint_only`` (the default): stored, evented, no extension."""
    project, task = _claimed()
    assert project.agent_policy.lease_extension_mode == LeaseExtensionMode.CHECKPOINT_ONLY
    task.refresh_from_db()
    untouched_expiry = task.lease_expires_at

    submission = _submit(task, kind=CheckpointKind.LIVENESS, message="still alive")

    assert submission.lease_extended is False
    assert submission.checkpoint.kind == CheckpointKind.LIVENESS
    assert submission.lease_expires_at == untouched_expiry, "the lease did not move"
    task.refresh_from_db()
    assert task.lease_expires_at == untouched_expiry
    assert task.last_checkpoint_at == submission.checkpoint.timestamp, (
        "the row and the touch still happen — only the extension is gated"
    )
    assert Event.objects.filter(type="task.checkpoint").count() == 1


def test_liveness_checkpoint_extends_under_checkpoint_and_liveness() -> None:
    """The opt-in mode: a liveness ping carries the extension too (OQ-04)."""
    _, task = _claimed(
        lease_extension_mode=LeaseExtensionMode.CHECKPOINT_AND_LIVENESS,
    )
    task.refresh_from_db()
    untouched_expiry = task.lease_expires_at

    submission = _submit(task, kind=CheckpointKind.LIVENESS)

    assert submission.lease_extended is True
    assert submission.lease_expires_at is not None, "an extending checkpoint returns an expiry"
    assert untouched_expiry is not None, "a live claim always carries an expiry"
    assert submission.lease_expires_at > untouched_expiry


def test_extension_respects_the_hard_cap_end_to_end() -> None:
    """WP-1.8 acceptance: the checkpoint extension never passes the cap."""
    project, task = _claimed()
    acquired = timezone.now() - timedelta(minutes=230)
    Task.objects.filter(pk=task.pk).update(lease_acquired_at=acquired)
    task.refresh_from_db()
    cap = acquired + timedelta(minutes=project.agent_policy.lease_max_total_minutes)

    submission = _submit(task)

    assert submission.capped is True
    assert submission.lease_expires_at == cap
    task.refresh_from_db()
    assert task.lease_expires_at == cap


def test_one_event_per_accepted_checkpoint() -> None:
    """Exactly one ``task.checkpoint`` per accepted checkpoint (Section 9.6)."""
    _, task = _claimed()

    _submit(task, message="first")
    _submit(task, message="second")

    assert Event.objects.filter(type="task.checkpoint").count() == 2
    assert TaskCheckpoint.objects.filter(task=task).count() == 2
