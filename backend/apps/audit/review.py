"""WP-3.6 wiring of the review rows T15/T16 — the sanctioned seam (MT-3.6-01).

Same discipline as ``apps.audit.transitions`` (WP-3.3) and
``apps.leases.wiring`` (WP-1.6): the dispatcher/registry/loader/hooks are
never edited here; ``DEFAULT_REGISTRY.register(spec, replace=True)`` puts
the two Section 8.2 Review rows on the process registry, lazily (the
WP-1.5 suites' snapshot/restore owns that state — production gets the
rows on the first review decision, tests inside their own restore
guards). This module also hosts :func:`submit_review_decision`, the one
service through which the ``POST /tasks/{id}/review`` endpoint fires the
rows (Section 9.1: ``tasks`` owns all state changes — the service never
writes ``state``).

**Row shapes — recorded readings (Section 20.1 item 5):**

* **T15** ``approve`` — From ``in_human_review``; To *"merge-pending"* is
  the Section 8.1 **sub-status** (``merge_status = pending``), never a
  seventh state, so the row is flag-only (``to_state=None`` — the T13
  reading, WP-3.3 precedent). Guard "*Resolution exists*": the dispatch
  must carry the current attempt's ``TaskResolution`` (the service
  resolved it under the row lock; a direct dispatcher caller without it
  is refused ``TASK_STATE_CONFLICT``). Side effects: ``merge_status`` =
  ``pending`` and the **Review Decision record** (MT-3.6-02's row,
  written in this same transaction — Section 8.2 rule 2). Event:
  ``review.decided`` (Section 9.6 catalog; Section 20.4 item 6).
* **T16** ``request_changes`` / ``reassign`` — From ``in_human_review``,
  To ``pending``, actor O. Guard "*Note required for request changes*"
  = a non-blank ``note``, else ``VALIDATION_ERROR`` (400) with a hint —
  the *fields* fail, so the catalog's malformed-input code applies.
  Side effects: ``latest_feedback`` set from the note (the overwrite
  semantics of Section 7.2 "latest wins"), ``attempt_number`` preserved
  (nothing here increments it — only T4's coder claim does), the coder
  lease cleared (the shared ``clear_coder_lease`` — the five columns are
  role-agnostic in effect), and the Review Decision recorded. For
  ``reassign`` the note is optional and ``latest_feedback`` moves only
  when one is supplied (MT-3.6-03's recorded reading — wiping a prior
  reviewer's note because the card was reshuffled would lose
  Section 11.5's context). Event: ``review.decided``.
* **``decided_via`` / ``decided_by``** ride the dispatch's ``extra``
  (the endpoint derives them server-side: owner-session token →
  ``web`` + user id; device token → ``mobile`` + device id — Section
  7.2's two channels, Sections 13/14). The dispatcher's actor column
  records ``owner`` for both: Section 8.2's legend reads *O = Owner
  (web/mobile)*, so the device is the owner's proxy, never a fourth
  actor (recorded reading).
* **Resolution binding**: ``approve`` always carries the resolution the
  reviewer saw (MT-3.6-04's stale guard lives in the service under the
  row lock); ``request_changes``/``reassign`` record the current
  attempt's resolution when one exists and stay ``NULL`` on a
  retry-exhaustion escalation (T9) that never had a submission.

The service enforces Section 12.2's *Review decisions* row (Owner /
Device) at the view layer and refuses anything but
``in_human_review`` with the Section 8.2 family code
``TASK_STATE_CONFLICT`` before the dispatch resolves the pair — the
cheap early refusal pattern of ``submit_audit_verdict``.
"""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.tasks.exceptions import TaskNotFound, TaskStateConflict, VersionConflict
from apps.tasks.models import MergeStatus, Task, TaskResolution, TaskState
from apps.tasks.models.transitions import TransitionReason
from apps.tasks.services.ids import ensure_valid_task_id
from apps.tasks.state_machine.dispatcher import dispatch_transition
from apps.tasks.state_machine.guards import clear_coder_lease
from apps.tasks.state_machine.loader import ensure_registered
from apps.tasks.state_machine.registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

from .independence import current_attempt_resolution
from .models import ReviewDecision, ReviewDecisionValue, ReviewVia

_NOTE_REQUIRED_HINT = (
    "request_changes requires a non-blank note — it becomes the next coder's latest_feedback "
    "(Section 11.5; T16 guard)."
)
_APPROVAL_STALE_DETAIL = (
    "The resolution this approval referenced has been replaced by a newer submission; "
    "refresh and re-review."
)


def _extra_resolution(context: TransitionContext, task: Task) -> TaskResolution | None:
    """The current-attempt resolution riding the dispatch, if any.

    ``None`` is a legitimate payload (a T9-anchored note action), so the
    type, task binding and *presence for approve* are asserted by each
    row's own guard — this helper only refuses a foreign-object contract
    break (a programming error, never a wire response).
    """
    resolution = context.extra.get("resolution")
    if resolution is not None and not isinstance(resolution, TaskResolution):
        raise ValueError("transition context 'resolution' must be a TaskResolution or None")
    if resolution is not None and resolution.task_id != task.pk:  # pragma: no cover - contract
        raise ValueError("resolution belongs to a different task")
    return resolution


