"""Optional per-task worktree helper (parent plan Section 10.8, gap G-26,
OQ-03 decision; MT-2.10-05).

G-26 names the hazard — several agents on one repository share a working
directory — and OQ-03 settles the policy: **one concurrent task per project
by default**, with per-task worktrees as an opt-in later improvement. This
module is that opt-in, strictly additive:

* gated on the manifest's ``agent_hints.worktree_mode`` (default ``false``,
  Section 10.3): disabled means every call short-circuits with a
  ``WorktreeOutcome`` describing why, and **nothing** is created — the
  default single-working-directory flow cannot come to depend on this
  module (MT-2.10-05 risk note);
* enabled: one worktree per task at the documented location
  ``<repo>/.worktrees/<task id>`` — inside the repository's control
  (Section 12.3) and meant to be listed in the project's ``.gitignore`` so
  it stays out of the manifest-tracked tree (the helper never edits
  ``.gitignore`` itself); lookups are idempotent (an existing worktree for
  the task's canonical branch is returned, not duplicated); two tasks always
  yield distinct roots (the G-26 mitigation);
* teardown restraint (Section 10.8): the helper may *report* that a
  worktree exists and is stale (registered in Git but its directory is
  gone), but it never removes worktrees, branches or any other ref —
  removal is recorded as an open question (OQ-10), not implemented.

The canonical branch comes from :func:`git_helper.branch.derive_branch_name`
— the single G-09 derivation source — so a worktree, the main working tree
and ``claim_task``'s response all name the same branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from ..api_errors import ErrorCode
from .branch import derive_branch_name
from .errors import GitHelperError
from .runner import run_git

__all__ = [
    "WORKTREES_DIRNAME",
    "WorktreeOutcome",
    "RegisteredWorktree",
    "inspect_worktree",
    "list_worktrees",
    "task_worktree",
]

#: The documented location of per-task worktrees, relative to the repo root.
#: Inside the repository's control (Section 12.3) and gitignore-able so the
#: manifest-tracked tree never sees it.
WORKTREES_DIRNAME: Final = ".worktrees"


@dataclass(frozen=True, slots=True)
class WorktreeOutcome:
    """What one :func:`task_worktree` call resolved to."""

    enabled: bool
    task_id: str
    branch: str | None
    root: Path | None
    created: bool

    @property
    def disabled(self) -> bool:
        return not self.enabled

    def as_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "task_id": self.task_id,
            "branch": self.branch,
            "root": str(self.root) if self.root is not None else None,
            "created": self.created,
        }


@dataclass(frozen=True, slots=True)
class RegisteredWorktree:
    """One row of ``git worktree list --porcelain``."""

    root: Path
    head_sha: str
    branch: str | None
    detached: bool
    stale: bool  # registered in Git but the directory is gone (report only)


def _disabled(task_id: str) -> WorktreeOutcome:
    return WorktreeOutcome(enabled=False, task_id=task_id, branch=None, root=None, created=False)


def _task_worktree_root(repo_root: Path, task_id: str) -> Path:
    """The documented per-task root — task-id constrained, inside the repo.

    The task id is validated by the branch derivation (canonical shape, no
    separators), so the composed path cannot traverse outside the
    repository's ``.worktrees/`` directory (Section 12.3).
    """
    return repo_root / WORKTREES_DIRNAME / task_id


def list_worktrees(repo_root: Path) -> tuple[RegisteredWorktree, ...]:
    """Parse ``git worktree list --porcelain`` (paths may contain spaces)."""
    result = run_git(Path(repo_root), ["worktree", "list", "--porcelain"])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not list worktrees of {str(repo_root)!r}.",
            hint="'git worktree list' failed — the repository metadata may be unreadable.",
            next_action="Check .git readability, then retry.",
            retryable=True,
            details={"git_error": result.stderr.strip()[:500]},
        )
    entries: list[RegisteredWorktree] = []
    root: Path | None = None
    head = ""
    branch: str | None = None
    detached = False

    def _flush() -> None:
        nonlocal root, head, branch, detached
        if root is not None:
            entries.append(
                RegisteredWorktree(
                    root=root,
                    head_sha=head,
                    branch=branch,
                    detached=detached,
                    stale=not root.is_dir(),
                )
            )
        root, head, branch, detached = None, "", None, False

    for line in result.stdout.splitlines():
        if not line.strip():
            _flush()
            continue
        field, _, value = line.partition(" ")
        if field == "worktree":
            _flush()  # a new entry begins without a blank line in some versions
            root = Path(value)
        elif field == "HEAD":
            head = value
        elif field == "branch":
            branch = value.removeprefix("refs/heads/")
        elif field == "detached":
            detached = True
    _flush()
    return tuple(entries)


def inspect_worktree(repo_root: Path, task_id: str) -> RegisteredWorktree | None:
    """The registered worktree for *task_id*, or ``None`` — read-only.

    Matches on the documented per-task root (case-normalized so a
    differently-cased spelling of one Windows path still matches).
    """
    target = _task_worktree_root(Path(repo_root), task_id)
    for entry in list_worktrees(repo_root):
        if str(entry.root).lower() == str(target).lower():
            return entry
    return None


def task_worktree(
    repo_root: Path,
    task_id: str,
    *,
    worktree_mode: bool,
    default_branch: str,
    auto_branch_prefix: str | None = None,
) -> WorktreeOutcome:
    """Create or resolve the per-task worktree (MT-2.10-05).

    ``worktree_mode`` is the manifest's ``agent_hints.worktree_mode``
    (Section 10.3, default false): disabled is a structured no-op that
    creates nothing. Enabled derives the canonical task branch (G-09) and
    creates the worktree from ``default_branch`` when the branch is new, or
    attaches it when the branch already exists — through the capability
    guard (``worktree add`` plus branch creation only, Section 10.8).
    """
    if not worktree_mode:
        return _disabled(task_id)

    root = Path(repo_root)
    branch = derive_branch_name(task_id, auto_branch_prefix=auto_branch_prefix)

    existing = inspect_worktree(root, task_id)
    if existing is not None:
        if existing.stale:
            raise GitHelperError(
                ErrorCode.VALIDATION_ERROR,
                f"the worktree for {task_id!r} is registered at "
                f"{str(existing.root)!r} but its directory is gone (stale).",
                hint="the helper never removes worktrees (Section 10.8) — a "
                "stale registration must be cleaned up by an operator.",
                next_action="Run 'git worktree prune' yourself (outside the "
                "helper) to drop the stale registration, then retry.",
                details={"task_id": task_id, "root": str(existing.root)},
            )
        return WorktreeOutcome(
            enabled=True,
            task_id=task_id,
            branch=branch,
            root=existing.root,
            created=False,
        )

    target = _task_worktree_root(root, task_id)
    branch_ref = f"refs/heads/{branch}"
    branch_exists = run_git(root, ["rev-parse", "--verify", "--quiet", branch_ref]).ok
    target.parent.mkdir(parents=True, exist_ok=True)
    if branch_exists:
        added = run_git(root, ["worktree", "add", str(target), branch])
    else:
        added = run_git(root, ["worktree", "add", "-b", branch, str(target), default_branch])
    if not added.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not create the worktree for {task_id!r} at {str(target)!r}.",
            hint="'git worktree add' failed after the guard approved it — the "
            "target path may be occupied or the repository state changed.",
            next_action="Remove the obstructing directory (outside the helper) "
            "or retry; the helper never deletes paths itself.",
            retryable=True,
            details={"git_error": added.stderr.strip()[:500], "task_id": task_id},
        )
    return WorktreeOutcome(
        enabled=True,
        task_id=task_id,
        branch=branch,
        root=target,
        created=True,
    )
