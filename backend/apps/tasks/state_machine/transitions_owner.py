"""Owner transitions T2 (publish), T3 (unpublish), T19 (archive) — MT-1.5-02.

The first three real rows on the registry (Section 8.2, actor **O**),
each transcribed with the table's exact From/To/Guard columns:

* **T2** ``draft`` → ``pending`` — guards: required fields valid;
  attachments ``ready`` (or override); dependencies exist. The side
  effect ("visible to agents") *is* the state: the work offer and board
  queries read ``pending`` (WP-1.6/WP-4.x), so there is no field to set.
* **T3** ``pending`` → ``draft`` — guard: no active lease; side effect
  ("hidden from agents") likewise follows from leaving ``pending``.
* **T19** any non-``completed`` → archived flag — no guards; the side
  effect is WP-1.4's ``archive_task`` setter (server-clock
  ``archived_at``, version bump, idempotent re-archive), the contract
  MT-1.4-06 handed this WP. ``to_state`` is ``None``: archiving is a
  flag, never a seventh state (Section 8.1), so the history row records
  ``from_state == to_state``.

Recorded readings (Section 20.1 item 5 — no hidden decisions):

* **"dependencies exist"** (T2) = every declared dependency exists **and
  is completed** — the MT-1.5-02 risk-note reading, sharing
  ``all_dependencies_completed`` with T4's "dependencies completed"
  guard; refusal is the catalog ``DEPENDENCY_UNMET`` (409), which the
  MT's acceptance criteria name. The alternative reading (existence
  only, phrased in MT-4.5-06) is flagged as an open-question candidate
  in the WP changelog.
* **"attachments ready (or override)"** passes vacuously: no attachment
  model exists until WP-1.11, and no override flag is invented here
  (the MT forbids it; an explicit override field is an OQ candidate for
  WP-1.11). The guard hook is this function, so WP-1.11/1.12 extend it
  without renaming anything.
* **"required fields valid"** = the task has a non-blank title — the
  only field the plan requires of a task (FR-TSK-02 boundary); a blank
  title answers ``VALIDATION_ERROR`` (400), the catalog's malformed-
  input code, because the *fields* are what fail, not the resource.
"""

from __future__ import annotations

from rest_framework.exceptions import ValidationError

from ..exceptions import TaskStateConflict
from ..models.task import Task, TaskState
from ..services.tasks import archive_task
from .guards import has_active_lease, require_completed_dependencies
from .registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec


def _guard_publish(task: Task, context: TransitionContext) -> None:
    """T2 guard — Section 8.2 verbatim.

    "Required fields valid; attachments ``ready`` (or override);
    dependencies exist" — see the module docstring for the recorded
    readings of each clause. ``context`` is unused: nothing about T2
    depends on who publishes (the Actor column already fixed Owner).
    """
    if not task.title.strip():
        raise ValidationError({"title": "Publish requires a non-empty title (T2 guard)."})
    # attachments ready (or override): vacuous until WP-1.11 attaches the
    # relation — the hook point, not a silently dropped guard.
    require_completed_dependencies(task)


def _guard_unpublish(task: Task, context: TransitionContext) -> None:
    """T3 guard — Section 8.2 verbatim: "No active lease".

    A leased task refuses with the Section 8.2 family code
    ``TASK_STATE_CONFLICT`` (409): the *row's* lifecycle refuses, the
    payload is fine.
    """
    if has_active_lease(task):
        raise TaskStateConflict(task.pk, reason="is leased (T3 guard: no active lease)")


def _side_effect_archive(task: Task, context: TransitionContext) -> Task | None:
    """T19 side effect — "Sets ``archived_at``; hidden from boards".

    Delegates to WP-1.4's ``archive_task`` (server clock, one version
    bump under the row lock, first timestamp wins) and returns the
    locked instance so the dispatcher adopts its already-persisted
    version/archived_at without double-bumping (MT-1.4-06 contract).
    """
    return archive_task(task=task)


def register() -> None:
    """Register T2, T3 and T19 on the default registry (loader-called)."""
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T2",
            trigger="publish",
            from_states=frozenset({TaskState.DRAFT}),
            to_state=TaskState.PENDING,
            actor_types=frozenset({"owner"}),
            guard=_guard_publish,
            side_effect=None,
            event_type="task.transitioned",
            reason_code="publish",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T3",
            trigger="unpublish",
            from_states=frozenset({TaskState.PENDING}),
            to_state=TaskState.DRAFT,
            actor_types=frozenset({"owner"}),
            guard=_guard_unpublish,
            side_effect=None,
            event_type="task.transitioned",
            reason_code="unpublish",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T19",
            trigger="archive",
            from_states=frozenset(
                {
                    TaskState.DRAFT,
                    TaskState.PENDING,
                    TaskState.IN_PROGRESS,
                    TaskState.TO_BE_AUDITED,
                    TaskState.IN_HUMAN_REVIEW,
                }
            ),
            to_state=None,  # archived flag, never a seventh state (Section 8.1)
            actor_types=frozenset({"owner"}),
            guard=None,  # Section 8.2 T19: Guard conditions = None
            side_effect=_side_effect_archive,
            event_type="task.transitioned",
            reason_code="archive",
        )
    )
