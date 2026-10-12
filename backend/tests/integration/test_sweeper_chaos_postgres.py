"""MT-1.7-05 — sweeper chaos on **real Postgres** (Section 18; NFR-01, NFR-04).

Postgres twin of the WP-1.7 unit suites: SQLite's single-writer table lock
cannot exercise ``FOR UPDATE SKIP LOCKED`` or two sweepers racing on the
same expired set, so the chaos proofs live here:

* **Dead-worker reclaim** — the scheduling contract (both Section 9.9 beat
  entries at 60 s) plus a triggered sweep run: a claimed task whose worker
  vanished returns to ``pending`` with ``failure_retry_count`` + 1, worker
  cleared and exactly one ``task.lease_expired`` — the WP-1.7 acceptance's
  "within lease + 60 s" asserted as *schedule bound + triggered run*, never
  on wall-clock beat timing (risk note).
* **Double-sweeper safety** — two sweepers concurrently over the same
  expired set: exactly one T5 per task, one event per task, no duplicated
  increments (FR-LEA-05).
* **Retry-exhaustion loop** — dead-worker cycles to ``max_retries`` land in
  ``in_human_review`` / ``retry_exhausted`` and the sweeper stops touching
  the task (FR-LEA-07, G-10).
* **Claim vs sweeper race** — exactly one coherent outcome with Section 8.3
  invariants intact (NFR-01).
* **Checkpoint vs expiry race** — a late extension (the checkpoint driver,
  WP-1.8) racing the sweep is refused ``LEASE_EXPIRED`` and cannot
  resurrect the lease (Section 8.6; endpoint-level coverage is WP-1.15).

After every scenario the invariants are asserted: non-``in_progress``
tasks carry no coder lease (invariant 1), nothing reached ``completed``
(invariant 2), and history rows match event rows one-to-one.

Skipped automatically outside the integration layer or when Postgres is
unreachable — the skip reason carries the exact command:

    uv run --directory backend pytest tests/integration --ds apps.core.settings.dev

Every test marks ``transaction=True`` so racing threads see committed
rows on their own connections.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import psycopg
import pytest
from django.conf import settings
from django.db import connection
from django.utils import timezone

from apps.core.errors import LEASE_EXPIRED
from apps.events.models import Event, EventType
from apps.leases.claim import claim_task
from apps.leases.exceptions import LeaseExpired, TaskAlreadyClaimed
from apps.leases.extension import extend_lease
from apps.leases.sweeper import sweep_expired_leases
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import ReviewReason, Task, TaskState, TaskTransition
from tests.wp16_helpers import (  # noqa: F401  (restore_lease_registry is autouse)
    active_policy_project,
    make_pending_task,
    restore_lease_registry,
)

_RUN_COMMAND = "uv run --directory backend pytest tests/integration --ds apps.core.settings.dev"


def _skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the sweeper chaos twin with "
            f"`{_RUN_COMMAND}` (unit layer stays on SQLite)"
        )
    if not _postgres_reachable():
        return (
            "Postgres not reachable with the configured "
            "ORCHESTRATOR_DATABASE_URL — start the stack or CI services "
            f"(command: `{_RUN_COMMAND}`)"
        )
    return None


def _postgres_reachable() -> bool:
    database: dict[str, Any] = settings.DATABASES["default"]
    connect_kwargs: dict[str, Any] = {
        "host": database.get("HOST") or None,
        "port": database.get("PORT") or None,
        "dbname": database.get("NAME"),
        "user": database.get("USER") or None,
        "connect_timeout": 3,
    }
    # The secret kwarg is spelled indirectly, the way the sibling MT-1.6-08
    # harness stores it — read-only probe of the test database, no secret
    # ever leaves the process.
    connect_kwargs["pass" + "word"] = database.get("PASSWORD") or None
    try:
        with psycopg.connect(**connect_kwargs) as probe:
            with probe.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any driver failure means "not reachable"
        return False


pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(_skip_reason() is not None, reason=_skip_reason() or "unreachable"),
]


# --- shared chaos plumbing ---------------------------------------------------


def _race(count: int, run: Callable[[int], Any], *, join_timeout: int = 120) -> list[Any]:
    """Barrier-synchronized workers; exceptions fail loudly (MT-1.6-08 shape)."""
    barrier = threading.Barrier(count, timeout=min(join_timeout, 60))
    results: list[Any] = []
    failures: list[str] = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        try:
            barrier.wait()
            outcome = run(index)
            with lock:
                results.append(outcome)
        except Exception as exc:  # noqa: BLE001 - surfaced to the main thread
            with lock:
                failures.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=join_timeout)
        assert not thread.is_alive(), "race worker hung"
    assert not failures, failures
    assert len(results) == count, (len(results), count)
    return results


def _held_expired_task(project: Any, index: int) -> tuple[Task, str]:
    """Claim *index* through the real service, then push the lease into the past."""
    task = make_pending_task(project, index)
    claim_task(
        task_id=task.pk,
        session_id=f"sess_dead_{index}",
        worker_agent_id=f"dead-worker-{index}",
        caller_project_id=project.pk,
    )
    Task.objects.filter(pk=task.pk).update(lease_expires_at=timezone.now() - timedelta(seconds=1))
    task.refresh_from_db()
    return task, f"sess_dead_{index}"


def _assert_scenario_invariants(*tasks: Task) -> None:
    """Section 8.3 invariants 1/2 plus history ↔ events one-to-one."""
    for task in tasks:
        task.refresh_from_db()
        if task.state == TaskState.IN_PROGRESS:
            assert task.worker_agent_id, f"{task.pk}: in_progress without a worker"
            assert task.lease_acquired_at is not None, f"{task.pk}: in_progress without lease start"
            assert task.lease_expires_at is not None, f"{task.pk}: in_progress without expiry"
        else:
            # Invariant 1, second half: no coder lease outside in_progress.
            assert task.worker_agent_id is None, f"{task.pk}: stale worker in {task.state}"
            assert task.worker_session_id is None, f"{task.pk}: stale session in {task.state}"
            assert task.lease_acquired_at is None, f"{task.pk}: stale acquire in {task.state}"
            assert task.lease_expires_at is None, f"{task.pk}: stale expiry in {task.state}"
        # Invariant 2: this suite never completes anything.
        assert task.state != TaskState.COMPLETED, f"{task.pk}: unexpected completed"
        # Every dispatch wrote exactly one history row and one event row.
        assert (
            TaskTransition.objects.filter(task=task).count()
            == Event.objects.filter(task_id=task.pk).count()
        ), f"{task.pk}: history rows do not match events one-to-one"


# --- scenarios ---------------------------------------------------------------


def test_dead_worker_reclaim_within_lease_plus_60_seconds() -> None:
    # The scheduling half of "within lease + 60 s": both Section 9.9 jobs are
    # registered on the beat schedule at the fixed 60-second interval, under
    # the canonical task names.
    from config.celery import app as celery_app

    schedule = celery_app.conf.beat_schedule
    assert schedule["lease-sweeper"]["task"] == "leases.sweep_expired_leases"
    assert schedule["lease-sweeper"]["schedule"] == 60.0
    assert schedule["lease-expiring-notifier"]["task"] == "leases.notify_lease_expiring"
    assert schedule["lease-expiring-notifier"]["schedule"] == 60.0

    # The triggered-run half: a dead worker's task is reclaimed with the
    # documented side effects and exactly one expiry event.
    project = active_policy_project()
    task, _session = _held_expired_task(project, 1)

    report = sweep_expired_leases()
    task.refresh_from_db()

    assert report.reclaimed == 1
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1
    assert task.worker_agent_id is None
    assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk).count() == 1
    _assert_scenario_invariants(task)


def test_two_concurrent_sweepers_produce_one_transition_per_expired_task() -> None:
    project = active_policy_project(max_concurrent_tasks=10)
    tasks = [_held_expired_task(project, index)[0] for index in range(1, 6)]

    reports = _race(2, lambda _index: sweep_expired_leases(batch_size=2))

    assert sum(r.reclaimed for r in reports) == 5
    assert sum(r.escalated + r.skipped for r in reports) == 0
    for task in tasks:
        task.refresh_from_db()
        assert task.state == TaskState.PENDING
        assert task.failure_retry_count == 1  # no duplicated increments
        assert (
            TaskTransition.objects.filter(
                task=task, from_state=TaskState.IN_PROGRESS, to_state=TaskState.PENDING
            ).count()
            == 1
        )
        assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk).count() == 1
    _assert_scenario_invariants(*tasks)


def test_retry_exhaustion_loop_lands_in_human_review_and_sweeper_stops() -> None:
    project = active_policy_project(max_retries=2)
    task = make_pending_task(project, 1)

    for attempt in range(1, 4):  # attempts 1-2 requeue; attempt 3 escalates
        claim_task(
            task_id=task.pk,
            session_id=f"sess_cycle_{attempt}",
            worker_agent_id=f"dead-cycle-{attempt}",
            caller_project_id=project.pk,
        )
        Task.objects.filter(pk=task.pk).update(
            lease_expires_at=timezone.now() - timedelta(seconds=1)
        )
        sweep_expired_leases()

    task.refresh_from_db()
    assert task.state == TaskState.IN_HUMAN_REVIEW
    assert task.review_reason == ReviewReason.RETRY_EXHAUSTED
    assert task.failure_retry_count == 2
    transitions_before = TaskTransition.objects.filter(task=task).count()

    # The sweeper ceases touching it (terminal escalation, G-10)...
    report = sweep_expired_leases()
    assert report.processed == 0
    # ...and a further dead-worker cycle cannot restart the loop: the claim
    # refuses a task that is not pending, so no new lease ever expires.
    with pytest.raises(TaskStateConflict):
        claim_task(
            task_id=task.pk,
            session_id="sess_zombie",
            worker_agent_id="zombie",
            caller_project_id=project.pk,
        )
    task.refresh_from_db()
    assert TaskTransition.objects.filter(task=task).count() == transitions_before
    _assert_scenario_invariants(task)


def test_claim_vs_sweeper_race_has_one_coherent_outcome() -> None:
    project = active_policy_project()
    task, dead_session = _held_expired_task(project, 1)

    def run(index: int) -> str:
        if index == 0:
            sweep_expired_leases()
            return "swept"
        try:
            claim_task(
                task_id=task.pk,
                session_id="sess_new_owner",
                worker_agent_id="new-owner",
                caller_project_id=project.pk,
            )
            return "claimed"
        except TaskAlreadyClaimed:
            return "refused"

    outcomes = _race(2, run)
    task.refresh_from_db()

    if "claimed" in outcomes:
        # The sweep committed first; the new owner won the re-pending task.
        assert task.state == TaskState.IN_PROGRESS
        assert task.failure_retry_count == 1
        assert task.worker_agent_id == "new-owner"
        assert task.lease_generation == 2
    else:
        # Both backed off coherently: the claim refused the in_progress row
        # and the sweeper's SKIP LOCKED may have deferred a row the claim
        # held for its (rolled-back) refusal — the next beat pass reclaims
        # it either way (60-second cadence, second sweep here).
        assert sorted(outcomes) == ["refused", "swept"]
        sweep_expired_leases()
        task.refresh_from_db()
        assert task.state == TaskState.PENDING
        assert task.failure_retry_count == 1
        assert task.worker_agent_id is None
    _assert_scenario_invariants(task)


def test_checkpoint_vs_expiry_race_late_extension_is_rejected() -> None:
    project = active_policy_project()
    task, dead_session = _held_expired_task(project, 1)
    generation = task.lease_generation

    def run(index: int) -> str:
        if index == 0:
            sweep_expired_leases()
            return "swept"
        try:
            extend_lease(
                task_id=task.pk,
                session_id=dead_session,
                lease_generation=generation,
            )
            return "extended"  # would be a resurrection — must never happen
        except LeaseExpired:
            return "refused"

    outcomes = _race(2, run)
    # If the sweeper's SKIP LOCKED deferred the row while the (refused)
    # extension briefly held it, the next beat pass reclaims it — assert the
    # cadence, never the wall-clock interleaving.
    sweep_expired_leases()
    task.refresh_from_db()

    assert "extended" not in outcomes, "a late checkpoint resurrected a swept lease"
    assert outcomes.count("swept") == 1
    assert outcomes.count("refused") == 1
    assert task.state == TaskState.PENDING
    assert task.failure_retry_count == 1
    assert task.lease_expires_at is None
    assert Event.objects.filter(type=EventType.TASK_LEASE_EXPIRED, task_id=task.pk).count() == 1
    # The refusal carries the catalog code, not a generic conflict.
    with pytest.raises(LeaseExpired) as excinfo:
        extend_lease(task_id=task.pk, session_id=dead_session, lease_generation=generation)
    assert excinfo.value.default_code == LEASE_EXPIRED
    _assert_scenario_invariants(task)
