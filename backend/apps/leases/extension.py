"""Lease extension with the hard total-age cap (Section 8.6; FR-LEA-03).

Section 8.6 fixes the formula: "each valid checkpoint sets
``lease_expires_at`` = min(now + duration, ``lease_acquired_at`` +
``lease_max_total_minutes``). After the hard cap, the owner must submit
or release; the sweeper then reclaims."

* ``duration`` and the cap come from Project Policy (defaults 45/240,
  Section 7.2) — never hardcoded (Section 20.5 traceability).
* The result carries ``capped`` so callers (the future checkpoint
  endpoint's response, the bridge's ``next_checkpoint_due`` hint) can
  surface "submit or release" guidance (MT-1.6-03 acceptance).
* Ownership goes through the **one** fencing helper: a stale generation
  or a dead lease answers ``LEASE_EXPIRED`` (no resurrection — Section
  8.6 "Expire"), a foreign session answers ``LEASE_NOT_OWNED``.
* The row is locked for the read-modify-write, so a racing extension
  cannot lose an update; ``version`` increments because Section 7.2
  bumps it on *every* change (recorded reading — the lease columns are
  ordinary row state, not exempt).

WP-1.8's checkpoint endpoint (MT-1.8-03) is the production caller; the
service and its cap tests land here because the formula is WP-1.6's
MT-1.6-03 scope. ``lease_extension_mode`` (OQ-04) gates *who may extend*
at the checkpoint layer — the default ``checkpoint_only`` means only
valid-owner requests, which is exactly this function's contract;
``checkpoint_and_liveness`` adds a different *caller* (the bridge
pings), not a different formula.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.exceptions import AuthForbiddenProject
from apps.tasks.exceptions import TaskNotFound
from apps.tasks.models import Task
from apps.tasks.services.ids import ensure_valid_task_id

from .exceptions import LeaseExpired
from .fencing import require_current_lease


@dataclass(frozen=True)
class LeaseExtension:
    """One extension outcome (MT-1.6-03: cap-reached must be observable)."""

    task_id: str
    lease_expires_at: datetime
    capped: bool  # True when the hard cap clamped the computed expiry


def extend_lease(
    *,
    task_id: str,
    session_id: str,
    lease_generation: int,
    caller_project_id: str | None = None,
) -> LeaseExtension:
    """Extend the caller's live lease by the policy duration, capped.

    Refuses with ``LEASE_EXPIRED`` / ``LEASE_NOT_OWNED`` (fencing) or
    ``TASK_NOT_FOUND`` (unknown id); a foreign-project caller answers
    ``AUTH_FORBIDDEN_PROJECT`` before anything is written.
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
        require_current_lease(task, session_id=session_id, lease_generation=lease_generation)

        policy = task.project.agent_policy
        now = timezone.now()
        if task.lease_acquired_at is None:  # pragma: no cover - Section 7.4 rule 2
            # A live lease (checked above) always carries its acquire time;
            # a null here would be a half-written row, refused not computed.
            raise LeaseExpired(task.pk, reason="lease record has no acquire time")
        cap = task.lease_acquired_at + timedelta(minutes=policy.lease_max_total_minutes)
        target = now + timedelta(minutes=policy.lease_duration_minutes)
        new_expiry = min(target, cap)

        task.lease_expires_at = new_expiry
        task.version += 1  # Section 7.2: version increments on every change
        task.save(update_fields=["lease_expires_at", "version", "updated_at"])
        return LeaseExtension(
            task_id=task.pk,
            lease_expires_at=new_expiry,
            capped=target > cap,
        )
