"""MT-2.9-03 — connection lifecycle, limits and teardown (Sections 10.2,
10.10, 9.9; FR-MCP-06, NFR-04).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.9-http-transport/
MT-2.9-03-connection-lifecycle.md. Covers: deterministic state transitions,
the documented connection cap with a structured rejection, the idle timeout
on an injected clock (a live SSE stream is never reaped), the shared cleanup
path on every exit route (client DELETE, failed handshake, idle sweep, server
shutdown), non-blocking teardown while the backend is unreachable, and
retryable errors on tool calls during an outage (the MT-2.3-02 behavior,
observed over HTTP).
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from orchestrator_bridge.http_service.connection import ConnectionState
from orchestrator_bridge.http_service.registry import ConnectionRegistry
from tests.http_harness import (
    FakeClock,
    happy_backend,
    http_settings,
    running_bridge,
    wait_for,
)

_PID_A = "PID00007"
_PID_B = "PID00008"


class FlakyBackend:
    """The send seam with an outage switch (fail every backend call on demand)."""

    def __init__(self, fake: Any) -> None:
        self.fake = fake
        self.down = False

    def send(self, method: str, url: str, headers: Any, body: Any, timeout: float) -> Any:
        if self.down:
            raise OSError("connection refused (simulated outage)")
        return self.fake.send(method, url, headers, body, timeout)


def _registry(bridge: Any) -> Any:
    return bridge.server.config.app.registry


def _state_of(connection: Any) -> ConnectionState:
    """Fetch the live state — breaks mypy's member-expression narrowing so
    sequential state asserts compare the *current* value, not a remembered
    literal from an earlier assert."""
    state: ConnectionState = connection.state
    return state


# --- capacity accounting (unit level, no server) ------------------------------


def test_connection_lifecycle_reservation_accounting_is_synchronous() -> None:
    """Admission check + reserve is one synchronous step (no overshoot)."""
    registry = ConnectionRegistry(
        max_connections=2, idle_timeout_seconds=1.0, time_func=time.monotonic
    )
    assert registry.size == 0 and registry.admitted_or_reserved == 0
    assert registry.has_capacity()
    assert registry.has_capacity()
    assert not registry.has_capacity()  # the cap counts in-flight handshakes
    assert registry.admitted_or_reserved == 2
    registry.cancel_reservation()
    registry.cancel_reservation()
    assert registry.admitted_or_reserved == 0
    with pytest.raises(RuntimeError):
        registry.cancel_reservation()  # never over-release
    assert registry.has_capacity()


# --- state machine ------------------------------------------------------------


def test_connection_lifecycle_states_progress_bound_then_active() -> None:
    """open -> bound (initialize) -> active (first routed request)."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.initialize()  # handshake only: bound, nothing routed yet
        registry = _registry(bridge)
        connection = registry.get(str(client.session_id))
        assert connection is not None
        assert _state_of(connection) is ConnectionState.BOUND
        assert connection.open_streams == 0

        client.notify_initialized()  # first routed request activates it
        assert _state_of(connection) is ConnectionState.ACTIVE

        with pytest.raises(RuntimeError, match="illegal connection transition"):
            connection.transition(ConnectionState.CLOSED)
        with pytest.raises(RuntimeError, match="illegal connection transition"):
            connection.transition(ConnectionState.ACTIVE)
        assert _state_of(connection) is ConnectionState.ACTIVE  # refusals never mutate


def test_connection_lifecycle_capacity_rejection_is_structured() -> None:
    """The documented cap refuses excess connections with the catalog code."""
    fake = happy_backend((_PID_A, "Tea"), (_PID_B, "Second"))
    settings = http_settings(http_max_connections=1)
    with running_bridge(settings, send=fake.send) as bridge:
        first = bridge.client(_PID_A, "token-for-A")
        first.connect()
        assert first.health().json()["connections"] == 1

        second = bridge.client(_PID_B, "token-for-B")
        response = second.raw_post(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "rejected", "version": "1"},
                },
            }
        )
        assert response.status_code == 503
        error = response.json()["error"]
        assert error["code"] == "CONCURRENCY_LIMIT_REACHED"
        assert error["retryable"] is True
        assert error["details"]["reason"] == "connection_limit"
        assert "close" in error["details"]["next_action"].lower()
        assert response.headers.get("mcp-session-id") is None
        # the rejection happened before any backend work for the second project
        assert not any(f"/projects/{_PID_B}" in c.path for c in fake.calls)

        # room frees when a connection closes (DELETE, then finalize)
        assert first.delete_session() in (200, 202, 204)
        wait_for(
            lambda: first.health().json()["connections"] == 0,
            message="slot released after DELETE",
        )
        third = bridge.client(_PID_B, "token-for-B")
        third.connect()
        assert third.health().json()["connections"] == 1


def test_connection_lifecycle_idle_timeout_closes_only_silent_connections() -> None:
    """Idle sweep closes quiet connections; an open SSE stream is never idle."""
    fake = happy_backend((_PID_A, "Tea"), (_PID_B, "Second"))
    clock = FakeClock()
    settings = http_settings(http_idle_timeout_seconds=15.0)
    with running_bridge(
        settings, send=fake.send, time_func=clock, sweep_tick_seconds=0.05
    ) as bridge:
        quiet = bridge.client(_PID_A, "token-for-A")
        quiet.connect()
        streaming = bridge.client(_PID_B, "token-for-B")
        streaming.connect()

        registry = _registry(bridge)
        streaming_connection = registry.get(str(streaming.session_id))
        assert streaming_connection is not None

        with streaming.sse_stream() as stream:
            assert stream.status_code == 200
            clock.advance(60.0)  # both connections are now "past" the timeout
            time.sleep(0.3)  # several sweep ticks on the wall clock
            # the open stream marks its connection live — only the quiet one dies
            assert registry.get(str(quiet.session_id)) is None
            assert registry.get(str(streaming.session_id)) is not None
            assert streaming.health().json()["connections"] == 1

        wait_for(
            lambda: registry.get(str(streaming.session_id)) is None,
            message="stream-dropped connection swept after the idle interval",
        )
        ends = [c for c in fake.calls if c.path.endswith("/end")]
        assert len(ends) >= 2  # every swept connection ended its session
        events = [r.get("event") for r in bridge.log_records()]
        assert "idle_sweep" in events
        reasons = [
            r.get("reason") for r in bridge.log_records() if r.get("event") == "connection_closed"
        ]
        assert "idle_timeout" in reasons


