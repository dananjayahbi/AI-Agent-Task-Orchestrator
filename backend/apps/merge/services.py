"""The merge queue protocol — pending / start / result (MT-3.7-01).

Section 9.2's Merge Executor surface as services the views delegate to
(Section 9.1: the ``merge`` app owns the queue API). Three operations:

* :func:`list_merge_pending` — one cursor page of merge-pending tasks
  (Section 8.1 sub-status ``merge_status = pending`` in a carrier
  state), FIFO by primary key so polling is stable while rows land.
  Agent callers see only their token's project (ADR-004 zero-bleed —
  the filter is the scope guard for this URL-less route); the Owner
  sees every project (Section 12.2: Owner *Read*).
* :func:`start_merge` — the queue's claim: ``pending`` → ``merging``
  under the row lock, **not** a dispatch (Section 8.2 has no row for
  ``start`` — recorded reading in ``transitions.py``), with the
  ``merge.started`` Section 9.6 event written in the same transaction
  (published post-commit). Wrong sub-status answers
  ``TASK_STATE_CONFLICT``; a lost response is retried with the same
  ``Idempotency-Key`` (ADR-012), never by a second mutation.
* :func:`report_merge_result` — dispatch exactly one of T17/T18:
  ``succeeded`` fires ``merge_succeeded`` → ``completed`` +
  ``merge_status = merged`` (ADR-008: completed only after the merge
  result is reported) carrying the resulting ``merge_sha``; a
  ``conflict``/``failed`` report fires ``merge_failed`` → back to
  ``in_human_review`` with ``review_reason = merge_conflict`` and the
  Section 9.8 push (the dispatcher's ``in_human_review``-entry rule).
  A repeat report on an exited task answers ``TASK_STATE_CONFLICT``
  (T17/T18 fire exactly once — the From column no longer matches).

Recorded readings (Section 20.1 item 5): ``start`` requires the
carrier **state** as well as the sub-status, so a stray task left in
``pending`` state by an out-of-band review decision can never enter
the queue (its state would refuse T17/T18 — queue entries are always
dispatchable); the service-level ``merge_status`` check runs before
the dispatch so a task that already exited answers the family code
without touching the registry; ``version`` is accepted as an optional
CAS token (FR-TSK-06) on both mutations — the executor chains it from
the pending listing through ``start`` to ``result``.
"""

from __future__ import annotations

from typing import NamedTuple

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.core.pagination import encode_cursor
from apps.events.services import write_event
from apps.tasks.exceptions import TaskNotFound, TaskStateConflict, VersionConflict
from apps.tasks.models import MergeStatus, Task, TaskResolution, TaskState
from apps.tasks.services.ids import ensure_valid_task_id
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .transitions import ensure_merge_wired

#: One actor for every executor-side mutation (the ``lease-sweeper``
#: pattern — Section 12.5 records the executor role, not a session).
MERGE_EXECUTOR_ACTOR_REF = "merge-executor"

#: OQ-06's fourth ``merge_strategy`` value (Section 7.2 lists three;
#: decided 2026-10-11) and the T20 trigger that resolves such entries
#: from the queue without any merge (MT-3.7-04's queue-side guard).
_MANUAL_STRATEGY = "manual"
_MANUAL_TRIGGER = "merge_manual"

#: The states that carry the merge-pending sub-status (Section 8.1).
_CARRIER_STATES: frozenset[str] = frozenset({TaskState.IN_HUMAN_REVIEW, TaskState.TO_BE_AUDITED})

#: The result values the executor may report (Section 7.2 + MT contract).
RESULT_SUCCEEDED = "succeeded"
RESULT_CONFLICT = MergeStatus.CONFLICT
RESULT_FAILED = MergeStatus.FAILED
RESULT_VALUES: frozenset[str] = frozenset(
    {RESULT_SUCCEEDED, str(RESULT_CONFLICT), str(RESULT_FAILED)}
)


class MergeResultOutcome(NamedTuple):
    """One accepted result report's outcome (the endpoint's response source)."""

    task: Task  # the post-transition row the dispatcher returned
    result: str  # succeeded | conflict | failed (echoed to the caller)
    sha: str | None  # the resulting sha on success (Section 11.4)


