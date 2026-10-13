"""MT-2.10-01 — repository identity, clean-state checks and the capability
guard (parent plan Sections 10.8, 12.3; FR-MCP-07).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-01-repo-state-checks.md. Every repository is a temp fixture from
``tests.git_fixtures`` — never this repository's Git state. The guard tests
are the WP-2.10 acceptance pin ("never pushes or deletes"): refusals happen
before any process starts, and an allowed operation demonstrably runs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.git_helper import GitHelperError, clean_state, repo_identity, run_git
from tests.git_fixtures import commit_all, git, make_repo, write_files

# --- repository identity ------------------------------------------------------


def test_git_repo_state_identity_resolves_toplevel(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    identity = repo_identity(repo)
    assert identity.toplevel.resolve() == repo.resolve()
    assert (identity.git_dir / "HEAD").exists() or identity.git_dir.name.endswith(".git")


def test_git_repo_state_identity_from_subdirectory(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"a/b/c.txt": "x\n"})
    identity = repo_identity(repo / "a" / "b")
    assert identity.toplevel.resolve() == repo.resolve()


def test_git_repo_identity_matches_expected_root(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    identity = repo_identity(repo, expected_root=repo)
    assert identity.toplevel.resolve() == repo.resolve()


def test_git_repo_state_identity_mismatch_is_structured(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    other = make_repo(tmp_path / "other")
    with pytest.raises(GitHelperError) as excinfo:
        repo_identity(repo, expected_root=other)
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert error.hint and error.next_action
    assert error.details is not None
    assert str(error.details["expected_root"]) == str(other)
    assert str(error.details["resolved_toplevel"]) == str(repo)


def test_git_repo_state_not_a_repository_is_structured(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(GitHelperError) as excinfo:
        repo_identity(plain)
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert "not inside a Git working tree" in str(excinfo.value)


# --- clean-state reporting ----------------------------------------------------


def test_git_repo_state_clean_repository_reports_clean(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    state = clean_state(repo)
    assert state.clean is True
    assert state.uncommitted_changes == 0
    assert state.untracked_files == 0
    assert state.operation_in_progress is False


def test_git_repo_state_dirty_and_untracked_are_counted(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    write_files(repo, {"README.md": "# changed\n"})
    write_files(repo, {"loose.txt": "untracked\n"})
    state = clean_state(repo)
    assert state.clean is False
    assert state.uncommitted_changes == 1
    assert state.untracked_files == 1


def test_git_repo_state_merge_in_progress_is_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"file.txt": "base\n"})
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"file.txt": "feat-side\n"})
    commit_all(repo, "feat edit")
    git(repo, "switch", "main")
    write_files(repo, {"file.txt": "main-side\n"})
    commit_all(repo, "main edit")
    merged = git(repo, "merge", "feat", check=False)
    assert merged.returncode != 0, "fixture merge must conflict to leave MERGE_HEAD"
    state = clean_state(repo)
    assert state.merge_in_progress is True
    assert state.operation_in_progress is True
    assert state.clean is False


def test_git_repo_state_rebase_in_progress_is_reported(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"file.txt": "base\n"})
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"file.txt": "feat-side\n"})
    commit_all(repo, "feat edit")
    git(repo, "switch", "main")
    write_files(repo, {"file.txt": "main-side\n"})
    commit_all(repo, "main edit")
    git(repo, "switch", "feat")
    rebased = git(repo, "rebase", "main", check=False)
    assert rebased.returncode != 0, "fixture rebase must conflict to leave rebase state"
    state = clean_state(repo)
    assert state.rebase_in_progress is True
    assert state.clean is False


# --- capability guard (Section 10.8; WP-2.10 acceptance) ----------------------


def test_git_repo_state_guard_allows_reads_and_branch_creation(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    assert run_git(repo, ["status", "--short"]).ok
    assert run_git(repo, ["rev-parse", "HEAD"]).ok
    assert run_git(repo, ["branch", "--list"]).ok
    created = run_git(repo, ["branch", "feat/from-guard", "main"])
    assert created.ok, created.stderr
    assert "feat/from-guard" in run_git(repo, ["branch", "--list"]).stdout


_FORBIDDEN_OPERATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("push", ("push", "origin", "main")),
    ("push --force", ("push", "--force", "origin", "main")),
    ("reset --hard", ("reset", "--hard", "HEAD")),
    ("reset", ("reset", "HEAD")),
    ("clean -fd", ("clean", "-fd")),
    ("rebase", ("rebase", "main")),
    ("commit", ("commit", "-m", "nope")),
    ("add", ("add", "-A")),
    ("init", ("init",)),
    ("clone", ("clone", "somewhere")),
    ("fetch", ("fetch", "origin")),
    ("pull", ("pull",)),
    ("tag create", ("tag", "v9.9")),
    ("tag -d", ("tag", "-d", "v1")),
    ("branch -D", ("branch", "-D", "feat/x")),
    ("branch -d", ("branch", "-d", "feat/x")),
    ("branch -m", ("branch", "-m", "old", "new")),
    ("worktree remove", ("worktree", "remove", "some/path")),
    ("worktree prune", ("worktree", "prune")),
    ("switch --force", ("switch", "--force", "main")),
    ("checkout --force", ("checkout", "--force", "main")),
    ("merge", ("merge", "feat")),
    ("cherry-pick", ("cherry-pick", "HEAD")),
    ("stash", ("stash", "pop")),
    ("update-ref", ("update-ref", "-d", "refs/heads/old")),
    ("symbolic-ref", ("symbolic-ref", "HEAD", "refs/heads/other")),
    ("unknown subcommand", ("magic",)),
)


@pytest.mark.parametrize(
    ("label", "args"),
    _FORBIDDEN_OPERATIONS,
    ids=[operation[0] for operation in _FORBIDDEN_OPERATIONS],
)
def test_git_repo_state_guard_rejects_mutations(
    tmp_path: Path, label: str, args: tuple[str, ...]
) -> None:
    """The structural proof: each forbidden operation raises *before* a
    process exists — the refusal message never depends on Git's answer."""
    repo = make_repo(tmp_path / "repo")
    with pytest.raises(GitHelperError) as excinfo:
        run_git(repo, list(args))
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "refuses" in error.message
    assert error.details is not None
    # the repository is untouched by the refused attempt
    assert clean_state(repo).clean is True


