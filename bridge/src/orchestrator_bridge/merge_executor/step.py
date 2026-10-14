"""Merge-step resolution for the Section 11.4 loop (MT-3.7-02; WP-3.7).

The loop owns the queue contract; *how* one task branch is merged lives
behind :class:`~orchestrator_bridge.merge_executor.loop.MergeStep`.
WP-3.7's pieces are now in place and this module is where they compose:

* MT-3.7-03's isolated temporary worktree (create/destroy around every
  attempt — the developer's tree stays untouched);
* MT-3.7-04's strategy dispatch (``squash`` / ``merge_commit`` /
  ``fast_forward_only`` from the queue entry's project ``merge_strategy``,
  with ``manual`` refused before any git process);

:class:`~orchestrator_bridge.merge_executor.strategy_step.WorktreeStrategyStep`
is the composed implementation; :func:`resolve_merge_step` is the single
wiring point the entry point calls **before** the first poll, so an
executor build can never start without its merge behavior in place.
"""

from __future__ import annotations

from ..config import Settings
from .loop import MergeStep
from .strategy_step import WorktreeStrategyStep

__all__ = ["resolve_merge_step"]


def resolve_merge_step(settings: Settings) -> MergeStep:
    """Return the wired merge step for this executor build.

    ``settings`` is the validated executor configuration (its
    ``merge_repo_paths`` allowlist was already enforced by
    ``config.validate_for_mode``); the step itself takes no configuration
    — the strategy comes from each queue entry (Section 7.2: never
    executor-side), the repository from the loop's allowlist check, and
    the worktree location from MT-3.7-03's module default.
    """
    del settings  # consumed by validation upstream; the step needs none of it
    return WorktreeStrategyStep()
