"""Dependency rules: write validation and the FR-TSK-07 readiness query.

Three responsibilities, one home (MT-1.4-05):

* :func:`validate_dependency_targets` — structure rules for any write:
  ids must be well-formed task ids that exist **in the same project**
  (GOAL-2 / ADR-004 zero-bleed: a cross-project dependency would let one
  project gate another's work), must not be the task itself, and must
  not close a dependency cycle. Every failure is a catalog
  ``VALIDATION_ERROR`` with per-id detail — structure problems are
  client input errors, never 500s. ``DEPENDENCY_UNMET`` stays reserved
  for WP-1.6's offer/claim-time enforcement (Section 9.2 catalog).

* :func:`set_dependencies` — the single replace-the-set edge writer both
  create and PATCH compose (declarative: ``depends_on`` in a payload *is*
  the task's dependency set). Callers own the transaction; validation
  runs before any row is touched, so a refusal persists nothing.

* :func:`all_dependencies_completed` — **the** readiness implementation
  for FR-TSK-07, documented as the contract WP-1.6's work selection
  (`GET /projects/{pid}/work`) and claim guard (Section 8.2 T4,
  Section 9.3 step 4 revalidation "inside the lock") must call, so the
  offer rule has exactly one predicate.

Cycle reading (flagged for the owner in the WP changelog): the plan never
states "cycles are rejected", but FR-TSK-07's offer rule — *all*
dependencies completed — is unsatisfiable inside a cycle, so a cycle
deadlocks its members forever. Prevention at write time is the only
sensible enforcement; cycles can also never arise from the transition
rules themselves, only from these writes.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from rest_framework.exceptions import ValidationError

from ..models import Task, TaskDependency, TaskState
from .ids import is_valid_task_id


def validate_dependency_targets(
    *,
    task: Task,
    dependency_ids: Iterable[Any],
) -> list[str]:
    """Validate a proposed dependency set for *task*; return it normalized.

    Checks in order: shape (string, well-formed Section 7.3 id), no
    self-edge, existence, same-project scope, then acyclicity (the
    reading above). Duplicates collapse to the first occurrence —
    ``[b, b]`` is one edge, not an IntegrityError.
    """
    requested: list[str] = []
    errors: list[str] = []
    seen: set[str] = set()
    for raw in dependency_ids:
        if not isinstance(raw, str):
            errors.append(f"{raw!r}: each dependency must be a task id string")
            continue
        if not is_valid_task_id(raw):
            errors.append(f"{raw!r}: not a task id ({{PID}}-T{{index}}, Section 7.3)")
            continue
        if raw == task.pk:
            errors.append(f"{raw}: a task cannot depend on itself")
            continue
        if raw not in seen:
            seen.add(raw)
            requested.append(raw)
    if errors:
        raise ValidationError({"depends_on": errors})
    if not requested:
        return requested

    found = dict(Task.objects.filter(pk__in=requested).values_list("pk", "project_id"))
    for dependency_id in requested:
        project_id = found.get(dependency_id)
        if project_id is None:
            errors.append(f"{dependency_id}: task not found")
        elif project_id != task.project_id:
            # Zero-Bleed (ADR-004): dependencies are always same-project;
            # cross-project edges are rejected, not silently scoped.
            errors.append(
                f"{dependency_id}: must belong to project {task.project_id} "
                "(cross-project dependencies are not allowed)"
            )
    if errors:
        raise ValidationError({"depends_on": errors})

    if _waits_on_reaches(requested, target=task.pk):
        raise ValidationError(
            {
                "depends_on": [
                    f"{task.pk}: the new edges would create a dependency "
                    "cycle (FR-TSK-07's 'all dependencies completed' is "
                    "unsatisfiable in a cycle)"
                ]
            }
        )
    return requested


def _waits_on_reaches(start: list[str], *, target: str) -> bool:
    """Follow ``depends_on`` edges from *start*; does the walk hit *target*?

    Iterative DFS with a visited set — bounded by the project's edge
    count, and the visited set makes a *pre-existing* cycle (however it
    got there) terminate instead of hanging validation.
    """
    seen: set[str] = set()
    frontier = list(start)
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        if current == target:
            return True
        frontier.extend(
            TaskDependency.objects.filter(task_id=current).values_list("depends_on_id", flat=True)
        )
    return False


def set_dependencies(*, task: Task, dependency_ids: Iterable[Any]) -> list[str]:
    """Replace *task*'s dependency set with *dependency_ids*; return it.

    Declarative write: the payload's ``depends_on`` **is** the set (edges
    not listed are removed, new ones added, shared ones untouched).
    Validation runs first; the caller's transaction makes the whole
    operation atomic with the task write it accompanies.
    """
    desired = validate_dependency_targets(task=task, dependency_ids=dependency_ids)
    existing = list(
        TaskDependency.objects.filter(task=task).values_list("depends_on_id", flat=True)
    )
    desired_set = set(desired)
    stale = [edge for edge in existing if edge not in desired_set]
    fresh = [edge for edge in desired if edge not in existing]
    if stale:
        TaskDependency.objects.filter(task=task, depends_on_id__in=stale).delete()
    if fresh:
        TaskDependency.objects.bulk_create(
            TaskDependency(task=task, depends_on_id=dependency_id) for dependency_id in fresh
        )
    return desired


def all_dependencies_completed(task: Task) -> bool:
    """FR-TSK-07 readiness — **the** contract for WP-1.6's offer/claim guard.

    True iff every edge in ``task``'s dependency set points at a task in
    the canonical G-01 state ``completed`` (a task with no dependencies
    is ready — vacuous truth).

    Contract notes for the callers the plan assigns this predicate to
    (Section 8.2 T4 guard; Section 9.3 step 4's "re-validate dependencies
    inside the lock"):

    * one ``SELECT ... EXISTS`` — no row locks of its own, so it is safe
      to call **inside** the claim transaction: the caller's
      ``select_for_update`` serializes the check against concurrent
      completions;
    * never raises — readiness is data, not protocol; the offer path is
      what translates ``False`` into the catalog's ``DEPENDENCY_UNMET``.
    """
    unmet = (
        TaskDependency.objects.filter(task=task)
        .exclude(depends_on__state=TaskState.COMPLETED)
        .exists()
    )
    return not unmet