def test_connection_lifecycle_failed_handshake_leaves_no_state() -> None:
    """A non-initialize opening POST is refused and fully cleaned up."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        response = client.raw_post(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response.status_code >= 400
        # The transport may *echo* the id it minted on the refused opening —
        # what matters is that no connection is ever filed under it.
        minted = response.headers.get("mcp-session-id")
        registry = _registry(bridge)
        if minted is not None:
            assert registry.get(minted) is None
            reuse = client.raw_post(
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                session_id=minted,
            )
            assert reuse.status_code == 404
            assert reuse.json()["error"]["details"]["reason"] == "unknown_session"
        wait_for(
            lambda: registry.admitted_or_reserved == 0,
            message="reservation released after the failed handshake",
        )
        assert registry.size == 0
        # The reservation drops before finalize() runs (app.py ordering), and
        # finalize's best-effort backend /end is async relative to the
        # response — wait for it the same way every other teardown test does.
        wait_for(
            lambda: any(call.path.endswith("/end") for call in fake.calls),
            message="the half-open backend session must be ended",
        )
        # capacity was never leaked: a real connection still binds
        client.connect()
        assert client.health().json()["connections"] == 1


def test_connection_lifecycle_client_delete_closes_cleanly() -> None:
    """Client exit path: manager stopped, session ended, registry empty."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()
        registry = _registry(bridge)
        connection = registry.get(str(client.session_id))
        assert connection is not None

        assert client.delete_session() in (200, 202, 204)
        wait_for(
            lambda: registry.get(str(client.session_id)) is None,
            message="DELETE finalizes the connection",
        )
        wait_for(
            lambda: connection.state is ConnectionState.CLOSED,
            message="state machine reaches closed",
        )
        ends = [c for c in fake.calls if c.path.endswith("/end")]
        assert ends, "teardown ends the backend session (Section 10.10)"
        reasons = [
            r.get("reason") for r in bridge.log_records() if r.get("event") == "connection_closed"
        ]
        assert reasons == ["client_terminated"]


def test_connection_lifecycle_shutdown_finalizes_open_connections() -> None:
    """Server exit path: every connection ends its session on shutdown."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()  # left open on purpose — shutdown must clean it up
        assert bridge.stop() == 0
    records = bridge.log_records()
    closed = [r for r in records if r.get("event") == "connection_closed"]
    assert closed and closed[0]["reason"] == "server_shutdown"
    ends = [c for c in fake.calls if c.path.endswith("/end")]
    assert ends, "shutdown ends the open backend session best-effort"


def test_connection_lifecycle_backend_down_teardown_never_blocks() -> None:
    """Teardown with an unreachable backend logs and completes anyway."""
    fake = happy_backend((_PID_A, "Tea"))
    flaky = FlakyBackend(fake)
    with running_bridge(http_settings(), send=flaky.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()
        registry = _registry(bridge)
        flaky.down = True  # backend disappears before teardown
        started = time.monotonic()
        assert client.delete_session() in (200, 202, 204)
        wait_for(
            lambda: registry.get(str(client.session_id)) is None,
            timeout=8.0,
            message="teardown completes despite the dead backend",
        )
        assert time.monotonic() - started < 8.0
        wait_for(
            lambda: "session_end_failed" in [r.get("event") for r in bridge.log_records()],
            timeout=8.0,
            message="teardown logs session_end_failed despite the dead backend (10.10)",
        )
        assert bridge.stop() == 0  # and shutdown stays clean


def test_connection_lifecycle_backend_outage_yields_retryable_tool_error() -> None:
    """NFR-04 / Section 10.10: an outage surfaces a retryable tool error,
    translated exactly like the MT-2.3-02 stdio path — no hang, no crash."""
    fake = happy_backend((_PID_A, "Tea"))
    flaky = FlakyBackend(fake)
    with running_bridge(http_settings(), send=flaky.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()
        flaky.down = True
        error = client.call_error_payload("get_available_tasks", {"limit": 5})
        assert error["code"] == "SERVER_ERROR"
        assert error["retryable"] is True
        assert error["hint"] and error["next_action"]
        # the connection survives the outage — reconnect-friendliness (NFR-04)
        assert client.health().json()["connections"] == 1
        flaky.down = False
        listing = client.call_payload("get_available_tasks", {"limit": 5})
        assert listing["count"] == 0


def test_connection_lifecycle_reconnect_gets_a_fresh_binding() -> None:
    """After a drop (DELETE), a fresh initialize binds a new connection."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()
        first_session = str(client.session_id)
        assert client.delete_session() in (200, 202, 204)
        wait_for(
            lambda: _registry(bridge).get(first_session) is None,
            message="first connection gone",
        )
        client.connect()  # NFR-04: reconnection just works
        assert str(client.session_id) != first_session
        connection = _registry(bridge).get(str(client.session_id))
        assert connection is not None
        assert connection.state is ConnectionState.ACTIVE
        assert client.call_payload("get_project_context")["project_id"] == _PID_A
