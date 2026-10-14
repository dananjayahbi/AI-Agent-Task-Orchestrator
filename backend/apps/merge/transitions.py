"""WP-3.7 wiring of the merge rows T17/T18 — the sanctioned seam (MT-3.7-01).

Same discipline as ``apps.audit.review`` (WP-3.6) and
``apps.audit.transitions`` (WP-3.3): the dispatcher/registry/loader/hooks
are never edited here; ``DEFAULT_REGISTRY.register(spec, replace=True)``
puts the two Section 8.2 merge rows on the process registry, lazily (the
WP-1.5 suites' snapshot/restore owns that state — production gets the
rows on the first queue call, tests inside their own restore guards).

**Row shapes — recorded readings (Section 20.1 item 5):**

* **T17** ``merge_succeeded`` — From the merge-pending carriers
  (``in_human_review`` from T15's approve, ``to_be_audited`` from
  T10/T13's engine-approved branches — Section 8.2's To column reads
  "merge-pending", the Section 8.1 **sub-status** ``merge_status`` in
  ``pending``/``merging``, never a seventh state); To ``completed``;
  actor M (the Merge Executor, mapped to the ``agent`` actor type —
  Section 8.2's legend). Guard "*Merge result reported with resulting
  sha*": the dispatch must carry a non-blank ``merge_sha`` (the
  risk-note contract — Section 7.2 has no sha column, so it rides the
  payload, the history note **and** the event ``data``). Side effects:
  ``merge_status`` = ``merged`` (Section 8.3 rule 2's precondition for
  ``completed``, set before the invariant runs) and nothing else — the
  task read-only-ness is the ``completed`` state itself. Event:
  ``merge.succeeded`` (Section 9.6 catalog; Section 20.4 item 6). The
  plan's T17 cell also says "emit ``task.completed``" — that string is
  **not** in the frozen 24-type catalog (Section 9.6 enumerates
  ``merge.succeeded``, never ``task.completed``), so the catalog-first
  rule (Section 20.4 item 5) keeps the row's single registered event at
  ``merge.succeeded``; recorded here rather than amending a frozen
  catalog from a micro-task.
* **T18** ``merge_failed`` — same From carriers; To ``in_human_review``
  (the task re-enters human review with ``review_reason`` =
  ``merge_conflict``, Section 8.4 canonical member); actor M. Guard:
  the dispatch must carry a ``merge_status`` of ``conflict`` or
  ``failed`` (which flavor the executor reports — Section 7.2's two
  failure values, never inferred). Side effects: ``merge_status`` from
  the payload, ``review_reason`` = ``merge_conflict``, and the
  Section 9.8 push rides the dispatcher's ``in_human_review``-entry
  rule (the MT-3.9-01 hook: ``review.requested`` fires with the reason
  and no rule details — T18 never consulted the Policy Engine). Event:
  ``merge.failed``.

The queue ``start`` step (pending → merging) is **not** a dispatch —
Section 8.2 has no row for it; it is a guarded sub-status write the
service performs under the row lock with its own ``merge.started``
event (Section 9.6), recorded here so the absence of a T-row for
``start`` is a decision, never an omission.

**T20 ``merge_manual`` (MT-3.7-04, OQ-06's queue-side guard):** a third
row, registered through the same seam, that completes a ``manual``
project's pending entry without any merge — the plan's T-table ends at
T19, so the row is flagged for the plan owner in the WP changelog
(Section 20.5 traceability) rather than silently amending the plan's
table from a micro-task. It fires exactly where WP-3.6's approval does
not: ``list_merge_pending`` resolves an accidentally enqueued manual
entry before the executor can claim it (recorded coordination note: if
WP-3.6 later short-circuits approval itself, this guard simply stops
being reached — ``completed`` still happens exactly once, ADR-008).
"""

from __future__ import annotations

from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import MergeStatus, ReviewReason, Task, TaskState
from apps.tasks.models.transitions import TransitionReason
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

