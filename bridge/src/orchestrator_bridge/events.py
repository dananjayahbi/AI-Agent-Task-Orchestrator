"""Resilience log events (parent plan Section 10.10; MT-2.1-03).

One structured event per retry attempt and per stale-session abort, each carrying
attempt/session context, so operations can reconstruct behavior from logs alone
(NFR-10) even when a remote run's logs are the only evidence. WP-2.3 (backend
retries with backoff) and WP-2.9/WP-2.2 (stale-session handling) are the callers —
this module fixes the event shapes, not the retry logic.
"""

from __future__ import annotations

from .logging import get_logger

__all__ = ["log_retry_attempt", "log_stale_session_abort"]


def log_retry_attempt(
    *,
    component: str,
    operation: str,
    attempt: int,
    max_attempts: int | None,
    cause: str,
    backoff_seconds: float | None = None,
) -> None:
    """One structured line per retry attempt (Section 10.10 backoff behavior)."""
    get_logger(component).info(
        "retry attempt",
        extra={
            "event": "retry_attempt",
            "operation": operation,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "cause": cause,
            "backoff_seconds": backoff_seconds,
        },
    )


def log_stale_session_abort(
    *,
    component: str,
    session_id: str,
    reason: str,
    stale_for_seconds: float | None = None,
) -> None:
    """One structured line per stale-session abort (Section 10.10 session end)."""
    get_logger(component).warning(
        "stale session abort",
        extra={
            "event": "stale_session_abort",
            "session_id": session_id,
            "reason": reason,
            "stale_for_seconds": stale_for_seconds,
        },
    )
