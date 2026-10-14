"""MT-3.7-04 — the three executable merge strategies + ``manual`` refusal.

Acceptance source: plan-doc-series/m3-audit-policy-merge/wp-3.7-merge-executor/
MT-3.7-04-merge-strategies.md (parent plan Sections 7.2, 11.4 step 3, 8.2
T17/T18, 10.8, 19; ADR-008; OQ-06). Table-driven: one green case per
``squash`` / ``merge_commit`` / ``fast_forward_only`` in a scratch repo,
the non-fast-forward case reported as a failure (the T18 path), the empty
merge classified failed, the CAS landing refusing a concurrently moved
default branch, and ``manual`` producing **no** merge attempt (no git
process, no worktree). Scratch repositories only — never this
repository's Git state; the executor temp root is redirected into
pytest's tmp_path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator_bridge.merge_executor import strategies as strategies_module
from orchestrator_bridge.merge_executor import strategy_step as strategy_step_module
from orchestrator_bridge.merge_executor import worktree as worktree_module
from orchestrator_bridge.merge_executor.loop import MergeOutcome
from orchestrator_bridge.merge_executor.queue import QueueItem
from orchestrator_bridge.merge_executor.strategies import (
    FAST_FORWARD_ONLY,
    MANUAL_STRATEGY,
    MERGE_COMMIT,
    SQUASH,
    STRATEGY_VALUES,
    apply_strategy,
    merge_shape_for,
)
from orchestrator_bridge.merge_executor.strategy_step import WorktreeStrategyStep
from orchestrator_bridge.merge_executor.worktree import temporary_worktree
from tests.git_fixtures import commit_all, git, make_repo, write_files

_EXECUTABLE = sorted(STRATEGY_VALUES)


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


def _repo_with_feature(tmp_path: Path, *, diverge_main: bool = False) -> Path:
    """``main`` plus ``feat/task-1`` one commit ahead (optionally diverged)."""
    repo = make_repo(tmp_path / "repo", {"README.md": "# base\n", "app.py": "V = 1\n"})
    git(repo, "checkout", "-qb", "feat/task-1")
    write_files(repo, {"README.md": "# feature\n", "feature.py": "NEW = True\n"})
    commit_all(repo, "feat/task-1: implement feature")
    git(repo, "checkout", "-q", "main")
    if diverge_main:
        write_files(repo, {"main_only.md": "main side\n"})
        commit_all(repo, "main: unrelated work")
    return repo


def _parents(repo: Path, ref: str) -> list[str]:
    """The parent shas of *ref* (``rev-list --parents -1``)."""
    line = git(repo, "rev-list", "--parents", "-1", ref).stdout.strip().split()
    return line[1:]


def _queue_item(strategy: str) -> QueueItem:
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


# --- one green case per executable strategy -----------------------------------


@pytest.mark.parametrize("strategy", _EXECUTABLE, ids=_EXECUTABLE)
def test_merge_strategy_lands_each_value_on_the_default_branch(
    wt_root: Path, tmp_path: Path, strategy: str
) -> None:
    """Each named strategy merges inside the worktree and lands on ``main``."""
    repo = _repo_with_feature(tmp_path)
    main_before = git(repo, "rev-parse", "main").stdout.strip()
    feature_tip = git(repo, "rev-parse", "feat/task-1").stdout.strip()
    before = _snapshot(repo)

    with temporary_worktree(repo, "main") as worktree:
        outcome = apply_strategy(
            worktree.path,
            branch="feat/task-1",
            strategy=strategy,
            default_branch="main",
            starting_sha=main_before,
        )
        assert worktree.path.is_dir()

    assert outcome.result == "succeeded"
    assert outcome.sha is not None
    new_main = git(repo, "rev-parse", "main").stdout.strip()
    # The merged result really IS the default branch now (T17's sha).
    assert new_main == outcome.sha
    # The dev tree's files are byte-identical (only refs moved).
    assert _snapshot(repo) == before

    if strategy == FAST_FORWARD_ONLY:
        assert new_main == feature_tip
    elif strategy == SQUASH:
        assert len(_parents(repo, "main")) == 1  # a single new commit
        subject = git(repo, "log", "--format=%s", "-1", "main").stdout.strip()
        assert subject.startswith("Squashed commit")  # Git's default message
    elif strategy == MERGE_COMMIT:
        parents = _parents(repo, "main")
        assert len(parents) == 2  # a true merge commit, branch history kept
        assert set(parents) == {main_before, feature_tip}

    assert not worktree.path.exists()  # destroyed on the success path too


# --- failures that must take the T18 report path ------------------------------


def test_merge_strategy_fast_forward_only_reports_non_ff_as_failed(
    wt_root: Path, tmp_path: Path
) -> None:
    """Diverged ``main`` under ``fast_forward_only`` → failed, nothing forced."""
    repo = _repo_with_feature(tmp_path, diverge_main=True)
    main_before = git(repo, "rev-parse", "main").stdout.strip()
    before = _snapshot(repo)

    with temporary_worktree(repo, "main") as worktree:
        outcome = apply_strategy(
            worktree.path,
            branch="feat/task-1",
            strategy=FAST_FORWARD_ONLY,
            default_branch="main",
            starting_sha=main_before,
        )

    assert outcome.result == "failed"
    assert outcome.sha is None
    assert "fast-forward" in outcome.details  # git's own refusal text
    assert git(repo, "rev-parse", "main").stdout.strip() == main_before
    assert _snapshot(repo) == before


def test_merge_strategy_empty_merge_is_failed_not_success(wt_root: Path, tmp_path: Path) -> None:
    """A branch tip already inside ``main`` is an empty merge → failed (11.4)."""
    repo = _repo_with_feature(tmp_path)
    git(repo, "merge", "--ff-only", "-q", "feat/task-1")  # main already has it
    main_before = git(repo, "rev-parse", "main").stdout.strip()

    with temporary_worktree(repo, "main") as worktree:
        outcome = apply_strategy(
            worktree.path,
            branch="feat/task-1",
            strategy=FAST_FORWARD_ONLY,
            default_branch="main",
            starting_sha=main_before,
        )

    assert outcome.result == "failed"
    assert "empty merge" in outcome.details
    assert git(repo, "rev-parse", "main").stdout.strip() == main_before


def test_merge_strategy_landing_refuses_a_concurrent_default_branch_move(
    wt_root: Path, tmp_path: Path
) -> None:
    """CAS landing: a default branch moved mid-merge is never forced over."""
    repo = _repo_with_feature(tmp_path)
    main_at_cut = git(repo, "rev-parse", "main").stdout.strip()

    with temporary_worktree(repo, "main") as worktree:
        # The developer commits to main while the merge runs elsewhere.
        write_files(repo, {"concurrent.md": "moved under the executor\n"})
        commit_all(repo, "main: concurrent developer commit")
        concurrent = git(repo, "rev-parse", "main").stdout.strip()
        assert concurrent != main_at_cut

        outcome = apply_strategy(
            worktree.path,
            branch="feat/task-1",
            strategy=MERGE_COMMIT,
            default_branch="main",
            starting_sha=main_at_cut,
        )

    assert outcome.result == "failed"
    assert "concurrently" in outcome.details
    # The developer's new tip survives — refusal, never a force-reset.
    assert git(repo, "rev-parse", "main").stdout.strip() == concurrent


# --- OQ-06: manual never produces an executor merge attempt -------------------


def test_merge_strategy_manual_is_refused_before_any_git_process(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``manual`` raises by structure — no runner call is even attempted."""
    attempts: list[tuple[str, ...]] = []

    def _record(cwd: Path, args: list[str], **kwargs: Any) -> Any:
        attempts.append(tuple(args))
        raise AssertionError("manual must never reach a git process")

    monkeypatch.setattr(strategies_module, "run_executor_git", _record)
    with pytest.raises(ValueError, match="not executable"):
        apply_strategy(
            tmp_path,
            branch="feat/task-1",
            strategy=MANUAL_STRATEGY,
            default_branch="main",
            starting_sha="0" * 40,
        )
    assert attempts == []


