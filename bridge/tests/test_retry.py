"""MT-2.3-02 — retry policy: bounded exponential backoff, jitter, flag authority.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.3-api-client/
MT-2.3-02-retry-backoff.md (parent plan Sections 9.2, 10.10, 23/ADR-012;
NFR-04, NFR-12).

Fully deterministic: sleeps are recorded (never awaited) and the jitter draws
come from a seeded ``random.Random`` — attempt counts and delay bounds are
asserted exactly, with no wall-clock dependence.
"""

from __future__ import annotations

import io
import json
import random
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ApiError, ErrorCode, ErrorKind
from orchestrator_bridge.config import Settings, load_settings
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.retry import (
    JITTER_MAX,
    JITTER_MIN,
    MAX_BACKOFF_SECONDS,
    RETRY_AFTER_CAP_SECONDS,
    RetryPolicy,
    retry_call,
)
from orchestrator_bridge.transport import ApiClient, WireResponse

ABSENT_CONFIG = Path("no-such-bridge-config.toml")
TOKEN = "fixture-token-not-a-real-secret"
POLICY = RetryPolicy(max_attempts=3, base_delay_seconds=1.0)


def _error(
    code: ErrorCode = ErrorCode.SERVER_ERROR,
    *,
    retryable: bool,
    kind: ErrorKind = ErrorKind.ENVELOPE,
    details: dict[str, Any] | None = None,
    status_code: int | None = 500,
) -> ApiError:
    return ApiError(
        code=code,
        message=f"{code} occurred",
        retryable=retryable,
        kind=kind,
        details=details,
        correlation_id="c0a8-4f2e-91d7",
        status_code=status_code,
    )


def _scripted(outcomes: list[ApiError]) -> tuple[Callable[[], str], list[int]]:
    """Operation failing with each queued ApiError, then succeeding with 'ok'."""
    calls: list[int] = []
    queue = list(outcomes)

    def operation() -> str:
        calls.append(1)
        if queue:
            raise queue.pop(0)
        return "ok"

    return operation, calls


def _sleeper() -> tuple[Callable[[float], None], list[float]]:
    sleeps: list[float] = []
    return sleeps.append, sleeps


def _settings(**overrides: str) -> Settings:
    env = {
        "ORCHESTRATOR_AGENT_TOKEN": TOKEN,
        "ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS": "3",
        "ORCHESTRATOR_BRIDGE_RETRY_BASE_DELAY_SECONDS": "1",
    }
    env.update(overrides)
    return load_settings(env=env, config_path=ABSENT_CONFIG)


def _envelope(code: str, *, retryable: bool, details: dict[str, Any] | None = None) -> bytes:
    error: dict[str, Any] = {
        "code": code,
        "message": f"{code} from backend",
        "retryable": retryable,
        "correlation_id": "c0a8-4f2e-91d7",
    }
    if details is not None:
        error["details"] = details
    return json.dumps({"error": error}).encode("utf-8")


def _client(
    *responses: WireResponse | BaseException,
    settings: Settings | None = None,
    stream: io.StringIO | None = None,
) -> tuple[ApiClient, list[WireResponse | BaseException], list[float]]:
    resolved = settings or _settings()
    if stream is not None:
        configure_logging(resolved, stream=stream)
    queue: list[WireResponse | BaseException] = list(responses)
    sleep, sleeps = _sleeper()

    def send(
        method: str, url: str, headers: Any, body: bytes | None, timeout: float
    ) -> WireResponse:
        if not queue:
            raise AssertionError("response queue exhausted")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    client = ApiClient(resolved, send=send, sleep=sleep, rng=random.Random(7))
    return client, queue, sleeps


# --- schedule: exponential, capped, jittered ---------------------------------


def test_backoff_delay_is_exponential_within_jitter_window() -> None:
    rng = random.Random(7)
    first = POLICY.backoff_delay(1, rng)
    third = POLICY.backoff_delay(3, rng)
    assert 1.0 * JITTER_MIN <= first <= 1.0 * JITTER_MAX
    assert 4.0 * JITTER_MIN <= third <= 4.0 * JITTER_MAX


def test_backoff_delay_is_capped_at_max() -> None:
    rng = random.Random(7)
    far = POLICY.backoff_delay(20, rng)  # 2**19 seconds unbounded
    assert far <= MAX_BACKOFF_SECONDS
    assert far >= MAX_BACKOFF_SECONDS * JITTER_MIN


