"""Voluntary release — T6 (Section 8.2; FR-LEA-06; MT-1.6-04).

FR-LEA-06 verbatim: "Voluntary release by the owner of the lease returns
the task to ``pending`` without a failure increment." The distinction
that keeps honest releases from consuming the project's ``max_retries``
budget (G-10): the sweeper's T5 increments ``failure_retry_count``, T6
never does.

* Ownership — agent callers prove the fencing pair
  (``session_id`` + ``lease_generation``, ADR-012; presence enforced by
  the API serializer and re-checked here — an omitted generation would
  silently defeat fencing, MT-1.6-05). The T6 guard runs the single
  fencing helper: a foreign session on a live lease answers
  ``LEASE_NOT_OWNED``; a dead or superseded lease answers
  ``LEASE_EXPIRED`` (reclamation itself stays T5's, Section 8.6).
* Late-owner gap — once the sweeper cleared the row (T5 → ``pending``)
  the guard can no longer see who held it, so the service pre-empts the
  dispatch for that one shape: an agent whose *current* generation matches
  a now-absent lease answers ``LEASE_EXPIRED`` (the WP-1.6 acceptance's
  "late owner calls return ``LEASE_EXPIRED`` after reclaim") instead of
  the state family's conflict; every other from-state keeps
  ``TASK_STATE_CONFLICT``.
* Owner override — Section 8.2 T6's "(or Owner override)": the endpoint
  accepts an owner session and dispatches with ``actor_type="owner"``,
  which the guard admits without the fencing pair; the Transition row's
  ``actor_type``/``actor_ref`` keep it auditable (Section 12.5).
* One transaction through the dispatcher: ``in_progress`` → ``pending``,
  worker fields cleared, exactly one T6 Transition row and one
  ``task.released`` event hook (Section 20.4 item 6);
  ``attempt_number`` and ``failure_retry_count`` untouched.
"""

from __future__ import annotations

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.tasks.exceptions import TaskNotFound
from apps.tasks.models import Task, TaskState
from apps.tasks.services.ids import ensure_valid_task_id
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .exceptions import LeaseExpired
from .wiring import ensure_wired, release_extra


def release_task(
    *,
    task_id: str,
    session_id: str | None,
    lease_generation: int | None,
    actor_type: str,
    actor_ref: str,
    owner_override: bool = False,
    reason: str = "",
    expected_version: int | None = None,
    caller_project_id: str | None = None,
) -> Task:
    """Release *task_id* back to ``pending`` (T6); return the updated row."""
    ensure_valid_task_id(task_id)
    if not owner_override and (session_id is None or lease_generation is None):
        raise ValidationError(
            {
                "session_id": "Agent releases must carry the session id and the lease "
                "generation (ADR-012 fencing carrier)."
            }
        )
    ensure_wired()

    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if actor_type == "agent":
            if caller_project_id is not None and task.project_id != caller_project_id:
                raise AuthForbiddenProject(
                    f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
                )
            if (
                task.state == TaskState.PENDING
                and task.lease_generation >= 1
                and lease_generation == task.lease_generation
            ):
                # The row already left in_progress: the lease this caller
                # carries was the latest and is gone (T5 swept it, or an
                # earlier T6 cleared it) — the late-owner refusal of
                # Section 8.6, not a state conflict.
                raise LeaseExpired(task.pk, reason="lease is no longer held")
        return dispatch_transition(
            task_id=task.pk,
            trigger="voluntary_release",
            actor_type=actor_type,
            actor_ref=actor_ref,
            expected_version=expected_version,
            note=reason,
            extra=release_extra(
                session_id=session_id,
                lease_generation=lease_generation,
                owner_override=owner_override,
            ),
        )
