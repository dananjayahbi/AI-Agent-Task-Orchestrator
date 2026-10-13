"""MT-2.5-02 — the editable capability table (Sections 10.4 step 3, 10.9).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.5-attachment-tool/
MT-2.5-02-client-capability-table.md (ADR-006 honesty: every unverified
client ships ``unknown``; missing/malformed degrades to unknown).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator_bridge.capability_table import (
    CAPABILITY_TABLE_ENV,
    DEFAULT_CAPABILITY_TABLE_PATH,
    load_capability_table,
)


def test_shipped_table_exists_and_records_every_plan_client_as_unknown() -> None:
    table = load_capability_table()
    assert table.entries, "the shipped bridge/capability_table/clients.json must load"
    names = {name for entry in table.entries for name in entry.client_names}
    assert {
        "claude-code",
        "vscode-copilot-ide",
        "opencode",
        "aider",
        "deepseek-based-harness",
        "custom-agent",
    } <= names
    assert all(entry.capability == "unknown" for entry in table.entries)
    # Nothing may claim vision before WP-2.11 verifies it (ADR-006).
    assert table.lookup("claude-code") == "unknown"


def test_missing_file_degrades_to_an_empty_table(tmp_path: Path) -> None:
    table = load_capability_table(tmp_path / "absent.json")
    assert table.entries == ()
    assert table.lookup("anything") is None


def test_malformed_json_degrades_to_an_empty_table(tmp_path: Path) -> None:
    broken = tmp_path / "clients.json"
    broken.write_text("{not json", encoding="utf-8")
    assert load_capability_table(broken).entries == ()


def test_non_object_file_degrades_to_an_empty_table(tmp_path: Path) -> None:
    broken = tmp_path / "clients.json"
    broken.write_text(json.dumps(["claude-code"]), encoding="utf-8")
    assert load_capability_table(broken).entries == ()


def test_bad_entries_are_skipped_and_bad_capability_becomes_unknown(tmp_path: Path) -> None:
    path = tmp_path / "clients.json"
    path.write_text(
        json.dumps(
            {
                "clients": [
                    "not-an-object",
                    {"capability": "vision"},
                    {"client_names": ["mixed"], "capability": "superpower"},
                    {"client_names": ["good"], "capability": "vision"},
                ]
            }
        ),
        encoding="utf-8",
    )
    table = load_capability_table(path)
    assert [entry.client_names for entry in table.entries] == [("mixed",), ("good",)]
    assert table.lookup("mixed") == "unknown"
    assert table.lookup("good") == "vision"


def test_lookup_is_case_insensitive_and_version_windowed(tmp_path: Path) -> None:
    path = tmp_path / "clients.json"
    path.write_text(
        json.dumps(
            {
                "clients": [
                    {
                        "client_names": ["Clipper"],
                        "capability": "vision",
                        "min_version": "1.2.0",
                        "max_version": "2.0.0",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    table = load_capability_table(path)
    assert table.lookup("clipper", "1.5.0") == "vision"
    assert table.lookup("clipper", "1.10.0") == "vision"  # numeric, not lexicographic
    assert table.lookup("clipper", "2.1.0") is None  # above the window
    assert table.lookup("clipper") is None  # bounded entries need a version
    assert table.lookup("other", "1.5.0") is None


def test_first_matching_entry_wins(tmp_path: Path) -> None:
    path = tmp_path / "clients.json"
    path.write_text(
        json.dumps(
            {
                "clients": [
                    {"client_names": ["dup"], "capability": "text_only"},
                    {"client_names": ["dup"], "capability": "vision"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert load_capability_table(path).lookup("dup") == "text_only"


def test_env_override_selects_an_alternate_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alternate = tmp_path / "elsewhere.json"
    alternate.write_text(
        json.dumps({"clients": [{"client_names": ["env-client"], "capability": "vision"}]}),
        encoding="utf-8",
    )
    monkeypatch.setenv(CAPABILITY_TABLE_ENV, str(alternate))
    assert load_capability_table().lookup("env-client") == "vision"


def test_default_path_points_at_the_repo_table() -> None:
    assert DEFAULT_CAPABILITY_TABLE_PATH.name == "clients.json"
    assert DEFAULT_CAPABILITY_TABLE_PATH.parent.name == "capability_table"
    assert DEFAULT_CAPABILITY_TABLE_PATH.exists()
