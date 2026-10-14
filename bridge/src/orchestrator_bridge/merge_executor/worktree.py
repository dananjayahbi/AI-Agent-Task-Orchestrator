"""Isolated temporary worktrees for the Merge Executor (parent plan Sections
11.4 steps 2/5, 10.8, 16.3; ADR-007, ADR-008; WP-3.7 / MT-3.7-03).

Section 11.4 step 2 requires a *clean temporary worktree of the default
branch* before every merge attempt, and step 5 / Section 19 guarantee the
developer's working directory is never modified — all Git action lives in
a throwaway worktree, never in the directory a human works in
(Principle P2's host-side consequence; ADR-008).

Design (recorded choices — the plan fixes neither):

* **Location** — ``<system temp>/orchestrator-merge-worktrees/<repo>-
  <short-id>/``, i.e. a host-local temp dir *outside* every repository,
  so a worktree never pollutes ``git status`` (MT-3.7-03 risk note).
* **No refs** — worktrees are created ``--detach`` at the default
  branch's tip: cleanup therefore never deletes a branch, honoring
  Section 10.8's no-delete discipline by construction.
* **Cleanup on every exit path** — :func:`temporary_worktree` is a
  context manager whose ``finally`` removes the worktree (success,
  conflict, or exception); removal failures are retried briefly (Windows
  file-handle churn, RISK-15) and then **reported**, never silently
  passed.
* **Leftover detection** — :func:`list_leftover_worktrees` enumerates
  the executor's temp-root worktrees for a repository (recognizable by
  location + naming prefix), the enumerable input MT-3.7-06's restart
  reconciliation consumes.
* **Guards before creation** — the repository must actually be one
  (``rev-parse --git-dir``) and the default branch must exist
  (``rev-parse --verify``); failures are reported, not retried blindly
  (Section 11.4 step 2's "abort cleanly").
"""

from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from ..logging import get_logger
from .errors import MergeExecutorError
from .git_runner import run_executor_git

__all__ = [
    "TEMP_WORKTREE_PREFIX",
    "TEMP_WORKTREE_ROOT_NAME",
    "TempWorktree",
    "list_leftover_worktrees",
    "remove_leftover_worktree",
    "temporary_worktree",
    "temp_worktree_root",
]

#: Sub-directory of the system temp dir that holds every executor
#: worktree — one recognizable location for creation *and* cleanup.
TEMP_WORKTREE_ROOT_NAME: Final = "orchestrator-merge-worktrees"

#: Naming prefix inside the root: ``<repo-name>--<branch>--<short-id>``.
TEMP_WORKTREE_PREFIX: Final = "orchestrator-merge-"

#: Removal is retried this many times with a short pause before the
#: failure is reported (Windows can hold handles in a fresh worktree —
#: RISK-15; on POSIX the first attempt normally succeeds).
_REMOVE_ATTEMPTS: Final = 3
_REMOVE_RETRY_PAUSE_SECONDS: Final = 0.2

_LOGGER_COMPONENT = "merge-executor"


def temp_worktree_root() -> Path:
    """The host-local root every executor worktree lives under (outside all repos)."""
    return Path(tempfile.gettempdir()) / TEMP_WORKTREE_ROOT_NAME


class TempWorktree:
    """One created temporary worktree (Section 11.4 step 2's workspace).

    ``path`` is the worktree checkout; ``repo_path`` the developer's
    repository it was branched from (**never** written to);
    ``default_branch`` the branch whose tip was checked out (detached).
    """

    __slots__ = ("default_branch", "path", "repo_path")

    def __init__(self, path: Path, repo_path: Path, default_branch: str) -> None:
        self.path = path
        self.repo_path = repo_path
        self.default_branch = default_branch

    def __repr__(self) -> str:
        return (
            f"TempWorktree(path={str(self.path)!r}, repo_path={str(self.repo_path)!r}, "
            f"default_branch={self.default_branch!r})"
        )


def _fail(message: str, reason: str) -> MergeExecutorError:
    get_logger(_LOGGER_COMPONENT).error(
        message,
        extra={"event": "worktree_error", "reason": reason},
    )
    return MergeExecutorError(message, reason=reason)


def _is_within(child: Path, parent: Path) -> bool:
    """True when *child* resolves inside *parent* (containment check)."""
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _create(repo_path: Path, default_branch: str) -> TempWorktree:
    """Create one detached worktree of ``default_branch`` under the temp root."""
    repo = repo_path.resolve()
    if not repo.is_dir():
        raise _fail(
            f"repository path {str(repo_path)!r} is not an existing directory",
            reason="the allowlist entry must point at an existing checkout "
            "(Section 10.2 — guards before creation)",
        )
    probe = run_executor_git(repo, ["rev-parse", "--git-dir"])
    if not probe.ok:
        raise _fail(
            f"repository path {str(repo)!r} is not a Git repository",
            reason="rev-parse --git-dir failed; the executor only opens real "
            "checkouts (Section 10.2 guard, reported not retried)",
        )
    branch_probe = run_executor_git(repo, ["rev-parse", "--verify", "--quiet", default_branch])
    if not branch_probe.ok:
        raise _fail(
            f"default branch {default_branch!r} does not exist in {str(repo)!r}",
            reason="Section 11.4 step 2 aborts cleanly when the worktree base "
            "is missing; a blind retry cannot create the branch",
        )

    root = temp_worktree_root()
    root.mkdir(parents=True, exist_ok=True)
    short_id = uuid.uuid4().hex[:8]
    path = root / f"{TEMP_WORKTREE_PREFIX}{repo.name}--{default_branch}--{short_id}"
    add = run_executor_git(repo, ["worktree", "add", "--detach", str(path), default_branch])
    if not add.ok:
        raise _fail(
            f"creating the temporary worktree for {str(repo)!r} failed: "
            f"{add.stderr.strip() or add.stdout.strip() or f'git exit {add.returncode}'}",
            reason="worktree add failed; the merge attempt aborts cleanly "
            "(Section 11.4 — reported, never retried blindly)",
        )
    return TempWorktree(path=path, repo_path=repo, default_branch=default_branch)


