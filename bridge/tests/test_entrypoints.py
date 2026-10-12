"""MT-2.1-04 — entry points: shared construction, mode precedence, stub boundaries.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.1-bridge-skeleton/
MT-2.1-04-entry-point-stubs.md (parent plan Sections 10.2, 10.11, 19.1;
FR-MCP-01; Section 6.6 MCP SDK).

WP-2.2 note: ``stdio.run`` now binds first (Section 10.3 steps 1–3), so every
startup test supplies a minimal temp manifest + token — the WP-2.1 handshake
contract (empty tool set, clean shutdown) is unchanged, and a missing manifest
fails fast per MT-2.2-01 (asserted below).
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
import threading
from collections.abc import Callable
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
_FIXTURE_TOKEN = "fixture-token-not-a-real-secret"


@pytest.fixture(autouse=True)
def _isolated_user_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """cli() must never read a real user config from this machine."""
    monkeypatch.setattr(config_module, "default_user_config_path", lambda: tmp_path / "bridge.toml")


def _settings(env: dict[str, str] | None = None) -> Settings:
    return load_settings(env=env or {}, config_path=_ABSENT_CONFIG)


def _bound_settings(
    tmp_path: Path, write_manifest: Callable[..., Path], env: dict[str, str] | None = None
) -> Settings:
    """Settings that satisfy Section 10.3 steps 1–3 (WP-2.2 startup binding).

    The manifest lives in *tmp_path* and is reached through the MT-2.1-02
    test-only override — no repo state and no real user config involved.
    """
    manifest = write_manifest(tmp_path / "bound-repo")
    bound_env = {
        "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": str(manifest),
        "ORCHESTRATOR_AGENT_TOKEN": _FIXTURE_TOKEN,
        **(env or {}),
    }
    return load_settings(env=bound_env, config_path=_ABSENT_CONFIG)


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
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    stream = io.StringIO()
    settings = _bound_settings(tmp_path, write_manifest)  # WP-2.2: bind before serving
    configure_logging(settings, stream=stream)
    fake = _FakeServer()
    monkeypatch.setattr(stdio_module, "create_server", lambda _settings_arg: fake)
    assert stdio_module.run(settings) == EXIT_OK
    assert fake.transport == "stdio"
    events = _stream_records(stream)
    assert [record["event"] for record in events] == ["startup", "shutdown"]
    assert all(record["component"] == "bridge.stdio" for record in events)
    assert events[0]["project_id"] == "PID00007"  # bound context reaches the startup log


def test_stdio_run_respects_configured_log_level(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    stream = io.StringIO()
    settings = _bound_settings(tmp_path, write_manifest, env={"ORCHESTRATOR_LOG_LEVEL": "ERROR"})
    configure_logging(settings, stream=stream)
    monkeypatch.setattr(stdio_module, "create_server", lambda _settings_arg: _FakeServer())
    assert stdio_module.run(settings) == EXIT_OK
    assert stream.getvalue() == ""  # INFO startup suppressed by config, not inline


def test_stdio_run_fails_fast_without_manifest(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """MT-2.2-01: no manifest → exit 1, ``binding_failed`` event, one scrubbed
    stderr line naming ``orchestrator init``, no server ever built."""
    # Own Git ceiling in tmp so the walk cannot reach this machine's real repo.
    repo = tmp_path / "unbound"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.chdir(repo)
    settings = _settings()  # no manifest override, no token
    stream = io.StringIO()
    configure_logging(settings, stream=stream)

    def _boom(_settings_arg: Settings) -> object:
        raise AssertionError("the server must not be built for an unbound session")

    monkeypatch.setattr(stdio_module, "create_server", _boom)
    assert stdio_module.run(settings) == EXIT_CONFIG_ERROR

    records = _stream_records(stream)
    failures = [record for record in records if record.get("event") == "binding_failed"]
    assert failures and failures[0]["error_type"] == "ManifestNotFoundError"
    captured = capsys.readouterr()
    assert "orchestrator init" in captured.err
    assert "bridge startup error:" in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""  # nothing can corrupt the JSON-RPC stream


# --- WP-2.1 acceptance: stdio handshake with an empty tool set -------------------


def test_stdio_process_handshake_lists_empty_tools(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    """JSON-RPC handshake over a real stdio process — the inspector-equivalent proof.

    Every stdout line must parse as a JSON-RPC message (framing intact) and the
    bridge's own diagnostics must appear as JSON lines on stderr only. Startup
    binds through a temp manifest + token first (WP-2.2 Section 10.3); the
    WP-2.1 contract — empty tool set, clean shutdown — is unchanged.
    """
    manifest = write_manifest(tmp_path / "bound-repo")
    env = {key: value for key, value in os.environ.items() if not key.startswith("ORCHESTRATOR_")}
    env["ORCHESTRATOR_BRIDGE_MANIFEST_PATH"] = str(manifest)
    env["ORCHESTRATOR_AGENT_TOKEN"] = _FIXTURE_TOKEN
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
    proc = subprocess.Popen(
        [sys.executable, "-m", "orchestrator_bridge"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=BRIDGE_ROOT,
    )
    stdin = proc.stdin
    stdout = proc.stdout
    stderr_pipe = proc.stderr
    assert stdin is not None and stdout is not None and stderr_pipe is not None
    # EOF (stdin close) is the SDK's shutdown trigger, so closing it while
    # tools/list is still in flight makes the response load-dependently
    # cancellable (observed ~1-in-5 full-file flake). Keep stdin open until the
    # response is observed, then EOF to exercise the clean-shutdown path; the
    # watchdog keeps a hung server from hanging the test.
    watchdog = threading.Timer(45.0, proc.kill)
    watchdog.start()
    try:
        stdin.write(messages + "\n")
        stdin.flush()
        rpc_lines: list[str] = []
        saw_tools = False
        for line in stdout:
            if not line.strip():
                continue
            rpc_lines.append(line)
            if json.loads(line).get("id") == 2:
                saw_tools = True
                break
        stdin.close()
    except BaseException:
        proc.kill()
        raise
    finally:
        watchdog.cancel()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=15)
    tail = stdout.read() or ""
    stderr = stderr_pipe.read() or ""
    if not saw_tools:
        pytest.fail(
            f"tools/list never answered (exit={proc.returncode}); "
            f"stdout={rpc_lines + tail.splitlines()!r}; stderr={stderr}"
        )
    assert proc.returncode == 0, f"clean shutdown failed: {stderr}"

    stdout_lines = [line for line in (*rpc_lines, *tail.splitlines()) if line.strip()]
    rpc_messages = [json.loads(line) for line in stdout_lines]
    assert all(message.get("jsonrpc") == "2.0" for message in rpc_messages)

    init_response = next(message for message in rpc_messages if message.get("id") == 1)
    assert init_response["result"]["serverInfo"]["name"] == "orchestrator-bridge"

    tools_response = next(message for message in rpc_messages if message.get("id") == 2)
    assert tools_response["result"]["tools"] == []

    diagnostics = [
        json.loads(line)
        for line in stderr.splitlines()
        if line.startswith("{")  # bridge JSON lines (SDK-internal lines filtered)
    ]
    startup = [record for record in diagnostics if record.get("event") == "startup"]
    assert startup and startup[0]["component"] == "bridge.stdio"


def test_stdio_process_fails_fast_without_manifest(tmp_path: Path) -> None:
    """Real-process fail-fast (MT-2.2-01): exit 1, one stderr line naming
    ``orchestrator init``, a ``binding_failed`` JSON record, empty stdout."""
    repo = tmp_path / "unbound"
    (repo / ".git").mkdir(parents=True)  # own ceiling: never reaches this repo
    env = {key: value for key, value in os.environ.items() if not key.startswith("ORCHESTRATOR_")}
    proc = subprocess.run(
        [sys.executable, "-m", "orchestrator_bridge"],
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env=env,
        cwd=repo,
        check=False,
    )
    assert proc.returncode == EXIT_CONFIG_ERROR == 1
    assert "orchestrator init" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert proc.stdout == ""  # the JSON-RPC stream stays clean

    diagnostics = [json.loads(line) for line in proc.stderr.splitlines() if line.startswith("{")]
    failures = [record for record in diagnostics if record.get("event") == "binding_failed"]
    assert failures and failures[0]["error_type"] == "ManifestNotFoundError"