#: The two merge-pending carrier states (Section 8.1 sub-status readers).
_MERGE_PENDING_STATES: frozenset[str] = frozenset(
    {TaskState.IN_HUMAN_REVIEW, TaskState.TO_BE_AUDITED}
)


def _extra_str(context: TransitionContext, key: str) -> str:
    """One string payload of the dispatch (``merge_sha`` / ``merge_status``)."""
    value = context.extra.get(key) if context.extra else None
    if not isinstance(value, str):
        raise ValueError(f"transition context requires a string {key!r} (WP-3.7 contract)")
    return value


def _guard_merge_succeeded(task: Task, context: TransitionContext) -> None:
    """T17 guard — Section 8.2 verbatim: "*with resulting sha*".

    A merge result without the resulting ``merge_sha`` is refused with
    the Section 8.2 family code (``TASK_STATE_CONFLICT``): the row's
    lifecycle refuses, matching T15's missing-resolution reading. The
    service/serializer validates the *payload* shape first (400), so
    this branch answers a direct dispatcher caller.
    """
    if task.merge_status not in (MergeStatus.PENDING, MergeStatus.MERGING):
        raise _not_merge_pending(task)
    if not _extra_str(context, "merge_sha").strip():
        raise TaskStateConflict(
            task.pk,
            reason="merge result reported without a resulting sha (T17 guard)",
        )


def _side_effect_merge_succeeded(task: Task, context: TransitionContext) -> Task | None:
    """T17 side effects — Section 8.2: ``merge_status`` = ``merged``.

    Set before the dispatcher's completed-invariant check runs (the
    Section 8.3 rule-2 precondition), so ``completed`` is reachable
    only through this row (ADR-008: never completed without a merge).
    """
    task.merge_status = MergeStatus.MERGED
    return None


def _guard_merge_failed(task: Task, context: TransitionContext) -> None:
    """T18 guard — Section 8.2 verbatim: "*Executor reports failure*".

    The flavor of failure rides the payload (``conflict``/``failed`` —
    Section 7.2 values); an unknown string is a programming error
    (``ValueError``), never a silently-coerced write.
    """
    if task.merge_status not in (MergeStatus.PENDING, MergeStatus.MERGING):
        raise _not_merge_pending(task)
    flavor = _extra_str(context, "merge_status")
    if flavor not in (MergeStatus.CONFLICT, MergeStatus.FAILED):
        raise ValueError(
            f"transition context merge_status {flavor!r} is not conflict/failed "
            "(Section 7.2 failure values)"
        )


def _side_effect_merge_failed(task: Task, context: TransitionContext) -> Task | None:
    """T18 side effects — ``merge_status`` from payload; reason ``merge_conflict``.

    ``review_reason`` = the Section 8.4 canonical member before the
    dispatcher's ``in_human_review``-entry hook demands it (MT-3.9-01);
    the Section 9.8 push fires from the same entry rule.
    """
    task.merge_status = MergeStatus(_extra_str(context, "merge_status"))
    task.review_reason = ReviewReason.MERGE_CONFLICT
    return None


def _not_merge_pending(task: Task) -> TaskStateConflict:
    """The shared refusal: the task is not in the merge-pending sub-status."""
    return TaskStateConflict(
        task.pk,
        reason=f"is {task.merge_status}, not pending/merging (no merge result accepted)",
    )


# --- registration -------------------------------------------------------------


def _wired_merge_succeeded_spec() -> TransitionSpec:
    """The T17 row — ``completed`` only after a reported merge (ADR-008)."""
    return TransitionSpec(
        transition_id="T17",
        trigger="merge_succeeded",
        from_states=_MERGE_PENDING_STATES,
        to_state=TaskState.COMPLETED,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor M (Merge Executor)
        guard=_guard_merge_succeeded,
        side_effect=_side_effect_merge_succeeded,
        event_type="merge.succeeded",  # Section 9.6 catalog (20.4 item 6)
        reason_code=TransitionReason.MERGE_SUCCEEDED,
        wired=True,
    )


