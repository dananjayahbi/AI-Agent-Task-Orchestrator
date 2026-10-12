"""MT-1.4-02 — atomic per-project task counter for gap-tolerant ids.

Executable proof of the allocation slice (Sections 7.2, 7.3; FR-TSK-01;
WP-1.4 acceptance):

* format: ``{PID}-T{index}`` with the 3-digit minimum and natural growth
  (``T001`` → ``T999`` → ``T1000`` → long indexes); ``T000`` never issued;
* the allocator is the **single** entry point: a structural test fails the
  build if any module outside ``services/ids.py`` writes ``task_counter``
  (Section 9.1 — the ``tasks`` module owns sequencing);
* **100 concurrent creations yield 100 unique, constraint-valid ids**
  (WP-1.4 acceptance) — barrier-synchronized threads against one project;
  the same test runs on **real Postgres** in CI's integration layer by
  Section 18's split (``backend/tests/integration/``);
* gaps are tolerated and never "repaired" (FR-TSK-01): a rolled-back
  allocation refunds its number without enabling a collision, and a
  committed-but-unused number stays permanently skipped — no fill-the-gap
  logic exists anywhere.

Run with ``pytest backend/tests/test_task_id_allocation.py`` (MT test
command). The file runs in CI's unit job (SQLite unit layer per Section
18); the Postgres twin lives in the integration suite.
"""

from __future__ import annotations

import re
import threading
import time
from pathlib import Path

import pytest
from django.db import connection, transaction
from django.db.utils import OperationalError

