"""MT-2.6-03 — merge-base patch capture: evidence, cap marker, determinism.

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/
MT-2.6-03-patch-capture.md (parent plan Sections 9.7, 10.8; FR-MCP-07).
The non-trivial merge-base fixture guards the silent poisoning risk (a naive
branch-vs-default-HEAD diff would leak the default branch's own commits into
the evidence); the cap boundary mirrors WP-3.2's inclusive 5 MB comparison
exactly (bridge prepares, backend stores); capture is keyed to the verified
sha, so neither a dirty working tree nor a moved branch can alter what was
captured.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.manifest import StartupBinding
from orchestrator_bridge.tools.errors import ToolFailure
from orchestrator_bridge.tools.submit_capture import (
    CAP_DEFAULT_MAX_BYTES,
    DIFF_TOO_LARGE_MARKER,
    capture_patch,
)
from tests.conftest import MINIMAL_MANIFEST
from tests.git_fixtures import commit_all, git, make_repo, write_files

_ASSIGNED_BRANCH = "feat/PID00007-T004"
_DEFAULT_BRANCH = "main"


def _repo_with_branch(tmp_path: Path) -> Path:
    """A repository whose assigned branch forks from an initial main commit."""
    repo = make_repo(
        tmp_path / "repo",
        {"README.md": "# fixture\n", "orchestrator.json": json.dumps(MINIMAL_MANIFEST)},
    )
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)
    write_files(repo, {"feature.py": "print('feature')\n"})
    commit_all(repo, "implement the feature")
    return repo


def _head(repo: Path, rev: str = "HEAD") -> str:
    return git(repo, "rev-parse", rev).stdout.strip()


def test_patch_capture_uses_the_merge_base_not_the_default_head(tmp_path: Path) -> None:
    # main moves *after* the fork: a naive three-dot/HEAD diff would include
    # main's commit; the merge-base diff must not.
    repo = make_repo(
        tmp_path / "repo",
        {"README.md": "# fixture\n", "orchestrator.json": json.dumps(MINIMAL_MANIFEST)},
    )
    fork_point = _head(repo)  # the common ancestor main must be diffed against
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)
    write_files(repo, {"feature.py": "print('feature')\n"})
    commit_all(repo, "implement the feature")
    git(repo, "checkout", "-q", _DEFAULT_BRANCH)
    write_files(repo, {"main-only.md": "main moved on\n"})
    commit_all(repo, "main advances independently")
    git(repo, "checkout", "-q", _ASSIGNED_BRANCH)

    captured = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=_head(repo)
    )

    assert captured.merge_base_sha == fork_point  # the fork commit, not main's head
    assert captured.commit_sha == _head(repo)
    assert "feature.py" in captured.patch
    assert "main-only.md" not in captured.patch  # never another branch's work
    assert captured.stats == {"insertions": 1, "deletions": 0, "files_changed": 1}
    assert captured.changed_files == ("feature.py",)
    assert captured.diff_too_large is False


def test_patch_capture_empty_diff_when_the_branch_added_nothing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)  # no commits of its own

    captured = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=_head(repo)
    )

    assert captured.patch == ""
    assert captured.patch_size_bytes == 0
    assert captured.stats == {"insertions": 0, "deletions": 0, "files_changed": 0}
    assert captured.changed_files == ()
    assert captured.diff_too_large is False


def test_patch_capture_marks_oversize_diffs_instead_of_reporting_a_body(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "repo")
    git(repo, "checkout", "-q", "-b", _ASSIGNED_BRANCH)
    write_files(repo, {"big.txt": "y" * (CAP_DEFAULT_MAX_BYTES + 64) + "\n"})
    commit_all(repo, "one enormous line")

    captured = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=_head(repo)
    )

    assert captured.patch_size_bytes > CAP_DEFAULT_MAX_BYTES
    assert captured.diff_too_large is True
    # Stats and file list still produced (the backend stores those per 9.7)…
    assert captured.stats["files_changed"] == 1
    assert captured.changed_files == ("big.txt",)
    # …and the evidence view carries the literal marker instead of the body.
    evidence = captured.evidence()
    assert evidence["marker"] == DIFF_TOO_LARGE_MARKER
    assert "diff --git" not in json.dumps(evidence)
    # The upload still carries the full text: the backend parses the received
    # bytes and applies the storage cap itself (WP-3.2 boundary coordination).
    assert "diff --git" in captured.patch


def test_patch_capture_cap_boundary_is_inclusive(tmp_path: Path) -> None:
    assert CAP_DEFAULT_MAX_BYTES == 5 * 1024 * 1024  # WP-3.2 PATCH_MAX_BYTES
    repo = _repo_with_branch(tmp_path)
    head = _head(repo)
    fixture_size = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=head
    ).patch_size_bytes

    at_the_cap = capture_patch(
        repo,
        branch=_ASSIGNED_BRANCH,
        default_branch=_DEFAULT_BRANCH,
        expected_head_sha=head,
        max_bytes=fixture_size,  # size == cap stays inclusive (backend `>`)
    )
    assert at_the_cap.diff_too_large is False

    one_below = capture_patch(
        repo,
        branch=_ASSIGNED_BRANCH,
        default_branch=_DEFAULT_BRANCH,
        expected_head_sha=head,
        max_bytes=fixture_size - 1,
    )
    assert one_below.diff_too_large is True


def test_patch_capture_refuses_a_branch_that_moved_since_verification(tmp_path: Path) -> None:
    repo = _repo_with_branch(tmp_path)
    verified_sha = _head(repo)
    write_files(repo, {"second.py": "z = 2\n"})
    commit_all(repo, "another commit lands after verification")

    with pytest.raises(ToolFailure) as excinfo:
        capture_patch(
            repo,
            branch=_ASSIGNED_BRANCH,
            default_branch=_DEFAULT_BRANCH,
            expected_head_sha=verified_sha,
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert "moved since verification" in translated.message
    assert translated.details is not None
    assert translated.details["expected_head_sha"] == verified_sha
    assert translated.details["actual_head_sha"] == _head(repo)


def test_patch_capture_ignores_working_tree_churn(tmp_path: Path) -> None:
    # Determinism (the MT's acceptance): the bundle is ref-to-ref at the
    # verified sha — uncommitted edits and new untracked files in the
    # worktree cannot change what is captured.
    repo = _repo_with_branch(tmp_path)
    head = _head(repo)
    first = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=head
    )

    write_files(repo, {"feature.py": "print('uncommitted edit')\n", "scratch.log": "noise\n"})

    second = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=head
    )

    assert second.patch == first.patch
    assert second.stats == first.stats
    assert second.changed_files == first.changed_files


def test_patch_capture_fails_clearly_without_a_merge_base(tmp_path: Path) -> None:
    # Unrelated histories: shallow-clone-like states must fail loudly, never
    # compute a wrong diff (MT-2.6-03 risk note).
    repo = _repo_with_branch(tmp_path)
    orphan = tmp_path / "orphan"
    orphan.mkdir()
    git(orphan, "init", "-q", "-b", "orphan-main")
    write_files(orphan, {"solo.txt": "unrelated\n"})
    commit_all(orphan, "no shared history")
    git(repo, "fetch", "-q", str(orphan), "orphan-main:orphan-main")
    git(repo, "checkout", "-q", "-b", "orphan-branch", "orphan-main")

    with pytest.raises(ToolFailure) as excinfo:
        capture_patch(
            repo,
            branch="orphan-branch",
            default_branch=_DEFAULT_BRANCH,
            expected_head_sha=_head(repo),
        )

    translated = excinfo.value.translated
    assert translated.code is ErrorCode.VALIDATION_ERROR
    assert translated.hint and translated.next_action


def test_patch_capture_paths_are_repo_relative(tmp_path: Path) -> None:
    # Section 12.3 / MT-2.10-06: forward-slash, repository-relative output on
    # every OS — the backend's scope engine and the spool depend on it.
    repo = _repo_with_branch(tmp_path)
    write_files(repo, {"nested/dir/file.py": "a = 1\n"})
    commit_all(repo, "nested file")

    captured = capture_patch(
        repo, branch=_ASSIGNED_BRANCH, default_branch=_DEFAULT_BRANCH, expected_head_sha=_head(repo)
    )

    assert "nested/dir/file.py" in captured.changed_files
    assert not any(entry.startswith("/") for entry in captured.changed_files)
    assert ":" not in captured.changed_files[0].split("/", 1)[0]  # no drive letters


def test_patch_capture_binding_helper_roundtrip(tmp_path: Path) -> None:
    # Smoke: the manifest's default_branch is what the submit flow passes in.
    repo = _repo_with_branch(tmp_path)
    manifest = dict(MINIMAL_MANIFEST)
    binding = StartupBinding(manifest_path=repo / "orchestrator.json", manifest=manifest)

    captured = capture_patch(
        repo,
        branch=_ASSIGNED_BRANCH,
        default_branch=str(binding.manifest["default_branch"]),
        expected_head_sha=_head(repo),
    )

    evidence = captured.evidence()
    assert captured.branch == _ASSIGNED_BRANCH
    assert evidence["branch"] == _ASSIGNED_BRANCH
    assert evidence["diff_too_large"] is False
    assert evidence["marker"] is None
