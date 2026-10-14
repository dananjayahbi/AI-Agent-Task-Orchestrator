"""The wired Section 11.4 merge step: worktree + strategy (MT-3.7-03/04).

Composition, deliberately in its own module so the loop (MT-3.7-02), the
worktree lifecycle (MT-3.7-03) and the strategies (MT-3.7-04) each stay
independently testable:

1. refuse ``manual`` **before any git process exists** (OQ-06: a manual
   project's task must never produce an executor merge attempt — the
   backend's queue-side guard keeps such entries out of the queue; this
   is the defense if one arrives anyway, e.g. a policy flipped after the
   claim);
2. validate the queue entry (a default branch from the project payload,
   a task branch from the resolution) — missing inputs are a ``failed``
   outcome with the reason, never an exception against a real queue row;
3. open MT-3.7-03's isolated temp worktree, capture the starting tip,
   run the project's strategy via :func:`apply_strategy`, and let the
   context manager destroy the worktree on **every** exit path (success,
   conflict, exception);

the outcome maps 1:1 onto the loop's ``MergeOutcome`` (succeeded+sha /
conflict / failed) so reporting stays the loop's contract.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .loop import MergeOutcome
from .queue import QueueItem
from .strategies import MANUAL_STRATEGY, StrategyOutcome, apply_strategy, worktree_head
from .worktree import temporary_worktree

__all__ = ["WorktreeStrategyStep"]


def _failed(details: str) -> MergeOutcome:
    return MergeOutcome(result="failed", details=details)


class WorktreeStrategyStep:
    """The ``resolve_merge_step``-returned :class:`MergeStep` implementation."""

    def __call__(
        self, item: QueueItem, repo_path: Path, project: Mapping[str, Any]
    ) -> MergeOutcome:
        """Merge ``item``'s branch in a throwaway worktree; classify the result.

        Never raises for merge outcomes: validation short-circuits return
        ``failed`` (the loop reports them through T18), and an unexpected
        exception is contained by the loop the same way.
        """
        if item.merge_strategy == MANUAL_STRATEGY:
            # No git process is started — structurally no merge attempt.
            return _failed(
                "merge_strategy 'manual' must never enter the executor queue "
                "(OQ-06: approval completes such tasks without a merge); "
                "no merge attempted"
            )
        default_branch = str(project.get("default_branch") or "").strip()
        if not default_branch:
            return _failed("the project payload declares no default_branch to merge into")
        if not item.branch_name:
            return _failed("the queue entry carries no task branch for this attempt")

        with temporary_worktree(repo_path, default_branch) as worktree:
            starting = worktree_head(worktree.path)
            if starting is None:
                return _failed(
                    f"the temporary worktree's HEAD could not be read at {default_branch!r}"
                )
            outcome = apply_strategy(
                worktree.path,
                branch=item.branch_name,
                strategy=item.merge_strategy,
                default_branch=default_branch,
                starting_sha=starting,
            )
        return _as_outcome(outcome)


def _as_outcome(outcome: StrategyOutcome) -> MergeOutcome:
    return MergeOutcome(result=outcome.result, sha=outcome.sha, details=outcome.details)