def _wired_merge_failed_spec() -> TransitionSpec:
    """The T18 row — conflict/failure returns to review with 8.4's reason."""
    return TransitionSpec(
        transition_id="T18",
        trigger="merge_failed",
        from_states=_MERGE_PENDING_STATES,
        to_state=TaskState.IN_HUMAN_REVIEW,
        actor_types=frozenset({"agent"}),  # Section 8.2 actor M (Merge Executor)
        guard=_guard_merge_failed,
        side_effect=_side_effect_merge_failed,
        event_type="merge.failed",  # Section 9.6 catalog (20.4 item 6)
        reason_code=TransitionReason.MERGE_FAILED,
        wired=True,
    )


# --- OQ-06 queue-side guard (MT-3.7-04) --------------------------------------


def _guard_merge_manual(task: Task, context: TransitionContext) -> None:
    """T20 guard — only a *pending* row of a ``manual`` project resolves.

    The row exists because WP-3.6's approval (T15) always leaves the
    task merge-pending: the queue-side guard is where OQ-06's "approval
    marks ``completed`` without executor involvement" is realized
    (MT-3.7-04 risk note: the short-circuit lives here, not in WP-3.6).
    A ``merging`` row was already claimed by an executor — it finishes
    through T17/T18, never hijacked mid-flight; a non-manual project
    answers TASK_STATE_CONFLICT so T17/T18 stay the only paths to
    ``completed`` for executable strategies (ADR-008).
    """
    if task.merge_status != MergeStatus.PENDING:
        raise TaskStateConflict(
            task.pk,
            reason=f"is {task.merge_status}, not pending (no manual resolution accepted)",
        )
    if task.project.agent_policy.merge_strategy != "manual":
        raise TaskStateConflict(
            task.pk,
            reason="its project's merge_strategy is not manual — OQ-06's "
            "queue-side resolution applies to manual projects only",
        )


def _side_effect_merge_manual(task: Task, context: TransitionContext) -> Task | None:
    """T20 side effect — ``merge_status`` = ``none``: there is no merge step.

    The dispatcher's Section 8.3 rule-2 invariant allows ``completed``
    with ``merge_status`` not ``merged`` exactly when the project says
    ``manual`` (OQ-06, decided 2026-10-11); ``none`` is the model's
    honest value for a task that was never meant to be merged.
    """
    task.merge_status = MergeStatus.NONE
    return None


def _wired_merge_manual_spec() -> TransitionSpec:
    """The T20 row — OQ-06's queue-side ``manual`` completion (recorded).

    Not a Section 8.2 plan row (the plan's table ends at T19): MT-3.7-04
    adds it through the same extension seam, flagged for the plan owner
    in the WP changelog (Section 20.5 traceability). ``event_type`` is
    the cataloged ``task.transitioned`` — Section 9.6 has no
    manual-completion type, and catalog-first forbids inventing one
    (the same recorded reading T17's ``task.completed`` note makes).
    """
    return TransitionSpec(
        transition_id="T20",
        trigger="merge_manual",
        from_states=_MERGE_PENDING_STATES,
        to_state=TaskState.COMPLETED,
        actor_types=frozenset({"agent"}),  # the queue surface's executor actor
        guard=_guard_merge_manual,
        side_effect=_side_effect_merge_manual,
        event_type="task.transitioned",  # Section 9.6 catalog (20.4 item 5)
        reason_code=TransitionReason.MERGE_MANUAL,
        wired=True,
    )


def ensure_merge_wired() -> None:
    """Put the wired T17/T18/T20 rows on the process registry (idempotent).

    Lazy like ``ensure_review_wired`` — never import-time or
    ``AppConfig.ready`` (the WP-1.5 suites assert the loader's rows and
    snapshot/restore the registry per test).
    """
    ensure_registered()
    for trigger, spec in (
        ("merge_succeeded", _wired_merge_succeeded_spec),
        ("merge_failed", _wired_merge_failed_spec),
        ("merge_manual", _wired_merge_manual_spec),
    ):
        row = DEFAULT_REGISTRY.get(trigger)
        if row is None or not row.wired:
            DEFAULT_REGISTRY.register(spec(), replace=True)


__all__ = ["ensure_merge_wired"]
