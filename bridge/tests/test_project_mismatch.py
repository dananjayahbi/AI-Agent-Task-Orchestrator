"""MT-2.2-05 — project-mismatch abort with a clear startup error.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.2-manifest-binding/
MT-2.2-05-project-mismatch-abort.md (parent plan Sections 10.3 binding rule,
12.2/12.3, 17; FR-SEC-01, FR-MCP-02, FR-SEC-04).

The authoritative detection is server-side: the backend answers
``AUTH_FORBIDDEN_PROJECT`` to the session open and the bridge maps that to
one remedy-bearing startup abort. The bridge never decodes the token to
determine its project (opaque bearer, Section 12.2); the local pre-check
option depends on MT-2.12-02 metadata that does not exist yet (recorded in
the WP changelog).
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from orchestrator_bridge.config import load_settings
from orchestrator_bridge.entrypoints import EXIT_CONFIG_ERROR
from orchestrator_bridge.entrypoints import stdio as stdio_module
from orchestrator_bridge.errors import ProjectMismatchError, SessionOpenError
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.session import open_session
from orchestrator_bridge.transport import ApiClient
from tests.conftest import (
    FIXTURE_TOKEN,
    FakeBackend,
    FakeRunServer,
    StubHttpBackend,
    build_binding,
    build_settings,
    envelope_wire,
)

_ABSENT_CONFIG = Path("no-such-bridge-config.toml")

_FORBIDDEN = envelope_wire(
    403,
    "AUTH_FORBIDDEN_PROJECT",
    "Token is scoped to 'PID00001', not 'PID00007'.",
)


def _mismatch_backend() -> FakeBackend:
    fake = FakeBackend()
    fake.route("POST", "/api/v1/agent-sessions", 403, json.loads(_FORBIDDEN.body))
    return fake


def _mismatch_client() -> ApiClient:
    return ApiClient.for_binding(build_binding(), build_settings(), send=_mismatch_backend().send)


def test_backend_403_at_open_becomes_project_mismatch_error() -> None:
    with pytest.raises(ProjectMismatchError) as excinfo:
        open_session(build_binding(), build_settings(), client=_mismatch_client())
    error = excinfo.value
    # One class, one vocabulary: mismatch is the failure half of session open.
    assert isinstance(error, SessionOpenError)
    assert error.canonical_code == "AUTH_FORBIDDEN_PROJECT"


def test_mismatch_message_names_project_code_and_remedies() -> None:
    with pytest.raises(ProjectMismatchError) as excinfo:
        open_session(build_binding(), build_settings(), client=_mismatch_client())
    message = str(excinfo.value)
    assert "PID00007" in message  # the manifest's project (repo-visible)
    assert "AUTH_FORBIDDEN_PROJECT" in message  # the backend's canonical code
    assert "ORCHESTRATOR_AGENT_TOKEN" in message  # remedy 1: point config at the right token
    assert "orchestrator init" in message  # remedy 2: re-run init
    # never the token, and never a value derived from it (FR-SEC-04; §17).
    assert FIXTURE_TOKEN not in message


def test_matching_project_control_opens_normally() -> None:
    """No false abort: a token the backend accepts opens the session."""
    fake = FakeBackend()
    fake.route_fn(
        "POST",
        "/api/v1/agent-sessions",
        lambda body: (201, {"id": body["id"], "project_id": "PID00007"}),
    )
    fake.route(
        "GET",
        "/api/v1/projects/PID00007",
        200,
        {"id": "PID00007", "name": "Tea Factory ERP", "system_prompt_rules": ""},
    )
    fake.route("GET", "/api/v1/projects/PID00007/policy", 200, {"max_concurrent_tasks": 1})
    client = ApiClient.for_binding(build_binding(), build_settings(), send=fake.send)
    session = open_session(build_binding(), build_settings(), client=client)
    assert session.agent_session_id


def test_bridge_never_sends_token_derived_identity_claims() -> None:
    """Binding is one token ↔ one project; the open body carries no identity
    the bridge could spoof (ADR-004) — the mismatch check stays server-side."""
    fake = _mismatch_backend()
    client = ApiClient.for_binding(build_binding(), build_settings(), send=fake.send)
    with pytest.raises(ProjectMismatchError):
        open_session(build_binding(), build_settings(), client=client)
    (call,) = fake.calls_to("POST", "/api/v1/agent-sessions")
    assert set(call.body) == {"id", "client_name", "capability", "transport"}


# --- the entry-point abort path (MT-2.1-04 exit codes; MT-2.1-03 logging) -------


def test_stdio_entry_point_mismatch_aborts_nonzero_and_scrubbed(
    stub_http_backend: StubHttpBackend,
    stub_manifest_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 1, one scrubbed stderr line, a ProjectMismatchError log record,
    empty stdout — the abort never half-starts the MCP server."""
    stub_http_backend.responses[("POST", "/api/v1/agent-sessions")] = (
        403,
        json.loads(_FORBIDDEN.body),
    )
    settings = load_settings(env=stub_manifest_env, config_path=_ABSENT_CONFIG)
    stream = io.StringIO()
    configure_logging(settings, stream=stream)

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("the server must not be built for a mismatched session")

    monkeypatch.setattr(stdio_module, "create_server", _boom)
    assert stdio_module.run(settings) == EXIT_CONFIG_ERROR

    captured = capsys.readouterr()
    assert "bridge startup error:" in captured.err
    assert "PID00007" in captured.err
    assert "AUTH_FORBIDDEN_PROJECT" in captured.err
    assert "orchestrator init" in captured.err
    assert FIXTURE_TOKEN not in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""  # the JSON-RPC stream stays clean

    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    failures = [record for record in records if record.get("event") == "binding_failed"]
    assert failures and failures[0]["error_type"] == "ProjectMismatchError"


def test_stdio_entry_point_matching_control_serves_and_ends_session(
    stub_http_backend: StubHttpBackend,
    stub_manifest_env: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Control: with a matching token the bridge starts, and the clean
    shutdown path ends the session best-effort (MT-2.2-04 pairing)."""
    server = FakeRunServer()
    monkeypatch.setattr(stdio_module, "create_server", lambda _s, **_k: server)
    settings = load_settings(env=stub_manifest_env, config_path=_ABSENT_CONFIG)
    assert stdio_module.run(settings) == 0
    assert server.transport == "stdio"
    methods_paths = [(call.method, call.path) for call in stub_http_backend.requests]
    assert ("POST", "/api/v1/agent-sessions") in methods_paths
    assert any(path.endswith("/end") for _method, path in methods_paths)
