"""MT-2.1-04 — entry points: shared construction, mode precedence, stub boundaries.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.1-bridge-skeleton/
MT-2.1-04-entry-point-stubs.md (parent plan Sections 10.2, 10.11, 19.1;
FR-MCP-01; Section 6.6 MCP SDK).
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import orchestrator_bridge.config as config_module
from orchestrator_bridge.config import RunMode, Settings, load_settings
from orchestrator_bridge.entrypoints import (
    EXIT_CONFIG_ERROR,
    EXIT_NOT_IMPLEMENTED,
    EXIT_OK,
    cli,
    resolve_mode,
)
from orchestrator_bridge.entrypoints import executor as executor_module
from orchestrator_bridge.entrypoints import http as http_module
from orchestrator_bridge.entrypoints import stdio as stdio_module
from orchestrator_bridge.logging import configure_logging
from orchestrator_bridge.server import create_server

BRIDGE_ROOT = Path(__file__).resolve().parent.parent
_ABSENT_CONFIG = Path("no-such-bridge-config.toml")


@pytest.fixture(autouse=True)
def _isolated_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cli() must never read a real user config from this machine."""
    monkeypatch.setattr(config_module, "default_user_config_path", lambda: tmp_path / "bridge.toml")


def _settings(env: dict[str, str] | None = None) -> Settings:
    return load_settings(env=env or {}, config_path=_ABSENT_CONFIG)