def _extra_note(context: TransitionContext) -> str:
    """The reviewer's note (may legitimately be blank for reassign)."""
    note = context.extra.get("note", "")
    if not isinstance(note, str):
        raise ValueError("transition context 'note' must be a string")
    return note


def _extra_identity(context: TransitionContext, key: str, allowed: tuple[str, ...]) -> str:
    """One non-blank ``decided_by``/``decided_via`` input of the record."""
    value = context.extra.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"transition context requires a non-blank {key!r} (WP-3.6 contract)")
    if value not in allowed:
        raise ValueError(f"transition context {key} {value!r} is not in {allowed}")
    return value


def _record_decision(
    task: Task,
    context: TransitionContext,
    *,
    decision: str,
    resolution: TaskResolution | None,
) -> ReviewDecision:
    """The MT-3.6-02 row, written inside the dispatch transaction (8.2 r2)."""
    record: ReviewDecision = ReviewDecision.objects.create(
        task=task,
        resolution=resolution,
        decision=decision,
        note=_extra_note(context),
        decided_by=_extra_identity(context, "decided_by", (context.actor_ref,)),
        decided_via=_extra_identity(context, "decided_via", tuple(ReviewVia.values)),
    )
    return record


# --- T15: approve (Section 8.2 row T15) --------------------------------------


def _guard_approve(task: Task, context: TransitionContext) -> None:
    """T15 guard — Section 8.2 verbatim: "Resolution exists".

    The service resolved the current-attempt resolution under the row
    lock before dispatching; a dispatch without one (a direct caller or
    a task escalated by T9 with no submission) answers the Section 8.2
    family code ``TASK_STATE_CONFLICT`` (409) — the row's lifecycle
    refuses, the payload is fine. ``resolution_id`` staleness is the
    service's separate MT-3.6-04 guard, not this column's.
    """
    if _extra_resolution(context, task) is None:
        raise TaskStateConflict(
            task.pk,
            reason="has no current-attempt resolution to approve (T15 guard)",
        )


def _side_effect_approve(task: Task, context: TransitionContext) -> Task | None:
    """T15 side effects — "``merge_status`` = ``pending``; record decision".

    Merge-pending is the Section 8.1 sub-status, never a seventh state;
    WP-3.7's queue picks the task up from here (Section 8.1: the card
    stays in its state with an "approved, merging" badge).
    """
    resolution = _extra_resolution(context, task)
    assert resolution is not None  # the guard above (and the service) proved it
    task.merge_status = MergeStatus.PENDING
    _record_decision(
        task,
        context,
        decision=ReviewDecisionValue.APPROVE,
        resolution=resolution,
    )
    return None


# --- T16: request changes / reassign (Section 8.2 row T16) -------------------


def _guard_note_required(task: Task, context: TransitionContext) -> None:
    """T16 guard — "Note required for request changes" (reassign needs none).

    The guard rides the ``request_changes`` spec only, so the trigger
    itself is the decision being guarded — no ``extra`` flag re-check.
    """
    if not _extra_note(context).strip():
        raise ValidationError({"note": _NOTE_REQUIRED_HINT})


def _side_effect_request_changes(task: Task, context: TransitionContext) -> Task | None:
    """T16 (request_changes) — latest wins, attempt preserved, worker clear."""
    note = _extra_note(context)
    task.latest_feedback = note  # Section 7.2: "latest" overwrite semantics
    clear_coder_lease(task)
    _record_decision(
        task,
        context,
        decision=ReviewDecisionValue.REQUEST_CHANGES,
        resolution=_extra_resolution(context, task),
    )
    return None


def _side_effect_reassign(task: Task, context: TransitionContext) -> Task | None:
    """T16 (reassign) — back to ``pending``, worker clear, note optional.

    ``latest_feedback`` moves only when a note was supplied (MT-3.6-03's
    recorded reading of the plan's side-effect column).
    """
    note = _extra_note(context)
    if note.strip():
        task.latest_feedback = note
    clear_coder_lease(task)
    _record_decision(
        task,
        context,
        decision=ReviewDecisionValue.REASSIGN,
        resolution=_extra_resolution(context, task),
    )
    return None


# --- registration -------------------------------------------------------------


def _wired_approve_spec() -> TransitionSpec:
    """The T15 row — merge-pending is a sub-status (T13's flag-only reading)."""
    return TransitionSpec(
        transition_id="T15",
        trigger="approve",
        from_states=frozenset({TaskState.IN_HUMAN_REVIEW}),
        to_state=None,  # §8.2 To "merge-pending" — the merge_status sub-status
        actor_types=frozenset({"owner"}),  # Section 8.2 actor O (web/mobile)
        guard=_guard_approve,
        side_effect=_side_effect_approve,
        event_type="review.decided",  # Section 9.6 catalog pair (20.4 item 6)
        reason_code=TransitionReason.APPROVE,
        wired=True,
    )