from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task
from apps.tasks.services.ids import (
    TASK_ID_PATTERN,
    allocate_task_id,
    is_valid_task_id,
    render_task_id,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project(db: None) -> Project:
    """One project row with a fresh counter (explicit id keeps ids stable)."""
    return Project.objects.create(
        id="PID00077",
        name="Task allocation tests",
        repo_path="/srv/repos/task-allocation",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


# --- format (FR-TSK-01; Section 7.3 "at least 3 digits ... T1000") ---------


def test_task_id_render_three_digits_then_natural_growth() -> None:
    """``T001``..``T999`` pad to three digits; ``T1000`` grows past them."""
    assert TASK_ID_PATTERN == r"^PID[0-9]{5}-T[0-9]{3,}$"
    assert render_task_id("PID00007", 1) == "PID00007-T001"  # the plan's example PID
    assert render_task_id("PID00007", 42) == "PID00007-T042"
    assert render_task_id("PID00007", 999) == "PID00007-T999"
    assert render_task_id("PID00007", 1000) == "PID00007-T1000"
    assert render_task_id("PID00007", 123456789) == "PID00007-T123456789"
    for index in (1, 999, 1000, 10_000):
        rendered = render_task_id("PID00007", index)
        assert is_valid_task_id(rendered), rendered


def test_task_id_render_refuses_the_never_issued_index_zero() -> None:
    """Index 0 is a programming error, never output (T000 does not exist)."""
    for bad in (0, -1, -999):
        with pytest.raises(ValueError, match=">= 1"):
            render_task_id("PID00007", bad)


# --- allocation consumes the counter (Section 7.2 task_counter; 7.3) -------


def test_allocation_increments_the_counter_and_builds_the_id(project: Project) -> None:
    """Lock + increment + render: T001, T002, ... from a fresh counter."""
    assert project.task_counter == 0

    first = allocate_task_id(project)
    assert first == "PID00077-T001"
    project.refresh_from_db()
    assert project.task_counter == 1

    second = allocate_task_id(project)
    assert second == "PID00077-T002"
    project.refresh_from_db()
    assert project.task_counter == 2


def test_sequential_allocation_is_contiguous_without_failures(
    project: Project,
) -> None:
    """No failures → no gaps: the committed baseline is exactly T001..T005."""
    ids = [allocate_task_id(project) for _ in range(5)]
    assert ids == [
        "PID00077-T001",
        "PID00077-T002",
        "PID00077-T003",
        "PID00077-T004",
        "PID00077-T005",
    ]
    assert len(set(ids)) == 5


# --- single entry point (Section 9.1; MT-1.4-02 acceptance) ----------------


def test_task_counter_is_written_only_by_the_allocator() -> None:
    """Structural drift guard: no other module writes the task counter.

    ``services/ids.py`` is the one allocation entry point for MT-1.4-03's
    create endpoint and WP-1.5's T1 side effect; ``projects/services``
    must not write it either (the model field default and the read-only
    API rendering are not writes). The pattern matches *writes*
    (assignments, augmented assignments, quoted update-fields keys) — a
    prose/docstring mention of the field name is not a write.
    """
    write_pattern = re.compile(r"task_counter\s*(?:[+\-*/]?=)|[\"']task_counter[\"']")
    tasks_root = BACKEND_ROOT / "apps" / "tasks"
    for path in sorted(tasks_root.rglob("*.py")):
        if "migrations" in path.parts or path.name == "ids.py":
            continue
        content = path.read_text(encoding="utf-8")
        assert write_pattern.search(content) is None, (
            f"{path.relative_to(BACKEND_ROOT)} writes task_counter — "
            "allocation belongs to services/ids.py alone (Section 9.1)"
        )

    allocator = (tasks_root / "services" / "ids.py").read_text(encoding="utf-8")
    assert "task_counter = task_counter + 1" in allocator, "the increment lives here"
    assert "RETURNING task_counter" in allocator, (
        "the id is built from the counter's new value in the same statement "
        "(Section 7.3: lock + increment + build, one atomic UPDATE)"
    )
    assert "transaction.atomic" in allocator, "the lock spans the creating transaction"

    for path in sorted((BACKEND_ROOT / "apps" / "projects" / "services").rglob("*.py")):
        content = path.read_text(encoding="utf-8")
        assert write_pattern.search(content) is None, (
            f"{path.relative_to(BACKEND_ROOT)} must not write the task counter "
            "— the tasks app owns sequencing (Section 9.1)"
        )


# --- gap tolerance (FR-TSK-01; Section 7.3) --------------------------------


class _Boom(Exception):
    """Simulated failure after allocation, before the task row exists."""


def test_rolled_back_allocation_is_refunded_without_reuse_collisions(
    project: Project,
) -> None:
    """A failed create refunds its number; reusing it cannot collide.

    The counter is transactional: rollback restores it, and because no
    task row ever carried the number, the next allocation issuing the
    same id is collision-free by construction (FR-TSK-01: reuse only
    matters when a row exists).
    """
    with pytest.raises(_Boom):
        with transaction.atomic():
            allocated = allocate_task_id(project)
            raise _Boom("create failed after allocation")

    project.refresh_from_db()
    assert project.task_counter == 0, "the increment rolled back with the create"
    assert not Task.objects.filter(pk=allocated).exists(), "no row carries the number"

    reused = allocate_task_id(project)
    assert reused == allocated, "a refunded number is safe to issue again"
    assert not Task.objects.filter(pk=allocated).exists()


def test_committed_gap_is_never_back_filled(project: Project) -> None:
    """A committed increment without a task row stays skipped forever.

    Models the durable gap source (allocator committed, insert failed
    outside that transaction / manual bump): the allocator continues from
    the counter and no code path ever returns to fill ``T001``..``T005`` —
    gap-tolerant means gaps are *tolerated*, not repaired (FR-TSK-01;
    Section 7.3).
    """
    Project.objects.filter(pk=project.pk).update(task_counter=5)  # simulated gap

    assert allocate_task_id(project) == "PID00077-T006"
    assert allocate_task_id(project) == "PID00077-T007"
    # ...and nothing ever reissued T001..T005.
    for gap_index in range(1, 6):
        assert not Task.objects.filter(pk=f"PID00077-T{gap_index:03d}").exists()


# --- WP-1.4 acceptance: 100 concurrent creations, unique ids ---------------


def create_task_concurrently(
    project_id: str,
    *,
    threads: int = 100,
    gate: threading.Semaphore | None = None,
    join_timeout: int = 120,
) -> list[str]:
    """Run *threads* parallel creations against one project; return the ids.

    Shared by the unit-layer test (SQLite, 100 bare threads) and the
    integration twin (real Postgres — pass ``gate`` to cap simultaneously
    open connections under the service's ``max_connections``).

    Contention handling is **time-bounded, not attempt-bounded**: each
    worker retries SQLite's shared-cache ``database is locked`` errors
    until a deadline (with capped backoff), because a fixed attempt count
    multiplied by SQLite's 5 s busy timeout can outlive the join window
    and leak live workers into teardown. A failed statement rolls its
    whole create back, so a retry consumes no number (and on Postgres the
    row lock serializes workers without retries). The barrier and the
    joins share one absolute deadline so a genuinely wedged worker fails
    the test loudly instead of hanging the suite.
    """
    start = time.monotonic()
    barrier = threading.Barrier(threads, timeout=min(join_timeout, 60))
    collected: list[str] = []
    failures: list[str] = []
    lock = threading.Lock()
    # One deadline for every worker's retries: started when the barrier
    # releases, comfortably inside the join window below.
    retry_deadline = start + join_timeout - 15

    def create_with_retry() -> str:
        delay = 0.001
        while time.monotonic() < retry_deadline:
            try:
                with transaction.atomic():
                    task_id = allocate_task_id(Project(pk=project_id))
                    Task.objects.create(
                        id=task_id,
                        project_id=project_id,
                        title="Concurrent creation",
                    )
                return task_id
            except OperationalError:
                time.sleep(delay)
                delay = min(delay * 2, 0.02)
        raise AssertionError(
            f"creation never got past the database lock within "
            f"{join_timeout - 15}s ({len(collected)} of {threads} succeeded)"
        )

    def worker() -> None:
        try:
            barrier.wait()
            if gate is not None:
                gate.acquire()
            try:
                task_id = create_with_retry()
                with lock:
                    collected.append(task_id)
            finally:
                if gate is not None:
                    gate.release()
                # Drop this thread's connection right away so the gate
                # really caps peak sessions on Postgres (max_connections).
                connection.close()
        except Exception as exc:  # surfaced to the main thread below
            with lock:
                failures.append(repr(exc))
        finally:
            connection.close()

    workers = [threading.Thread(target=worker) for _ in range(threads)]
    for thread in workers:
        thread.start()
    join_deadline = start + join_timeout
    for thread in workers:
        thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
        assert not thread.is_alive(), (
            f"worker thread hung ({len(collected)} of {threads} creations done, "
            f"{len(failures)} failures)"
        )

    assert not failures, failures
    return collected


@pytest.mark.django_db(transaction=True)
def test_one_hundred_concurrent_creations_yield_unique_ids() -> None:
    """WP-1.4 acceptance, verbatim: 100 parallel creations, unique ids.

    Barrier-synchronized threads meet real table locks on the shared
    in-memory SQLite database; the retry loop absorbs them, then the
    assertion covers exactly what the plan promises — uniqueness and the
    FR-TSK-01 pattern — never contiguity (gaps are tolerated).
    """
    project = Project.objects.create(
        id="PID00078",
        name="Concurrent task creations",
        repo_path="/srv/repos/concurrent-tasks",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )

    ids = create_task_concurrently(project.pk, threads=100)

    assert len(ids) == 100, len(ids)
    assert len(set(ids)) == 100, "a task id was reused"
    for task_id in ids:
        assert is_valid_task_id(task_id), task_id
        assert task_id.startswith("PID00078-"), task_id
    project.refresh_from_db()
    assert project.task_counter == 100, (
        "the counter advances exactly once per committed creation "
        "(rolled-back attempts refund — FR-TSK-01 gap tolerance)"
    )
    assert Task.objects.filter(project=project).count() == 100
