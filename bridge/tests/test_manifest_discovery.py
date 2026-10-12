"""MT-2.2-01 — upward manifest discovery: walk, Git ceiling, override, fail-fast.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.2-manifest-binding/
MT-2.2-01-manifest-discovery.md (parent plan Sections 10.3 step 1, 10.11,
19.1; FR-MCP-02).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from orchestrator_bridge.errors import INIT_COMMAND, ManifestNotFoundError, ManifestParseError
from orchestrator_bridge.manifest_discovery import (
    MANIFEST_FILENAME,
    _not_found_error,
    discover_manifest,
)


def _fake_repo(root: Path) -> Path:
    """A minimal Git repository boundary: *root* with a ``.git`` directory."""
    (root / ".git").mkdir(parents=True, exist_ok=True)
    return root


# --- upward walk: subfolder binds the repo manifest (WP-2.2 acceptance) -------


def test_subfolder_resolves_manifest_at_repo_root(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    manifest = write_manifest(repo)
    deep = repo / "src" / "nested" / "deep"
    deep.mkdir(parents=True)

    found = discover_manifest(deep)
    assert found.path == manifest.resolve()
    document = found.document
    assert isinstance(document, dict)
    assert document["project_id"] == "PID00007"


def test_subfolder_and_repo_root_resolve_identical_path(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    manifest = write_manifest(repo)
    sub = repo / "apps" / "web"
    sub.mkdir(parents=True)

    assert discover_manifest(sub).path == discover_manifest(repo).path == manifest.resolve()


def test_default_cwd_is_the_process_working_directory(
    tmp_path: Path, write_manifest: Callable[..., Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    manifest = write_manifest(repo)
    nested = repo / "pkg"
    nested.mkdir()
    monkeypatch.chdir(nested)

    assert discover_manifest().path == manifest.resolve()


def test_nested_manifest_wins_over_repo_root(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    """First-found wins: the nearest manifest up the walk is the bound one."""
    repo = _fake_repo(tmp_path / "repo")
    write_manifest(repo)
    nested = repo / "service"
    nearest = write_manifest(nested)
    leaf = nested / "src"
    leaf.mkdir()

    assert discover_manifest(leaf).path == nearest.resolve()


# --- ceiling: the walk stops at the Git root ---------------------------------


def test_manifest_at_git_root_is_found_before_ceiling(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    manifest = write_manifest(repo)  # manifest and .git share the root directory

    assert discover_manifest(repo).path == manifest.resolve()


def test_decoy_manifest_above_repo_is_never_consulted(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    write_manifest(tmp_path)  # decoy one level above the repository
    repo = _fake_repo(tmp_path / "repo")
    bound = write_manifest(repo)
    sub = repo / "sub"
    sub.mkdir()

    assert discover_manifest(sub).path == bound.resolve()


def test_walk_never_crosses_git_root_to_reach_decoy(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    write_manifest(tmp_path)  # decoy outside the repository
    repo = _fake_repo(tmp_path / "repo")
    sub = repo / "sub"
    sub.mkdir()

    with pytest.raises(ManifestNotFoundError) as excinfo:
        discover_manifest(sub)
    message = str(excinfo.value)
    assert MANIFEST_FILENAME in message
    assert "repository root" in message
    assert INIT_COMMAND in message


def test_git_file_pointer_is_a_ceiling_for_worktrees(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    """``.git`` as a file (worktree/submodule pointer): the directory that holds
    it is the boundary — checked for a manifest, then never walked past."""
    worktree = tmp_path / "worktree"
    write_manifest(worktree)
    (worktree / ".git").write_text("gitdir: ../real/.git/worktrees/wt\n", encoding="utf-8")
    nested = worktree / "pkg"
    nested.mkdir()

    assert discover_manifest(nested).path == (worktree / MANIFEST_FILENAME).resolve()


def test_walk_does_not_pass_git_file_pointer_without_manifest(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    write_manifest(tmp_path)  # decoy above the worktree
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: ../real/.git/worktrees/wt\n", encoding="utf-8")
    nested = worktree / "pkg"
    nested.mkdir()

    with pytest.raises(ManifestNotFoundError, match="repository root"):
        discover_manifest(nested)


# --- not found: fail fast, never fall back to an unbound session --------------


def test_missing_manifest_message_names_init_command(tmp_path: Path) -> None:
    repo = _fake_repo(tmp_path / "repo")
    sub = repo / "src"
    sub.mkdir()

    with pytest.raises(ManifestNotFoundError) as excinfo:
        discover_manifest(sub)
    message = str(excinfo.value)
    assert f"no {MANIFEST_FILENAME} found" in message
    assert INIT_COMMAND in message
    assert "Traceback" not in message  # one clear line, no internals


def test_filesystem_root_ceiling_message_when_no_git_exists(tmp_path: Path) -> None:
    """Exported tree (no ``.git`` anywhere): same fail-fast, worded for the
    filesystem-root ceiling — recorded per the MT risk note (unit-level, since
    ancestors of ``tmp_path`` are outside the test's control)."""
    from_fs_root = _not_found_error(Path("/somewhere/export"), reached_git_root=False)
    from_repo_root = _not_found_error(Path("/somewhere/repo"), reached_git_root=True)
    assert "filesystem root (no Git repository found)" in str(from_fs_root)
    assert INIT_COMMAND in str(from_fs_root)
    assert "repository root" in str(from_repo_root)
    assert str(from_fs_root) != str(from_repo_root)


# --- test-only override: bypass the walk without changing production semantics --


def test_override_returns_target_file_without_walking(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    # No .git and no manifest anywhere near the start directory: only the
    # override can succeed here.
    elsewhere = tmp_path / "standalone"
    elsewhere.mkdir()
    target = write_manifest(tmp_path / "outside", name="custom-manifest.json")

    found = discover_manifest(elsewhere, override=target)
    assert found.path == target.resolve()
    document = found.document
    assert isinstance(document, dict)
    assert document["project_id"] == "PID00007"


def test_relative_override_resolves_against_start_directory(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    target = write_manifest(repo, name="custom.json")

    found = discover_manifest(repo, override=Path("custom.json"))
    assert found.path == target.resolve()


def test_missing_override_fails_fast_with_actionable_message(tmp_path: Path) -> None:
    _fake_repo(tmp_path / "repo")
    absent = tmp_path / "repo" / "no-such.json"

    with pytest.raises(ManifestNotFoundError) as excinfo:
        discover_manifest(tmp_path / "repo", override=absent)
    message = str(excinfo.value)
    assert "does not exist" in message
    assert MANIFEST_FILENAME in message


# --- discovery locates and parses only; validation is MT-2.2-02's seam --------


def test_discovery_returns_structurally_valid_json_without_schema_checks(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    """A parseable document with schema faults is discovery's success — the
    schema/version seam belongs exclusively to ``manifest_validation``."""
    repo = _fake_repo(tmp_path / "repo")
    write_manifest(repo, document={"anything": 1, "schema_version": 99})

    found = discover_manifest(repo)
    assert found.document == {"anything": 1, "schema_version": 99}


def test_invalid_json_raises_parse_error_naming_the_file(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    broken = write_manifest(repo)
    broken.write_text('{"schema_version": 1, oops', encoding="utf-8")

    with pytest.raises(ManifestParseError) as excinfo:
        discover_manifest(repo)
    message = str(excinfo.value)
    assert "not valid JSON" in message
    assert MANIFEST_FILENAME in message


def test_non_utf8_file_raises_parse_error(
    tmp_path: Path, write_manifest: Callable[..., Path]
) -> None:
    repo = _fake_repo(tmp_path / "repo")
    binary = write_manifest(repo)
    binary.write_bytes(b"\xff\xfe\x7b\x22\x61\x22\x7d")  # UTF-16 BOM, not UTF-8

    with pytest.raises(ManifestParseError, match="not valid UTF-8"):
        discover_manifest(repo)
