"""Agent transition stubs T4/T6/T7/T8 — MT-1.5-04 (register now, wire later).

The four rows the coder agent dispatches, registered with the exact
Section 8.2 From/To/Actor shape so the matrix (MT-1.5-06) enumerates the
full table today, while their **behavior is delegated**: guards and side
effects are stubs that raise ``TransitionNotWired`` (deterministic, no
state/version/history/event writes — the dispatcher refuses a
``wired=False`` row even earlier, right after the actor check).

Each stub's docstring transcribes the table's Guard and Side-effects
cells **verbatim** — that text is the contract WP-1.6 (T4/T6 claim and
release) and WP-2.6/WP-3.2 (T7/T8 submit) wire against, through the
registry extension point only:

    DEFAULT_REGISTRY.register(rewired_spec, replace=True)

…never by editing the dispatcher (MT-1.5-04 acceptance). Guard
signatures already carry the stable ``(task, context)`` shape, with
caller-specific inputs (session id, resolution payload,
``requires_human_attention`` evidence) read from ``context.extra`` —
MT-1.5-04's risk note demands the signature not drift at wiring time.

T8's ``review_reason`` values are fixed to the Section 8.4 members
``self_flagged`` / ``scope_violation`` (exposed as
:data:`T8_REVIEW_REASONS` so tests assert the strict pair).
"""

from __future__ import annotations

from ..exceptions import TransitionNotWired
from ..models.task import ReviewReason, Task, TaskState
from .registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec

#: The only two review reasons T8 may set (Section 8.4 canonical enum).
T8_REVIEW_REASONS: tuple[str, ...] = (ReviewReason.SELF_FLAGGED, ReviewReason.SCOPE_VIOLATION)


# --- T4: claim (WP-1.6 wires the row) ---------------------------------------


def _guard_claim(task: Task, context: TransitionContext) -> None:
    """T4 guards — Section 8.2 verbatim (the wiring contract, WP-1.6).

    "Project active; token scope matches; dependencies completed;
    ``max_concurrent_tasks`` not exceeded; row lock won". Notes for the
    wiring WP: token scope is already enforced at the API boundary
    (ADR-004), dependencies completed is
    ``services.dependencies.all_dependencies_completed``, concurrency
    and the row lock live inside the claim transaction of Section 9.3
    (WP-1.6), which reads its caller identity from ``context``.
    """
    raise TransitionNotWired("claim", transition_id="T4", wired_by="WP-1.6")


def _side_effect_claim(task: Task, context: TransitionContext) -> Task | None:
    """T4 side effects — Section 8.2 verbatim (wiring contract, WP-1.6).

    "Set worker, session, lease, ``attempt_number``+1; emit
    ``task.claimed``" — the event type is already registered on the row
    (Section 9.6 catalog); the lease fields follow Section 8.6 acquire.
    """
    raise TransitionNotWired("claim", transition_id="T4", wired_by="WP-1.6")


# --- T6: voluntary release (WP-1.6 wires the row) ----------------------------


def _guard_release(task: Task, context: TransitionContext) -> None:
    """T6 guard — Section 8.2 verbatim: "Caller owns lease (or Owner override)".

    The wiring WP compares ``context.actor_ref``/session against the
    lease holder (catalog refusal: ``LEASE_NOT_OWNED``) and admits the
    Owner override exactly as written. The signature is the stable one
    MT-1.5-04's risk note pins.
    """
    raise TransitionNotWired("voluntary_release", transition_id="T6", wired_by="WP-1.6")


def _side_effect_release(task: Task, context: TransitionContext) -> Task | None:
    """T6 side effects — Section 8.2 verbatim: "Clear worker; no failure increment".

    Clearing reuses ``guards.clear_coder_lease``; ``failure_retry_count``
    is deliberately untouched (a voluntary release is not a failure).
    """
    raise TransitionNotWired("voluntary_release", transition_id="T6", wired_by="WP-1.6")


