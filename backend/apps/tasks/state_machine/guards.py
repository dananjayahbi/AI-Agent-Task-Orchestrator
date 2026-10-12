"""Shared guard helpers used by more than one Section 8.2 row (MT-1.5-01).

Small, single-purpose predicates/refusals that several table rows cite
verbatim: the lease predicate of Section 7.4 rule 2 (T3's "no active
lease" guard, later claim/release checks), the worker clearing that
T5/T9's "clear worker" side effect and Section 8.3 invariant 1 both
depend on, and the dependency-readiness refusal shared by T2 (and,
when wired, T4's "dependencies completed" guard). Keeping them here is
what lets the rows stay literal copies of the plan's Guard/Side-effect
columns instead of drifting prose.
"""

from __future__ import annotations

from ..exceptions import DependencyUnmet
from ..models.task import Task
from ..services.dependencies import all_dependencies_completed


def has_active_lease(task: Task) -> bool:
    """Whether a worker currently holds *task* (Section 7.4 rule 2 reading).

    The rule fixes ``lease_expires_at`` non-null **iff** a worker holds
    the task, and WP-1.4's fields are written together — so any lease
    timestamp or worker label present means "held". An expired-but-not-
    yet-swept lease still counts as held here: T3's guard is "no active
    lease" against *records*, and the sweeper (T5) is what clears a
    dead worker's claim, not the owner's unpublish.
    """
    return task.lease_expires_at is not None or task.worker_agent_id is not None


def clear_coder_lease(task: Task) -> None:
    """Clear every worker-owned field (Section 8.2 "clear worker").

    Covers the four worker/lease columns of Section 7.2 —
    ``worker_agent_id``, ``worker_session_id``, ``claimed_role``,
    ``lease_acquired_at``/``lease_expires_at`` — so Section 8.3
    invariant 1 ("a task in any other state has no coder lease") holds
    after any transition out of ``in_progress``. ``last_checkpoint_at``
    is deliberately kept: it is history for the UI's stalled indicator
    (Section 8.6), not a lease field.
    """
    task.worker_agent_id = None
    task.worker_session_id = None
    task.claimed_role = None
    task.lease_acquired_at = None
    task.lease_expires_at = None


def require_completed_dependencies(task: Task) -> None:
    """The dependency refusal T2's "dependencies exist" guard surfaces.

    Reading (MT-1.5-02 risk note): "dependencies exist" means every
    declared dependency task exists **and is completed** — the same
    predicate ``services.dependencies.all_dependencies_completed``
    defines for FR-TSK-07 / T4, translated to the catalog's
    ``DEPENDENCY_UNMET`` exactly as that function's contract promises
    ("the offer path is what translates False into DEPENDENCY_UNMET").
    A task with no dependencies passes vacuously.
    """
    if not all_dependencies_completed(task):
        raise DependencyUnmet(task.pk)