def _wired_request_changes_spec() -> TransitionSpec:
    """The T16 request_changes half — note-guarded return to ``pending``."""
    return TransitionSpec(
        transition_id="T16",
        trigger="request_changes",
        from_states=frozenset({TaskState.IN_HUMAN_REVIEW}),
        to_state=TaskState.PENDING,
        actor_types=frozenset({"owner"}),  # Section 8.2 actor O (web/mobile)
        guard=_guard_note_required,
        side_effect=_side_effect_request_changes,
        event_type="review.decided",
        reason_code=TransitionReason.REQUEST_CHANGES,
        wired=True,
    )


def _wired_reassign_spec() -> TransitionSpec:
    """The T16 reassign half — unconditional return to ``pending``."""
    return TransitionSpec(
        transition_id="T16",
        trigger="reassign",
        from_states=frozenset({TaskState.IN_HUMAN_REVIEW}),
        to_state=TaskState.PENDING,
        actor_types=frozenset({"owner"}),  # Section 8.2 actor O (web/mobile)
        guard=None,  # Section 8.2 T16's note clause binds request changes only
        side_effect=_side_effect_reassign,
        event_type="review.decided",
        reason_code=TransitionReason.REASSIGN,
        wired=True,
    )


def ensure_review_wired() -> None:
    """Put the wired T15/T16 rows on the process registry (idempotent).

    Lazy like ``ensure_audit_wired`` — never import-time or
    ``AppConfig.ready`` (the WP-1.5 suites assert the loader's rows and
    snapshot/restore the registry per test).
    """
    ensure_registered()
    for trigger, spec in (
        ("approve", _wired_approve_spec),
        ("request_changes", _wired_request_changes_spec),
        ("reassign", _wired_reassign_spec),
    ):
        row = DEFAULT_REGISTRY.get(trigger)
        if row is None or not row.wired:
            DEFAULT_REGISTRY.register(spec(), replace=True)


# --- the service the endpoint delegates to (MT-3.6-01) -----------------------


class ReviewOutcome(NamedTuple):
    """One accepted decision's outcome (the endpoint's response source)."""

    task: Task  # the post-transition row the dispatcher returned
    decision: ReviewDecision  # the record the side effect wrote


def submit_review_decision(
    task_id: str,
    *,
    decision: str,
    note: str,
    resolution_id: UUID | None,
    version: int,
    decided_by: str,
    decided_via: str,
    caller_project_id: str | None = None,
) -> ReviewOutcome:
    """Fire exactly one T15/T16 row and return its recorded outcome.

    Lock, scope, state, resolution binding — then dispatch, all in one
    transaction (Section 8.2 rule 2), so a refused decision leaves no
    Review Decision row, no version bump and no event behind.

    MT-3.6-04 (approve safety, Section 14.2): the approval is **bound to
    the ``resolution_id`` the reviewer saw**. The check runs under the
    task's row lock and inside the dispatch transaction, so a
    re-submission cannot slip between the comparison and the write — a
    stale binding answers ``VERSION_CONFLICT`` (409; the catalog's
    stale-resource semantics — choice recorded in the WP-3.6 changelog)
    with a refresh-and-re-review message and **zero** T15 side effects.
    Only ``approve`` is resolution-bound (Section 14.2 names the
    approval; the note actions carry no such binding — no invented
    guards).
    """
    ensure_valid_task_id(task_id)
    ensure_review_wired()

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        if task.state != TaskState.IN_HUMAN_REVIEW:
            # Cheap early refusal (the dispatcher would answer the same
            # 409): only a task under review accepts a review decision.
            raise TaskStateConflict(
                task.pk,
                reason=f"is {task.state}, not in_human_review (no review decision accepted)",
            )

        current = current_attempt_resolution(task)
        resolution = current
        if decision == ReviewDecisionValue.APPROVE:
            if resolution_id is None:
                raise ValidationError(
                    {
                        "resolution_id": (
                            "approve binds the resolution the reviewer saw "
                            "(Section 14.2; MT-3.6-04) — send its id."
                        )
                    }
                )
            candidate = TaskResolution.objects.filter(task=task, pk=resolution_id).first()
            if candidate is None:
                raise ValidationError(
                    {"resolution_id": "is not one of this task's stored submissions."}
                )
            if current is None or candidate.pk != current.pk:
                # Section 14.2 approve safety: a newer submission
                # invalidates a stale approval (ADR-012).
                raise VersionConflict(
                    task.pk,
                    expected=version,
                    actual=task.version,
                    detail=_APPROVAL_STALE_DETAIL,
                )
            resolution = candidate

        updated = dispatch_transition(
            task_id=task.pk,
            trigger=decision,
            actor_type="owner",  # §8.2 legend: O = Owner (web/mobile)
            actor_ref=decided_by,
            expected_version=version,
            note=note,
            extra={
                "decision": decision,
                "resolution": resolution,
                "note": note,
                "decided_by": decided_by,
                "decided_via": decided_via,
            },
        )
        record = ReviewDecision.objects.filter(task=updated).order_by("-decided_at").first()
        assert record is not None, "the side effect wrote the record in this transaction"
        return ReviewOutcome(task=updated, decision=record)


__all__ = [
    "ReviewOutcome",
    "ensure_review_wired",
    "submit_review_decision",
]