# --- T7: submit (WP-2.6/WP-3.2 wire the row) ---------------------------------


def _guard_submit(task: Task, context: TransitionContext) -> None:
    """T7 guards — Section 8.2 verbatim (wiring contract, WP-2.6).

    "Lease owner and not expired; resolution valid; ``audit_required``
    true; not self-flagged; scope check ok". Inputs arrive through
    ``context.extra`` (session id, resolution record); the catalog
    refusals already exist for each clause (``LEASE_NOT_OWNED``,
    ``LEASE_EXPIRED``, ``VALIDATION_ERROR``, ``SCOPE_VIOLATION``).
    """
    raise TransitionNotWired("submit", transition_id="T7", wired_by="WP-2.6")


def _side_effect_submit(task: Task, context: TransitionContext) -> Task | None:
    """T7 side effects — Section 8.2 verbatim: "Store resolution + patch; clear worker".

    Resolution/patch storage is WP-2.6's models; clearing reuses
    ``guards.clear_coder_lease`` so Section 8.3 invariant 1 holds on the
    ``to_be_audited`` row.
    """
    raise TransitionNotWired("submit", transition_id="T7", wired_by="WP-2.6")


# --- T8: self-flagged / scope-violation submit (WP-2.6 wires the row) --------


def _guard_submit_flagged(task: Task, context: TransitionContext) -> None:
    """T8 guard — Section 8.2 verbatim:
    "``requires_human_attention`` true or changed files outside scope".

    The evidence (resolution flags, changed-file list vs
    ``target_scope``) rides ``context.extra``; out-of-scope evidence
    refuses/escalates with the catalog ``SCOPE_VIOLATION`` semantics of
    Section 12.3.
    """
    raise TransitionNotWired("submit_flagged", transition_id="T8", wired_by="WP-2.6")


def _side_effect_submit_flagged(task: Task, context: TransitionContext) -> Task | None:
    """T8 side effects — Section 8.2 verbatim.

    "``review_reason`` = ``self_flagged`` or ``scope_violation``;
    push notification" — the reason pair is :data:`T8_REVIEW_REASONS`
    (Section 8.4, nothing wider); the push rides the dispatcher's
    Section 9.8 ``in_human_review``-entry rule when the row is wired.
    """
    raise TransitionNotWired("submit_flagged", transition_id="T8", wired_by="WP-2.6")


def register() -> None:
    """Register the four stubs on the default registry (loader-called)."""
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T4",
            trigger="claim",
            from_states=frozenset({TaskState.PENDING}),
            to_state=TaskState.IN_PROGRESS,
            actor_types=frozenset({"agent"}),  # Section 8.2 actor C
            guard=_guard_claim,
            side_effect=_side_effect_claim,
            event_type="task.claimed",
            reason_code="claim",
            wired=False,
            stubbed_by="WP-1.6",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T6",
            trigger="voluntary_release",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.PENDING,
            actor_types=frozenset({"agent", "owner"}),  # Section 8.2 actors C, O
            guard=_guard_release,
            side_effect=_side_effect_release,
            event_type="task.released",
            reason_code="voluntary_release",
            wired=False,
            stubbed_by="WP-1.6",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T7",
            trigger="submit",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.TO_BE_AUDITED,
            actor_types=frozenset({"agent"}),  # Section 8.2 actor C
            guard=_guard_submit,
            side_effect=_side_effect_submit,
            event_type="task.transitioned",
            reason_code="submit",
            wired=False,
            stubbed_by="WP-2.6",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T8",
            trigger="submit_flagged",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.IN_HUMAN_REVIEW,
            actor_types=frozenset({"agent", "system"}),  # Section 8.2 actors C, S
            guard=_guard_submit_flagged,
            side_effect=_side_effect_submit_flagged,
            event_type="task.transitioned",
            reason_code="submit_flagged",
            wired=False,
            stubbed_by="WP-2.6",
        )
    )
