"""MT-2.9-02 — per-connection project binding from URL path and token
(parent plan Sections 10.2, 10.3 step 4; FR-MCP-06, FR-MCP-02).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.9-http-transport/
MT-2.9-02-connection-binding.md. The negatives go through **real HTTP** (raw
posts through ``http_harness``) so the exact status, catalog code, hint and
next action the client sees are asserted, together with the "no session
state" guarantee: a rejected connection leaves the registry empty and ends
any backend session it opened on the way.
"""

from __future__ import annotations

from typing import Any

from orchestrator_bridge.tools.schemas import TOOL_SPECS
from tests.http_harness import (
    _BEARER_SCHEME,
    McpHttpClient,
    RunningBridge,
    happy_backend,
    http_settings,
    running_bridge,
    service_envelope,
    wait_for,
)

_PID_A = "PID00007"
_PID_B = "PID00008"


def _init_payload(request_id: int = 1) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "wp-2-9-binding", "version": "1.0"},
        },
    }


def _error_of(response: Any) -> dict[str, Any]:
    assert response.status_code >= 400, response.status_code
    payload = response.json()
    error: dict[str, Any] = payload["error"]
    # Section 9.2: exactly the five published fields.
    assert set(error) == {"code", "message", "retryable", "details", "correlation_id"}
    return error


def _registry(bridge: RunningBridge) -> Any:
    return bridge.server.config.app.registry


# --- happy path ----------------------------------------------------------------


def test_connection_binding_valid_url_and_token_binds_session() -> None:
    """URL project + presented token open one bound backend session."""
    fake = happy_backend((_PID_A, "Tea Factory ERP"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "token-for-A")
        client.connect()
        assert client.health().json()["connections"] == 1
        (opened,) = fake.calls_to("POST", "/api/v1/agent-sessions")
        assert opened.headers["Authorization"].endswith("token-for-A")
        # Step 5 read the *URL's* project with that token — bound context.
        orientation = client.call_payload("get_project_context")
        assert orientation["project_name"] == "Tea Factory ERP"
        # Context fetched exactly once at open (MT-2.4-06 cache, per connection).
        reads = [c for c in fake.calls if c.path == f"/api/v1/projects/{_PID_A}"]
        assert len(reads) == 1


def test_connection_binding_no_tool_takes_a_project_id_over_http() -> None:
    """Binding is transport-level only: the advertised schemas stay clean."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        client.connect()
        tools = client.tools_list()
        for tool in tools:
            properties = tool["inputSchema"].get("properties", {})
            assert "project_id" not in properties, tool["name"]
        # identical to the declared contracts (one registry, Section 10.1)
        assert [t["name"] for t in tools] == [spec.name for spec in TOOL_SPECS]


# --- rejections (first barrier, locally, catalog codes only) -------------------


def test_connection_binding_malformed_project_id_rejected_before_backend() -> None:
    """A URL id outside ^PID[0-9]{5}$ never reaches a backend call."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        response = client.raw_post(_init_payload(), project_id="not-a-project")
        error = _error_of(response)
        assert response.status_code == 400
        assert error["code"] == "VALIDATION_ERROR"
        assert error["details"]["reason"] == "invalid_project_id"
        assert error["details"]["hint"] and error["details"]["next_action"]
        assert not fake.calls, "malformed URL must not touch the backend"
        assert client.health().json()["connections"] == 0


def test_connection_binding_missing_authorization_rejected() -> None:
    """No Authorization header -> AUTH_REQUIRED with a fix-oriented pair."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        response = client.raw_post(_init_payload(), omit_auth=True)
        error = _error_of(response)
        assert response.status_code == 401
        assert error["code"] == "AUTH_REQUIRED"
        assert "Authorization" in error["details"]["next_action"]
        assert not fake.calls
        assert client.health().json()["connections"] == 0


def test_connection_binding_wrong_scheme_and_unsafe_token_rejected() -> None:
    """Non-Bearer scheme and a whitespace-bearing token are both 401s."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "tok")
        wrong_scheme = client.raw_post(_init_payload(1), auth_header="Basic dXNlcg==")
        assert _error_of(wrong_scheme)["code"] == "AUTH_REQUIRED"
        unsafe = client.raw_post(
            _init_payload(2),
            token="has spaces inside",
        )
        assert _error_of(unsafe)["code"] == "AUTH_REQUIRED"
        assert not fake.calls


def test_connection_binding_token_of_other_project_rejected_no_session_state() -> None:
    """Backend 403 on the context read -> 403, and no session survives.

    The session opens (the backend resolves the token's project — ADR-004),
    the *URL's* project read then rejects: the opened session is ended
    best-effort, the response carries no ``Mcp-Session-Id``, and the
    registry stays empty (FR-MCP-06 second barrier, MT-2.9-02 "no session
    state").
    """
    fake = happy_backend()
    fake.route(
        "GET",
        f"/api/v1/projects/{_PID_A}",
        403,
        service_envelope("AUTH_FORBIDDEN_PROJECT", "token belongs to another project"),
    )
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "token-for-B")
        response = client.raw_post(_init_payload())
        error = _error_of(response)
        assert response.status_code == 403
        assert error["code"] == "AUTH_FORBIDDEN_PROJECT"
        assert error["details"]["hint"] and error["details"]["next_action"]
        assert _PID_A in error["details"]["next_action"]
        assert response.headers.get("mcp-session-id") is None
        assert client.health().json()["connections"] == 0
        ends = [c for c in fake.calls if c.path.endswith("/end")]
        assert ends, "the opened backend session must be ended on rejection"


