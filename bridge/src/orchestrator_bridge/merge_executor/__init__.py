"""Host-side Merge Executor package (parent plan Sections 10.1 item 7, 10.2,
11.4; ADR-008; WP-3.7).

The Section 11.4 five-step loop as one sequential worker: poll the merge
queue (``GET /merge/pending``), claim an entry (``POST /merge/{task}/start``),
hand the allowlist-verified repo to the injected merge step (MT-3.7-03's
isolated temp worktree plus MT-3.7-04's strategy dispatch), and report the
outcome (``POST /merge/{task}/result``) with the resulting sha on success.

Layering:

* :mod:`.queue` â€” the typed Section 9.2 client (pending/start/result +
  project context) over the shared transport, one ADR-012 idempotency
  key per logical operation;
* :mod:`.loop` â€” the loop contract: sequential execution, the Section
  10.2 repo allowlist check *before* the claim, backoff on backend
  outages (Section 10.10) without duplicate completions, structured
  logging of every queue transition (MT-3.7-06's recovery input);
* :mod:`.step` â€” the wiring point for the Git work (never performed by
  the loop itself â€” Principle P2 / ADR-007 isolation): it resolves to
  the composed step in :mod:`.strategy_step` (MT-3.7-03's
  :mod:`.worktree` lifecycle around MT-3.7-04's :mod:`.strategies`).

The entry point lives in :mod:`orchestrator_bridge.entrypoints.executor`.
"""

from __future__ import annotations

from .errors import MergeExecutorError
from .journal import MergeJournal, journal_path
from .loop import (
    DEFAULT_POLL_SECONDS,
    MUTATION_BACKOFF_ATTEMPTS,
    OUTAGE_BACKOFF_CAP_SECONDS,
    MergeExecutorLoop,
    MergeOutcome,
    MergeReportError,
    MergeStep,
)
from .queue import (
    RESULT_CONFLICT,
    RESULT_FAILED,
    RESULT_SUCCEEDED,
    RESULT_VALUES,
    MergeQueueClient,
    MergeStart,
    QueueItem,
    QueuePage,
)
from .recovery import (
    ExecutorLock,
    MergeRecoveryError,
    acquire_executor_lock,
    cleanup_leftover_worktrees,
    reconcile_on_startup,
    startup_recovery,
)
from .step import resolve_merge_step
from .strategies import STRATEGY_VALUES, StrategyOutcome, apply_strategy
from .strategy_step import WorktreeStrategyStep
from .worktree import (
    TEMP_WORKTREE_PREFIX,
    TempWorktree,
    list_leftover_worktrees,
    temp_worktree_root,
    temporary_worktree,
)

__all__ = [
    "DEFAULT_POLL_SECONDS",
    "MUTATION_BACKOFF_ATTEMPTS",
    "OUTAGE_BACKOFF_CAP_SECONDS",
    "RESULT_CONFLICT",
    "RESULT_FAILED",
    "RESULT_SUCCEEDED",
    "RESULT_VALUES",
    "TEMP_WORKTREE_PREFIX",
    "ExecutorLock",
    "MergeExecutorError",
    "MergeExecutorLoop",
    "MergeJournal",
    "MergeOutcome",
    "MergeQueueClient",
    "MergeRecoveryError",
    "MergeReportError",
    "MergeStart",
    "MergeStep",
    "QueueItem",
    "QueuePage",
    "STRATEGY_VALUES",
    "StrategyOutcome",
    "TempWorktree",
    "WorktreeStrategyStep",
    "acquire_executor_lock",
    "apply_strategy",
    "cleanup_leftover_worktrees",
    "journal_path",
    "list_leftover_worktrees",
    "reconcile_on_startup",
    "resolve_merge_step",
    "startup_recovery",
    "temporary_worktree",
    "temp_worktree_root",
]
