"""Repository identity and clean-state checks (parent plan Sections 10.8,
10.3 step 1, 12.3; MT-2.10-01).

The foundation every later capability builds on:

* :func:`repo_identity` — confirm *root* is inside a Git work tree, resolve
  its top-level directory, and (when the session's manifest-discovered root
  is known) confirm the two agree. A mismatch is a structured error before
  anything else runs — the helper must never collect evidence from a
  repository other than the one the session bound to (Section 10.3).
* :func:`clean_state` — a structured report of the working tree: clean or
  not, counts of uncommitted and untracked entries, and whether a
  merge/rebase/cherry-pick/revert is in progress. Reporting only — the
  helper never enforces cleanliness here (submission-time enforcement is
  WP-2.6's; MT-2.10-01 scope note) except where a later slice (branch
  creation) requires it.

Paths are compared with :func:`os.path.normcase` (case-insensitive on
Windows — drive letters and path case would otherwise fake a mismatch) and
resolved through :meth:`Path.resolve` so symlinked spellings of one root
compare equal.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api_errors import ErrorCode
from .errors import GitHelperError
from .runner import GitResult, run_git

__all__ = ["CleanState", "RepoIdentity", "clean_state", "repo_identity"]


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def _require_work_tree(root: Path) -> GitResult:
    result = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if result.ok and result.stdout.strip() == "true":
        return result
    raise GitHelperError(
        ErrorCode.VALIDATION_ERROR,
        f"{str(root)!r} is not inside a Git working tree.",
        hint="the Git helper operates on the manifest-discovered repository "
        "root (Section 10.3 step 1); this path is not in one.",
        next_action="Run the agent inside the project repository, or point the "
        "session at the correct repository root.",
        details={"path": str(root)},
    )


@dataclass(frozen=True, slots=True)
class RepoIdentity:
    """What "this is the expected repository" resolved to."""

    root: Path
    toplevel: Path
    git_dir: Path

    def as_dict(self) -> dict[str, str]:
        """JSON-safe view for tool/flow consumers."""
        return {
            "root": str(self.root),
            "toplevel": str(self.toplevel),
            "git_dir": str(self.git_dir),
        }


def repo_identity(root: Path, *, expected_root: Path | None = None) -> RepoIdentity:
    """Resolve and verify repository identity from *root* (MT-2.10-01).

    *root* may be any directory inside the work tree (the helper resolves
    the top level itself); ``expected_root`` is the session's
    manifest-discovered root. Identity mismatch raises — no status, no diff,
    no branch work happens against the wrong repository.
    """
    base = Path(root)
    _require_work_tree(base)

    toplevel = _top_level(base)
    if expected_root is not None and not _same_path(toplevel, Path(expected_root)):
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"repository root {str(base)!r} belongs to {str(toplevel)!r}, "
            f"not the session's expected root {str(expected_root)!r}.",
            hint="the session is bound to the manifest-discovered root "
            "(Section 10.3); Git evidence must come from that repository.",
            next_action="Rebind the session from the correct repository "
            "directory, or stop: this root is a different repository.",
            details={
                "resolved_toplevel": str(toplevel),
                "expected_root": str(Path(expected_root)),
            },
        )

    git_dir = _git_dir(base, toplevel)
    return RepoIdentity(root=base, toplevel=toplevel, git_dir=git_dir)


def _top_level(base: Path) -> Path:
    result = run_git(base, ["rev-parse", "--show-toplevel"])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"could not resolve the repository top level from {str(base)!r}.",
            hint="'git rev-parse --show-toplevel' failed — the directory may "
            "have vanished, or the repository metadata is unreadable.",
            next_action="Verify the repository exists and its .git is readable, then retry.",
            details={"git_error": result.stderr.strip()[:500]},
        )
    return Path(result.stdout.strip())


def _git_dir(base: Path, toplevel: Path) -> Path:
    result = run_git(base, ["rev-parse", "--absolute-git-dir"])
    if result.ok:
        return Path(result.stdout.strip())
    return toplevel / ".git"  # standard layout fallback; identity already verified


@dataclass(frozen=True, slots=True)
class CleanState:
    """The structured working-tree report (MT-2.10-01 acceptance)."""

    clean: bool
    uncommitted_changes: int
    untracked_files: int
    merge_in_progress: bool
    rebase_in_progress: bool
    cherry_pick_in_progress: bool
    revert_in_progress: bool

    @property
    def operation_in_progress(self) -> bool:
        return (
            self.merge_in_progress
            or self.rebase_in_progress
            or self.cherry_pick_in_progress
            or self.revert_in_progress
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "uncommitted_changes": self.uncommitted_changes,
            "untracked_files": self.untracked_files,
            "merge_in_progress": self.merge_in_progress,
            "rebase_in_progress": self.rebase_in_progress,
            "cherry_pick_in_progress": self.cherry_pick_in_progress,
            "revert_in_progress": self.revert_in_progress,
        }


def _operation_flags(git_dir: Path) -> dict[str, bool]:
    """Detect in-progress operations from the well-known marker paths."""
    return {
        "merge_in_progress": (git_dir / "MERGE_HEAD").exists(),
        "rebase_in_progress": (git_dir / "rebase-merge").is_dir()
        or (git_dir / "rebase-apply").is_dir(),
        "cherry_pick_in_progress": (git_dir / "CHERRY_PICK_HEAD").exists(),
        "revert_in_progress": (git_dir / "REVERT_HEAD").exists(),
    }


def clean_state(root: Path) -> CleanState:
    """Report the working-tree state of the repository at *root*.

    Uses ``git status --porcelain=v1 -z`` (machine format, one NUL-separated
    entry per path — spaces and non-ASCII never break the parse; MT-2.10-06).
    Untracked directories count as their single ``dir/`` entry, matching
    Git's own summary.
    """
    base = Path(root)
    _require_work_tree(base)
    identity = repo_identity(base)

    result = run_git(base, ["status", "--porcelain=v1", "-z", "--untracked-files=normal"])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not read the working-tree state of {str(base)!r}.",
            hint="'git status' failed — the repository metadata may be unreadable or locked.",
            next_action="Check .git readability and locks, then retry.",
            retryable=True,
            details={"git_error": result.stderr.strip()[:500]},
        )

    uncommitted = 0
    untracked = 0
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        status = entry[:2]
        if status == "??":
            untracked += 1
        else:
            uncommitted += 1

    flags = _operation_flags(identity.git_dir)
    return CleanState(
        clean=uncommitted == 0 and untracked == 0 and not any(flags.values()),
        uncommitted_changes=uncommitted,
        untracked_files=untracked,
        **flags,
    )
