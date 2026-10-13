"""MT-2.12-04 — per-client MCP registration snippets: coverage, secret-free, pointers.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.12-init-command/
MT-2.12-04-client-snippets.md (Section 10.9 matrix; FR-MCP-01; 20.4 item 3).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from orchestrator_bridge.init.snippets import bridge_command, render_snippets
from orchestrator_bridge.rules import CLIENT_MATRIX
from tests.conftest import FIXTURE_TOKEN

CONFIG_PATH = Path("C:/Users/example/AppData/Roaming/orchestrator/bridge.toml")
COMMAND = ["C:/venv/Scripts/orchestrator-bridge-stdio.exe"]
MODULE_COMMAND = [sys.executable, "-m", "orchestrator_bridge", "--mode", "stdio"]


def _render(command: list[str] | None = None) -> str:
    return render_snippets(config_path=CONFIG_PATH, command=command or COMMAND)


def test_every_section_10_9_matrix_client_gets_a_block() -> None:
    text = _render()
    for label, _key, _text_only in CLIENT_MATRIX:
        assert f"### {label}" in text


def test_every_snippet_launches_the_stdio_entry() -> None:
    text = _render()
    # Every block references the installed stdio launcher (FR-MCP-01: one server).
    assert text.count(COMMAND[0]) >= len(CLIENT_MATRIX)
    assert "orchestrator-bridge-stdio" in text


def test_no_snippet_carries_a_token() -> None:
    text = _render()
    assert FIXTURE_TOKEN not in text
    assert "agent_token" not in text  # no config key pasted into client files


def test_snippets_reference_the_user_level_config_source() -> None:
    text = _render()
    assert str(CONFIG_PATH) in text
    assert "ORCHESTRATOR_AGENT_TOKEN" in text
    assert "never" in text.lower()  # "never from this snippet" posture


def test_every_snippet_points_at_the_self_test_and_inspector() -> None:
    text = _render()
    assert text.count("orchestrator init --self-test") >= len(CLIENT_MATRIX)
    assert "MCP inspector" in text
    assert "@modelcontextprotocol/inspector" in text


def test_aider_gets_a_wrapper_command_line_not_a_json_key() -> None:
    text = _render()
    aider_block = text.split("### Aider")[1].split("### ")[0]
    assert "mcpServers" not in aider_block  # no invented config key
    assert COMMAND[0] in aider_block
    assert "wrapper" in aider_block.lower()


def test_machine_paths_are_marked_ephemeral() -> None:
    text = _render()
    assert "never commit" in text


def test_bridge_command_prefers_the_console_script_on_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "orchestrator_bridge.init.snippets.shutil.which",
        lambda name: "C:/venv/Scripts/orchestrator-bridge-stdio.exe",
    )
    assert bridge_command() == ["C:/venv/Scripts/orchestrator-bridge-stdio.exe"]


def test_bridge_command_falls_back_to_the_module_form(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("orchestrator_bridge.init.snippets.shutil.which", lambda name: None)
    command = bridge_command()
    assert command[0] == sys.executable
    assert command[1:] == ["-m", "orchestrator_bridge", "--mode", "stdio"]
    # The fallback renders into every client block too.
    text = render_snippets(config_path=CONFIG_PATH, command=command)
    assert "-m orchestrator_bridge" in text


def test_generated_output_is_not_written_to_the_repo(tmp_path: Path) -> None:
    # Snippets are terminal output only (MT-2.12-04): rendering touches no files.
    before = sorted(path.name for path in tmp_path.iterdir())
    render_snippets(config_path=tmp_path / "bridge.toml", command=COMMAND)
    assert sorted(path.name for path in tmp_path.iterdir()) == before
