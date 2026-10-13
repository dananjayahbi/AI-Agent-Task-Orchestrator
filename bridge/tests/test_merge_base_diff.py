"""MT-2.10-03 — merge-base diff with stats and changed-file list
(parent plan Sections 9.7, 10.8; FR-MCP-07).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-03-merge-base-diff.md. The divergent-base fixture is the essential
guard: the diff must be branch-vs-merge-base, never branch-vs-default-HEAD.
Temp fixture repositories only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.git_helper import GitHelperError, merge_base_diff
from tests.git_fixtures import commit_all, git, make_repo, write_files


def _forked_repo(tmp_path: Path) -> tuple[Path, str, str]:
    """main and feat share history; both then advance (bases diverge).

    Returns (repo, main_at_fork, main_head). The merge-base of feat and main
    is the fork commit — feat's diff must NOT include main's later commit.
    """
    repo = make_repo(tmp_path / "repo", {"shared.txt": "one\ntwo\nthree\n"})
    fork = git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"shared.txt": "one\ntwo-branch\nthree\n"})
    write_files(repo, {"feature/added.py": "def ready():\n    return 42\n"})
    commit_all(repo, "feat work")
    git(repo, "switch", "main")
    write_files(repo, {"main-only.txt": "advance\n"})
    commit_all(repo, "main advances")
    main_head = git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    git(repo, "switch", "feat")
    return repo, fork, main_head


def test_merge_base_diff_uses_merge_base_not_default_head(tmp_path: Path) -> None:
    """The divergent-base assertion (Section 9.7; MT risk note)."""
    repo, fork, main_head = _forked_repo(tmp_path)
    assert fork != main_head, "fixture must diverge"
    diff = merge_base_diff(repo, "feat", "main")
    assert diff.merge_base_sha == fork
    assert diff.head_sha == git(repo, ["rev-parse", "HEAD"]).stdout.strip()
    # main's post-fork file is NOT in the task branch's evidence
    assert "main-only.txt" not in diff.patch
    paths = {entry.path for entry in diff.changed_files}
    assert "main-only.txt" not in paths
    assert paths == {"shared.txt", "feature/added.py"}


def test_merge_base_diff_stats_are_accurate(tmp_path: Path) -> None:
    repo, _, _ = _forked_repo(tmp_path)
    diff = merge_base_diff(repo, "feat", "main")
    assert diff.stats.files_changed == 2
    by_path = {entry.path: entry for entry in diff.changed_files}
    assert by_path["shared.txt"].insertions == 1
    assert by_path["shared.txt"].deletions == 1
    assert by_path["feature/added.py"].status == "A"
    assert by_path["feature/added.py"].insertions == 2
    assert diff.stats.insertions == sum(e.insertions for e in diff.changed_files)
    assert diff.stats.deletions == sum(e.deletions for e in diff.changed_files)


def test_merge_base_diff_empty_branch_reports_empty_bundle(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    git(repo, "switch", "main")
    diff = merge_base_diff(repo, "feat", "main")
    assert diff.patch == ""
    assert diff.stats.files_changed == 0
    assert diff.stats.insertions == 0
    assert diff.changed_files == ()


def test_merge_base_diff_patch_size_bytes_is_reported(tmp_path: Path) -> None:
    """Size feeds the Section 9.7 5 MB cap decision — the helper does not
    truncate; it reports the true byte size of the patch it produced."""
    repo, _, _ = _forked_repo(tmp_path)
    diff = merge_base_diff(repo, "feat", "main")
    assert diff.patch_size_bytes == len(diff.patch.encode("utf-8"))
    assert diff.patch_size_bytes > 0


def test_merge_base_diff_paths_are_repo_relative_forward_slash(tmp_path: Path) -> None:
    """The cross-OS normalization contract (Section 12.3, MT-2.10-06):
    even a file created under a nested directory yields forward-slash
    repository-relative paths."""
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    write_files(repo, {"src/deeply/nested/module.py": "x = 1\n"})
    commit_all(repo, "nested add")
    diff = merge_base_diff(repo, "feat", "main")
    paths = [entry.path for entry in diff.changed_files]
    assert paths == ["src/deeply/nested/module.py"]
    assert all("\\" not in path and not Path(path).is_absolute() for path in paths)


def test_merge_base_diff_deleted_file_status(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"doomed.txt": "bye\n", "keeper.txt": "hi\n"})
    git(repo, "switch", "-qc", "feat")
    (repo / "doomed.txt").unlink()
    commit_all(repo, "remove doomed")
    diff = merge_base_diff(repo, "feat", "main")
    by_path = {entry.path: entry for entry in diff.changed_files}
    assert by_path["doomed.txt"].status == "D"
    assert by_path["doomed.txt"].insertions == 0
    assert by_path["doomed.txt"].deletions == 1


def test_merge_base_diff_binary_file_is_marked_not_counted(tmp_path: Path) -> None:
    """Binary stats follow Git's own output: numstat shows ``-``; the entry
    is marked binary with zero counted lines."""
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    (repo / "blob.bin").write_bytes(bytes(range(256)) * 4)
    commit_all(repo, "binary add")
    diff = merge_base_diff(repo, "feat", "main")
    entry = next(e for e in diff.changed_files if e.path == "blob.bin")
    assert entry.binary is True
    assert entry.insertions == 0 and entry.deletions == 0


def test_merge_base_diff_missing_branch_is_structured(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    with pytest.raises(GitHelperError) as excinfo:
        merge_base_diff(repo, "ghost-branch", "main")
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "ghost-branch" in error.message
    assert error.hint and error.next_action


def test_merge_base_diff_missing_default_branch_is_structured(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "switch", "-qc", "feat")
    with pytest.raises(GitHelperError) as excinfo:
        merge_base_diff(repo, "feat", "trunk")
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "trunk" in error.message


def test_merge_base_diff_unrelated_histories_is_structured(tmp_path: Path) -> None:
    """An orphan branch shares no ancestor with main — the merge-base call
    itself fails and the helper names the situation instead of guessing."""
    repo = make_repo(tmp_path / "repo", {"file.txt": "x\n"})
    git(repo, "switch", "--orphan", "island")
    write_files(repo, {"other.txt": "y\n"})
    commit_all(repo, "island root")
    with pytest.raises(GitHelperError) as excinfo:
        merge_base_diff(repo, "island", "main")
    error = excinfo.value
    assert error.code is ErrorCode.VALIDATION_ERROR
    assert "unrelated" in error.message
    assert "recreate" in error.next_action.lower() or "report" in error.next_action.lower()


def test_merge_base_diff_rejects_flag_like_ref_arguments(tmp_path: Path) -> None:
    """Ref arguments can never become Git flags (arg-injection seam)."""
    repo = make_repo(tmp_path / "repo")
    for branch, default in (("--output=stolen", "main"), ("feat", "--no-renames")):
        with pytest.raises(GitHelperError):
            merge_base_diff(repo, branch, default)
