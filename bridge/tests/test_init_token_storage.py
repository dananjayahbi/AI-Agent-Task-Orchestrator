"""MT-2.12-02 — token storage: hidden input, merge, permissions, path guard, round-trip.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.12-init-command/
MT-2.12-02-token-storage.md (FR-MCP-08 duty 2; FR-SEC-04; Section 12.2).
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from orchestrator_bridge.config import default_user_config_path, load_settings
from orchestrator_bridge.errors import InitError
from orchestrator_bridge.init.token_store import acquire_token, store_agent_token
from tests.conftest import FIXTURE_TOKEN


def test_store_writes_outside_the_repo_and_the_loader_reads_it_back(
    tmp_path: Path, isolated_init_config: Path
) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    path = store_agent_token(FIXTURE_TOKEN, repo_root=repo)
    assert path == isolated_init_config
    assert not path.is_relative_to(repo.resolve())  # FR-SEC-04: never in-tree
    assert load_settings(env={}, config_path=path).agent_token == FIXTURE_TOKEN


def test_store_merges_keeping_other_keys_and_comments(tmp_path: Path) -> None:
    config = tmp_path / "profile" / "bridge.toml"
    config.parent.mkdir(parents=True)
    config.write_text(
        '# my bridge config\nlog_level = "DEBUG"\nmerge_repo_paths = ["a", "b"]\n',
        encoding="utf-8",
    )
    store_agent_token(FIXTURE_TOKEN, config_path=config)
    settings = load_settings(env={}, config_path=config)
    assert settings.agent_token == FIXTURE_TOKEN
    assert settings.log_level == "DEBUG"
    assert settings.merge_repo_paths == ("a", "b")
    text = config.read_text(encoding="utf-8")
    assert "# my bridge config" in text  # comments survive a re-init


def test_reinit_replaces_only_the_token_key(tmp_path: Path) -> None:
    config = tmp_path / "bridge.toml"
    store_agent_token(FIXTURE_TOKEN, config_path=config)
    store_agent_token("second-token-abc", config_path=config)
    settings = load_settings(env={}, config_path=config)
    assert settings.agent_token == "second-token-abc"
    assert (
        load_settings(env={"ORCHESTRATOR_AGENT_TOKEN": "env-token"}, config_path=config).agent_token
        == "env-token"
    )  # env precedence intact (Section 10.3 step 3)


def test_store_refuses_a_repo_internal_path(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    inside = repo / "bridge.toml"
    with pytest.raises(InitError, match="inside the repository"):
        store_agent_token(FIXTURE_TOKEN, config_path=inside, repo_root=repo)
    assert not inside.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permission bits only")
def test_store_applies_owner_only_permissions(tmp_path: Path) -> None:
    config = tmp_path / "profile" / "bridge.toml"
    store_agent_token(FIXTURE_TOKEN, config_path=config)
    mode = stat.S_IMODE(config.stat().st_mode)
    assert mode == 0o600, f"expected 0600, got {oct(mode)}"
    dir_mode = stat.S_IMODE(config.parent.stat().st_mode)
    assert dir_mode == 0o700, f"expected 0700 on the config dir, got {oct(dir_mode)}"


def test_default_path_is_profile_anchored_never_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "profile"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    path = default_user_config_path()
    assert path.is_relative_to(tmp_path.resolve())  # profile dir, not the repo/cwd
    assert path.name == "bridge.toml" and path.parent.name == "orchestrator"


# --- token input (acquire) -----------------------------------------------------


def test_acquire_prefers_the_environment_over_prompting() -> None:
    used: list[str] = []

    def _prompt(question: str) -> str:
        used.append(question)
        return "prompt-token"

    token = acquire_token(environ={"ORCHESTRATOR_AGENT_TOKEN": FIXTURE_TOKEN}, prompt=_prompt)
    assert token == FIXTURE_TOKEN
    assert used == []  # env wins; no prompt shown


def test_acquire_uses_a_hidden_prompt_and_trims() -> None:
    seen: list[str] = []

    def _prompt(question: str) -> str:
        seen.append(question)
        return f"  {FIXTURE_TOKEN}\n"

    token = acquire_token(environ={}, prompt=_prompt)
    assert token == FIXTURE_TOKEN
    assert "hidden" in seen[0].lower()  # the prompt says the input is not echoed


def test_acquire_rejects_empty_and_unsafe_values_without_echoing_them() -> None:
    with pytest.raises(InitError, match="no agent token"):
        acquire_token(environ={}, prompt=lambda _q: "   ")
    with pytest.raises(InitError) as excinfo:
        acquire_token(environ={}, prompt=lambda _q: "two words")
    assert "two words" not in str(excinfo.value)  # never echo typed material
    with pytest.raises(InitError):
        acquire_token(environ={"ORCHESTRATOR_AGENT_TOKEN": "bad token"}, prompt=lambda _q: "x")


def test_acquire_headless_without_a_token_fails_with_the_env_var_named() -> None:
    with pytest.raises(InitError, match="ORCHESTRATOR_AGENT_TOKEN"):
        acquire_token(environ={}, prompt=None, stdin_isatty=False)


def test_acquire_cancelled_prompt_is_a_clear_failure() -> None:
    def _cancel(_question: str) -> str:
        raise KeyboardInterrupt

    with pytest.raises(InitError, match="cancelled"):
        acquire_token(environ={}, prompt=_cancel)


# --- no-secrets discipline ------------------------------------------------------


def test_storage_returns_only_the_path_never_the_value(tmp_path: Path) -> None:
    config = tmp_path / "bridge.toml"
    returned = store_agent_token(FIXTURE_TOKEN, config_path=config)
    # The function's entire result is the path; the value lives only in the file.
    assert returned == config
    assert FIXTURE_TOKEN not in str(returned)


def test_errors_never_carry_the_token_value(tmp_path: Path) -> None:
    config = tmp_path / "bridge.toml"
    config.write_text("this is not toml [[[\n", encoding="utf-8")
    with pytest.raises(InitError) as excinfo:
        store_agent_token(FIXTURE_TOKEN, config_path=config)
    assert FIXTURE_TOKEN not in str(excinfo.value)
    with pytest.raises(InitError, match="empty"):
        store_agent_token("   ", config_path=tmp_path / "other.toml")
