"""The single lease-fencing check (Section 8.6; ADR-012; MT-1.6-05).

One implementation every mutating lease consumer shares — release's T6
guard, the extension function, and the future WP-1.8 checkpoint /
WP-2.6 submission paths — so fencing can never diverge per endpoint
(MT-1.6-05 acceptance: "no divergent per-endpoint fencing").

Section 8.6: "every claim increments an internal lease generation;
mutating calls carry the generation so a slow former owner can never
overwrite state after the task is reclaimed." The check answers only the
two catalog codes that describe lease ownership:

1. the caller's generation must equal the task's current one — a stale
   value (the task was reclaimed and re-claimed) answers
   ``LEASE_EXPIRED``;
2. the task must still hold a live lease — dead/swept/superseded leases
   answer ``LEASE_EXPIRED`` (Section 8.6: late checkpoints must not
   resurrect; the WP-1.6 acceptance's "late owner calls return
   ``LEASE_EXPIRED`` after reclaim");
3. only then does the session identity matter — a different session on a
   live lease answers ``LEASE_NOT_OWNED``.

Order is deliberate and tested: the late owner of a swept lease gets
``LEASE_EXPIRED`` (its fence is the *current* generation but the lease
is dead), never ``LEASE_NOT_OWNED``, matching the WP-1.6 acceptance
wording exactly.
"""

from __future__ import annotations

from django.utils import timezone

from apps.tasks.models import Task

from .exceptions import LeaseExpired, LeaseNotOwned


def require_current_lease(
    task: Task,
    *,
    session_id: str | None,
    lease_generation: int | None,
) -> None:
    """Refuse unless *session_id*+*lease_generation* own the live lease.

    Raises ``LEASE_EXPIRED`` (stale or dead lease) or ``LEASE_NOT_OWNED``
    (someone else's live lease); returns ``None`` when the caller owns an
    unexpired lease. Callers run inside their claim/lock transaction so
    the verdict is stable for the write that follows (Section 9.3 step 4
    discipline).
    """
    if session_id is None or lease_generation is None:
        # Agent mutations must carry both (ADR-012); the API boundary
        # answers VALIDATION_ERROR for a missing field before dispatch —
        # reaching here means a non-API caller skipped the boundary.
        raise LeaseNotOwned(task.pk, reason="missing session id or lease generation")
    if lease_generation != task.lease_generation:
        raise LeaseExpired(
            task.pk,
            reason=(
                f"fencing generation {lease_generation} is stale (current {task.lease_generation})"
            ),
        )
    if (
        task.worker_session_id is None
        or task.lease_expires_at is None
        or task.lease_expires_at <= timezone.now()
    ):
        raise LeaseExpired(task.pk, reason="lease is no longer held")
    if task.worker_session_id != session_id:
        raise LeaseNotOwned(task.pk, reason="session mismatch")