def list_merge_pending(
    *,
    caller_project_id: str | None,
    cursor: str | None,
    page_size: int,
) -> tuple[list[Task], str | None]:
    """One page of merge-pending tasks plus its ``next_cursor``.

    FIFO by primary key (ascending — oldest approval first, a stable
    documented sort: task ids page the same way their allocation
    order does). Fetch-one-lookahead (pagination.md): ``next_cursor``
    is ``None`` exactly when the page is the last one. Archived tasks
    (T19) never enter the queue, and only carrier states are listed —
    a stray sub-status outside them could never dispatch T17/T18, so
    offering it would hand the executor a task it cannot finish
    (recorded reading; see the module docstring).

    **OQ-06 queue-side guard (MT-3.7-04):** entries whose project's
    ``merge_strategy`` is ``manual`` are *resolved* here — dispatched
    through T20 to ``completed`` without any merge — and never
    returned, so an accidentally enqueued manual task produces no
    executor merge attempt. The cursor advances past them (computed
    from the raw fetched page), so a page full of manual entries still
    makes progress on the next poll.
    """
    queryset = Task.objects.filter(
        merge_status=MergeStatus.PENDING,
        state__in=_CARRIER_STATES,
        archived_at__isnull=True,
    ).select_related("project__agent_policy")
    if caller_project_id is not None:
        queryset = queryset.filter(project_id=caller_project_id)
    ordered = queryset.order_by("pk")
    if cursor is not None:
        ordered = ordered.filter(pk__gt=cursor)
    fetched = list(ordered[: page_size + 1])
    has_more = len(fetched) > page_size
    page = fetched[:page_size]
    next_cursor = encode_cursor(page[-1].pk) if has_more and page else None
    return _resolve_manual_entries(page), next_cursor


def _resolve_manual_entries(tasks: list[Task]) -> list[Task]:
    """Complete (and drop) every ``manual`` entry; return the rest.

    Each resolution is one T20 dispatch in its own transaction with its
    ``task.transitioned`` event (Section 9.6). A ``TaskStateConflict``
    from a raced row (claimed or exited between the listing read and
    the dispatch) returns the row unchanged — resolution never masks or
    forces a concurrent transition; the *next* poll re-reads its state.
    """
    if not any(task.project.agent_policy.merge_strategy == _MANUAL_STRATEGY for task in tasks):
        return tasks
    ensure_merge_wired()
    kept: list[Task] = []
    for task in tasks:
        if task.project.agent_policy.merge_strategy != _MANUAL_STRATEGY:
            kept.append(task)
            continue
        try:
            dispatch_transition(
                task_id=task.pk,
                trigger=_MANUAL_TRIGGER,
                actor_type="agent",  # the queue surface's executor actor
                actor_ref=MERGE_EXECUTOR_ACTOR_REF,
                note="manual merge_strategy (OQ-06): resolved without an executor merge",
                extra={"event_data": {"merge_strategy": _MANUAL_STRATEGY}},
            )
        except TaskStateConflict:
            kept.append(task)  # raced — the next poll re-reads its state
    return kept


def branch_names_for(tasks: list[Task]) -> dict[str, str]:
    """Current-attempt branch per task id (the executor's merge input).

    One query for the whole page; a task without a matching resolution
    is absent from the mapping (the serializer renders ``null`` — a
    defensive reading, since every merge-pending carrier required a
    resolution to get here).
    """
    resolutions = TaskResolution.objects.filter(task__in=tasks)
    current = {task.pk: task.attempt_number for task in tasks}
    return {
        resolution.task_id: resolution.branch_name
        for resolution in resolutions
        if resolution.attempt_number == current.get(resolution.task_id)
    }


