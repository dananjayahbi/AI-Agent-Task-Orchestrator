"""Retry with bounded exponential backoff and jitter (parent plan Sections 9.2,
10.10, 23/ADR-012; NFR-04, NFR-12; MT-2.3-02).

The classification rule is the Section 9.2 envelope's ``retryable`` flag —
authoritative whenever the server provided one (error-envelope.md rule 3:
"Retrying a non-retryable failure is a client bug"). Consequences, all tested:

* ``VALIDATION_ERROR``, ``TASK_ALREADY_CLAIMED``, ``TASK_STATE_CONFLICT`` and
  every other ``retryable: false`` envelope surface after **exactly one
  attempt**, even when the HTTP status would look transient;
* ``retryable: true`` envelopes (``RATE_LIMITED``, ``SERVER_ERROR``, …),
  transport failures (no envelope) and malformed 5xx bodies are retried;
* the attempt count is bounded (``settings.retry_max_attempts``) so an
  unreachable backend can never wedge an agent (NFR-04): the final attempt's
  error is re-raised for the tool layer to present.

Delays: exponential ``base · 2ⁿ⁻¹`` capped at
:data:`MAX_BACKOFF_SECONDS`, multiplied by a jitter factor in
``[0.5, 1.0]`` (deterministic under an injected ``rng``), except when the
envelope supplies ``details.retry_after_seconds`` — a server-provided delay is
honored up to :data:`RETRY_AFTER_CAP_SECONDS` instead (MT-2.3-02 scope; the
detail key name is fixed here, the plan is silent — OQ note in the changelog).

**Safety dependency (ADR-012, MT-2.3-02 risk note):** retrying a *mutating*
call can double-apply without idempotency keys. MT-2.3-03 attaches a stable
``Idempotency-Key`` to every mutating request, prepared **once per logical
call** in ``transport`` — the key is therefore identical across the retries
this module issues, which is exactly what makes these retries safe. Until that
slice lands, only reads are safe to retry; the changelog records the pairing.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from .api_errors import ApiError
from .config import Settings

__all__ = [
    "JITTER_MAX",
    "JITTER_MIN",
    "MAX_BACKOFF_SECONDS",
    "RETRY_AFTER_CAP_SECONDS",
    "RetryPolicy",
    "retry_call",
]

#: Schedule ceiling for exponential growth (Section 10.10: bounded, not endless).
MAX_BACKOFF_SECONDS: Final = 30.0
#: Ceiling for a server-supplied ``details.retry_after_seconds`` (same spirit).
RETRY_AFTER_CAP_SECONDS: Final = 120.0
#: Jitter window applied to the schedule delay (tests assert these bounds).
JITTER_MIN: Final = 0.5
JITTER_MAX: Final = 1.0

#: The envelope ``details`` key carrying a server-requested retry delay.
RETRY_AFTER_DETAIL: Final = "retry_after_seconds"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Bounded attempt count plus the backoff schedule's documented defaults."""

    max_attempts: int
    base_delay_seconds: float
    max_delay_seconds: float = MAX_BACKOFF_SECONDS

    @classmethod
    def from_settings(cls, settings: Settings) -> RetryPolicy:
        """Build the policy from named configuration (Section 9.10)."""
        return cls(
            max_attempts=settings.retry_max_attempts,
            base_delay_seconds=settings.retry_base_delay_seconds,
        )

    def backoff_delay(self, failed_attempt: int, rng: random.Random) -> float:
        """Delay after *failed_attempt* (1-based): capped exponential × jitter.

        ``base · 2ⁿ⁻¹`` grows 1s, 2s, 4s… capped at ``max_delay_seconds``; the
        jitter factor in ``[JITTER_MIN, JITTER_MAX]`` de-synchronizes agents
        hammering one backend (Section 10.10).
        """
        raw = self.base_delay_seconds * float(2 ** (failed_attempt - 1))
        capped = min(raw, self.max_delay_seconds)
        return capped * rng.uniform(JITTER_MIN, JITTER_MAX)

    def retry_after_delay(self, error: ApiError) -> float | None:
        """A valid server-supplied delay from the envelope, else ``None``.

        Only meaningful for envelope errors that supplied
        ``details.retry_after_seconds`` as a positive number; anything else
        falls back to the backoff schedule (MT-2.3-02 scope sentence).
        """
        details = error.details
        if not details:
            return None
        value = details.get(RETRY_AFTER_DETAIL)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        if value <= 0:
            return None
        return min(float(value), RETRY_AFTER_CAP_SECONDS)


def retry_call[T](
    operation: Callable[[], T],
    policy: RetryPolicy,
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    on_retry: Callable[[int, ApiError, float], None] | None = None,
) -> T:
    """Run *operation*, retrying retryable :class:`ApiError` per *policy*.

    ``attempt`` is 1-based; a non-retryable error — or the attempt cap —
    re-raises the *last* error immediately. Non-``ApiError`` exceptions
    (programming bugs) are never retried. ``on_retry(attempt, error, delay)``
    fires before each sleep (transport uses it for the ``api_retry`` log
    event); ``sleep`` and ``rng`` are injected so tests are deterministic —
    no wall-clock waits, no flaky jitter.
    """
    generator = rng if rng is not None else random.Random()
    attempt = 1
    while True:
        try:
            return operation()
        except ApiError as error:
            # The server's flag decides; the cap bounds the loop (NFR-04).
            if not error.retryable or attempt >= policy.max_attempts:
                raise
            server_delay = policy.retry_after_delay(error)
            delay = (
                policy.backoff_delay(attempt, generator) if server_delay is None else server_delay
            )
            if on_retry is not None:
                on_retry(attempt, error, delay)
            sleep(delay)
            attempt += 1
