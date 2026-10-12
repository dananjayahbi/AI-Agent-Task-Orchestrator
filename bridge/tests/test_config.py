"""MT-2.1-02 — configuration layering: precedence, validation, redaction, sources.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.1-bridge-skeleton/MT-2.1-02-config-layering.md
(parent plan Sections 10.1/10.3/10.11; FR-SEC-04; NFR-10).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.config import (
    DEFAULT_API_BASE_URL,
    ConfigError,
    RunMode,
    Settings,
    default_user_config_path,
    load_settings,
    validate_for_mode,
)

BRIDGE_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_TOKEN = "fixture-token-not-a-real-secret"


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "bridge.toml"
    path.write_text(content, encoding="utf-8")
    return path


# --- precedence: env > user file > defaults ----------------------------------


def test_file_absent_yields_defaults(tmp_path: Path) -> None:
    settings = load_settings(env={}, config_path=tmp_path / "absent.toml")
    assert settings.api_base_url == DEFAULT_API_BASE_URL
    assert settings.agent_token is None
    assert settings.manifest_path is None
    assert settings.log_level == "INFO"
    assert settings.log_format == "json"
    assert settings.mode is RunMode.STDIO
    assert settings.timeout_seconds == 30.0
    assert settings.merge_repo_paths == ()


def test_file_values_apply_when_env_absent(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'log_level = "debug"\nlog_format = "text"\nmode = "http"\n'
        'api_base_url = "https://backend.example/api/v1"\n'
        'manifest_path = "/tmp/manifest.json"\ntimeout_seconds = 5\n'
        'merge_repo_paths = ["/repo/a", "/repo/b"]\n'
        'agent_token = "' + FIXTURE_TOKEN + '"\n',
    )
    settings = load_settings(env={}, config_path=path)
    assert settings.log_level == "DEBUG"
    assert settings.log_format == "text"
    assert settings.mode is RunMode.HTTP
    assert settings.api_base_url == "https://backend.example/api/v1"
    assert settings.manifest_path == Path("/tmp/manifest.json")
    assert settings.timeout_seconds == 5.0
    assert settings.merge_repo_paths == ("/repo/a", "/repo/b")
    assert settings.agent_token == FIXTURE_TOKEN


def test_env_overrides_file_for_every_key(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        'log_level = "debug"\nlog_format = "text"\nmode = "http"\n'
        'api_base_url = "https://from-file.example/api/v1"\n'
        'manifest_path = "/from/file"\ntimeout_seconds = 5\n'
        'merge_repo_paths = ["/repo/file"]\nagent_token = "' + FIXTURE_TOKEN + '"\n',
    )
    env = {
        "ORCHESTRATOR_LOG_LEVEL": "ERROR",
        "ORCHESTRATOR_LOG_FORMAT": "json",
        "ORCHESTRATOR_BRIDGE_MODE": "merge-executor",
        "ORCHESTRATOR_API_BASE_URL": "http://from-env:8000/api/v1",
        "ORCHESTRATOR_BRIDGE_MANIFEST_PATH": "/from/env",
        "ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS": "11",
        "ORCHESTRATOR_MERGE_REPO_PATHS": "/repo/env-a,/repo/env-b",
        "ORCHESTRATOR_AGENT_TOKEN": "env-" + FIXTURE_TOKEN,
    }
    settings = load_settings(env=env, config_path=path)
    assert settings.log_level == "ERROR"
    assert settings.log_format == "json"
    assert settings.mode is RunMode.MERGE_EXECUTOR
    assert settings.api_base_url == "http://from-env:8000/api/v1"
    assert settings.manifest_path == Path("/from/env")
    assert settings.timeout_seconds == 11.0
    assert settings.merge_repo_paths == ("/repo/env-a", "/repo/env-b")
    assert settings.agent_token == "env-" + FIXTURE_TOKEN


def test_exported_empty_env_value_counts_as_unset(tmp_path: Path) -> None:
    path = _write(tmp_path, 'log_level = "DEBUG"\n')
    settings = load_settings(env={"ORCHESTRATOR_LOG_LEVEL": ""}, config_path=path)
    assert settings.log_level == "DEBUG"


def test_foreign_orchestrator_env_vars_are_ignored(tmp_path: Path) -> None:
    settings = load_settings(
        env={"ORCHESTRATOR_DATABASE_URL": "postgres://elsewhere/db"},
        config_path=tmp_path / "absent.toml",
    )
    assert settings.api_base_url == DEFAULT_API_BASE_URL


# --- validation: unknown keys, malformed values, required keys ---------------


def test_unknown_file_key_fails_fast(tmp_path: Path) -> None:
    path = _write(tmp_path, 'typo_level = "DEBUG"\n')
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={}, config_path=path)
    message = str(excinfo.value)
    assert "typo_level" in message and "allowed keys" in message


def test_malformed_toml_fails_fast_without_value_leak(tmp_path: Path) -> None:
    path = _write(tmp_path, 'agent_token = "' + FIXTURE_TOKEN + '"\nlog_level [broken\n')
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={}, config_path=path)
    message = str(excinfo.value)
    assert "not valid TOML" in message
    assert FIXTURE_TOKEN not in message


@pytest.mark.parametrize(
    ("env", "fragment"),
    [
        ({"ORCHESTRATOR_LOG_LEVEL": "loud"}, "log_level"),
        ({"ORCHESTRATOR_LOG_FORMAT": "xml"}, "log_format"),
        ({"ORCHESTRATOR_BRIDGE_MODE": "serial"}, "mode"),
        ({"ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS": "soon"}, "timeout_seconds"),
        ({"ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS": "0"}, "timeout_seconds"),
        ({"ORCHESTRATOR_API_BASE_URL": "ftp://backend"}, "api_base_url"),
    ],
)
def test_malformed_values_fail_fast(env: dict[str, str], fragment: str, tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env=env, config_path=tmp_path / "absent.toml")
    assert fragment in str(excinfo.value)


def test_wrong_type_token_error_never_echoes_the_value(tmp_path: Path) -> None:
    path = _write(tmp_path, "agent_token = 12345\n")
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={}, config_path=path)
    message = str(excinfo.value)
    assert "agent_token" in message
    assert "12345" not in message


def test_wrong_type_merge_repo_paths_in_file_fails_fast(tmp_path: Path) -> None:
    path = _write(tmp_path, "merge_repo_paths = 5\n")
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env={}, config_path=path)
    assert "merge_repo_paths" in str(excinfo.value)


def test_missing_required_key_for_merge_executor_mode(tmp_path: Path) -> None:
    settings = load_settings(env={}, config_path=tmp_path / "absent.toml")
    with pytest.raises(ConfigError) as excinfo:
        validate_for_mode(settings, RunMode.MERGE_EXECUTOR)
    message = str(excinfo.value)
    assert "ORCHESTRATOR_MERGE_REPO_PATHS" in message and "merge_repo_paths" in message
    # stdio and http bind without startup config (Section 10.2) — no raise
    validate_for_mode(settings, RunMode.STDIO)
    validate_for_mode(settings, RunMode.HTTP)


def test_required_key_present_passes_validation(tmp_path: Path) -> None:
    settings = load_settings(
        env={"ORCHESTRATOR_MERGE_REPO_PATHS": "/repo/a"}, config_path=tmp_path / "absent.toml"
    )
    validate_for_mode(settings, RunMode.MERGE_EXECUTOR)


# --- secrets hygiene ----------------------------------------------------------


def test_agent_token_is_redacted_in_repr(tmp_path: Path) -> None:
    settings = load_settings(
        env={"ORCHESTRATOR_AGENT_TOKEN": FIXTURE_TOKEN}, config_path=tmp_path / "absent.toml"
    )
    rendered = repr(settings)
    assert FIXTURE_TOKEN not in rendered
    assert "[REDACTED]" in rendered
    assert str(settings) == rendered  # __str__ falls back to __repr__


def test_loader_never_reads_cwd_env_or_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-SEC-04: no cwd-relative .env, no manifest source — env/user-file only."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"ORCHESTRATOR_AGENT_TOKEN={FIXTURE_TOKEN}\n", encoding="utf-8")
    (tmp_path / "manifest.json").write_text(
        f'{{"agent_token": "{FIXTURE_TOKEN}", "orchestrator_api": "http://evil"}}',
        encoding="utf-8",
    )
    settings = load_settings(env={}, config_path=tmp_path / "absent.toml")
    assert settings.agent_token is None
    assert settings.api_base_url == DEFAULT_API_BASE_URL


# --- user-level path resolution ----------------------------------------------


def test_default_user_config_path_is_profile_anchored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    path = default_user_config_path()
    assert path == tmp_path / "Roaming" / "orchestrator" / "bridge.toml"
    assert path.parts[-2:] == ("orchestrator", "bridge.toml")


def test_posix_path_branch_uses_xdg_config_home() -> None:
    from orchestrator_bridge.config import _config_base

    base = _config_base("linux", {"XDG_CONFIG_HOME": "/home/user/.config"})
    assert base == Path("/home/user/.config")
    fallback = _config_base("linux", {})
    assert fallback.name == ".config"


# --- shipped example files ----------------------------------------------------


def test_env_example_documents_exactly_the_loader_keys() -> None:
    documented = {
        line.split("=", 1)[0].strip()
        for line in (BRIDGE_ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line.startswith("ORCHESTRATOR_")
    }
    from orchestrator_bridge.config import _ENV_KEYS

    # ORCHESTRATOR_CORRELATION_ID is the MT-2.1-03 runtime scope input, documented
    # here but not a Settings key.
    assert documented == set(_ENV_KEYS.values()) | {"ORCHESTRATOR_CORRELATION_ID"}


def test_user_config_example_parses_as_placeholders(tmp_path: Path) -> None:
    settings = load_settings(env={}, config_path=BRIDGE_ROOT / "user-config.example.toml")
    assert settings.mode is RunMode.STDIO
    assert settings.agent_token is None
    assert settings.api_base_url == DEFAULT_API_BASE_URL


def test_settings_repr_type_is_stable() -> None:
    """One settings object type for every consumer (Section 10.1 config seam)."""
    settings = load_settings(env={}, config_path=Path("definitely-absent.toml"))
    assert isinstance(settings, Settings)