def _stream_records(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


class _FakeServer:
    """Stands in for MCPServer so stdio.run() can be exercised without blocking."""

    def __init__(self) -> None:
        self.transport: str | None = None

    def run(self, transport: str = "stdio") -> None:
        self.transport = transport


# --- shared server construction -----------------------------------------------


def test_create_server_advertises_empty_tool_set() -> None:
    server = create_server(_settings())
    tools = asyncio.run(server.list_tools())
    assert tools == []  # WP-2.1 acceptance, Section 19.1 (FR-MCP-01)


# --- mode selection precedence -------------------------------------------------


def test_default_mode_is_stdio() -> None:
    settings = _settings()
    assert settings.mode is RunMode.STDIO
    assert resolve_mode(None, settings) is RunMode.STDIO


def test_configured_mode_key_overrides_default() -> None:
    settings = _settings({"ORCHESTRATOR_BRIDGE_MODE": "http"})
    assert resolve_mode(None, settings) is RunMode.HTTP


def test_explicit_invocation_beats_configured_mode() -> None:
    settings = _settings({"ORCHESTRATOR_BRIDGE_MODE": "http"})
    assert resolve_mode(RunMode.STDIO, settings) is RunMode.STDIO
    assert resolve_mode(RunMode.MERGE_EXECUTOR, settings) is RunMode.MERGE_EXECUTOR


def test_cli_default_dispatches_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[Settings] = []

    def _fake_run(settings: Settings) -> int:
        seen.append(settings)
        return EXIT_OK

    monkeypatch.setattr(stdio_module, "run", _fake_run)
    assert cli([]) == EXIT_OK
    assert len(seen) == 1 and seen[0].mode is RunMode.STDIO


def test_mode_flag_beats_config_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_BRIDGE_MODE", "stdio")
    code = cli(["--mode", "http"])
    assert code == EXIT_NOT_IMPLEMENTED  # would be 0/stdio without the flag


def test_configured_mode_key_drives_generic_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_BRIDGE_MODE", "http")
    assert cli([]) == EXIT_NOT_IMPLEMENTED


def test_mode_script_is_explicit_over_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ORCHESTRATOR_BRIDGE_MODE", "http")
    # console scripts parse the process argv — stand in for pytest's own argv
    monkeypatch.setattr(sys, "argv", ["orchestrator-bridge-stdio"])
    called: list[Settings] = []

    def _fake_run(settings: Settings) -> int:
        called.append(settings)
        return EXIT_OK

    monkeypatch.setattr(stdio_module, "run", _fake_run)
    assert stdio_module.main() == EXIT_OK
    assert called, "explicit stdio script must dispatch stdio, not the configured http"


# --- stub boundaries ------------------------------------------------------------


def test_http_stub_fails_fast_with_wp_reference(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli(["--mode", "http"])
    captured = capsys.readouterr()
    assert code == EXIT_NOT_IMPLEMENTED == 2
    assert "not yet implemented" in captured.err
    assert "WP-2.9" in captured.err
    assert "Traceback" not in captured.err
    # the resolved mode (flag) also picks the log stream: http diagnostics on stdout
    assert '"event": "mode_not_implemented"' in captured.out


def test_http_stub_never_builds_a_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def _boom(settings: Settings) -> object:
        raise AssertionError("the HTTP stub must not build a partial server")

    monkeypatch.setattr("orchestrator_bridge.server.create_server", _boom)
    assert http_module.run(_settings({"ORCHESTRATOR_BRIDGE_MODE": "http"})) == EXIT_NOT_IMPLEMENTED
    assert "WP-2.9" in capsys.readouterr().err


def test_executor_callable_raises_wp_boundary() -> None:
    with pytest.raises(NotImplementedError, match="WP-3.7"):
        executor_module.run(_settings())


def test_executor_script_fails_fast_with_wp_reference(capsys: pytest.CaptureFixture[str]) -> None:
    code = cli(["--mode", "merge-executor"])
    captured = capsys.readouterr()
    assert code == EXIT_NOT_IMPLEMENTED
    assert "not yet implemented" in captured.err
    assert "WP-3.7" in captured.err


def test_config_error_fails_fast_with_clear_message(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("ORCHESTRATOR_BRIDGE_MODE", "serial")
    code = cli([])
    captured = capsys.readouterr()
    assert code == EXIT_CONFIG_ERROR == 1
    assert "configuration error" in captured.err and "mode" in captured.err
    assert "Traceback" not in captured.err


# --- startup/shutdown structured logs from the layered loader -------------------


def test_stdio_run_emits_startup_and_shutdown_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stream = io.StringIO()
    settings = _settings()  # defaults from the layered loader
    configure_logging(settings, stream=stream)
    fake = _FakeServer()
    monkeypatch.setattr(stdio_module, "create_server", lambda _settings_arg: fake)
    assert stdio_module.run(settings) == EXIT_OK
    assert fake.transport == "stdio"
    events = _stream_records(stream)
    assert [record["event"] for record in events] == ["startup", "shutdown"]
    assert all(record["component"] == "bridge.stdio" for record in events)


def test_stdio_run_respects_configured_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = io.StringIO()
    settings = _settings({"ORCHESTRATOR_LOG_LEVEL": "ERROR"})
    configure_logging(settings, stream=stream)
    monkeypatch.setattr(stdio_module, "create_server", lambda _settings_arg: _FakeServer())
    assert stdio_module.run(settings) == EXIT_OK
    assert stream.getvalue() == ""  # INFO startup suppressed by config, not inline


# --- WP-2.1 acceptance: stdio handshake with an empty tool set -------------------


def test_stdio_process_handshake_lists_empty_tools() -> None:
    """JSON-RPC handshake over a real stdio process — the inspector-equivalent proof.

    Every stdout line must parse as a JSON-RPC message (framing intact) and the
    bridge's own diagnostics must appear as JSON lines on stderr only.
    """
    env = {key: value for key, value in os.environ.items() if not key.startswith("ORCHESTRATOR_")}
    messages = "\n".join(
        [
            json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "wp-2-1-test", "version": "1.0"},
                    },
                }
            ),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator_bridge"],
        input=messages + "\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env=env,
        cwd=BRIDGE_ROOT,
        check=False,
    )
    assert proc.returncode == 0, f"clean shutdown failed: {proc.stderr}"

    stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    rpc_messages = [json.loads(line) for line in stdout_lines]
    assert all(message.get("jsonrpc") == "2.0" for message in rpc_messages)

    init_response = next(message for message in rpc_messages if message.get("id") == 1)
    assert init_response["result"]["serverInfo"]["name"] == "orchestrator-bridge"

    tools_response = next(message for message in rpc_messages if message.get("id") == 2)
    assert tools_response["result"]["tools"] == []

    diagnostics = [
        json.loads(line)
        for line in proc.stderr.splitlines()
        if line.startswith("{")  # bridge JSON lines (SDK-internal lines filtered)
    ]
    startup = [record for record in diagnostics if record.get("event") == "startup"]
    assert startup and startup[0]["component"] == "bridge.stdio"
