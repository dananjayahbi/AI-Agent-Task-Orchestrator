"""MT-3.7-05 — conflict reporting: clean abort, untouched dev tree, T18 feed.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-05-conflict-reporting.md (parent plan Sections 11.4 step 4, 19 WP-3.7
acceptance, 8.2 T18, 9.6/9.8; ADR-008). The bridge half: a *simulated*
conflict (scratch repositories diverging on one file) run through the
composed step must classify as ``conflict`` (the loop's T18 report flavor)
with git's ``CONFLICT`` lines as details, leave no partial merge state
(worktree removed on the exit path), and leave the developer's working
tree byte-identical — including ``git status`` (nothing lands on a
conflict). The backend half (T18 applied once, ``merge.failed`` event and
push) is MT-3.7-01's ``backend/tests/test_merge_queue.py`` suite, run via
``pytest backend/tests -k t18`` per the MT's test command.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator_bridge.merge_executor import worktree as worktree_module
from orchestrator_bridge.merge_executor.loop import MergeOutcome
from orchestrator_bridge.merge_executor.queue import QueueItem
from orchestrator_bridge.merge_executor.strategies import MERGE_COMMIT, SQUASH
from orchestrator_bridge.merge_executor.strategy_step import WorktreeStrategyStep
from tests.git_fixtures import commit_all, git, make_repo, write_files

#: Strategies whose shape can reach a real conflict — ``fast_forward_only``
#: refuses a diverged branch before any three-way merge exists (MT-3.7-04).
_CONFLICT_CAPABLE = [SQUASH, MERGE_COMMIT]


@pytest.fixture()
def wt_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the executor's temp root under the test's tmp_path."""
    root = tmp_path / "exec-temp"
    monkeypatch.setattr(worktree_module, "temp_worktree_root", lambda: root)
    return root


def _snapshot(repo: Path) -> dict[str, bytes]:
    """Byte-snapshot of every file outside .git (the dev tree's observable state)."""
    state: dict[str, bytes] = {}
    for path in sorted(repo.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(repo).parts:
            continue
        state[str(path.relative_to(repo))] = path.read_bytes()
    return state


def _conflicting_repo(tmp_path: Path) -> Path:
    """``main`` and ``feat/task-1`` edit the same file differently."""
    repo = make_repo(tmp_path / "repo", {"README.md": "# base\n", "app.py": "V = 1\n"})
    git(repo, "checkout", "-qb", "feat/task-1")
    write_files(repo, {"README.md": "# feature's idea of the README\n"})
    commit_all(repo, "feat/task-1: rewrite README")
    git(repo, "checkout", "-q", "main")
    write_files(repo, {"README.md": "# main's competing README\n"})
    commit_all(repo, "main: competing README")
    return repo


def _item(strategy: str) -> QueueItem:
    return QueueItem(
        id="PID00001-T001",
        project_id="PID00001",
        title="t",
        state="in_human_review",
        version=1,
        merge_status="pending",
        branch_name="feat/task-1",
        merge_strategy=strategy,
    )


@pytest.mark.parametrize("strategy", _CONFLICT_CAPABLE, ids=_CONFLICT_CAPABLE)
def test_conflict_report_aborts_cleanly_with_the_dev_tree_untouched(
    wt_root: Path, tmp_path: Path, strategy: str
) -> None:
    """Simulated conflict → ``conflict`` outcome, no partial state, dev tree intact."""
    repo = _conflicting_repo(tmp_path)
    before = _snapshot(repo)
    status_before = git(repo, "status", "--porcelain").stdout
    main_before = git(repo, "rev-parse", "main").stdout.strip()

    outcome: MergeOutcome = WorktreeStrategyStep()(
        _item(strategy),
        repo,
        {"default_branch": "main", "repo_path": str(repo)},
    )

    # The loop's T18 flavor with git's CONFLICT lines as the report details.
    assert outcome.result == "conflict"
    assert outcome.sha is None
    assert "CONFLICT" in outcome.details
    assert "README.md" in outcome.details

    # Nothing landed: the default branch and every byte of the dev tree stand.
    assert git(repo, "rev-parse", "main").stdout.strip() == main_before
    assert _snapshot(repo) == before
    assert git(repo, "status", "--porcelain").stdout == status_before

    # No partial merge state survives: the worktree was removed on the
    # exit path (its forced removal is RISK-15's guaranteed cleanup).
    root = worktree_module.temp_worktree_root()
    assert not root.exists() or not any(root.iterdir())


def test_conflict_report_leaves_no_temp_worktree_behind_after_repeats(
    wt_root: Path, tmp_path: Path
) -> None:
    """Repeated conflicts on the same task never accumulate worktrees (RISK-04)."""
    repo = _conflicting_repo(tmp_path)
    for _ in range(3):
        outcome = WorktreeStrategyStep()(
            _item(SQUASH),
            repo,
            {"default_branch": "main", "repo_path": str(repo)},
        )
        assert outcome.result == "conflict"
    root = worktree_module.temp_worktree_root()
    assert not root.exists() or not any(root.iterdir())