def test_merge_strategy_manual_queued_by_mistake_produces_no_merge_attempt(
    monkeypatch: pytest.MonkeyPatch, wt_root: Path, tmp_path: Path
) -> None:
    """The full step: a manual queue entry is resolved without opening a worktree."""
    repo = _repo_with_feature(tmp_path)

    def _forbid(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("a manual entry must never open a worktree")

    monkeypatch.setattr(strategy_step_module, "temporary_worktree", _forbid)
    outcome: MergeOutcome = WorktreeStrategyStep()(
        _queue_item(MANUAL_STRATEGY),
        repo,
        {"default_branch": "main", "repo_path": str(repo)},
    )
    assert outcome.result == "failed"
    assert outcome.sha is None
    assert "manual" in outcome.details and "no merge attempted" in outcome.details


# --- the queue row's strategy field (Section 7.2: default squash) -------------


def test_merge_strategy_defaults_to_squash_when_the_row_omits_it() -> None:
    row: dict[str, Any] = {
        "id": "PID00001-T001",
        "project_id": "PID00001",
        "title": "t",
        "state": "in_human_review",
        "version": 1,
        "merge_status": "pending",
        "branch_name": "feat/task-1",
    }
    assert QueueItem.from_payload(row).merge_strategy == SQUASH
    row["merge_strategy"] = MERGE_COMMIT
    assert QueueItem.from_payload(row).merge_strategy == MERGE_COMMIT


def test_merge_strategy_shapes_match_the_runner_allowlist() -> None:
    """Each strategy maps to exactly one structural runner shape (10.8)."""
    assert merge_shape_for(SQUASH, "b") == ["merge", "--squash", "b"]
    assert merge_shape_for(MERGE_COMMIT, "b") == ["merge", "--no-ff", "--no-edit", "b"]
    assert merge_shape_for(FAST_FORWARD_ONLY, "b") == ["merge", "--ff-only", "b"]
    # And every shape passes the runner's own validator (no process needed).
    from orchestrator_bridge.merge_executor.git_runner import _SUBCOMMAND_VALIDATORS

    for strategy in _EXECUTABLE:
        _SUBCOMMAND_VALIDATORS["merge"](merge_shape_for(strategy, "b")[1:])
