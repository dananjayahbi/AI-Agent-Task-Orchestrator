"""MT-2.2-04 — session open/end with a cached project context.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.2-manifest-binding/
MT-2.2-04-session-lifecycle.md (parent plan Sections 10.3 steps 4–5, 9.2,
10.10, 19.3; FR-MCP-02, FR-MCP-06, FR-SEC-01).

The backend is mocked at the transport's send seam (WP-2.3's single injectable
HTTP boundary — the protocol's preferred mock point); the stdio entry point's
socket-level proof lives in ``test_entrypoints.py`` against the loopback stub.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.endpoints import endpoint
from orchestrator_bridge.errors import SessionOpenError
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.session import (
    SESSION_END_TIMEOUT_SECONDS,
    close_session,
    new_session_id,
    open_session,
)
from orchestrator_bridge.transport import ApiClient
from tests.conftest import FIXTURE_TOKEN, FakeBackend, build_binding, build_settings, envelope_wire

_OPEN = ("POST", endpoint("session_open").path)
_PROJECT = ("GET", "/api/v1/projects/PID00007")
_POLICY = ("GET", "/api/v1/projects/PID00007/policy")
_END = ("POST", "/api/v1/agent-sessions")


def _happy_backend() -> FakeBackend:
    """The Section 10.3 startup surface: open → project → policy."""
    fake = FakeBackend()
    fake.route_fn(
        *_OPEN,
        lambda body: (201, {"id": body["id"], "project_id": "PID00007", "transport": "stdio"}),
    )
    fake.route(
        *_PROJECT,
        200,
        {"id": "PID00007", "name": "Tea Factory ERP", "system_prompt_rules": "Project rule."},
    )
    fake.route(*_POLICY, 200, {"max_concurrent_tasks": 1, "lease_duration_minutes": 45})
    return fake


def _client(fake: FakeBackend) -> ApiClient:
    return ApiClient.for_binding(build_binding(), build_settings(), send=fake.send)


# --- step 4: open ---------------------------------------------------------------


def test_open_posts_bridge_issued_session_id_and_stores_it() -> None:
    fake = _happy_backend()
    session = open_session(build_binding(), build_settings(), client=_client(fake))
    (call,) = fake.calls_to(*_OPEN)
    assert call.body["id"] == session.agent_session_id
    assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", call.body["id"])
    # ADR-004: the project is never in the body — the backend derives it from
    # the token; the bridge cannot address another project even by accident.
    assert "project_id" not in call.body
    assert call.body["transport"] == "stdio"
    assert call.body["client_name"] == "orchestrator-bridge"
    assert call.body["capability"] == "unknown"
    # the bearer rides the header, and only the header (Section 12.4).
    assert call.headers["Authorization"].startswith("Bearer ")
    assert FIXTURE_TOKEN in call.headers["Authorization"]
    assert all(FIXTURE_TOKEN not in json.dumps(c.body) for c in fake.calls)


def test_open_mints_unique_unguessable_ids() -> None:
    fake = _happy_backend()
    binding, settings = build_binding(), build_settings()
    first = open_session(binding, settings, client=_client(fake))
    second = open_session(binding, settings, client=_client(fake))
    assert first.agent_session_id != second.agent_session_id
    assert len(first.agent_session_id) >= 32  # uuid4().hex — entropy, not structure


def test_open_is_mutating_so_it_carries_an_idempotency_key() -> None:
    fake = _happy_backend()
    open_session(build_binding(), build_settings(), client=_client(fake))
    (call,) = fake.calls_to(*_OPEN)
    assert "Idempotency-Key" in call.headers  # ADR-012 replay-safe open
    for read in (_PROJECT, _POLICY):
        (read_call,) = fake.calls_to(*read)
        assert "Idempotency-Key" not in read_call.headers  # reads never carry one


# --- step 5: context cache ------------------------------------------------------


def test_context_is_name_rules_and_policy_summary_only() -> None:
    fake = _happy_backend()
    session = open_session(build_binding(), build_settings(), client=_client(fake))
    context = session.context
    assert context.project_id == "PID00007"
    assert context.name == "Tea Factory ERP"
    assert context.rules == "Project rule."
    assert context.policy_summary == {"max_concurrent_tasks": 1, "lease_duration_minutes": 45}
    # Section 10.3 step 5 set exactly — extra backend fields are not cached
    # (MT-2.2-04 risk note: caching more invites client-side policy drift).
    fields = set(context.__dataclass_fields__)
    assert fields == {"project_id", "name", "rules", "policy_summary"}


def test_context_is_fetched_once_per_session_open() -> None:
    fake = _happy_backend()
    open_session(build_binding(), build_settings(), client=_client(fake))
    assert len(fake.calls_to(*_PROJECT)) == 1
    assert len(fake.calls_to(*_POLICY)) == 1


def test_context_cache_is_process_memory_not_disk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ "For the session": nothing is written anywhere but memory (FR-SEC-04)."""
    fake = _happy_backend()
    monkeypatch.chdir(tmp_path)
    open_session(build_binding(), build_settings(), client=_client(fake))
    assert list(tmp_path.iterdir()) == []  # cwd untouched; no cache file appears


