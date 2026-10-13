"""Dashboard summary aggregation — Section 9.2 Dashboard row (MT-1.15-06).

``GET /dashboard/summary`` is a read-only roll-up for the Owner's Overview
surfaces (Section 14.1 Home / FR-MOB-01): one card per registered project,
ordered by project id (the zero-padded Section 7.3 ids make lexicographic
order the deterministic creation order — the same reading as the
``GET /projects`` list). Three figures per card, all computed **server-side**
and authoritative on the wire (the mobile client never recomputes any of
them — MT-5.6-01 risk note):

* ``state_counts`` — per-state counts of the project's **non-archived**
  tasks, zero-filled over the six canonical G-01 values (ADR-010); T19's
  default board visibility excludes archived tasks, and the Overview cards
  mirror the board (Section 8.1: archiving is a flag, never a seventh state).
* ``velocity`` — tasks that reached ``completed`` within a trailing 7-day
  rolling window on the **server clock** (principle P7), counted from the
  append-only TaskTransition log (``to_state = completed``). Conservative by
  design: one grouped query, no extrapolation or per-day averaging. The
  window and definition are **documented defaults, not plan facts** — the
  plan names "velocity" but never defines it (raised as an OQ in the WP-1.15
  changelog); a ``now`` argument exists purely as a deterministic test seam,
  production callers pass nothing and get ``timezone.now()``.
* ``active_agents`` — the project's AgentSession rows with
  ``ended_at IS NULL`` (Section 7.2 lifecycle; no heartbeat freshness is
  invented — OQ-04 stays closed).

Read-only by construction: the module imports models across apps but never
writes state — Section 9.1's dependency rule is about *state changes*, and
the ``tasks`` app remains their only writer.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.agents.models import AgentSession
from apps.tasks.models import Task, TaskState, TaskTransition

from ..models import Project

#: Velocity look-back window. Documented default (the plan states no number),
#: recorded as an OQ in the WP-1.15 changelog — not a plan fact.
VELOCITY_WINDOW_DAYS = 7

#: The six canonical G-01/ADR-010 state keys, in Section 8.1 order.
STATE_KEYS: tuple[str, ...] = tuple(TaskState.values)


def _state_counts_by_project() -> dict[str, dict[str, int]]:
    """Per-project, per-state counts of non-archived tasks (T19 visibility)."""
    grouped = (
        Task.objects.filter(archived_at__isnull=True)
        .values("project_id", "state")
        .annotate(total=Count("id"))
    )
    counts: dict[str, dict[str, int]] = {}
    for row in grouped:
        counts.setdefault(str(row["project_id"]), {})[str(row["state"])] = int(row["total"])
    return counts


def _velocity_by_project(cutoff: datetime) -> dict[str, int]:
    """Per-project completions at or after ``cutoff`` (transition log)."""
    grouped = (
        TaskTransition.objects.filter(to_state=TaskState.COMPLETED, timestamp__gte=cutoff)
        .values("task__project_id")
        .annotate(total=Count("id"))
    )
    return {str(row["task__project_id"]): int(row["total"]) for row in grouped}


def _active_agents_by_project() -> dict[str, int]:
    """Per-project count of sessions the bridge has not ended."""
    grouped = (
        AgentSession.objects.filter(ended_at__isnull=True)
        .values("project_id")
        .annotate(total=Count("id"))
    )
    return {str(row["project_id"]): int(row["total"]) for row in grouped}


def build_dashboard_summary(*, now: datetime | None = None) -> dict[str, list[dict[str, Any]]]:
    """Render the Section 9.2 dashboard payload: ``{"projects": [cards]}``.

    ``now`` defaults to the server clock and exists only so tests can pin
    the velocity window deterministically (principle P7 in production).
    """
    clock = now if now is not None else timezone.now()
    cutoff = clock - timedelta(days=VELOCITY_WINDOW_DAYS)

    state_counts = _state_counts_by_project()
    velocity = _velocity_by_project(cutoff)
    active_agents = _active_agents_by_project()

    cards: list[dict[str, Any]] = []
    for project in Project.objects.order_by("pk"):
        pid = str(project.pk)
        per_state = state_counts.get(pid, {})
        cards.append(
            {
                "project_id": pid,
                "name": project.name,
                # Zero-filled over the six G-01 keys: every card always carries
                # the complete state picture, absent states read 0 (never null).
                "state_counts": {key: per_state.get(key, 0) for key in STATE_KEYS},
                "velocity": velocity.get(pid, 0),
                "active_agents": active_agents.get(pid, 0),
            }
        )
    return {"projects": cards}
