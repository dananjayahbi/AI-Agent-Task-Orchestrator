"""MT-2.4-05 — release_task (voluntary, no failure increment).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.4-core-tools/
MT-2.4-05-release-task.md (parent plan Sections 9.2, 10.5, 10.10; FR-MCP-03,
FR-LEA-01). The no-increment behavior is the backend's contract (FR-LEA-06);
the bridge proves it never *requests* an attempt consumption — the guard test
pins the request shape to exactly the ReleaseRequest fields.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.tools.claim import claim_task
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.release import release_request_body, release_task
from tests.conftest import FakeBackend, build_runtime, envelope_wire

_RELEASE_PATH = endpoint("release").path.format(id="PID00007-T004")
_CLAIM_PATH = endpoint("claim").path.format(id="PID00007-T004")

_RELEASED_TASK = {
    "id": "PID00007-T004",
    "project_id": "PID00007",
    "title": "Add invoice export",
    "state": "pending",
    "failure_retry_count": 0,
    "attempt_number": 2,
}
_CLAIM_RESPONSE = {
    "task": {"id": "PID00007-T004", "state": "in_progress"},
    "lease": {
        "task_id": "PID00007-T004",
        "assigned_agent": "coder-1",
        "session_id": "fixture-session-0001",
        "role": "coder",
        "lease_generation": 3,
        "lease_acquired_at": "2026-10-12T09:00:00Z",
        "lease_expires_at": "2026-10-12T09:45:00Z",
        "lease_hard_cap_at": "2026-10-12T13:00:00Z",
        "last_checkpoint": None,
        "failure_retry_count": 0,
    },
    "rules_block": {"standard_rules": [], "project_rules": ""},
}


def _backend(status: int = 200, payload: Any = None) -> FakeBackend:
    fake = FakeBackend()
    fake.route(
        "POST",
        _RELEASE_PATH,
        status,
        _RELEASED_TASK if payload is None else payload,
    )
    return fake


def test_successful_release_returns_state_and_next_action() -> None:
    result = release_task(build_runtime(_backend()), task_id="PID00007-T004", reason="done")
    assert result["task_id"] == "PID00007-T004"
    assert result["state"] == "pending"
    assert result["released"] is True
    assert "get_available_tasks" in result["next_action"]


def test_release_body_is_exactly_the_fencing_pair_and_reason() -> None:
    fake = _backend()
    runtime = build_runtime(fake)
    runtime.record_lease("PID00007-T004", 3)  # as a prior claim would have
    release_task(runtime, task_id="PID00007-T004", reason="scope change")
    (call,) = fake.calls_to("POST", _RELEASE_PATH)
    # Guard (MT acceptance): no attempt/failure-increment field exists to send.
    assert set(call.body) <= {"session_id", "lease_generation", "reason"}
    assert call.body == {
        "session_id": "fixture-session-0001",
        "lease_generation": 3,
        "reason": "scope change",
    }
    assert call.headers["Idempotency-Key"]  # retried release replays (NFR-12)


def test_release_without_a_recorded_claim_still_asks_the_backend() -> None:
    """No local lease guessing (Section 19.3): the generation is omitted and
    the backend answers authoritatively (LEASE_*), which the shutdown-race
    path of Section 10.10 relies on."""
    fake = _backend()
    release_task(build_runtime(fake), task_id="PID00007-T004", reason="exiting")
    (call,) = fake.calls_to("POST", _RELEASE_PATH)
    assert "lease_generation" not in call.body
    assert call.body["session_id"] == "fixture-session-0001"


def test_claim_then_release_round_trip_carries_the_generation() -> None:
    fake = _backend()
    fake.route("POST", _CLAIM_PATH, 200, _CLAIM_RESPONSE)
    runtime = build_runtime(fake)
    claim_task(runtime, task_id="PID00007-T004", agent_identifier="coder-1")
    release_task(runtime, task_id="PID00007-T004", reason="re-planning")
    (release,) = fake.calls_to("POST", _RELEASE_PATH)
    assert release.body["lease_generation"] == 3


def test_request_body_builder_has_no_failure_field() -> None:
    runtime = build_runtime()
    runtime.record_lease("PID00007-T004", 3)
    body = release_request_body(runtime, task_id="PID00007-T004", reason="x")
    assert set(body) == {"session_id", "lease_generation", "reason"}
    assert "failure_retry_count" not in body and "attempt" not in " ".join(body)


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (409, "LEASE_NOT_OWNED"),
        (409, "LEASE_EXPIRED"),
        (409, "TASK_STATE_CONFLICT"),
        (404, "TASK_NOT_FOUND"),
        (400, "VALIDATION_ERROR"),
    ],
)
def test_release_errors_surface_with_exact_codes_and_calm_guidance(status: int, code: str) -> None:
    envelope = json.loads(envelope_wire(status, code, f"backend said {code}").body)
    with pytest.raises(ToolFailure) as excinfo:
        release_task(build_runtime(_backend(status, envelope)), task_id="PID00007-T004")
    translated = excinfo.value.translated
    assert translated.code is ErrorCode(code)
    assert translated.hint and translated.next_action
    if code == "LEASE_EXPIRED":
        # The MT's risk note: an expired lease on shutdown is a clean next
        # action, not an alarm.
        assert (
            "get_available_tasks" in translated.next_action
            or "re-acquire" in translated.next_action
        )


def test_malformed_release_response_is_a_structured_server_error() -> None:
    with pytest.raises(ToolFailure) as excinfo:
        release_task(build_runtime(_backend(200, ["not", "an", "object"])), task_id="PID00007-T004")
    assert excinfo.value.translated.code is ErrorCode.SERVER_ERROR