def test_zero_base_delay_is_allowed_by_policy_construction() -> None:
    """The *settings* layer enforces > 0; the policy itself stays a plain value."""
    assert RetryPolicy(max_attempts=1, base_delay_seconds=0.0).max_attempts == 1


# --- server-provided retry delay ---------------------------------------------


def test_retry_after_detail_overrides_schedule() -> None:
    error = _error(ErrorCode.RATE_LIMITED, retryable=True, details={"retry_after_seconds": 7})
    assert POLICY.retry_after_delay(error) == 7.0


def test_retry_after_detail_is_capped() -> None:
    error = _error(ErrorCode.RATE_LIMITED, retryable=True, details={"retry_after_seconds": 5000})
    assert POLICY.retry_after_delay(error) == RETRY_AFTER_CAP_SECONDS


@pytest.mark.parametrize(
    "details",
    [
        {"retry_after_seconds": "soon"},
        {"retry_after_seconds": -1},
        {"retry_after_seconds": True},
        {"retry_after": 5},
        {},
    ],
)
def test_invalid_retry_after_falls_back_to_schedule(details: dict[str, Any]) -> None:
    error = _error(ErrorCode.RATE_LIMITED, retryable=True, details=details)
    assert POLICY.retry_after_delay(error) is None


# --- retry loop: attempt counts and classification ---------------------------


def test_retryable_failures_retried_until_success_with_bounded_delays() -> None:
    operation, calls = _scripted(
        [_error(retryable=True), _error(retryable=True, kind=ErrorKind.TRANSPORT_FAILURE)]
    )
    sleep, sleeps = _sleeper()

    result = retry_call(operation, POLICY, sleep=sleep, rng=random.Random(7))

    assert result == "ok"
    assert len(calls) == 3  # two failures + success
    assert len(sleeps) == 2
    assert 1.0 * JITTER_MIN <= sleeps[0] <= 1.0 * JITTER_MAX  # attempt 1 → base
    assert 2.0 * JITTER_MIN <= sleeps[1] <= 2.0 * JITTER_MAX  # attempt 2 → 2×base


def test_non_retryable_envelope_surfaces_after_exactly_one_attempt() -> None:
    operation, calls = _scripted(
        [
            _error(
                ErrorCode.TASK_ALREADY_CLAIMED,
                retryable=False,
                status_code=409,
            )
        ]
    )
    sleep, sleeps = _sleeper()

    with pytest.raises(ApiError) as excinfo:
        retry_call(operation, POLICY, sleep=sleep, rng=random.Random(7))

    assert excinfo.value.code is ErrorCode.TASK_ALREADY_CLAIMED
    assert len(calls) == 1
    assert sleeps == []


def test_retryable_flag_is_authoritative_even_against_status_intuition() -> None:
    """A 5xx envelope marked ``retryable: false`` is NOT retried (flag rules)."""
    operation, calls = _scripted([_error(retryable=False, status_code=503)])

    with pytest.raises(ApiError):
        retry_call(operation, POLICY, sleep=lambda _: None, rng=random.Random(7))

    assert len(calls) == 1


def test_rate_limited_flag_true_retried_up_to_attempt_cap() -> None:
    def operation() -> str:
        raise _error(ErrorCode.RATE_LIMITED, retryable=True, status_code=429)

    calls: list[int] = []
    sleep, sleeps = _sleeper()

    def counting() -> str:
        calls.append(1)
        return operation()

    with pytest.raises(ApiError) as excinfo:
        retry_call(counting, POLICY, sleep=sleep, rng=random.Random(7))

    assert excinfo.value.code is ErrorCode.RATE_LIMITED
    assert len(calls) == 3  # bounded (NFR-04): no wedge against a down backend
    assert len(sleeps) == 2


def test_transport_failures_are_retried() -> None:
    operation, calls = _scripted(
        [_error(retryable=True, kind=ErrorKind.TRANSPORT_FAILURE, status_code=None)]
    )
    sleep, sleeps = _sleeper()

    assert retry_call(operation, POLICY, sleep=sleep, rng=random.Random(7)) == "ok"
    assert len(calls) == 2 and len(sleeps) == 1


def test_server_retry_after_detail_is_used_for_sleep() -> None:
    operation, _ = _scripted(
        [
            _error(
                ErrorCode.RATE_LIMITED,
                retryable=True,
                details={"retry_after_seconds": 7},
                status_code=429,
            )
        ]
    )
    sleep, sleeps = _sleeper()

    assert retry_call(operation, POLICY, sleep=sleep, rng=random.Random(7)) == "ok"
    assert sleeps == [7.0]


