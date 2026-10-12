"""Shared plumbing for the WP-1.6 lease/claim suites (MT-1.6-01 … 09).

Not a test module (no ``test_`` prefix), mirroring
``tests/wp15_helpers.py``: the registry-restore fixture every WP-1.6
suite must autouse, plus small factories over WP-1.5's helpers.

**Why the restore fixture is mandatory** (wiring module's docstring):
``claim_task``/``release_task`` call ``ensure_wired()``, which replaces
the T4/T6 stub rows on the process registry — the WP-1.5 suites assert
those stubs (``SPECS`` snapshots the stub rows at collection time) and
snapshot/restore the registry per test. Every module that can trigger
wiring therefore imports :func:`restore_lease_registry` so each test
starts and ends on the stub registry; without it, one wired test would
make a later ``TransitionNotWired`` assertion fail spuriously.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY

from .wp15_helpers import (  # noqa: F401  (re-exported for suites)
    install_event_recorder,
    make_project,
    make_task,
    registered_registry,
    reset_hooks,
)

__all__ = [
    "PASSWORD",
    "active_policy_project",
    "claim",
    "install_event_recorder",
    "make_pending_task",
    "make_project",
    "make_task",
    "publish",
    "registered_registry",
    "reset_hooks",
    "restore_lease_registry",
]

PASSWORD = "wp16-tests-1!"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def restore_lease_registry() -> Iterator[None]:
    """Snapshot the registry before the test; restore the stubs after.

    Autouse in every WP-1.6 module that imports it (each suite's namespace
    picks it up — the same promotion trick, defined once here).
    """
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)
        reset_hooks()


def make_pending_task(project: Project, index: int, **overrides: object) -> Task:
    """A ``pending`` task row — T2's outcome without spending a dispatch."""
    return make_task(project, index, state=TaskState.PENDING, **overrides)


def publish(task: Task, *, actor_ref: str = "wp16-tests") -> Task:
    """Dispatch T2 (owner publish) — the realistic route into ``pending``."""
    return dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref=actor_ref,
    )


def claim(
    task: Task,
    *,
    session_id: str = "sess_wp16_claimant",
    worker_agent_id: str = "wp16-coder-label",
    caller_project_id: str | None = None,
) -> Task:
    """Claim *task* through the real service (Section 9.3)."""
    from apps.leases.claim import claim_task  # local import: wiring is lazy

    return claim_task(
        task_id=task.pk,
        session_id=session_id,
        worker_agent_id=worker_agent_id,
        caller_project_id=caller_project_id if caller_project_id is not None else task.project_id,
    )


def active_policy_project(pid: str = "PID00001", **policy_fields: object) -> Project:
    """One active project with an explicitly-tuned Section 7.2 policy."""
    project = make_project(pid=pid)
    if policy_fields:
        ProjectPolicy.objects.filter(pk=project.agent_policy_id).update(**policy_fields)
        project.agent_policy.refresh_from_db()
    return project