def start_merge(
    task_id: str,
    *,
    caller_project_id: str | None,
    version: int | None = None,
) -> Task:
    """Mark one pending task ``merging`` and emit ``merge.started``.

    One transaction (Section 8.2 rule 2's spirit — the sub-status write
    and its Section 9.6 event commit together; publishing is the
    events app's post-commit hook). Refusals: ``TASK_NOT_FOUND``
    (404), ``AUTH_FORBIDDEN_PROJECT`` (403, scope before anything
    else), ``TASK_STATE_CONFLICT`` (409 — not merge-pending, not in a
    carrier state, archived, or already claimed by another executor),
    ``VERSION_CONFLICT`` (409 — a stale ``version`` changes nothing).
    """
    ensure_valid_task_id(task_id)

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.archived_at is not None:
            raise TaskStateConflict(
                task.pk,
                reason="is archived; the merge queue only offers live tasks",
            )
        if task.state not in _CARRIER_STATES:
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.state}, not a merge-pending carrier state",
            )
        if task.merge_status != MergeStatus.PENDING:
            # Already merging (a second executor's claim) or exited —
            # both answer the Section 8.2 family code before any write.
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.merge_status}, not pending (no start accepted)",
            )
        if version is not None and task.version != version:
            raise VersionConflict(task.pk, expected=version, actual=task.version)

        task.merge_status = MergeStatus.MERGING
        task.version += 1  # Section 7.2: increments on every change
        task.save(update_fields=["merge_status", "version"])
        write_event(
            type="merge.started",
            project_id=task.project_id,
            actor_type="agent",
            actor_ref=MERGE_EXECUTOR_ACTOR_REF,
            task_id=task.pk,
            data={
                "from_merge_status": str(MergeStatus.PENDING),
                "to_merge_status": str(MergeStatus.MERGING),
                "task_version": task.version,
            },
        )
    return task


def report_merge_result(
    task_id: str,
    *,
    result: str,
    sha: str | None,
    details: str,
    version: int | None,
    caller_project_id: str | None,
) -> MergeResultOutcome:
    """Dispatch exactly one T17/T18 row for one reported merge outcome.

    ``succeeded`` requires the resulting ``merge_sha`` (T17's guard —
    it rides the request payload, the history note **and** the event
    ``data``: Section 7.2 has no sha column, so those three carriers
    are the documented contract, never a silent schema change).
    ``conflict``/``failed`` dispatch T18 with the payload's flavor
    (Section 7.2 values, never inferred server-side).

    All under the row lock (lock, scope, cheap sub-status refusal,
    dispatch — the ``submit_review_decision`` pattern), so a refused
    report leaves no version bump, no history row and no event.
    """
    ensure_valid_task_id(task_id)
    ensure_merge_wired()
    if result not in RESULT_VALUES:
        raise ValueError(f"result {result!r} is not succeeded/conflict/failed")
    if result == RESULT_SUCCEEDED and not (sha or "").strip():
        raise ValidationError(
            {"sha": "a successful merge must report the resulting sha (Section 11.4)."}
        )

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.merge_status not in (MergeStatus.PENDING, MergeStatus.MERGING):
            # Exited the queue (result already applied, or never
            # enqueued): the dispatcher would answer the same 409 —
            # the cheap early refusal skips the registry round trip.
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.merge_status}, not pending/merging (no merge result accepted)",
            )

        succeeded = result == RESULT_SUCCEEDED
        note = f"merge succeeded: {sha}" if succeeded else (details or "merge failed")
        if succeeded and details:
            note = f"{note} — {details}"
        extra: dict[str, object] = {
            "details": details,
            "event_data": (
                {"merge_sha": sha} if succeeded else {"merge_status": result, "details": details}
            ),
        }
        if succeeded:
            extra["merge_sha"] = sha
        else:
            extra["merge_status"] = result

        updated = dispatch_transition(
            task_id=task.pk,
            trigger="merge_succeeded" if succeeded else "merge_failed",
            actor_type="agent",  # Section 8.2 actor M (Merge Executor)
            actor_ref=MERGE_EXECUTOR_ACTOR_REF,
            expected_version=version,
            note=note,
            extra=extra,
        )
        return MergeResultOutcome(
            task=updated,
            result=result,
            sha=sha if succeeded else None,
        )


__all__ = [
    "MERGE_EXECUTOR_ACTOR_REF",
    "RESULT_CONFLICT",
    "RESULT_FAILED",
    "RESULT_SUCCEEDED",
    "RESULT_VALUES",
    "MergeResultOutcome",
    "branch_names_for",
    "list_merge_pending",
    "report_merge_result",
    "start_merge",
]
