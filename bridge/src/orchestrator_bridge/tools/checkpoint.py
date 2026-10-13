"""``log_task_checkpoint`` (parent plan Sections 8.6, 9.2, 10.5; FR-LEA-03; MT-2.6-01).

The progress + lease-extension tool. The backend owns the extension formula
(Section 8.6: ``lease_expires_at`` = min(now + duration, acquired + hard cap)
and the late-checkpoint gate — WP-1.8); the bridge's job is the honest wire
call and the response assembly the plan's catalog promises: **the new expiry
plus the ``next_checkpoint_due`` hint** (RISK-02 — agents never checkpoint
against a stale deadline).

* body = the ``CheckpointCreateSerializer`` contract — ``session_id`` +
  ``lease_generation`` (the ADR-012 fencing pair, same as every mutating
  call; a never-claimed task sends generation 0 and the backend answers
  authoritatively), ``message`` and the optional ``percent`` (the tool-level
  ``percentage`` input maps to the Section 7.2 wire field).
* idempotency: the POST is mutating, so the WP-2.3 transport mints and
  replays one ``Idempotency-Key`` across its retry attempts (NFR-12,
  ADR-012).
* the ``next_checkpoint_due`` hint is derived from the same numbers the
  response returns (MT-2.6-01 risk note): the interval is one third of the
  session's lease window (:func:`checkpoint_interval_minutes`, rule 5) and
  the instant is clamped to the *new* ``lease_expires_at`` — never a
  deadline beyond the lease itself. When the extension hit the hard cap
  (``capped``), the hint becomes the cap instant and the guidance says
  submit or release: no more lease is coming (Section 8.6).
* ``LEASE_EXPIRED`` is the Section 10.5 contract: stop and re-claim
  (:mod:`error_translation` carries the RISK-02 wording). The bridge does
  not resurrect anything — the backend rejects stale generations with zero
  writes (WP-1.8 ``test_checkpoint_ownership`` asserts that against the
  real database); the bridge adds no retry of its own for non-retryable
  envelopes.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from ..api_errors import ApiError, ErrorCode, ErrorKind
from ..endpoints import endpoint
from ..error_translation import translate_error
from ..rules import DEFAULT_LEASE_MINUTES, checkpoint_interval_minutes
from .errors import ToolFailure
from .runtime import ToolRuntime

__all__ = ["log_task_checkpoint", "make_handler"]


def _failure(error: ApiError) -> ToolFailure:
    """Translate a backend error into the structured tool failure."""
    return ToolFailure(translate_error(error))


def _policy_lease_minutes(runtime: ToolRuntime) -> int:
    """The session policy's lease window (Section 7.2 default when absent)."""
    raw = runtime.project_context().policy_summary.get("lease_duration_minutes")
    if isinstance(raw, int) and not isinstance(raw, bool) and raw > 0:
        return raw
    return DEFAULT_LEASE_MINUTES


def _parse_timestamp(raw: Any) -> datetime | None:
    """One ISO timestamp from the response, or None when absent/unparseable."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _iso(moment: datetime) -> str:
    """One UTC instant in the wire's ``Z``-suffixed ISO spelling."""
    return moment.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _utc_now() -> datetime:
    """The current UTC instant (the injectable seam's default)."""
    return datetime.now(tz=UTC)


def log_task_checkpoint(
    runtime: ToolRuntime,
    *,
    task_id: str,
    message: str = "",
    percentage: int | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    """One progress checkpoint; returns the new expiry plus the next-due hint."""
    body = {
        "session_id": runtime.agent_session_id,
        # Fencing pair with the session id (ADR-012); a task never claimed in
        # this process sends 0 and the backend answers LEASE_EXPIRED/LEASE_
        # NOT_OWNED authoritatively rather than the bridge guessing (19.3).
        "lease_generation": runtime.lease_generation(task_id) or 0,
        "message": message,
        "percent": percentage,
    }
    try:
        payload = runtime.client.request(
            "POST", endpoint("checkpoint_create").path.format(id=task_id), body=body
        )
    except ApiError as exc:
        raise _failure(exc) from None
    if not isinstance(payload, Mapping):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="checkpoint response is not the documented object",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "checkpoint_create"},
            )
        )
    checkpoint = payload.get("checkpoint")
    if not isinstance(checkpoint, Mapping):
        raise _failure(
            ApiError(
                code=ErrorCode.SERVER_ERROR,
                message="checkpoint response is missing the stored checkpoint row",
                retryable=False,
                kind=ErrorKind.MALFORMED_RESPONSE,
                details={"endpoint": "checkpoint_create"},
            )
        )
    capped = payload.get("capped") is True
    expires_at = _parse_timestamp(payload.get("lease_expires_at"))

    # RISK-02: one source for the deadline — the interval scales with the
    # session's lease window and the instant is clamped to the expiry the
    # response just returned (never beyond the lease itself).
    clock = now if now is not None else _utc_now
    interval = checkpoint_interval_minutes(_policy_lease_minutes(runtime))
    next_due = clock() + timedelta(minutes=interval)
    if expires_at is not None:
        next_due = min(next_due, expires_at)
    if capped:
        # Hard cap reached (Section 8.6): no further extension is coming, so
        # the next-due hint becomes the lease deadline itself and the
        # guidance is submit-or-release, not "keep checkpointing".
        next_due = expires_at if expires_at is not None else next_due
        next_action = (
            "The lease hard cap is reached — no more extension is possible: "
            "submit_task_resolution now, or release_task if the work must stop."
        )
    else:
        next_action = (
            "Send the next checkpoint before next_checkpoint_due to keep the lease alive (rule 5)."
        )
    return {
        "task_id": task_id,
        "checkpoint": {
            "id": checkpoint.get("id"),
            "timestamp": checkpoint.get("timestamp"),
            "percent": checkpoint.get("percent"),
            "kind": checkpoint.get("kind"),
        },
        "lease_extended": payload.get("lease_extended") is True,
        "lease_expires_at": payload.get("lease_expires_at"),
        "capped": capped,
        "next_checkpoint_due": _iso(next_due),
        "next_action": next_action,
    }


def make_handler(runtime: ToolRuntime) -> Callable[..., dict[str, Any]]:
    """The registered MCP handler: schema-typed arguments, bound session."""

    def log_task_checkpoint_tool(
        task_id: str,
        message: str = "",
        percentage: int | None = None,
    ) -> dict[str, Any]:
        """Log one checkpoint; returns the new expiry and the next-due hint."""
        return log_task_checkpoint(runtime, task_id=task_id, message=message, percentage=percentage)

    return log_task_checkpoint_tool