def test_max_attempts_one_disables_retry() -> None:
    operation, calls = _scripted([_error(retryable=True)])
    sleep, sleeps = _sleeper()

    with pytest.raises(ApiError):
        retry_call(operation, RetryPolicy(max_attempts=1, base_delay_seconds=1.0), sleep=sleep)

    assert len(calls) == 1 and sleeps == []


def test_non_api_error_propagates_without_retry() -> None:
    calls: list[int] = []

    def boom() -> str:
        calls.append(1)
        raise ValueError("bridge bug, not a backend failure")

    with pytest.raises(ValueError, match="bridge bug"):
        retry_call(boom, POLICY, sleep=lambda _: None)

    assert len(calls) == 1


def test_on_retry_callback_reports_attempt_error_and_delay() -> None:
    operation, _ = _scripted([_error(retryable=True)])
    seen: list[tuple[int, str, float]] = []

    retry_call(
        operation,
        POLICY,
        sleep=lambda _: None,
        rng=random.Random(7),
        on_retry=lambda attempt, error, delay: seen.append((attempt, str(error.code), delay)),
    )

    assert len(seen) == 1
    attempt, code, delay = seen[0]
    assert attempt == 1
    assert code == ErrorCode.SERVER_ERROR
    assert delay > 0


# --- client integration: the transport actually retries ----------------------


def test_client_retries_5xx_then_succeeds_with_identical_headers() -> None:
    """5xx and timeouts retry (WP-2.3 acceptance); retries replay identical
    headers — the ADR-012 pairing MT-2.3-03 completes with the key itself."""
    stream = io.StringIO()
    client, _, sleeps = _client(
        WireResponse(500, {}, _envelope("SERVER_ERROR", retryable=True)),
        TimeoutError("read timed out"),
        WireResponse(200, {}, b'{"ok": true}'),
        stream=stream,
    )

    assert client.request("GET", "/api/v1/projects/PID00007") == {"ok": True}
    assert len(sleeps) == 2

    logged = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    retries = [entry for entry in logged if entry.get("event") == "api_retry"]
    assert [entry["attempt"] for entry in retries] == [1, 2]
    assert retries[0]["error_code"] == ErrorCode.SERVER_ERROR
    responses = [entry for entry in logged if entry.get("event") == "api_response"]
    assert len(responses) == 1  # success logged once, retries logged separately


def test_client_surfaces_non_retryable_after_one_attempt() -> None:
    client, _, sleeps = _client(
        WireResponse(409, {}, _envelope("TASK_ALREADY_CLAIMED", retryable=False))
    )

    with pytest.raises(ApiError) as excinfo:
        client.request("POST", "/api/v1/tasks/PID00007-T004/claim")

    assert excinfo.value.code is ErrorCode.TASK_ALREADY_CLAIMED
    assert sleeps == []


def test_client_stops_at_attempt_cap_and_logs_final_failure_once() -> None:
    stream = io.StringIO()
    client, _, sleeps = _client(
        WireResponse(503, {}, _envelope("SERVER_ERROR", retryable=True)),
        WireResponse(503, {}, _envelope("SERVER_ERROR", retryable=True)),
        WireResponse(503, {}, _envelope("SERVER_ERROR", retryable=True)),
        stream=stream,
    )

    with pytest.raises(ApiError) as excinfo:
        client.request("GET", "/api/v1/projects/PID00007/work")

    assert excinfo.value.code is ErrorCode.SERVER_ERROR
    assert excinfo.value.retryable is True  # final failure still marked retryable upstream
    assert len(sleeps) == 2  # 3 attempts, 2 backoffs

    logged = [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]
    assert len([e for e in logged if e.get("event") == "api_retry"]) == 2
    assert len([e for e in logged if e.get("event") == "api_error"]) == 1


def test_client_rate_limit_honors_server_delay_end_to_end() -> None:
    client, _, sleeps = _client(
        WireResponse(
            429,
            {},
            _envelope("RATE_LIMITED", retryable=True, details={"retry_after_seconds": 9}),
        ),
        WireResponse(200, {}, b"{}"),
    )

    assert client.request("GET", "/api/v1/projects/PID00007/work") == {}
    assert sleeps == [9.0]
