"""Local Git helper (parent plan Section 10.8; FR-MCP-07; WP-2.10).

Read-mostly Git operations with a structural capability guard: the helper
uses only read operations plus branch creation (and opt-in worktree add) —
it **never pushes, force-resets, or deletes**, on any platform, because
:func:`git_helper.runner.run_git` default-denies every other invocation
(:mod:`git_helper.runner` owns the allowlist; refusal tests pin it).

Capabilities (Section 10.8, in slice order):

* :func:`~git_helper.repo.repo_identity` / :func:`~git_helper.repo.clean_state`
  — repository identity and clean-state checks (MT-2.10-01);
* :func:`~git_helper.branch.derive_branch_name` /
  :func:`~git_helper.branch.create_or_switch_branch`
  — G-09 canonical branch naming and the create-or-switch operation
  (MT-2.10-02);
* :func:`~git_helper.diff.merge_base_diff`
  — merge-base diff with stats and changed-file list, the Section 9.7
  evidence bundle (MT-2.10-03);
* :func:`~git_helper.secret_scan.scan_patch`
  — secret-like pattern scan of added lines, feeding Policy Engine rule R5
  (MT-2.10-04);
* :func:`~git_helper.worktree.task_worktree`
  — the optional per-task worktree helper, gated on the manifest's
  ``agent_hints.worktree_mode`` (MT-2.10-05; OQ-03).

Every operation takes an explicit repository root (never the process cwd),
so the same functions serve the main working tree or a per-task worktree —
the integration seam WP-2.6's submission capture uses. Failures are
:class:`~git_helper.errors.GitHelperError`: a Section 9.2 catalog code plus
the Section 10.5 hint/next-action pair.
"""

from __future__ import annotations

from .branch import (
    DEFAULT_BRANCH_PREFIX_TEMPLATE,
    TASK_ID_PATTERN,
    BranchSwitch,
    create_or_switch_branch,
    derive_branch_name,
)
from .diff import ChangedFile, DiffStats, MergeBaseDiff, merge_base_diff
from .errors import GitHelperError, failure_payload
from .repo import CleanState, RepoIdentity, clean_state, repo_identity
from .runner import GitResult, run_git
from .secret_scan import (
    SecretFinding,
    SecretPattern,
    SecretScanResult,
    load_patterns,
    scan_patch,
)
from .worktree import RegisteredWorktree, WorktreeOutcome, inspect_worktree, task_worktree

__all__ = [
    "DEFAULT_BRANCH_PREFIX_TEMPLATE",
    "TASK_ID_PATTERN",
    "BranchSwitch",
    "ChangedFile",
    "CleanState",
    "DiffStats",
    "GitHelperError",
    "GitResult",
    "MergeBaseDiff",
    "RegisteredWorktree",
    "RepoIdentity",
    "SecretFinding",
    "SecretPattern",
    "SecretScanResult",
    "WorktreeOutcome",
    "clean_state",
    "create_or_switch_branch",
    "derive_branch_name",
    "failure_payload",
    "inspect_worktree",
    "load_patterns",
    "merge_base_diff",
    "repo_identity",
    "run_git",
    "scan_patch",
    "task_worktree",
]
