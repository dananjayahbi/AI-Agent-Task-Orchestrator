"""Lease sweeper: Flow B's beat step (Sections 6.5, 8.2 T5/T9, 8.6, 9.9).

FR-LEA-04, FR-LEA-05, G-10 (MT-1.7-02 + MT-1.7-03). Every 60 seconds the beat
job selects ``in_progress`` rows whose ``lease_expires_at`` has passed under
``FOR UPDATE SKIP LOCKED`` and dispatches the registry's system transition
for each row, inside a transaction, repeating until no candidates remain:

* T5 (``lease_expired``) — back to ``pending`` with ``failure_retry_count`` + 1
  and the worker lease cleared, while the project's retry budget lasts.
* T9 (``retry_exhausted``) — to ``in_human_review`` with ``review_reason``
  ``retry_exhausted`` once ``failure_retry_count`` already meets the project
  policy's ``max_retries`` (MT-1.7-03; the increment that *reaches* the budget
  is the preceding T5, "the sweep following the increment" escalates).

Recorded reading (Section 6.5 vs the frozen registry): T9's Section 8.2
from-state is ``in_progress``, so a sweep dispatches exactly one transition
per expired row — T9 *instead of* T5 when the budget is already exhausted,
never T5 then T9 for the same row (which the registry would refuse with
``TASK_STATE_CONFLICT``). The task therefore cannot bounce
``pending`` ↔ ``in_progress`` forever (G-10): every expiry either consumes
retry budget or escalates.

State is never written directly — every change goes through
``dispatch_transition`` (Section 9.1), so history rows, events and the push
trigger remain the registry's job. Selection and dispatch hold the row lock,
which makes double sweeps (two beat instances, FR-LEA-05) safe: the second
sweeper skips rows the first has locked and finds them out of ``in_progress``
after commit.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.core.correlation import (
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from apps.tasks.exceptions import TaskStateConflict
from apps.tasks.models import Task, TaskState
from apps.tasks.state_machine.dispatcher import dispatch_transition

logger = logging.getLogger(__name__)

# actor_ref for every transition this job dispatches (Section 9.6 envelope
# example uses exactly this spelling for the sweeper).
SWEEPER_ACTOR_REF = "lease-sweeper"

# Documented default (MT-1.7-02 risk note): bounds how many rows one sweep
# transaction locks and dispatches. The plan fixes the interval (60 s) but
# not the batch size; the next beat run picks up any remainder.
DEFAULT_BATCH_SIZE = 100


@dataclass
class SweepReport:
    """One sweep run's outcome (structured for logs and the Celery result)."""

    reclaimed: int = 0  # T5 dispatches
    escalated: int = 0  # T9 dispatches
    skipped: int = 0  # dispatch conflicts (defensive; expected 0)
    correlation_id: str = ""

    @property
    def processed(self) -> int:
        return self.reclaimed + self.escalated + self.skipped


def sweep_expired_leases(*, batch_size: int = DEFAULT_BATCH_SIZE) -> SweepReport:
    """Reclaim every expired lease; idempotent and safe under concurrency.

    Selects expired ``in_progress`` rows under ``FOR UPDATE SKIP LOCKED``,
    dispatches T5/T9 per row inside the batch transaction, and repeats until
    a selection round comes back empty. A run of nothing to do is a clean
    no-op. One correlation id scopes the whole run (WP-0.5-03): every log
    line and every event written by the dispatched transitions carries it.
    """
    if batch_size < 1:
        raise ValueError(f"batch_size must be >= 1 (got {batch_size})")
    token = set_correlation_id(new_correlation_id())
    report = SweepReport(correlation_id=get_correlation_id())
    try:
        _sweep_loop(batch_size=batch_size, report=report)
    finally:
        reset_correlation_id(token)
    logger.info(
        "lease sweep complete",
        extra={
            "sweeper_reclaimed": report.reclaimed,
            "sweeper_escalated": report.escalated,
            "sweeper_skipped": report.skipped,
        },
    )
    return report


def _sweep_loop(*, batch_size: int, report: SweepReport) -> None:
    # `seen` guarantees termination even if a row somehow survives its own
    # dispatch (e.g. a caught conflict): it is excluded from later rounds.
    seen: set[str] = set()
    while True:
        with transaction.atomic():
            batch = list(
                Task.objects.select_for_update(skip_locked=True)
                .filter(state=TaskState.IN_PROGRESS, lease_expires_at__lt=timezone.now())
                .exclude(pk__in=seen)
                .order_by("lease_expires_at")
                .values_list("pk", flat=True)[:batch_size]
            )
            if not batch:
                # Empty selection: the atomic block commits an empty read and
                # the loop ends — a sweep of nothing is a clean no-op.
                return
            for task_id in batch:
                seen.add(task_id)
                _dispatch_for(task_id, report)


def _dispatch_for(task_id: str, report: SweepReport) -> None:
    task = Task.objects.select_for_update().select_related("project__agent_policy").get(pk=task_id)
    retry_budget_exhausted = task.failure_retry_count >= task.project.agent_policy.max_retries
    trigger = "retry_exhausted" if retry_budget_exhausted else "lease_expired"
    try:
        dispatch_transition(
            task_id=str(task.pk),
            trigger=trigger,
            actor_type="system",
            actor_ref=SWEEPER_ACTOR_REF,
        )
    except TaskStateConflict:
        # The row stopped being dispatchable between selection and dispatch —
        # impossible while the lock is held (the guard re-reads the same
        # locked values), but a defensive skip keeps one bad row from failing
        # the whole run; `seen` excludes it from later rounds.
        report.skipped += 1
        logger.warning(
            "lease sweeper skipped undispatchable task",
            extra={"task_id": str(task.pk), "sweeper_trigger": trigger},
        )
        return
    if retry_budget_exhausted:
        report.escalated += 1
    else:
        report.reclaimed += 1
    logger.info(
        "lease sweeper dispatched transition",
        extra={
            "task_id": str(task.pk),
            "sweeper_trigger": trigger,
            "lease_generation": task.lease_generation,
            "failure_retry_count": task.failure_retry_count,
            "worker_agent_id": task.worker_agent_id,
        },
    )