def _destroy(worktree: TempWorktree, *, sleep: Callable[[float], None] = time.sleep) -> None:
    """Remove one worktree; retry briefly, then report — never silently pass."""
    root = temp_worktree_root()
    if not _is_within(worktree.path, root):
        # Defensive: the removal allowlist is "everything under our root".
        raise _fail(
            f"refusing to remove {str(worktree.path)!r}: outside the executor "
            f"temp root {str(root)!r}",
            reason="cleanup only ever deletes worktrees the executor created "
            "(Section 10.8 — no deletes outside the temp root)",
        )
    last_error = ""
    for attempt in range(1, _REMOVE_ATTEMPTS + 1):
        remove = run_executor_git(
            worktree.repo_path, ["worktree", "remove", "--force", str(worktree.path)]
        )
        if remove.ok and not worktree.path.exists():
            get_logger(_LOGGER_COMPONENT).info(
                "temporary worktree removed",
                extra={"event": "worktree_removed", "path": str(worktree.path)},
            )
            return
        last_error = (
            remove.stderr.strip() or remove.stdout.strip() or f"git exit {remove.returncode}"
        )
        if worktree.path.exists():
            # `worktree remove` can leave the directory behind on refusal;
            # it is ours (containment-checked above) — take it directly so
            # a conflicted worktree cannot pin the host temp dir forever.
            try:
                shutil.rmtree(worktree.path)
                get_logger(_LOGGER_COMPONENT).warning(
                    "worktree directory required direct removal",
                    extra={"event": "worktree_removed_forcibly", "path": str(worktree.path)},
                )
                return
            except OSError as exc:
                last_error = f"{type(exc).__name__}: {exc}"
        if attempt < _REMOVE_ATTEMPTS:
            sleep(_REMOVE_RETRY_PAUSE_SECONDS)
    raise _fail(
        f"failed to remove temporary worktree {str(worktree.path)!r} after "
        f"{_REMOVE_ATTEMPTS} attempts: {last_error}",
        reason="cleanup failures are reported, never silently passed "
        "(WP-3.7 cleanup guarantees; MT-3.7-06 reconciles leftovers)",
    )


@contextmanager
def temporary_worktree(
    repo_path: Path,
    default_branch: str,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[TempWorktree]:
    """Yield a clean detached worktree of ``default_branch``; remove it always.

    The single Section 11.4 step-2/step-5 seam: the merge step does all
    its Git work inside ``worktree.path`` and the developer's checkout is
    untouched. Every exit path — success, conflict, injected exception —
    runs cleanup; a cleanup failure raises (reported), it never passes
    silently.
    """
    worktree = _create(repo_path, default_branch)
    try:
        yield worktree
    finally:
        _destroy(worktree, sleep=sleep)


def list_leftover_worktrees(repo_path: Path) -> tuple[Path, ...]:
    """Enumerate this repository's executor worktrees still on disk.

    Recognizable by construction: they live under the executor temp root
    with :data:`TEMP_WORKTREE_PREFIX` names. The enumerable input
    MT-3.7-06's restart reconciliation consumes to clean up after a
    crash; nothing is removed here (enumeration is a read).
    """
    root = temp_worktree_root()
    if not root.is_dir():
        return ()
    repo_token = f"{Path(repo_path).resolve().name}--"
    leftovers = sorted(
        entry
        for entry in root.iterdir()
        if entry.is_dir()
        and entry.name.startswith(TEMP_WORKTREE_PREFIX)
        and repo_token in entry.name
    )
    return tuple(leftovers)


def remove_leftover_worktree(path: Path, repo_path: Path) -> None:
    """Remove one enumerated leftover (MT-3.7-06 startup cleanup).

    Containment-checked exactly like every other removal (the path must
    sit under the executor temp root), then torn down through the same
    retrying destroy. A leftover whose repository has vanished (or any
    other refusal from ``worktree remove``) falls back to a direct
    removal of the contained directory — the path *was* enumerated from
    the executor's own root, so it is ours by construction — and the
    fallback is logged, never silent (RISK-15's reported-cleanup rule).
    """
    root = temp_worktree_root()
    if not _is_within(path, root):
        raise _fail(
            f"refusing to remove leftover {str(path)}: outside the executor temp root {str(root)}",
            reason="cleanup only ever deletes worktrees the executor created "
            "(Section 10.8 — no deletes outside the temp root)",
        )
    try:
        _destroy(TempWorktree(path=path, repo_path=repo_path, default_branch=""))
    except MergeExecutorError:
        if not path.exists():
            return
        try:
            shutil.rmtree(path)
        except OSError as exc:
            raise _fail(
                f"failed to remove leftover worktree {str(path)}: {type(exc).__name__}: {exc}",
                reason="startup cleanup reports what it cannot remove; a "
                "leftover never becomes silent debris (MT-3.7-06)",
            ) from exc
        get_logger(_LOGGER_COMPONENT).warning(
            "leftover worktree required direct removal",
            extra={"event": "worktree_removed_forcibly", "path": str(path)},
        )
