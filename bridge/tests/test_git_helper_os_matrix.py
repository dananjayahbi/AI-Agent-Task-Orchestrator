"""MT-2.10-06 — OS matrix tests: Windows, macOS, Linux; paths with spaces
(parent plan Sections 10.8, 18; WP-2.10 acceptance; NFR-07 via CI).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-06-os-matrix-tests.md. This module is written so the **same tests
pass on all three host OSes** — it is the suite the CI matrix runs per leg
(the matrix job itself is a CI-pipeline follow-up recorded in the WP
changelog; pipeline config is outside this WP's file protocol):

* every fixture repository lives under a path **containing a space**, and
  the test asserts that before trusting any result (a fixture that avoids
  spaces proves nothing — MT risk note);
* on Windows the path additionally carries non-ASCII characters (the
  classic Git-wrapper breaker); other OSes skip that one leg with a named
  reason — no silent skips (Section 20.4 item 1);
* the push/reset/delete rejection sentinel runs unconditionally on every
  OS (the Section 10.8 guarantee is platform-independent);
* repository-relative outputs are asserted forward-slash on every OS.

Temp fixture repositories only — never this repository's Git state.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from orchestrator_bridge.git_helper import (
    GitHelperError,
    clean_state,
    create_or_switch_branch,
    merge_base_diff,
    repo_identity,
    run_git,
    scan_patch,
    task_worktree,
)
from tests.git_fixtures import commit_all, git, make_repo, write_files

_SPACE_DIR_NAME = "repo with spaces"
_UNICODE_DIR_NAME = "prueba español-ünïcode"


def _space_repo(tmp_path: Path, *, unicode_leg: bool = False, **kwargs: object) -> Path:
    """A fixture repository whose absolute path contains a space (and, on
    the Windows leg, non-ASCII characters). The assertion is part of the
    test: a fixture that dodged the hard case would silently pass."""
    directory_name = f"{_UNICODE_DIR_NAME} {_SPACE_DIR_NAME}" if unicode_leg else _SPACE_DIR_NAME
    repo = make_repo(tmp_path / directory_name, **kwargs)  # type: ignore[arg-type]
    assert " " in str(repo), "fixture path must contain a space (MT-2.10-06)"
    if unicode_leg:
        assert any(ord(ch) > 127 for ch in str(repo)), "unicode leg needs non-ASCII path"
    return repo


# --- one capability sweep per path flavor -------------------------------------


def test_git_helper_space_path_identity_status_and_branch(tmp_path: Path) -> None:
    repo = _space_repo(tmp_path, files={"src/some file.txt": "one\ntwo\n"})
    identity = repo_identity(repo)
    assert identity.toplevel.resolve() == repo.resolve()
    assert clean_state(repo).clean is True
    switched = create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert switched.created is True
    write_files(repo, {"src/some file.txt": "one\ntwo-changed\n"})
    commit_all(repo, "edit under a spaced path")
    assert clean_state(repo).clean is True


def test_git_helper_space_path_diff_normalization(tmp_path: Path) -> None:
    """Forward-slash, repository-relative paths even when the repository
    itself lives under a spaced (and nested) path — the MT-2.10-03
    normalization contract holds on every OS."""
    repo = _space_repo(tmp_path)
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"deep dir/another file.py": "print('hi')\n"})
    commit_all(repo, "nested spaced file")
    diff = merge_base_diff(repo, "feat", "main")
    assert [entry.path for entry in diff.changed_files] == ["deep dir/another file.py"]
    assert diff.stats.insertions == 1


def test_git_helper_space_path_secret_scan(tmp_path: Path) -> None:
    repo = _space_repo(tmp_path)
    git(repo, "switch", "-qc", "feat")
    secret_line = 'api_key = "s3cr3t-value-9x"\n'  # pragma: allowlist secret
    write_files(repo, {"cfg/app settings.yaml": secret_line})
    commit_all(repo, "add a secret under a spaced path")
    diff = merge_base_diff(repo, "feat", "main")
    result = scan_patch(diff)
    assert result.count == 1
    assert result.findings[0].path == "cfg/app settings.yaml"
    assert "s3cr3t-value-9x" not in str(result.as_dict())


def test_git_helper_space_path_worktree_helper(tmp_path: Path) -> None:
    repo = _space_repo(tmp_path)
    outcome = task_worktree(repo, "PID00007-T004", worktree_mode=True, default_branch="main")
    assert outcome.created is True and outcome.root is not None
    assert outcome.root.is_dir()
    # the worktree root also carries the space; reads work from inside it
    assert clean_state(outcome.root).clean is True


# --- the Windows-specific non-ASCII leg (named skip elsewhere) ----------------


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="MT-2.10-06 assigns the non-ASCII path leg to the Windows OS matrix run",
)
def test_git_helper_windows_nonascii_path_full_sweep(tmp_path: Path) -> None:
    repo = _space_repo(tmp_path, unicode_leg=True, files={"README.md": "# fixture\n"})
    identity = repo_identity(repo)
    assert identity.toplevel.resolve() == repo.resolve()
    switched = create_or_switch_branch(repo, "feat/PID00007-T004", default_branch="main")
    assert switched.created is True
    write_files(repo, {"archivoñ éspañol.txt": "contenido\n"})
    commit_all(repo, "unicode file")
    diff = merge_base_diff(repo, "feat/PID00007-T004", "main")
    assert [entry.path for entry in diff.changed_files] == ["archivoñ éspañol.txt"]
    assert clean_state(repo).clean is True


# --- the Section 10.8 sentinel: platform-independent --------------------------


def test_git_helper_rejects_push_reset_delete_on_every_os(tmp_path: Path) -> None:
    """WP-2.10 acceptance: never pushes or deletes — refused structurally,
    on every OS, including repositories under spaced paths."""
    repo = _space_repo(tmp_path)
    git(repo, "tag", "v1")
    for args in (
        ("push",),
        ("push", "--force"),
        ("reset", "--hard"),
        ("clean", "-fd"),
        ("branch", "-D", "main"),
        ("tag", "-d", "v1"),
        ("worktree", "prune"),
    ):
        with pytest.raises(GitHelperError):
            run_git(repo, list(args))
    assert "main" in git(repo, ["branch", "--list"]).stdout
    assert "v1" in git(repo, ["tag", "-l"]).stdout


def test_git_helper_refusal_happens_before_git_runs(tmp_path: Path) -> None:
    """A refusal is the helper's own (pre-process) — it cannot depend on the
    OS, the Git build, or the repository answering."""
    missing = tmp_path / "no such dir"
    for args in (("push",), ("reset", "--hard"), ("branch", "-D", "main")):
        with pytest.raises(GitHelperError) as excinfo:
            run_git(missing, list(args))
        assert "refuses" in excinfo.value.message
