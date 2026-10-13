"""MT-2.9-01 — the local HTTP/SSE server mode (Sections 10.1, 10.2, 9.10,
10.10; FR-MCP-01).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.9-http-transport/
MT-2.9-01-http-sse-server.md. Every test here drives the **production entry**
(``entrypoints.http.run``) on a loopback port through ``http_harness``: real
sockets, real uvicorn, real MCP streamable-HTTP framing — only the
bridge→backend leg is the WP-2.3 send seam.
"""

from __future__ import annotations

import socket
import threading
from pathlib import Path

import pytest

from orchestrator_bridge.config import ConfigError, load_settings
from orchestrator_bridge.entrypoints import EXIT_CONFIG_ERROR, EXIT_OK
from orchestrator_bridge.entrypoints import http as http_module
from orchestrator_bridge.tools.schemas import CORE_TOOL_NAMES, TOOL_SPECS
from tests.conftest import FakeBackend
from tests.http_harness import free_port, happy_backend, http_settings, running_bridge

BRIDGE_ROOT = Path(__file__).resolve().parent.parent
_ABSENT_CONFIG = Path("no-such-bridge-config.toml")


def backend_for(project_id: str, name: str) -> FakeBackend:
    """The Section 10.3 happy path for one project at the send seam."""
    return happy_backend((project_id, name))


# --- MT-2.9-01 acceptance ------------------------------------------------------


def test_http_server_health_endpoint_reports_liveness() -> None:
    """``GET /health`` answers 200 with mode and connection counters."""
    settings = http_settings()
    with running_bridge(settings, send=backend_for("PID00007", "Tea").send) as bridge:
        response = bridge.client("PID00007", "tok").health()
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["mode"] == "http"
        assert payload["connections"] == 0
        assert payload["max_connections"] == settings.http_max_connections


def test_http_server_initialize_tool_call_and_clean_shutdown() -> None:
    """The MT command: handshake + tool dispatch over HTTP/SSE, clean exit.

    One codebase, two transports (FR-MCP-01): the same ``create_server`` tool
    set, declared schemas and Section 10.6 initialize instructions that the
    stdio wire serves appear here, over real HTTP with SSE framing.
    """
    fake = backend_for("PID00007", "Tea Factory ERP")
    settings = http_settings()
    with running_bridge(settings, send=fake.send) as bridge:
        client = bridge.client("PID00007", "project-token-0001")
        init = client.connect()
        assert init["serverInfo"]["name"] == "orchestrator-bridge"
        # Section 10.6 rules arrive on connect, exactly as over stdio (G-08).
        instructions = init.get("instructions")
        assert isinstance(instructions, str)
        assert "8. Provide a clear execution summary." in instructions
        assert "Rules for Tea Factory ERP." in instructions

        tools = client.tools_list()
        assert [tool["name"] for tool in tools] == list(CORE_TOOL_NAMES)
        by_name = {tool["name"]: tool for tool in tools}
        for spec in TOOL_SPECS:
            assert by_name[spec.name]["inputSchema"] == dict(spec.input_schema)

        orientation = client.call_payload("get_project_context")
        assert orientation["project_id"] == "PID00007"
        assert orientation["project_name"] == "Tea Factory ERP"

        health = client.health().json()
        assert health["connections"] == 1

        # Section 10.2: the backend session was opened with the *presented*
        # token, transport "http" (the run mode's wire value).
        (opened,) = fake.calls_to("POST", "/api/v1/agent-sessions")
        assert opened.body["transport"] == "http"
        assert opened.headers["Authorization"].endswith("project-token-0001")

        code = bridge.stop()
        assert code == EXIT_OK

    records = bridge.log_records()
    startup = [r for r in records if r.get("event") == "startup"]
    assert startup, "one clean startup line with the bound address is required"
    assert startup[0]["mode"] == "http"
    assert startup[0]["port"] == settings.http_port
    assert f"http://127.0.0.1:{settings.http_port}" in startup[0]["message"]
    assert [r for r in records if r.get("event") == "shutdown"], "clean shutdown line"
    # The DELETE above finalized the connection: session end ran best-effort.
    ends = [c for c in fake.calls if c.path.endswith("/end")]
    assert ends, "client-terminated connection must end its backend session"


def test_http_server_sse_get_stream_establishes() -> None:
    """The server->client leg of the HTTP+SSE transport (Section 10.2)."""
    fake = backend_for("PID00007", "Tea")
    with running_bridge(http_settings(), send=fake.send) as bridge:
        client = bridge.client("PID00007", "tok")
        client.connect()
        with client.sse_stream() as stream:
            assert stream.status_code == 200
            assert "text/event-stream" in stream.headers["content-type"]
        # The dropped stream does not close the connection (only DELETE, the
        # idle timeout or shutdown do) — the session is still established.
        health = client.health().json()
        assert health["connections"] == 1


def test_http_server_listen_defaults_are_documented() -> None:
    """Section 9.10: documented defaults, no environment-specific values."""
    settings = load_settings(env={}, config_path=_ABSENT_CONFIG)
    assert settings.http_host == "127.0.0.1"  # loopback-only default (12.4)
    assert settings.http_port == 8765  # never shadows the backend's 8000
    assert settings.http_max_connections == 16
    assert settings.http_idle_timeout_seconds == 900.0

    example = (BRIDGE_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "ORCHESTRATOR_BRIDGE_HTTP_HOST=127.0.0.1" in example
    assert "ORCHESTRATOR_BRIDGE_HTTP_PORT=8765" in example
    assert "ORCHESTRATOR_BRIDGE_HTTP_MAX_CONNECTIONS=16" in example
    assert "ORCHESTRATOR_BRIDGE_HTTP_IDLE_TIMEOUT_SECONDS=900" in example

    invalid = {"ORCHESTRATOR_BRIDGE_HTTP_PORT": "70000"}
    with pytest.raises(ConfigError, match="http_port"):
        load_settings(env=invalid, config_path=_ABSENT_CONFIG)


def test_http_server_bind_failure_fails_fast_without_traceback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An occupied address exits 1 with one line — never a hang or traceback."""
    port = free_port()
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", port))
    blocker.listen(1)
    result: dict[str, int] = {}

    def _serve() -> None:
        result["code"] = http_module.run(http_settings(http_port=port))

    thread = threading.Thread(target=_serve, daemon=True)
    try:
        thread.start()
        thread.join(timeout=15)
        assert not thread.is_alive(), "bind failure must return promptly"
    finally:
        blocker.close()
    assert result.get("code") == EXIT_CONFIG_ERROR
    captured = capsys.readouterr()
    assert "bridge startup error" in captured.err
    assert "Traceback" not in captured.err
