"""Tasks-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

The envelope handler (``apps/core/exceptions.py``) passes any DRF
``APIException`` whose ``default_code`` is already canonical straight
through, so these classes never invent a code — they name one that exists
in the closed 19-code catalog and choose the HTTP status the OpenAPI
contract documents for that endpoint.

Status decisions (recorded in the WP changelog):

* ``TASK_NOT_FOUND`` → **404**: the resource-owning status the core
  handler's docstring anticipates ("Resource-owning work packages ...
  keep their own status"); the generic ``NotFound`` → 400 mapping stays
  for resources that have no catalog code of their own (projects).
* ``VERSION_CONFLICT`` → **409**: "a stale version returns a conflict"
  (Section 8.2 rules; FR-TSK-06) — the same conflict class the plan
  assigns ``TASK_STATE_CONFLICT`` (HTTP 409 explicitly).
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import (
    DEPENDENCY_UNMET,
    ROLE_NOT_PERMITTED,
    SERVER_ERROR,
    TASK_NOT_FOUND,
    TASK_STATE_CONFLICT,
    VERSION_CONFLICT,
)


class TaskNotFound(APIException):
    """Unknown (but well-formed) ``{id}`` on a task-addressed route."""

    status_code = status.HTTP_404_NOT_FOUND
    default_code = TASK_NOT_FOUND
    default_detail = "Task does not exist."


class VersionConflict(APIException):
    """The PATCH carried a stale ``version`` (FR-TSK-06; MT-1.4-03).

    The envelope's ``details`` carry the task id and both versions so the
    UI can show *what* moved without parsing the message (messages stay
    human-only — error-envelope.md rule 2).
    """

    status_code = status.HTTP_409_CONFLICT
    default_code = VERSION_CONFLICT
    default_detail = "The task changed since it was read; refresh and retry."

    def __init__(
        self,
        task_id: str,
        *,
        expected: int,
        actual: int,
        detail: str | None = None,
    ) -> None:
        """Attach the conflict context (still a catalog-codable exception)."""
        super().__init__(
            detail
            or (
                f"Task {task_id} is at version {actual}; the request carried "
                f"stale version {expected}."
            )
        )
        self.task_id = task_id
        self.expected = expected
        self.actual = actual


class TaskStateConflict(APIException):
    """A write refused because of the row's lifecycle condition (FR-TSK-08).

    MT-1.4-06's recorded mapping (Section 20.4 item 5): **both** the
    read-only ``completed`` refusal (Section 8.2 T17 side effect;
    Section 7.4 rule 3) and the archived-task refusal answer
    ``TASK_STATE_CONFLICT`` — the catalog has no ``TASK_ARCHIVED`` /
    ``READ_ONLY`` code and a 20th is forbidden, and ``VALIDATION_ERROR``
    would blame a payload that is perfectly valid: the *resource*
    refuses. ``TASK_STATE_CONFLICT`` is the Section 8.2 family ("not
    allowed in this state", explicitly HTTP 409).

    Boundary (MT-1.4-06 risk note): this is the **update endpoint's**
    write refusal. WP-1.5 owns the transition registry's guard framework
    — two competing state checks must not grow here; the transition
    service guards its own writes.
    """

    status_code = status.HTTP_409_CONFLICT
    default_code = TASK_STATE_CONFLICT
    default_detail = "This task no longer accepts edits."

    def __init__(self, task_id: str, *, reason: str, detail: str | None = None) -> None:
        """Attach *which* lifecycle condition refused the write."""
        super().__init__(detail or f"Task {task_id} {reason}.")
        self.task_id = task_id
        self.reason = reason


class DependencyUnmet(APIException):
    """A guard refused because dependencies are not ``completed`` yet.

    The catalog code Section 9.2 reserves for exactly this condition —
    MT-1.5-02's T2 dependency guard surfaces it (its acceptance criteria
    name ``DEPENDENCY_UNMET``); the offer/claim paths of WP-1.6 reuse
    this class with the same reading ``services.dependencies`` records
    (``all_dependencies_completed`` is the predicate, this is the
    refusal).

    Status decision (recorded in the WP changelog): **409** — a
    resource-condition refusal in the ``TASK_STATE_CONFLICT`` family
    (the payload is valid; the *task's* dependency state refuses), not
    400 ``VALIDATION_ERROR`` (nothing about the request is malformed).
    """

    status_code = status.HTTP_409_CONFLICT
    default_code = DEPENDENCY_UNMET
    default_detail = "Dependencies of this task are not completed yet."

    def __init__(self, task_id: str, *, unmet: str = "", detail: str | None = None) -> None:
        """Name the task (and the unmet dependency ids, when known)."""
        suffix = f": {unmet}" if unmet else ""
        message = detail or f"Task {task_id} waits on dependencies not done{suffix}."
        super().__init__(message)
        self.task_id = task_id
        self.unmet = unmet


class TransitionActorForbidden(APIException):
    """The dispatcher's actor rejection (Section 8.2 Actor column).

    Resolution order is state-then-actor (MT-1.5-01): an illegal pair
    already answered ``TASK_STATE_CONFLICT`` above, so reaching this
    class means the table row exists but its Actor column excludes the
    caller — e.g. an agent dispatching T2 (publish, actor O).
    ``ROLE_NOT_PERMITTED`` is the catalog's wrong-role code and the
    same 403 the authorization matrix produces for API-level role
    refusals (Section 12.2).
    """

    status_code = status.HTTP_403_FORBIDDEN
    default_code = ROLE_NOT_PERMITTED
    default_detail = "This actor may not dispatch this transition."

    def __init__(
        self,
        task_id: str,
        *,
        trigger: str,
        actor_type: str,
        allowed: str,
        detail: str | None = None,
    ) -> None:
        """Attach who was refused, which row, and who may dispatch it."""
        super().__init__(
            detail
            or (
                f"Actor {actor_type!r} may not fire '{trigger}' on {task_id}; "
                f"the transition table allows: {allowed}."
            )
        )
        self.task_id = task_id
        self.trigger = trigger
        self.actor_type = actor_type


class TransitionNotWired(APIException):
    """A registered stub (T4/T6/T7/T8) was dispatched before its WP wired it.

    Deterministic by construction (MT-1.5-04): the dispatcher refuses a
    ``wired=False`` row right after the actor check, before guards,
    side effects, ``version``, history or the event hook — the task is
    untouched. The catalog has no ``NOT_IMPLEMENTED`` code and a 20th is
    forbidden (Section 20.4 item 5), so this is the one wire code the
    catalog does hold for a server-side integration gap:
    **500 ``SERVER_ERROR``** — the *client* asked for a legal transition
    the server has not wired yet, which is not a client error and not a
    state conflict. Wiring WPs replace the stub through
    ``registry.register(..., replace=True)`` and this class stops firing
    without touching the dispatcher.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_code = SERVER_ERROR
    default_detail = "This transition is registered as a stub and is not wired yet."

    def __init__(
        self,
        trigger: str,
        *,
        transition_id: str,
        wired_by: str,
        detail: str | None = None,
    ) -> None:
        """Name the stub row and the WP that will wire it."""
        super().__init__(
            detail
            or (
                f"Transition {transition_id} ('{trigger}') is a stub: "
                f"{wired_by} wires it through the registry extension point."
            )
        )
        self.trigger = trigger
        self.transition_id = transition_id
        self.wired_by = wired_by
