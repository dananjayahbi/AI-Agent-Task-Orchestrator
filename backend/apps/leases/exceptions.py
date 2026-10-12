"""Leases-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

Four refusals the claim/release/extension services surface; each names a
code that already exists in the closed 19-code catalog — this module
never invents one. HTTP status decisions (recorded in the WP changelog,
same practice as WP-1.4/WP-1.5):

* ``TASK_ALREADY_CLAIMED`` → **409**: another worker holds the row — a
  resource-condition conflict (the Section 9.2 envelope example's code),
  not a client mistake and not retryable by the same attempt.
* ``CONCURRENCY_LIMIT_REACHED`` → **409**: the project's
  ``max_concurrent_tasks`` refuses this claim right now (T4 guard,
  Section 9.3 step 4) — a state refusal in the ``TASK_STATE_CONFLICT``
  family, distinct code because the plan prints it separately.
* ``LEASE_EXPIRED`` → **409**: the lease is dead or superseded
  (Section 8.6: late calls must not resurrect it) — conflicting with the
  row's current lease state.
* ``LEASE_NOT_OWNED`` → **403**: the caller is not the lease holder —
  an ownership refusal, the same status family as the other 403
  authorization codes (``ROLE_NOT_PERMITTED``,
  ``AUTH_FORBIDDEN_PROJECT``).
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import (
    CONCURRENCY_LIMIT_REACHED,
    LEASE_EXPIRED,
    LEASE_NOT_OWNED,
    TASK_ALREADY_CLAIMED,
)


class TaskAlreadyClaimed(APIException):
    """Another worker holds the task (Section 9.3 step 3 follow-up read)."""

    status_code = status.HTTP_409_CONFLICT
    default_code = TASK_ALREADY_CLAIMED
    default_detail = "Task is held by another worker."

    def __init__(self, task_id: str, *, holder: str | None = None) -> None:
        """Name the task (and the current holder's label when known)."""
        suffix = f" (held by {holder})" if holder else ""
        super().__init__(f"Task {task_id} is held by another worker{suffix}.")
        self.task_id = task_id


class ConcurrencyLimitReached(APIException):
    """T4 guard refusal: ``max_concurrent_tasks`` reached (FR-LEA-08)."""

    status_code = status.HTTP_409_CONFLICT
    default_code = CONCURRENCY_LIMIT_REACHED
    default_detail = "Project concurrency limit reached."

    def __init__(self, task_id: str, *, limit: int) -> None:
        """Attach the project's limit so the caller knows the budget."""
        super().__init__(
            f"Task {task_id} cannot be claimed: the project already runs "
            f"{limit} concurrent task(s) (max_concurrent_tasks)."
        )
        self.task_id = task_id
        self.limit = limit


class LeaseExpired(APIException):
    """The lease is dead, expired, or superseded by a newer generation."""

    status_code = status.HTTP_409_CONFLICT
    default_code = LEASE_EXPIRED
    default_detail = "Lease expired; stop and re-claim."

    def __init__(self, task_id: str, *, reason: str) -> None:
        """Attach *why* the lease is dead (expiry, sweep, or stale fence)."""
        super().__init__(f"Task {task_id} lease expired: {reason}.")
        self.task_id = task_id
        self.reason = reason


class LeaseNotOwned(APIException):
    """The caller does not hold this task's lease (session mismatch)."""

    status_code = status.HTTP_403_FORBIDDEN
    default_code = LEASE_NOT_OWNED
    default_detail = "Lease is held by a different session."

    def __init__(self, task_id: str, *, reason: str = "session mismatch") -> None:
        """Attach the ownership refusal reason (still catalog-codable)."""
        super().__init__(f"Task {task_id} lease not owned: {reason}.")
        self.task_id = task_id
        self.reason = reason
