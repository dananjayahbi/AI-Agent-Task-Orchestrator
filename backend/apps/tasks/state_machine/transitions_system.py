"""System transitions T5 (lease expired), T9 (retry exhausted) — MT-1.5-03.

The system actor (**S**) owns the two recovery rows of Section 8.2 that
keep agents from wedging tasks; the WP-1.7 lease sweeper will be their
caller (this WP implements and tests the service side only):

* **T5** ``in_progress`` → ``pending`` — guard: ``lease_expires_at`` <
  now; side effects: ``failure_retry_count`` + 1, clear worker, emit
  ``task.lease_expired`` (FR-LEA-04). The emit rides the dispatcher's
  single event hook with T5's registered ``event_type`` — a Section 9.6
  catalog entry, asserted by the tests.
* **T9** ``in_progress`` → ``in_human_review`` — guard:
  ``failure_retry_count`` >= ``max_retries`` (project policy, default 3
  — G-10); side effects: ``review_reason`` = ``retry_exhausted``
  (Section 8.4 canonical member), clear worker, and the Section 9.8
  push — which the dispatcher fires generically for every
  ``in_human_review`` entry (its dedupe key ``(event type, task id,
  state version)`` rides the payload), so WP-5.4 plugs in without T9
  changing (MT-1.5-03 risk note).

Recorded reading (the parent's open decision "T9 worker-field clearing
vs Section 8.3 invariant 1"): the T9 row's Side-effects cell does not
mention clearing the worker, but Section 8.3 invariant 1 says "a task
in any other state has no coder lease" — so T9's side effect **also**
clears the worker fields (same helper as T5, without the failure
increment). Without it, an escalation fired straight from
``in_progress`` (the sweeper's Flow B) would strand a coder lease on an
``in_human_review`` row. Recorded in the WP changelog.

Escalation ordering (T5 first, then T9 on the same sweep) is WP-1.7's
concern (MT-1.7-03); these rows only answer for the pair presented to
them — a task below ``max_retries`` refuses T9 with
``TASK_STATE_CONFLICT`` while T5 still applies, and the boundary tests
pin exactly that (``failure_retry_count == max_retries - 1``).
"""

from __future__ import annotations

from django.utils import timezone

from ..exceptions import TaskStateConflict
from ..models.task import ReviewReason, Task, TaskState
from .guards import clear_coder_lease
from .registry import DEFAULT_REGISTRY, TransitionContext, TransitionSpec


def _guard_lease_expired(task: Task, context: TransitionContext) -> None:
    """T5 guard — Section 8.2 verbatim: ``lease_expires_at`` < now.

    No lease (``None``) or a deadline still in the future refuses with
    the Section 8.2 family code: there is nothing to sweep.
    """
    if task.lease_expires_at is None:
        raise TaskStateConflict(task.pk, reason="holds no lease (T5 guard: lease_expires_at < now)")
    if task.lease_expires_at >= timezone.now():
        raise TaskStateConflict(
            task.pk, reason="lease has not expired (T5 guard: lease_expires_at < now)"
        )


def _side_effect_lease_expired(task: Task, context: TransitionContext) -> Task | None:
    """T5 side effects — Section 8.2 verbatim.

    "``failure_retry_count``+1; clear worker; emit ``task.lease_expired``"
    — the emit is the dispatcher's event hook with the row's registered
    event type (Section 9.6 catalog); clearing also removes the lease
    timestamps so Section 8.3 invariant 1 holds on the returned
    ``pending`` row.
    """
    task.failure_retry_count += 1
    clear_coder_lease(task)
    return None


def _guard_retry_exhausted(task: Task, context: TransitionContext) -> None:
    """T9 guard — Section 8.2 verbatim: ``failure_retry_count`` >= max_retries.

    ``max_retries`` is the project policy value (Section 7.2, default 3
    — G-10). Below the limit refuses with ``TASK_STATE_CONFLICT``: the
    sweeper's escalation trigger has not met its condition yet.
    """
    limit = task.project.agent_policy.max_retries
    if task.failure_retry_count < limit:
        raise TaskStateConflict(
            task.pk,
            reason=(
                f"has {task.failure_retry_count} failures below max_retries "
                f"{limit} (T9 guard: failure_retry_count >= max_retries)"
            ),
        )


def _side_effect_retry_exhausted(task: Task, context: TransitionContext) -> Task | None:
    """T9 side effects — Section 8.2 verbatim plus the invariant 1 clearing.

    Sets ``review_reason`` to the canonical ``retry_exhausted`` member
    (Section 8.4) and clears the worker (see the module docstring's
    recorded reading). The push notification fires from the dispatcher's
    Section 9.8 rule when the transition lands ``in_human_review``.
    """
    task.review_reason = ReviewReason.RETRY_EXHAUSTED
    clear_coder_lease(task)
    return None


def register() -> None:
    """Register T5 and T9 on the default registry (loader-called)."""
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T5",
            trigger="lease_expired",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.PENDING,
            actor_types=frozenset({"system"}),
            guard=_guard_lease_expired,
            side_effect=_side_effect_lease_expired,
            event_type="task.lease_expired",  # Section 9.6 catalog
            reason_code="lease_expired",
        )
    )
    DEFAULT_REGISTRY.register(
        TransitionSpec(
            transition_id="T9",
            trigger="retry_exhausted",
            from_states=frozenset({TaskState.IN_PROGRESS}),
            to_state=TaskState.IN_HUMAN_REVIEW,
            actor_types=frozenset({"system"}),
            guard=_guard_retry_exhausted,
            side_effect=_side_effect_retry_exhausted,
            event_type="task.transitioned",
            reason_code="retry_exhausted",
        )
    )
