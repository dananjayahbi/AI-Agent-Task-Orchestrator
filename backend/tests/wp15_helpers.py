"""Shared plumbing for the WP-1.5 state-machine suites (MT-1.5-01 … 06).

Not a test module (no ``test_`` prefix): factories, registry/hook
plumbing and the Section 9.1 direct-write scanner that several of the
six suites assert against. Pytest fixtures themselves stay inside each
suite (the idiom — and no shared ``conftest.py`` is touched, so WPs
running beside this one never collide on it).

The scanner (:func:`find_state_writes`) is the executable form of the
dependency rule — *``tasks`` owns all state changes; other modules call
the state machine service and never write ``state`` directly*
(Section 9.1). It is deliberately narrow (the risk note: scope it to the
Task ``state`` column to avoid false positives): instance assignments
(``.state =``), queryset ``.update(state=...)`` and
``bulk_update(["state"])``. Creation calls such as
``Task.objects.create(state=...)`` are **not** flagged — that is T1's
documented create exemption (the row's initial value, Section 8.2 T1),
recorded in the WP changelog. Migrations are framework-generated
artifacts and are excluded with ``__pycache__``.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from django.db import connection

from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import Task, TaskState
from apps.tasks.state_machine.hooks import set_event_hook, set_review_push_hook
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY

BACKEND_ROOT = Path(__file__).resolve().parent.parent
APPS_ROOT = BACKEND_ROOT / "apps"

# Section 9.6's event catalog, verbatim — no type outside this tuple may
# ever be emitted (Section 20.4 item 6). Shared by the system-transition
# and matrix suites so both assert the same frozen list.
SECTION_9_6_EVENTS: tuple[str, ...] = (
    "project.created",
    "project.updated",
    "task.created",
    "task.updated",
    "task.transitioned",
    "task.claimed",
    "task.released",
    "task.checkpoint",
    "task.lease_expiring",
    "task.lease_expired",
    "attachment.processing",
    "attachment.ready",
    "attachment.failed",
    "audit.claimed",
    "audit.passed",
    "audit.escalated",
    "review.requested",
    "review.decided",
    "merge.started",
    "merge.succeeded",
    "merge.failed",
    "agent.session_started",
    "agent.session_ended",
    "system.alert",
)

# Narrow to the Task state column (MT-1.5-06 risk note): assignments on an
# instance, queryset updates and bulk updates. Comparisons (``==``, ``!=``)
# and field *definitions* (``state = models.CharField(...)``) never match.
STATE_WRITE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.state\s*=[^=]"),
    re.compile(r"\.update\s*\([^)\n]*\bstate\s*=[^=]"),
    re.compile(r"bulk_update\s*\([^)\n]*['\"]state['\"]"),
)


def find_state_writes(*, exclude_parts: tuple[str, ...] = ()) -> list[str]:
    """Every production line that writes ``state``, as ``relpath:line: text``.

    Scans ``backend/apps`` (production code — tests are fixtures, not
    product paths). ``exclude_parts`` drops directory names anywhere in
    the relative path; the dispatcher suite passes
    ``("state_machine",)`` for its Section 9.1 "outside the service"
    scope, while MT-1.5-06's formal test scans *with* the service and
    asserts every hit is the dispatcher's single assignment.
    """
    hits: list[str] = []
    for path in sorted(APPS_ROOT.rglob("*.py")):
        relative = path.relative_to(APPS_ROOT)
        if "__pycache__" in relative.parts:
            continue
        if any(part in relative.parts for part in exclude_parts):
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if any(pattern.search(line) for pattern in STATE_WRITE_PATTERNS):
                hits.append(f"{relative.as_posix()}:{number}: {line.strip()}")
    return hits


def make_project(*, pid: str = "PID00001", name: str = "WP-1.5 tests") -> Project:
    """One project row with the Section 7.1 policy pair (id kept stable)."""
    return Project.objects.create(
        id=pid,
        name=name,
        repo_path=f"/srv/repos/{name.lower().replace(' ', '-')}",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def make_task(
    project: Project,
    index: int,
    *,
    state: str = TaskState.DRAFT,
    **overrides: Any,
) -> Task:
    """One task row with a deterministic id; the counter stays allocator-honest."""
    payload: dict[str, Any] = {
        "id": f"{project.pk}-T{index:03d}",
        "project": project,
        "title": f"Task {index:03d}",
        "state": state,
    }
    payload.update(overrides)
    task = Task.objects.create(**payload)
    Project.objects.filter(pk=project.pk, task_counter__lt=index).update(task_counter=index)
    return task


@contextmanager
def registered_registry() -> Iterator[None]:
    """Snapshot the default registry; restore it (probe rows never leak)."""
    ensure_registered()
    snapshot = DEFAULT_REGISTRY.specs()
    try:
        yield
    finally:
        DEFAULT_REGISTRY.replace_all(snapshot)


def install_event_recorder() -> list[Mapping[str, Any]]:
    """Record every in-transaction event emission (plus its atomicity)."""
    records: list[Mapping[str, Any]] = []

    def record(payload: Mapping[str, Any]) -> None:
        records.append({**dict(payload), "_in_atomic_block": connection.in_atomic_block})

    set_event_hook(record)
    return records


def install_push_recorder() -> list[Mapping[str, Any]]:
    """Record every Section 9.8 review-push trigger."""
    records: list[Mapping[str, Any]] = []
    set_review_push_hook(records.append)
    return records


def reset_hooks() -> None:
    """Back to the production default seams (WP-1.9's writer is wired;
    the WP-5.4 push seam stays a no-op until then)."""
    set_event_hook(None)
    set_review_push_hook(None)