def test_git_repo_state_guard_never_pushes_or_deletes(tmp_path: Path) -> None:
    """WP-2.10 acceptance sentinel: push and every delete form are refused."""
    repo = make_repo(tmp_path / "repo")
    git(repo, "tag", "v1")
    for args in (
        ("push",),
        ("push", "origin", "--all"),
        ("branch", "-D", "main"),
        ("tag", "-d", "v1"),
        ("worktree", "remove", str(tmp_path / "missing")),
        ("reset", "--hard"),
    ):
        with pytest.raises(GitHelperError):
            run_git(repo, list(args))
    # and the tag the delete targeted still exists — nothing was deleted
    assert "v1" in run_git(repo, ["tag", "-l"]).stdout


def test_git_repo_state_guard_rejects_global_options(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    for args in (
        ("--git-dir=" + str(repo / ".git"), "status"),
        ("--work-tree=" + str(repo), "status"),
        ("-c", "core.hooksPath=hooks", "status"),
        ("--no-pager", "status"),
    ):
        with pytest.raises(GitHelperError):
            run_git(repo, list(args))


def test_git_repo_state_guard_rejects_write_flags_on_reads(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    for args in (
        ("log", "--output=stolen.txt", "-n", "1"),
        ("diff", "--output=stolen.txt"),
        ("diff", "--ext-diff"),
    ):
        with pytest.raises(GitHelperError):
            run_git(repo, list(args))


def test_git_repo_state_runner_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(GitHelperError) as excinfo:
        run_git(tmp_path / "no-such-dir", ["status"])
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR


def test_git_repo_state_runner_runs_inside_root(tmp_path: Path) -> None:
    """The command's cwd is the repository root — output reflects it."""
    repo = make_repo(tmp_path / "repo", {"only-here.txt": "x\n"})
    listed = run_git(repo, ["ls-files"])
    assert listed.ok
    assert "only-here.txt" in listed.stdout
