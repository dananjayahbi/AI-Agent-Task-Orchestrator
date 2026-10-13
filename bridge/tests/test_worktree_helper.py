"""MT-2.10-05 — optional per-task worktree helper (parent plan Section 10.8,
gap G-26, OQ-03; FR-MCP-07).

Acceptance source: plan-doc-series/m2-mcp-bridge/wp-2.10-git-helper/
MT-2.10-05-worktree-helper.md. The OQ-03 default (one concurrent task per
project) is preserved: disabled mode creates nothing, and no test may ever
observe the helper deleting anything. Temp fixture repositories only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.api_errors import ErrorCode
from orchestrator_bridge.git_helper import (
    GitHelperError,
    WorktreeOutcome,
    derive_branch_name,
    inspect_worktree,
    run_git,
    task_worktree,
)
from orchestrator_bridge.git_helper.worktree import WORKTREES_DIRNAME, list_worktrees
from tests.git_fixtures import git, make_repo

_TASK_A = "PID00007-T004"
_TASK_B = "PID00007-T005"


def _enabled(repo: Path, task_id: str) -> WorktreeOutcome:
    return task_worktree(repo, task_id, worktree_mode=True, default_branch="main")


# --- the OQ-03 default: disabled is a structured no-op ------------------------


def test_worktree_helper_disabled_by_default_creates_nothing(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    outcome = task_worktree(repo, _TASK_A, worktree_mode=False, default_branch="main")
    assert outcome.enabled is False
    assert outcome.disabled is True
    assert outcome.root is None and outcome.branch is None and outcome.created is False
    assert not (repo / WORKTREES_DIRNAME).exists(), "disabled mode must create nothing"
    assert outcome.as_dict()["enabled"] is False


def test_worktree_helper_disabled_result_names_the_task(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    outcome = task_worktree(repo, _TASK_A, worktree_mode=False, default_branch="main")
    assert outcome.task_id == _TASK_A
    assert outcome.branch is None


# --- enabled mode: creation, idempotence, isolation ---------------------------


def test_worktree_helper_enabled_creates_on_canonical_branch(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo", {"README.md": "# fixture\n"})
    outcome = _enabled(repo, _TASK_A)
    assert outcome.enabled is True
    assert outcome.created is True
    assert outcome.branch == derive_branch_name(_TASK_A)
    assert outcome.root is not None and outcome.root.is_dir()
    # the worktree is a working tree of the same repository, on the branch
    branch = git(outcome.root, ["branch", "--show-current"]).stdout.strip()
    assert branch == derive_branch_name(_TASK_A)
    assert (outcome.root / "README.md").exists()


def test_worktree_helper_lookup_is_idempotent(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    first = _enabled(repo, _TASK_A)
    second = _enabled(repo, _TASK_A)
    assert first.created is True
    assert second.created is False
    assert first.root == second.root


def test_worktree_helper_two_tasks_get_distinct_roots(tmp_path: Path) -> None:
    """G-26 mitigation exercised: concurrent tasks never share a directory."""
    repo = make_repo(tmp_path / "repo")
    first = _enabled(repo, _TASK_A)
    second = _enabled(repo, _TASK_B)
    assert first.created and second.created
    assert first.root is not None and second.root is not None
    assert first.root != second.root
    assert first.root.parent == second.root.parent == repo / WORKTREES_DIRNAME


def test_worktree_helper_root_stays_inside_repository_control(tmp_path: Path) -> None:
    """Section 12.3: the documented location is under the repository root —
    `.worktrees/<task id>`, meant for the project's .gitignore (the helper
    never edits files it was not asked to)."""
    repo = make_repo(tmp_path / "repo")
    outcome = _enabled(repo, _TASK_A)
    assert outcome.root is not None
    resolved_root = outcome.root.resolve()
    assert str(resolved_root).startswith(str(repo.resolve()))
    assert WORKTREES_DIRNAME in resolved_root.parts
    assert _TASK_A in resolved_root.parts


def test_worktree_helper_inspect_finds_registered_worktree(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    outcome = _enabled(repo, _TASK_A)
    entry = inspect_worktree(repo, _TASK_A)
    assert entry is not None
    assert entry.branch == derive_branch_name(_TASK_A)
    assert entry.stale is False
    assert entry.root == outcome.root
    assert inspect_worktree(repo, _TASK_B) is None


def test_worktree_helper_main_tree_state_is_untouched(tmp_path: Path) -> None:
    """Creating a worktree neither switches the main tree's branch nor
    dirties it (the default single-working-directory flow is unchanged).
    The documented layout keeps the tree clean once the project gitignores
    ``.worktrees/`` — the helper itself never edits tracked files."""
    repo = make_repo(tmp_path / "repo", {".gitignore": f"{WORKTREES_DIRNAME}/\n"})
    _enabled(repo, _TASK_A)
    assert git(repo, ["branch", "--show-current"]).stdout.strip() == "main"
    assert git(repo, ["status", "--porcelain"]).stdout.strip() == ""


# --- teardown restraint (Section 10.8; OQ recorded) ---------------------------


def test_worktree_helper_reports_stale_without_deleting(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    outcome = _enabled(repo, _TASK_A)
    assert outcome.root is not None
    import shutil

    shutil.rmtree(outcome.root)  # simulate an operator deleting the directory
    entry = inspect_worktree(repo, _TASK_A)
    assert entry is not None and entry.stale is True
    with pytest.raises(GitHelperError) as excinfo:
        _enabled(repo, _TASK_A)
    assert "prune" in excinfo.value.next_action
    # the helper never prunes: the stale registration is still listed
    assert any(_TASK_A in str(e.root) for e in list_worktrees(repo))


def test_worktree_helper_refuses_unparseable_task_id(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "repo")
    with pytest.raises(GitHelperError) as excinfo:
        _enabled(repo, "../escape")
    assert excinfo.value.code is ErrorCode.VALIDATION_ERROR
    assert not (repo / WORKTREES_DIRNAME).exists()


def test_worktree_helper_guard_still_forbids_mutations_with_worktrees(tmp_path: Path) -> None:
    """The MT-2.10-01 guard applies unchanged with worktrees in play — the
    WP-2.10 acceptance sentinel in the worktree context."""
    repo = make_repo(tmp_path / "repo")
    outcome = _enabled(repo, _TASK_A)
    assert outcome.root is not None
    for args in (
        ("push",),
        ("reset", "--hard"),
        ("branch", "-D", derive_branch_name(_TASK_A)),
        ("worktree", "remove", str(outcome.root)),
        ("worktree", "prune"),
    ):
        with pytest.raises(GitHelperError):
            run_git(repo, list(args))
        with pytest.raises(GitHelperError):
            run_git(outcome.root, list(args))
