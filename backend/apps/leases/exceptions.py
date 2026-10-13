"""Leases-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

Five refusals the claim/release/extension services surface; each names a
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
    ROLE_NOT_PERMITTED,
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


class RoleNotAllowed(APIException):
    """The caller's *declared role* may not act on this state (Section 12.2).

    WP-3.3 (MT-3.3-01): ``POST /tasks/{id}/claim`` carries the Section
    10.5 ``role`` input, and the Section 12.2 matrix is unambiguous —
    claim ``pending`` is coder-only, claim ``to_be_audited`` is
    auditor-only. A request whose ``role`` matches the *other* claimable
    state is a **role** refusal (403 ``ROLE_NOT_PERMITTED``), distinct
    from a state the role may claim from at all (the registry's 409
    ``TASK_STATE_CONFLICT``). The token's scopes answer first (the
    permission classes); this is the request-intent half behind them.
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_code = ROLE_NOT_PERMITTED
    default_detail = "This role may not claim a task in that state."

    def __init__(self, task_id: str, *, role: str, state: str) -> None:
        """Name the role/state pair the matrix refused (no secrets).

        The stored attribute is ``task_state`` (never spelled like the
        Task column): the MT-1.5-06 direct-write scanner reads an
        assignment to ``state`` as a Task state write, and this is an
        exception field.
        """
        super().__init__(
            f"Task {task_id} is {state}: the {role} role may not claim it "
            "(Section 12.2 claim rows)."
        )
        self.task_id = task_id
        self.role = role
        self.task_state = state
