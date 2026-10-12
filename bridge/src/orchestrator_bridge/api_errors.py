"""Typed client-side API errors for the bridge (parent plan Section 9.2; MT-2.3-01).

The bridge-internal representation of every way a backend call can fail, with
exactly the Section 9.2 envelope fields preserved verbatim on the typed error:

* ``envelope`` — the backend answered a non-2xx with the standard error
  envelope; ``code``, ``message``, ``retryable``, ``details`` and
  ``correlation_id`` are carried through unchanged (MT-2.3-01 acceptance;
  MT-2.3-04 passes them through translation without rewriting).
* ``malformed_response`` — a body that is not a parseable envelope (bad JSON,
  wrong nesting, missing required field); degrades to a ``SERVER_ERROR``-tagged
  error instead of crashing the caller. The HTTP status still drives the
  retryable guess (5xx/408/429 yes, other 4xx no) because no flag was provided.
* ``transport_failure`` — no HTTP response at all (connection refused, DNS
  failure, timeout): also ``SERVER_ERROR``-tagged and retryable, per Section
  10.10 ("backend unreachable: tool calls fail with a retryable error").

The catalog is closed — ``error-envelope.md`` publishes the 19 Section 9.2
codes and :class:`ErrorCode` mirrors it exactly (the MT-2.3-05 contract test
asserts the enum against the OpenAPI document's ``CodeEnum``). An envelope
carrying an unknown code cannot be emitted as-is (Section 20.4 item 5): the
transport downgrades it to ``SERVER_ERROR`` and preserves the upstream value in
``details["upstream_code"]``, so newer backends stay diagnosable without the
bridge inventing a code.

``retryable`` is the server's flag whenever an envelope was parsed — the
authoritative input for MT-2.3-02's retry loop; the bridge never re-guesses it
for envelope errors (error-envelope.md rule 3: "Retrying a non-retryable
failure is a client bug").
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Final

__all__ = [
    "API_ERROR_KINDS",
    "CANONICAL_ERROR_CODES",
    "ApiError",
    "ErrorCode",
    "ErrorKind",
]


class ErrorCode(StrEnum):
    """The 19 canonical Section 9.2 codes, in the catalog's published order."""

    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FORBIDDEN_PROJECT = "AUTH_FORBIDDEN_PROJECT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_STATE_CONFLICT = "TASK_STATE_CONFLICT"
    TASK_ALREADY_CLAIMED = "TASK_ALREADY_CLAIMED"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    LEASE_NOT_OWNED = "LEASE_NOT_OWNED"
    DEPENDENCY_UNMET = "DEPENDENCY_UNMET"
    CONCURRENCY_LIMIT_REACHED = "CONCURRENCY_LIMIT_REACHED"
    SCOPE_VIOLATION = "SCOPE_VIOLATION"
    ROLE_NOT_PERMITTED = "ROLE_NOT_PERMITTED"
    AUDITOR_SAME_AS_CODER = "AUDITOR_SAME_AS_CODER"
    ATTACHMENT_NOT_READY = "ATTACHMENT_NOT_READY"
    ATTACHMENT_UNSUPPORTED_FORMAT = "ATTACHMENT_UNSUPPORTED_FORMAT"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    RATE_LIMITED = "RATE_LIMITED"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    SERVER_ERROR = "SERVER_ERROR"


#: Published order (error-envelope.md) — drives iteration in tests and reports.
CANONICAL_ERROR_CODES: Final[tuple[ErrorCode, ...]] = tuple(ErrorCode)


class ErrorKind(StrEnum):
    """How the failure was produced (MT-2.3-01's three parsing paths)."""

    ENVELOPE = "envelope"
    MALFORMED_RESPONSE = "malformed_response"
    TRANSPORT_FAILURE = "transport_failure"


API_ERROR_KINDS: Final[tuple[ErrorKind, ...]] = tuple(ErrorKind)


class ApiError(Exception):
    """One typed backend failure: catalog code plus the Section 9.2 fields.

    Raised by :class:`orchestrator_bridge.transport.ApiClient` for every
    non-success outcome (including transport-level failures) and consumed by
    the MT-2.3-02 retry loop (``retryable``) and the MT-2.3-04 translator
    (``code``/``details``/``correlation_id`` passthrough).

    ``str(exc)`` is safe for logs and stderr: it names the code, HTTP status
    (when a response existed) and the backend's human-readable message — no
    token, no request body, no idempotency key (Sections 12.4, 17).
    """

    def __init__(
        self,
        *,
        code: ErrorCode,
        message: str,
        retryable: bool,
        kind: ErrorKind,
        details: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.kind = kind
        self.details = details
        self.correlation_id = correlation_id
        self.status_code = status_code

    def __str__(self) -> str:
        where = "" if self.status_code is None else f" (HTTP {self.status_code})"
        return f"{self.code}{where}: {self.message}"
