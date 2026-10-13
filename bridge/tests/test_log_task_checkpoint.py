"""MT-2.6-01 — ``log_task_checkpoint``: new expiry, next-due hint, fencing.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/
MT-2.6-01-checkpoint-tool.md (parent plan Sections 8.6, 10.5, 9.2; FR-LEA-03;
RISK-02). The backend owns the extension formula and the late-checkpoint gate
(WP-1.8 asserts zero-write rejection against the real database); these tests
pin the bridge half: the honest wire contract, the next-due hint derived from
the response's own lease numbers, the hard-cap guidance, the LEASE_EXPIRED
stop-and-reclaim mapping with no blind retry, and idempotent replay of one
logical checkpoint across transport retries.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.tools.checkpoint import log_task_checkpoint
from orchestrator_bridge.tools.errors import ToolFailure
from tests.conftest import FakeBackend, build_runtime, build_settings, envelope_wire

_TASK_ID = "PID00007-T004"
_CHECKPOINT_PATH = f"/api/v1/tasks/{_TASK_ID}/checkpoints"

#: 10:05 on the clock; the 45-minute policy lease yields a 15-minute interval.
_NOW = datetime(2026, 10, 13, 10, 5, tzinfo=UTC)


def _now() -> datetime:
    return _NOW


def _checkpoint_wire(
    *, lease_expires_at: str | None = "2026-10-13T10:50:00Z", capped: bool = False
) -> dict[str, Any]:
    """The WP-1.8 ``CheckpointWriteResponseSerializer`` shape (MT-1.8-03)."""
    return {
        "checkpoint": {
            "id": "6f1c0a9e-6a8e-4a5e-9d0e-3f5d3b6a1c22",
            "task_id": _TASK_ID,
            "attempt_number": 1,
            "session_id": "fixture-session-0001",
            "timestamp": "2026-10-13T10:05:00Z",
            "message": "halfway there",
            "percent": 50,
            "token_usage": {},
            "kind": "progress",
        },
        "lease_extended": True,
        "lease_expires_at": lease_expires_at,
        "capped": capped,
    }


def test_log_task_checkpoint_reports_new_expiry_and_next_due_hint(
    fake_backend: FakeBackend,
) -> None:
    fake_backend.route("POST", _CHECKPOINT_PATH, 200, _checkpoint_wire())
    runtime = build_runtime(fake_backend)

    result = log_task_checkpoint(
        runtime, task_id=_TASK_ID, message="halfway there", percentage=50, now=_now
    )

    # The Section 10.5 promise: new expiry plus the RISK-02 next-due hint,
    # the latter derived from the same numbers the response returned.
    assert result["task_id"] == _TASK_ID
    assert result["lease_extended"] is True
    assert result["lease_expires_at"] == "2026-10-13T10:50:00Z"
    assert result["capped"] is False
    assert result["next_checkpoint_due"] == "2026-10-13T10:20:00Z"  # now + 15 minutes
    assert result["checkpoint"]["id"] == "6f1c0a9e-6a8e-4a5e-9d0e-3f5d3b6a1c22"
    assert result["checkpoint"]["percent"] == 50

    # The CheckpointCreateSerializer wire contract, field for field.
    (call,) = fake_backend.calls_to("POST", _CHECKPOINT_PATH)
    assert call.body == {
        "session_id": "fixture-session-0001",
        "lease_generation": 0,  # never claimed in this process → backend decides
        "message": "halfway there",
        "percent": 50,
    }
    assert call.headers["Idempotency-Key"]  # every mutating call carries one


def test_log_task_checkpoint_carries_the_claimed_lease_generation(
    fake_backend: FakeBackend,
) -> None:
    fake_backend.route("POST", _CHECKPOINT_PATH, 200, _checkpoint_wire())
    runtime = build_runtime(fake_backend)
    runtime.record_lease(_TASK_ID, 3)

    log_task_checkpoint(runtime, task_id=_TASK_ID, now=_now)

    (call,) = fake_backend.calls_to("POST", _CHECKPOINT_PATH)
    assert call.body["lease_generation"] == 3  # ADR-012 fencing half


def test_log_task_checkpoint_clamps_next_due_to_the_new_expiry(
    fake_backend: FakeBackend,
) -> None:
    # The lease only extends five minutes ahead: the hint must not promise a
    # deadline beyond the lease itself (the "one source" risk note).
    fake_backend.route(
        "POST", _CHECKPOINT_PATH, 200, _checkpoint_wire(lease_expires_at="2026-10-13T10:12:00Z")
    )
    runtime = build_runtime(fake_backend)

    result = log_task_checkpoint(runtime, task_id=_TASK_ID, now=_now)

    assert result["next_checkpoint_due"] == "2026-10-13T10:12:00Z"


def test_log_task_checkpoint_capped_extension_guides_submit_or_release(
    fake_backend: FakeBackend,
) -> None:
    fake_backend.route(
        "POST",
        _CHECKPOINT_PATH,
        200,
        _checkpoint_wire(lease_expires_at="2026-10-13T11:00:00Z", capped=True),
    )
    runtime = build_runtime(fake_backend)

    result = log_task_checkpoint(runtime, task_id=_TASK_ID, now=_now)

    assert result["capped"] is True
    assert result["next_checkpoint_due"] == "2026-10-13T11:00:00Z"  # the deadline itself
    assert "submit_task_resolution" in result["next_action"]
    assert "release_task" in result["next_action"]


def test_log_task_checkpoint_lease_expired_stops_and_reclaims(
    fake_backend: FakeBackend,
) -> None:
    fake_backend.route(
        "POST",
        _CHECKPOINT_PATH,
        409,
        json.loads(envelope_wire(409, "LEASE_EXPIRED", "the lease expired", retryable=False).body),
    )
    runtime = build_runtime(fake_backend, settings=build_settings(retry_max_attempts=2))

    with pytest.raises(ToolFailure) as excinfo:
        log_task_checkpoint(runtime, task_id=_TASK_ID, message="late", now=_now)

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.LEASE_EXPIRED
    assert translated.hint  # Section 10.5 error rule
    assert "claim_task" in translated.next_action  # stop and re-claim (Section 8.6)
    # Non-retryable envelope → no blind retry, exactly one wire call, and the
    # bridge holds no lease state that a late checkpoint could have "woken".
    assert len(fake_backend.calls) == 1
    assert runtime.lease_generation(_TASK_ID) is None


def test_log_task_checkpoint_retry_replays_one_idempotency_key(
    fake_backend: FakeBackend,
) -> None:
    attempts = {"count": 0}

    def _flaky(_body: Any) -> tuple[int, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return 500, {"error": {"code": "SERVER_ERROR", "message": "blip", "retryable": True}}
        return 200, _checkpoint_wire()

    fake_backend.route_fn("POST", _CHECKPOINT_PATH, _flaky)
    runtime = build_runtime(fake_backend, settings=build_settings(retry_max_attempts=2))

    result = log_task_checkpoint(runtime, task_id=_TASK_ID, now=_now)

    assert result["lease_extended"] is True  # the replayed call succeeded
    first, second = fake_backend.calls_to("POST", _CHECKPOINT_PATH)
    assert first.headers["Idempotency-Key"] == second.headers["Idempotency-Key"]


def test_log_task_checkpoint_malformed_response_is_a_server_error(
    fake_backend: FakeBackend,
) -> None:
    fake_backend.route("POST", _CHECKPOINT_PATH, 200, ["not", "an", "object"])
    runtime = build_runtime(fake_backend)

    with pytest.raises(ToolFailure) as excinfo:
        log_task_checkpoint(runtime, task_id=_TASK_ID, now=_now)

    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR
    assert excinfo.value.translated.hint