def test_connection_binding_backend_rejected_credential_surfaces_auth_required() -> None:
    """A credential the backend refuses at the open -> AUTH_REQUIRED (401)."""
    fake = happy_backend()
    fake.route_fn(
        "POST",
        "/api/v1/agent-sessions",
        lambda _body: (401, service_envelope("AUTH_REQUIRED", "token revoked")),
    )
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "revoked-token")
        response = client.raw_post(_init_payload())
        error = _error_of(response)
        assert response.status_code == 401
        assert error["code"] == "AUTH_REQUIRED"
        assert error["details"]["next_action"]
        assert client.health().json()["connections"] == 0


def test_connection_binding_cross_project_url_rejected_locally() -> None:
    """Session id of project A under project B's URL -> refused locally.

    The FR-MCP-06 first barrier: no backend call for the requested project
    happens at all.
    """
    fake = happy_backend((_PID_A, "Tea"), (_PID_B, "Second"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "token-for-A")
        client.connect()
        calls_before = len(fake.calls)
        response = client.raw_post(
            {"jsonrpc": "2.0", "id": 9, "method": "tools/list", "params": {}},
            project_id=_PID_B,
        )
        error = _error_of(response)
        assert response.status_code == 403
        assert error["code"] == "AUTH_FORBIDDEN_PROJECT"
        assert error["details"]["reason"] == "cross_project_request"
        assert _PID_A in error["message"]
        assert len(fake.calls) == calls_before, "no backend call may serve the attempt"
        # the original connection is undisturbed
        assert client.call_payload("get_project_context")["project_id"] == _PID_A


def test_connection_binding_foreign_token_on_established_connection_rejected() -> None:
    """A known session id under a different token -> credential mismatch 403."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client(_PID_A, "token-for-A")
        client.connect()
        response = client.raw_post(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
            token="token-for-someone-else",
        )
        error = _error_of(response)
        assert response.status_code == 403
        assert error["code"] == "AUTH_FORBIDDEN_PROJECT"
        assert error["details"]["reason"] == "credential_mismatch"
        # and the rightful token still works
        assert client.health().json()["connections"] == 1
        client.tools_list()


# --- per-connection state objects (isolation precondition) ---------------------


def test_connection_binding_state_is_per_connection() -> None:
    """Two live connections hold independent state objects (MT test: two
    connections with distinct contexts not overlapping)."""
    fake = happy_backend((_PID_A, "Tea Factory ERP"), (_PID_B, "Second Project"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client_a = bridge.client(_PID_A, "token-for-A")
        client_b = bridge.client(_PID_B, "token-for-B")
        client_a.connect()
        client_b.connect()

        registry = _registry(bridge)
        conn_a = registry.get(str(client_a.session_id))
        conn_b = registry.get(str(client_b.session_id))
        assert conn_a is not None and conn_b is not None
        assert conn_a is not conn_b
        assert conn_a.runtime is not conn_b.runtime
        assert conn_a.session.agent_session_id != conn_b.session.agent_session_id
        assert conn_a.binding.project_id == _PID_A
        assert conn_b.binding.project_id == _PID_B
        assert conn_a.token != conn_b.token

        ctx_a = client_a.call_payload("get_project_context")
        ctx_b = client_b.call_payload("get_project_context")
        assert ctx_a["project_name"] == "Tea Factory ERP"
        assert ctx_b["project_name"] == "Second Project"
        assert conn_a.runtime.context is not conn_b.runtime.context
        # closing A leaves B fully functional and forgets only A
        assert client_a.delete_session() in (200, 202, 204)
        wait_for(
            lambda: registry.get(str(client_a.session_id)) is None,
            message="connection A finalized after its DELETE",
        )
        assert client_b.call_payload("get_project_context")["project_id"] == _PID_B
        assert client_b.health().json()["connections"] == 1


def test_connection_binding_registry_holds_bound_state_only_after_initialize() -> None:
    """A half-finished client (headers only) never files a connection."""
    fake = happy_backend((_PID_A, "Tea"))
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client: McpHttpClient = bridge.client(_PID_A, "tok")
        # wrong path shape: not even an endpoint
        stray = client._client.post(  # raw probe outside the MCP path
            f"{bridge.base_url}/projects/{_PID_A}/messages",
            json=_init_payload(),
            headers={"Authorization": f"{_BEARER_SCHEME} {client.token}"},
        )
        assert stray.status_code == 404
        assert stray.json()["error"]["code"] == "VALIDATION_ERROR"
        assert not fake.calls
        assert client.health().json()["connections"] == 0
