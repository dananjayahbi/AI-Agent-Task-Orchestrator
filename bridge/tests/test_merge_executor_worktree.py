"""MT-3.7-03 — isolated temporary worktrees that never touch the dev tree.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-03-temp-worktree.md (parent plan Sections 11.4 steps 2/4/5, 10.8, 16.3,
19 WP-3.7 acceptance; ADR-007, ADR-008; RISK-15). A scratch repository carries
a dirty working tree and untracked files; every test runs create → simulate a
merge attempt → destroy and asserts the dev tree is byte-identical and no
temp artifacts remain. The temp root is redirected into pytest's tmp_path so
the suite never touches the host's real temp dir.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from orchestrator_bridge.merge_executor import worktree as worktree_module
from orchestrator_bridge.merge_executor.errors import MergeExecutorError
from orchestrator_bridge.merge_executor.git_runner import run_executor_git
from orchestrator_bridge.merge_executor.worktree import (
    TEMP_WORKTREE_PREFIX,
    TempWorktree,
    list_leftover_worktrees,
    temporary_worktree,
)
from tests.git_fixtures import git, make_repo, write_files


@pytest.fixture()
def wt_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the executor's temp root under the test's tmp_path."""
    root = tmp_path / "exec-temp"
    monkeypatch.setattr(worktree_module, "temp_worktree_root", lambda: root)
    return root


def _dirty_repo(tmp_path: Path) -> Path:
    """A repository with a committed tree plus a dirty file and an untracked one."""
    repo = make_repo(
        tmp_path / "repo",
        {"README.md": "# fixture\n", "src/app.py": "VERSION = 1\n"},
    )
    # Dirty tracked file (staged + unstaged layers) and an untracked secret-ish
    # file: the exact state a developer leaves behind mid-task.
    (repo / "src/app.py").write_text("VERSION = 2  # uncommitted work\n", encoding="utf-8")
    git(repo, "add", "src/app.py")
    (repo / "src/app.py").write_text("VERSION = 3  # also unstaged\n", encoding="utf-8")
    write_files(repo, {"notes.local.md": "personal scratch notes\n"})
    return repo


def _snapshot(repo: Path) -> dict[str, bytes]:
    """Byte-snapshot of every file outside .git (the dev tree's observable state)."""
    state: dict[str, bytes] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(repo).parts:
            continue
        state[str(path.relative_to(repo))] = path.read_bytes()
    return state


def _simulate_merge_attempt(worktree_path: Path) -> None:
    """What a merge step does inside the workspace: write, stage, commit."""
    write_files(Path(worktree_path), {"merge-result.txt": "merged\n"})
    git(Path(worktree_path), "add", "-A")
    git(Path(worktree_path), "commit", "-m", "simulated merge")


# --- Section 11.4 step 2: a clean worktree of the default branch ---------------


def test_worktree_is_created_detached_from_the_default_branch(
    wt_root: Path, tmp_path: Path
) -> None:
    repo = _dirty_repo(tmp_path)
    head_before = git(repo, "rev-parse", "HEAD").stdout.strip()

    with temporary_worktree(repo, "main") as worktree:
        assert worktree.path.is_dir()
        # Detached at the default branch's tip — no branch/ref was created.
        assert git(worktree.path, "rev-parse", "HEAD").stdout.strip() == head_before
        assert "refs/heads" not in git(worktree.path, "symbolic-ref", "HEAD", check=False).stdout
        # Clean checkout: the developer's dirty file is NOT in the workspace.
        assert (worktree.path / "src/app.py").read_text(encoding="utf-8") == "VERSION = 1\n"
        assert not (worktree.path / "notes.local.md").exists()
        # Inside the executor temp root, outside the repository.
        assert str(worktree.path).startswith(str(wt_root.resolve()))
        assert wt_root in [worktree.path, *worktree.path.parents]

    # Destroyed on exit.
    assert not worktree.path.exists()


# --- Section 11.4 step 5 / Section 19: the dev tree is untouched ---------------