# --- transient failures (Section 10.10 bounded retry via the WP-2.3 client) ------


def test_transient_5xx_is_retried_then_opens() -> None:
    fake = _happy_backend()
    attempts = {"count": 0}

    def flaky(body: Any) -> tuple[int, Any]:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return 500, None
        return 201, {"id": body["id"], "project_id": "PID00007"}

    fake.route_fn(*_OPEN, flaky)
    settings = build_settings(retry_max_attempts=2, retry_base_delay_seconds=0.0)
    client = ApiClient.for_binding(build_binding(), settings, send=fake.send, sleep=lambda _s: None)
    session = open_session(build_binding(), settings, client=client)
    assert session.agent_session_id
    assert attempts["count"] == 2


def test_persistent_failure_aborts_with_canonical_code() -> None:
    fake = _happy_backend()
    fake.route(*_OPEN, 500, None)  # malformed body → SERVER_ERROR-tagged, status-guessed
    settings = build_settings(retry_max_attempts=1)
    with pytest.raises(SessionOpenError) as excinfo:
        open_session(build_binding(), settings, client=_client(fake))
    assert str(ErrorCode.SERVER_ERROR) in str(excinfo.value)
    assert FIXTURE_TOKEN not in str(excinfo.value)


# --- canonical error mapping (Section 9.2 catalog) ------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (401, "AUTH_REQUIRED"),
        (429, "RATE_LIMITED"),
        (500, "SERVER_ERROR"),
        (400, "VALIDATION_ERROR"),
    ],
)
def test_backend_rejections_become_session_open_errors(status: int, code: str) -> None:
    fake = _happy_backend()
    retryable = status in (429, 500)
    fake.route(
        *_OPEN,
        status,
        json.loads(envelope_wire(status, code, "rejected", retryable=retryable).body),
    )
    with pytest.raises(SessionOpenError) as excinfo:
        open_session(build_binding(), build_settings(), client=_client(fake))
    assert code in str(excinfo.value)
    assert FIXTURE_TOKEN not in str(excinfo.value)


def test_context_fetch_failure_also_aborts_startup() -> None:
    """Step 5 failures abort too — the bridge never serves without context."""
    fake = _happy_backend()
    fake.route(*_PROJECT, 503, None)
    with pytest.raises(SessionOpenError):
        open_session(build_binding(), build_settings(), client=_client(fake))


def test_non_object_context_response_is_a_typed_failure() -> None:
    fake = _happy_backend()
    fake.route(*_PROJECT, 200, ["not", "an", "object"])
    with pytest.raises(SessionOpenError):
        open_session(build_binding(), build_settings(), client=_client(fake))


# --- end: best-effort teardown ---------------------------------------------------


def test_close_posts_end_with_the_session_id_and_bounds_the_client() -> None:
    fake = _happy_backend()
    binding, settings = build_binding(), build_settings()
    session = open_session(binding, settings, client=_client(fake))
    fake.route("POST", f"/api/v1/agent-sessions/{session.agent_session_id}/end", 200, None)
    assert close_session(binding, settings, session, send=fake.send) is True
    (end,) = fake.calls_to("POST", f"/api/v1/agent-sessions/{session.agent_session_id}/end")
    assert end.headers["Idempotency-Key"]  # repeated best-effort ends replay safely


def test_close_failure_logs_and_returns_never_raises() -> None:
    fake = _happy_backend()
    binding, settings = build_binding(), build_settings()
    session = open_session(binding, settings, client=_client(fake))
    fake.route("POST", f"/api/v1/agent-sessions/{session.agent_session_id}/end", 500, None)
    import io

    stream = io.StringIO()
    configure_logging(settings, stream=stream)
    assert close_session(binding, settings, session, send=fake.send) is False
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert any(record.get("event") == "session_end_failed" for record in records)
    # exactly one attempt — the bounded posture of Section 10.10 (no retry
    # loop can hold the process open on the way out).
    ends = [c for c in fake.calls if c.path.endswith("/end")]
    assert len(ends) == 1


def test_session_end_timeout_is_aggressive() -> None:
    """The shutdown budget is a small constant, not the request timeout."""
    assert 0 < SESSION_END_TIMEOUT_SECONDS <= 5.0


def test_new_session_ids_never_repeat() -> None:
    ids = {new_session_id() for _ in range(100)}
    assert len(ids) == 100
