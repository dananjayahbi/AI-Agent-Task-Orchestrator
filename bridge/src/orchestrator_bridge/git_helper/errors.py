"""Structured failures for the local Git helper (parent plan Sections 9.2,
10.5, 10.8; MT-2.10-01).

Every deliberate Git-helper failure is a :class:`GitHelperError`: a catalog
code (error-envelope.md rule 4 — the closed 19-code Section 9.2 catalog, never
extended here), a human-readable message and the Section 10.5 *hint* /
*next action* pair. The shape mirrors the bridge's other structured failures
(:mod:`tools.errors`) so a future tool layer over the helper translates
without a second vocabulary; this module invents no fields and no codes
(Section 20.4 item 5).

The common cases, by code:

* ``VALIDATION_ERROR`` — bad input the caller can fix (a task id that does
  not parse, a branch name that is not a valid ref, a path that is not a Git
  repository, a dirty working tree where cleanliness is required, a missing
  or unrelated ref, an operation the capability guard forbids);
* ``SERVER_ERROR`` — Git itself failed unexpectedly on an otherwise valid
  invocation (a timeout, an unreadable repository).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..api_errors import ErrorCode

__all__ = ["GitHelperError", "failure_payload"]


class GitHelperError(Exception):
    """One deliberate, catalog-coded Git-helper failure.

    ``str(exc)`` is the code plus message — safe for logs: the helper never
    puts token material or environment values into a failure (Section 12.4).
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        hint: str,
        next_action: str,
        retryable: bool = False,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.next_action = next_action
        self.retryable = retryable
        self.details = dict(details) if details is not None else None

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


def failure_payload(error: GitHelperError, *, correlation_id: str | None = None) -> dict[str, Any]:
    """The wire-shaped view of one failure: envelope fields plus hint/action.

    Mirrors :func:`tools.errors.payload_text`'s JSON body (the Section 9.2
    fields with ``hint``/``next_action`` riding alongside, per Section 10.5)
    so tool-layer translation stays a structural copy, not a redesign.
    """
    payload: dict[str, Any] = {
        "code": str(error.code),
        "message": error.message,
        "hint": error.hint,
        "next_action": error.next_action,
        "retryable": error.retryable,
        "details": dict(error.details) if error.details is not None else None,
        "correlation_id": correlation_id,
    }
    return payload
