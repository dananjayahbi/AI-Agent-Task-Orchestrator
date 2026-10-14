"""The single execution path for task state changes (Section 9.1; MT-1.5-01).

One function — :func:`dispatch_transition` — implements Section 8.2's
three universal rules inside one ``transaction.atomic()``:

1. **Illegal pair →** ``TASK_STATE_CONFLICT`` (409) from the closed
   catalog — raised by ``TransitionRegistry.resolve`` before anything is
   written, so an unmapped ``(from_state, trigger)`` changes nothing.
2. **One transaction** writes the state change (and every side effect),
   the ``version`` increment, **exactly one** Task Transition history
   row (FR-TSK-04) and **exactly one** Section 9.6 Event row per
   registered row event via the single in-transaction hook
   (``hooks.emit_transition_event`` — WP-1.9 registers the writer;
   until then the seam is a no-op, never a second mechanism) — plus,
   on ``in_human_review`` entry only, the WP-3.9 ``review.requested``
   event (MT-3.9-02: one per entry, same transaction, published
   post-commit like every other event). A failure anywhere — guard,
   invariant, or the hook itself — rolls the whole dispatch back.
3. **Optimistic version**: ``expected_version`` (what the UI saw) is
   compared against the locked row; a stale value answers
   ``VERSION_CONFLICT`` (409) and changes nothing.

Section 8.3 invariants are enforced as dispatch-time assertions where
they are checkable here: never reach ``completed`` without
``merge_status = merged`` (rule 2, with the OQ-06/ADR-008 no-merge-step
exception), and the coder lease lives only in ``in_progress`` (rule 1).
Rules 3 and 4 belong to WP-3.x (auditor sessions, Policy Engine) and
are not yet enforceable at dispatch time.

Resolution order is deliberate and testable: **state pair → actor →
wired → guard → side effects → invariants → persist → history → event →
review.requested (entry only) → push**. State first (Section 8.2 rule 1
makes every illegal pair a conflict regardless of who asks), then the
Actor column (``TransitionActorForbidden`` — 403 ``ROLE_NOT_PERMITTED``),
then the MT-1.5-04 stub refusal (nothing written), then the row's own
guards.

T1 (create) is **exempt from the registry by design**, recorded per
MT-1.5-01's risk note: T1's From column is "*(new)*" — no row, no
from-state, none of the six canonical values representable — and its
side effects (allocate id, land in ``draft``) are the INSERT itself,
already implemented as ``T1's model-level step`` by WP-1.4's
``create_task`` inside the Section 7.3 creating transaction. Routing it
through this dispatcher would fake a from-state the table does not
have; the ``task.created`` event point stays in ``create_task`` for
WP-1.9 (same seam).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db import transaction
from django.utils import timezone

from ..exceptions import (
    TaskNotFound,
    TaskStateConflict,
    TransitionActorForbidden,
    TransitionNotWired,
    VersionConflict,
)
from ..models import (
    ClaimedRole,
    MergeStatus,
    ReviewReason,
    Task,
    TaskState,
    TaskTransition,
    TransitionReason,
)
from .hooks import emit_transition_event, review_rule_details, trigger_review_push
from .loader import ensure_registered
from .registry import ACTOR_TYPES, DEFAULT_REGISTRY, TransitionContext, TransitionSpec

# Section 9.6: tasks created in a no-merge project skip the executor only
# when the policy says so (OQ-06 decided: merge_strategy "manual").
_NO_MERGE_STEP = "manual"


def dispatch_transition(
    *,
    task_id: str,
    trigger: str,
    actor_type: str,
    actor_ref: str,
    expected_version: int | None = None,
    reason_code: str | None = None,
    note: str = "",
    extra: Mapping[str, Any] | None = None,
) -> Task:
    """Dispatch one Section 8.2 row for *task_id*; return the updated task.

    ``reason_code`` defaults to the row's registered code and must stay
    inside the model's catalog (Section 8.4 review reasons plus the
    Section 8.2 trigger codes) — a value outside it is a programming
    error (``ValueError``), never a silent write: codes are added to the
    catalog first (Section 20.4 item 5). ``extra`` feeds the row's
    guard/side-effect callables through ``TransitionContext`` (session
    ids, resolution payloads — WP-1.6/WP-2.6 wiring inputs).
    """
    ensure_registered()
    if actor_type not in ACTOR_TYPES:
        raise ValueError(f"actor_type {actor_type!r} is not owner/agent/system (Section 7.2).")
    if not actor_ref.strip():
        raise ValueError("actor_ref must identify the actor (FR-TSK-04 records who).")
    context = TransitionContext(actor_type=actor_type, actor_ref=actor_ref, extra=extra)

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if expected_version is not None and task.version != expected_version:
            raise VersionConflict(task.pk, expected=expected_version, actual=task.version)

        spec = DEFAULT_REGISTRY.resolve(task_id=task.pk, state=task.state, trigger=trigger)
        if actor_type not in spec.actor_types:
            raise TransitionActorForbidden(
                task.pk,
                trigger=trigger,
                actor_type=actor_type,
                allowed=", ".join(sorted(spec.actor_types)),
            )
        if not spec.wired:
            # MT-1.5-04: deterministic refusal before guards/side effects —
            # state, version and history stay untouched.
            raise TransitionNotWired(
                trigger, transition_id=spec.transition_id, wired_by=spec.stubbed_by or "?"
            )

        reason = reason_code if reason_code is not None else spec.reason_code
        if reason not in dict(TransitionReason.choices):
            raise ValueError(
                f"reason_code {reason!r} is not in the transition-reason catalog "
                "(Section 8.4 review reasons + Section 8.2 trigger codes)."
            )

        if spec.guard is not None:
            spec.guard(task, context)
        from_state = task.state
        version_before = task.version
        if spec.side_effect is not None:
            # A side effect may persist the row itself (T19's archive_task
            # contract) and return the freshly locked instance; adopting it
            # keeps the dispatcher's view of version/archived_at honest.
            adopted = spec.side_effect(task, context)
            if adopted is not None:
                task = adopted
        if spec.to_state is not None:
            # The one direct write of `state` anywhere in the codebase
            # (Section 9.1) — the direct-write test of MT-1.5-06 allows
            # exactly this line's package.
            task.state = spec.to_state

        _assert_completed_invariant(task)
        _assert_lease_invariant(task)

        if task.version == version_before:
            # Incremented on every change (Section 7.2); a self-saving side
            # effect (T19) already bumped it, so exactly one bump per dispatch.
            task.version += 1
            task.save()

        TaskTransition.objects.create(
            task=task,
            from_state=from_state,
            to_state=task.state,
            actor_type=actor_type,
            actor_ref=actor_ref,
            reason_code=reason,
            note=note,
        )
        emit_transition_event(
            {
                "type": spec.event_type,
                "project_id": task.project_id,
                "task_id": task.pk,
                "occurred_at": timezone.now(),
                "actor": {"type": actor_type, "ref": actor_ref},
                "data": {
                    "from_state": from_state,
                    "to_state": task.state,
                    "reason_code": reason,
                    "task_version": task.version,
                },
            }
        )
        if spec.to_state == TaskState.IN_HUMAN_REVIEW:
            # WP-3.9 (MT-3.9-01/02): exactly one ``review.requested``
            # event per ``in_human_review`` entry (Section 9.8's push
            # trigger — T8/T9/T14 today, T18 when WP-3.7 wires it, and
            # any fifth entry path by the same hook rule). The ``data``
            # contract: the canonical Section 8.4 ``review_reason`` the
            # row's side effect set, the dedupe key's ``task_version``
            # (Section 9.8), and — only where the Policy Engine decided
            # (T14 via the audit app's rule-details provider) — the
            # persisted ``policy_rule_results``; T8/T9/T18 carry their
            # reason with no rule-details key at all (absence is
            # expressible, never a fabricated rule set). An entry row
            # that never set a reason is a wiring bug — a programming
            # error (``ValueError``), never a silent payload.
            review_reason = task.review_reason
            if review_reason not in set(ReviewReason.values):
                raise ValueError(
                    f"review_reason {review_reason!r} is not a Section 8.4 member — "
                    f"{spec.transition_id} must set it before entry (MT-3.9-01)."
                )
            review_data: dict[str, Any] = {
                "review_reason": review_reason,
                "task_version": task.version,
            }
            review_data.update(review_rule_details(task, spec.transition_id))
            emit_transition_event(
                {
                    "type": "review.requested",
                    "project_id": task.project_id,
                    "task_id": task.pk,
                    "occurred_at": timezone.now(),
                    "actor": {"type": actor_type, "ref": actor_ref},
                    "data": review_data,
                }
            )
            # Section 9.8: push on `in_human_review` entry (all reasons) —
            # the dedupe key (event type, task id, state version) rides the
            # payload for WP-5.4's dispatcher. The push is a downstream
            # consumer of this one entry signal, never a second writer.
            trigger_review_push(
                {
                    "event_type": spec.event_type,
                    "project_id": task.project_id,
                    "task_id": task.pk,
                    "state_version": task.version,
                    "reason_code": reason,
                }
            )
    return task


def _assert_completed_invariant(task: Task) -> None:
    """Section 8.3 rule 2: never ``completed`` without ``merged``.

    OQ-06's exception: a project whose ``merge_strategy`` is ``manual``
    has no merge step, so approval may complete it directly (decided
    2026-10-11, ADR-008 context). A breach is a state-condition refusal
    and answers the Section 8.2 family: ``TASK_STATE_CONFLICT`` (409).
    """
    if task.state != TaskState.COMPLETED or task.merge_status == MergeStatus.MERGED:
        return
    if task.project.agent_policy.merge_strategy == _NO_MERGE_STEP:
        return
    raise TaskStateConflict(
        task.pk,
        reason="would reach completed with merge_status not merged (Section 8.3 rule 2)",
    )


def _assert_lease_invariant(task: Task) -> None:
    """Section 8.3 rule 1: a coder lease lives only in ``in_progress``.

    Checked against the task *after* the transition's side effects ran:
    leaving ``in_progress`` must have cleared the worker (T5/T6/T7/T9
    side effects; T8's wiring will do the same), and entering it (T4's
    wiring) must have set worker, role and lease together. A breach is a
    wiring bug surfaced as ``TASK_STATE_CONFLICT`` (409) with rollback —
    never a silently half-claimed row.
    """
    if task.state == TaskState.IN_PROGRESS:
        missing = [
            name
            for name, value in (
                ("worker_agent_id", task.worker_agent_id),
                ("claimed_role", task.claimed_role),
                ("lease_expires_at", task.lease_expires_at),
            )
            if value is None
        ]
        if missing:
            raise TaskStateConflict(
                task.pk,
                reason=(
                    "would sit in_progress without worker/lease fields "
                    f"({', '.join(missing)}) — Section 8.3 rule 1"
                ),
            )
        return
    if task.claimed_role == ClaimedRole.CODER:
        raise TaskStateConflict(
            task.pk,
            reason="would keep a coder lease outside in_progress (Section 8.3 rule 1)",
        )


def registered_specs() -> dict[str, TransitionSpec]:
    """The rows the dispatcher can resolve (matrix enumeration, tools)."""
    ensure_registered()
    return DEFAULT_REGISTRY.specs()