def test_dirty_dev_tree_is_byte_identical_through_create_and_destroy(
    wt_root: Path, tmp_path: Path
) -> None:
    repo = _dirty_repo(tmp_path)
    before = _snapshot(repo)
    status_before = git(repo, "status", "--porcelain").stdout

    with temporary_worktree(repo, "main") as worktree:
        _simulate_merge_attempt(worktree.path)
        # The merge ran entirely inside the workspace…
        assert (worktree.path / "merge-result.txt").exists()

    # …and the developer's directory is byte-identical afterwards.
    assert _snapshot(repo) == before
    assert git(repo, "status", "--porcelain").stdout == status_before
    # No temp artifacts remain: the root is empty and Git forgot the worktree.
    assert list(wt_root.iterdir()) == []
    listed = git(repo, "worktree", "list", "--porcelain").stdout
    # git prints forward slashes; compare separator- and case-insensitively.
    assert str(repo.resolve()).replace("\\", "/").lower() in listed.lower()
    assert TEMP_WORKTREE_PREFIX not in listed


def test_cleanup_runs_on_the_exception_path(wt_root: Path, tmp_path: Path) -> None:
    repo = _dirty_repo(tmp_path)
    before = _snapshot(repo)
    escaped: list[Path] = []

    with pytest.raises(RuntimeError, match="merge exploded"):
        with temporary_worktree(repo, "main") as worktree:
            escaped.append(worktree.path)
            raise RuntimeError("merge exploded")

    assert escaped and not escaped[0].exists()
    assert list(wt_root.iterdir()) == []
    assert _snapshot(repo) == before


# --- WP-3.7 cleanup guarantees + MT-3.7-06's leftover enumeration --------------


def test_leftovers_are_enumerable_after_an_aborted_run(wt_root: Path, tmp_path: Path) -> None:
    repo = _dirty_repo(tmp_path)
    # Simulate a crash: the worktree was created and never destroyed.
    crashed = worktree_module._create(repo, "main")  # noqa: SLF001 - crash simulation
    try:
        leftovers = list_leftover_worktrees(repo)
        assert crashed.path in leftovers
        # A different repository's leftovers never bleed into this one.
        other = make_repo(tmp_path / "other", branch="main")
        assert list_leftover_worktrees(other) == ()
    finally:
        worktree_module._destroy(crashed)  # noqa: SLF001 - test teardown
    assert list_leftover_worktrees(repo) == ()


