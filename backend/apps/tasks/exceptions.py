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

from apps.core.errors import TASK_NOT_FOUND, TASK_STATE_CONFLICT, VERSION_CONFLICT


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
