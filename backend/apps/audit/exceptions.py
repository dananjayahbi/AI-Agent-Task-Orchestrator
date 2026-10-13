"""Audit-domain exceptions carrying Section 9.2 catalog codes (20.4 item 5).

One refusal today; this module never invents a code:

* ``AUDITOR_SAME_AS_CODER`` → **409**: the G-20 / Section 10.5 claim
  error when the claiming auditor's session or agent label matches the
  current attempt's coder (Section 8.3 invariant 3; Section 12.1
  self-approval mitigation). It sits in the claim conflict family with
  ``TASK_ALREADY_CLAIMED`` — a refusal about *this task's audit state*
  that the same claim request cannot retry its way past (409, not the
  403 role family: the caller's role may be perfectly valid, the
  *independence* condition is what fails). The authorization-matrix
  probe's ``ok=(200, 409)`` for the auditor claim cell records the same
  family choice.
"""

from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from apps.core.errors import AUDITOR_SAME_AS_CODER


class AuditorSameAsCoder(APIException):
    """G-20: the auditor is not independent of the coder of this attempt."""

    status_code = status.HTTP_409_CONFLICT
    default_code = AUDITOR_SAME_AS_CODER
    default_detail = "The auditor must differ from the coder of this attempt."

    def __init__(self, task_id: str, *, reason: str) -> None:
        """Attach *why* independence failed (session, label, or no record)."""
        super().__init__(f"Task {task_id} cannot be audited by this session: {reason}.")
        self.task_id = task_id
        self.reason = reason


__all__ = ["AuditorSameAsCoder"]