def test_removal_reports_rather_than_passes_silently(
    wt_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Windows-style churn: removal fails every attempt → loud error (RISK-15)."""
    repo = _dirty_repo(tmp_path)
    crashed = worktree_module._create(repo, "main")  # noqa: SLF001 - refusal fixture
    calls: list[float] = []

    # A locked path: even direct rmtree cannot remove it. Fail both the
    # runner's remove and the rmtree fallback so every attempt reports.
    real_runner = run_executor_git
    real_rmtree = shutil.rmtree

    def _failing_remove(cwd: Path, args: Sequence[str], **kwargs: Any) -> Any:
        if list(args)[:2] == ["worktree", "remove"]:
            return SimpleNamespace(ok=False, returncode=1, stdout="", stderr="directory busy")
        return real_runner(cwd, args, **kwargs)

    def _failing_rmtree(path: Path, **kwargs: Any) -> None:
        raise OSError(13, "Permission denied (locked)")

    monkeypatch.setattr(worktree_module, "run_executor_git", _failing_remove)
    monkeypatch.setattr(shutil, "rmtree", _failing_rmtree)
    try:
        with pytest.raises(MergeExecutorError, match="failed to remove temporary worktree"):
            worktree_module._destroy(crashed, sleep=calls.append)  # noqa: SLF001 - refusal path
    finally:
        # Restore real behavior for the sandbox teardown below.
        monkeypatch.setattr(worktree_module, "run_executor_git", real_runner)
        monkeypatch.setattr(shutil, "rmtree", real_rmtree)

    # The retries were observable (paced pauses) and the failure loud.
    assert calls == [
        worktree_module._REMOVE_RETRY_PAUSE_SECONDS,  # noqa: SLF001
        worktree_module._REMOVE_RETRY_PAUSE_SECONDS,  # noqa: SLF001
    ]
    assert crashed.path.exists()  # left for MT-3.7-06 reconciliation, not hidden
    assert crashed.path in list_leftover_worktrees(repo)
    # Teardown for the sandbox: clean up with the real runner.
    worktree_module._destroy(crashed)  # noqa: SLF001
    assert list_leftover_worktrees(repo) == ()


def test_cleanup_refuses_paths_outside_the_temp_root(tmp_path: Path) -> None:
    """The removal allowlist is 'our root only' — a foreign path is refused."""
    repo = make_repo(tmp_path / "repo")
    outside = tmp_path / "not-a-worktree"
    outside.mkdir()
    forged = TempWorktree(path=outside, repo_path=repo, default_branch="main")
    with pytest.raises(MergeExecutorError, match="outside the executor"):
        worktree_module._destroy(forged)  # noqa: SLF001 - guard path
    assert outside.exists()  # nothing was deleted


# --- Guards before creation (Section 11.4 step 2; Section 10.2) ----------------


def test_non_repository_path_is_reported_not_retried(wt_root: Path, tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(MergeExecutorError, match="not a Git repository"):
        temporary_worktree(plain, "main").__enter__()


def test_missing_default_branch_is_reported_not_retried(wt_root: Path, tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")  # branch 'main' only
    with pytest.raises(MergeExecutorError, match="does not exist"):
        with temporary_worktree(repo, "release/does-not-exist"):
            pass
    assert list(wt_root.iterdir()) == [] if wt_root.exists() else True


def test_missing_directory_is_reported(wt_root: Path, tmp_path: Path) -> None:
    with pytest.raises(MergeExecutorError, match="not an existing directory"):
        with temporary_worktree(tmp_path / "absent", "main"):
            pass


# --- Section 10.8 discipline: the runner's structural refusals -----------------


@pytest.mark.parametrize(
    ("args", "match"),
    [
        (["push", "origin", "main"], "not on the allowlist"),
        (["reset", "--hard"], "not on the allowlist"),
        # commit IS allowlisted (MT-3.7-04) but only as the squash shape:
        (["commit", "-m", "x"], "only 'commit --no-edit'"),
        (["commit", "--no-edit", "extra"], "only 'commit --no-edit'"),
        (["worktree", "prune"], "worktree prune"),
        (["worktree", "remove", "--force", "x"], None),  # allowed verb, checked by caller
        (["worktree", "add", "path"], "detach is required"),
        (["worktree", "add", "--force", "--detach", "p", "b"], "outside the verb"),
        (["--git-dir=/elsewhere", "status"], "global Git options"),
        (["rev-parse", "--output=x", "HEAD"], "outside the allowlist"),
        # MT-3.7-04's strategy shapes (structural refusals, pre-process):
        (["merge"], "a merge shape is required"),
        (["merge", "main"], "only the three strategy shapes"),
        (["merge", "--squash", "--ff-only", "b"], "only the three strategy shapes"),
        (["merge", "--ff-only", "a", "b"], "exactly one task-branch positional"),
        (["merge", "--abort", "b"], "only the three strategy shapes"),
        (["update-ref", "refs/heads/main", "abc"], "exactly ref, new sha and old sha"),
        (["update-ref", "refs/tags/v1", "0" * 40, "1" * 40], "only refs/heads/"),
        (["update-ref", "refs/heads/main", "nope", "0" * 40], "full hex commit ids"),
        (["update-ref", "refs/heads/main..x", "0" * 40, "1" * 40], "only refs/heads/"),
    ],
)
def test_runner_refusals_happen_before_any_process(
    tmp_path: Path, args: list[str], match: str | None
) -> None:
    if match is None:
        # Allowed verb: the guard passes it through; the caller decides
        # what a non-zero git exit means (tmp_path is not a repository,
        # so git itself fails — but no guard refusal fired).
        run = run_executor_git(tmp_path, args)
        assert run.returncode != 0
        return
    with pytest.raises(MergeExecutorError) as excinfo:
        run_executor_git(tmp_path, args)
    assert match in str(excinfo.value)


def test_runner_reports_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(MergeExecutorError, match="not an existing directory"):
        run_executor_git(tmp_path / "absent", ["rev-parse", "--git-dir"])


def test_runner_permits_the_worktree_lifecycle(tmp_path: Path) -> None:
    """The allowed verbs really work end to end on a scratch repository."""
    repo = make_repo(tmp_path / "repo")
    assert run_executor_git(repo, ["rev-parse", "--git-dir"]).ok
    root = tmp_path / "wt"
    root.mkdir()
    target = root / "ws"
    add = run_executor_git(repo, ["worktree", "add", "--detach", str(target), "main"])
    assert add.ok, add.stderr
    assert (
        run_executor_git(repo, ["worktree", "list", "--porcelain"]).stdout.count("worktree ") == 2
    )
    remove = run_executor_git(repo, ["worktree", "remove", "--force", str(target)])
    assert remove.ok, remove.stderr
    assert not target.exists()
