"""Canonical error envelope and code catalog (Section 9.2; error-envelope.md).

Single source for the wire contract: the five envelope fields, the closed
19-code catalog, and the payload builder shared by every producer of a non-2xx
response. Section 9.2 of the parent plan stays authoritative; this module must
never add, drop or rename a code (Section 20.4, item 5).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from .scrub import scrub_mapping, scrub_text

# --- The canonical catalog (Section 9.2), in plan order ---------------------
AUTH_REQUIRED: Final = "AUTH_REQUIRED"
AUTH_FORBIDDEN_PROJECT: Final = "AUTH_FORBIDDEN_PROJECT"
VALIDATION_ERROR: Final = "VALIDATION_ERROR"
TASK_NOT_FOUND: Final = "TASK_NOT_FOUND"
TASK_STATE_CONFLICT: Final = "TASK_STATE_CONFLICT"
TASK_ALREADY_CLAIMED: Final = "TASK_ALREADY_CLAIMED"
LEASE_EXPIRED: Final = "LEASE_EXPIRED"
LEASE_NOT_OWNED: Final = "LEASE_NOT_OWNED"
DEPENDENCY_UNMET: Final = "DEPENDENCY_UNMET"
CONCURRENCY_LIMIT_REACHED: Final = "CONCURRENCY_LIMIT_REACHED"
SCOPE_VIOLATION: Final = "SCOPE_VIOLATION"
ROLE_NOT_PERMITTED: Final = "ROLE_NOT_PERMITTED"
AUDITOR_SAME_AS_CODER: Final = "AUDITOR_SAME_AS_CODER"
ATTACHMENT_NOT_READY: Final = "ATTACHMENT_NOT_READY"
ATTACHMENT_UNSUPPORTED_FORMAT: Final = "ATTACHMENT_UNSUPPORTED_FORMAT"
POLICY_VIOLATION: Final = "POLICY_VIOLATION"
RATE_LIMITED: Final = "RATE_LIMITED"
VERSION_CONFLICT: Final = "VERSION_CONFLICT"
SERVER_ERROR: Final = "SERVER_ERROR"

CANONICAL_ERROR_CODES: Final[tuple[str, ...]] = (
    AUTH_REQUIRED,
    AUTH_FORBIDDEN_PROJECT,
    VALIDATION_ERROR,
    TASK_NOT_FOUND,
    TASK_STATE_CONFLICT,
    TASK_ALREADY_CLAIMED,
    LEASE_EXPIRED,
    LEASE_NOT_OWNED,
    DEPENDENCY_UNMET,
    CONCURRENCY_LIMIT_REACHED,
    SCOPE_VIOLATION,
    ROLE_NOT_PERMITTED,
    AUDITOR_SAME_AS_CODER,
    ATTACHMENT_NOT_READY,
    ATTACHMENT_UNSUPPORTED_FORMAT,
    POLICY_VIOLATION,
    RATE_LIMITED,
    VERSION_CONFLICT,
    SERVER_ERROR,
)

_CANONICAL_CODE_SET: Final[frozenset[str]] = frozenset(CANONICAL_ERROR_CODES)


def is_canonical_code(code: str) -> bool:
    """Whether *code* exists in the closed Section 9.2 catalog."""
    return code in _CANONICAL_CODE_SET


def build_error_envelope(
    *,
    code: str,
    message: str,
    retryable: bool,
    details: Mapping[str, object] | None = None,
    correlation_id: str = "",
) -> dict[str, object]:
    """Build the standard envelope (Section 9.2) — exactly five fields.

    ``message`` and ``details`` pass through scrubbing (Sections 17, 12.4) so
    an echoing error path can never leak a token; ``code`` must come from the
    catalog (callers enforce that — this builder does not invent codes).
    """
    return {
        "error": {
            "code": code,
            "message": scrub_text(message),
            "retryable": retryable,
            "details": scrub_mapping(details or {}),
            "correlation_id": correlation_id,
        }
    }
