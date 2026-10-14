"""The three executable merge strategies inside the temp worktree (MT-3.7-04).

Section 11.4 step 3: "Merge the task branch using the project's
``merge_strategy``." Section 7.2 defines ``squash`` / ``merge_commit`` /
``fast_forward_only`` (default ``squash``); OQ-06's fourth value
``manual`` never reaches this module — :func:`apply_strategy` refuses it
by structure, and the queue-side guard (backend ``merge`` app) keeps
manual projects out of the executor queue entirely.

Each strategy issues exactly one of the runner's structural merge shapes
(git_runner.py), then **lands** the result on the default branch with the
CAS ``update-ref refs/heads/<branch> <new> <old>`` form: the branch moves
from exactly the tip the worktree was cut from, or the landing refuses —
a concurrent move of the default branch is never forced over (Section
10.8's no-force discipline; the executor still never pushes — whether a
remote receives the merged branch stays the open owner decision recorded
in MT-3.7-02).

Failure classification feeds Section 11.4 step 4 directly:

* a merge output containing ``CONFLICT`` (git's verbatim marker) is a
  ``conflict`` — ``merge --abort`` is issued best-effort (it cannot
  unwind a *squash* conflict: no ``MERGE_HEAD`` exists, so the MT-3.7-03
  worktree removal that always follows is the guaranteed cleanup; a
  ``reset`` stays forbidden by Section 10.8);
* every other non-zero exit (non-fast-forward under ``fast_forward_only``,
  an empty merge, a refused landing, a missing commit identity under the
  scrubbed config) is ``failed``;
* both feed T18 with the offending git output as ``details``.

Recorded choices (the plan fixes neither): the squash commit message is
Git's own ``SQUASH_MSG`` default (``commit --no-edit`` — risk note:
"reuse the default Git behavior"), and authorship resolves through Git's
identity chain under the runner's scrubbed environment (repo-local
``user.*``, else OS autodetect) — no metadata conventions are invented.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .git_runner import GitRun, run_executor_git

__all__ = [
    "FAST_FORWARD_ONLY",
    "MANUAL_STRATEGY",
    "MERGE_COMMIT",
    "SQUASH",
    "STRATEGY_VALUES",
    "StrategyOutcome",
    "apply_strategy",
    "merge_shape_for",
    "worktree_head",
]

#: Section 7.2's three executable values, verbatim (Section 20.5: no
#: renamed or extra strategy names may ever exist).
SQUASH: Final = "squash"
MERGE_COMMIT: Final = "merge_commit"
FAST_FORWARD_ONLY: Final = "fast_forward_only"
STRATEGY_VALUES: Final[frozenset[str]] = frozenset({SQUASH, MERGE_COMMIT, FAST_FORWARD_ONLY})

#: OQ-06's fourth value — never executable, refused by structure here.
MANUAL_STRATEGY: Final = "manual"

#: Git prints one ``CONFLICT (kind): …`` line per colliding path (or
#: ``CONFLICT (content): Merge conflict in <path>``) — the details T18
#: carries, parsed without a second git invocation.
_CONFLICT_LINE: Final = re.compile(r"^CONFLICT\b.*$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class StrategyOutcome:
    """One strategy attempt's classification (the loop's MergeOutcome source)."""

    result: str  # succeeded | conflict | failed (Section 7.2 values)
    sha: str | None = None  # the resulting sha on success (T17's guard)
    details: str = ""  # conflict lines / git error summary for T18


def merge_shape_for(strategy: str, branch: str) -> list[str]:
    """The one ``git merge`` invocation *strategy* is allowed to issue.

    Raises :class:`ValueError` for anything outside the three executable
    values — callers (the worktree step) never translate an unknown or
    ``manual`` value into a git command.
    """
    if strategy == SQUASH:
        return ["merge", "--squash", branch]
    if strategy == MERGE_COMMIT:
        return ["merge", "--no-ff", "--no-edit", branch]
    if strategy == FAST_FORWARD_ONLY:
        return ["merge", "--ff-only", branch]
    raise ValueError(
        f"merge strategy {strategy!r} is not executable "
        f"(Section 7.2 executable values: {sorted(STRATEGY_VALUES)})"
    )


def worktree_head(worktree: Path) -> str | None:
    """The worktree's current HEAD, or None when it cannot be read.

    Used twice around a strategy attempt: before (the landing's CAS old
    value) and after (the resulting sha).
    """
    run = run_executor_git(worktree, ["rev-parse", "--verify", "--quiet", "HEAD"])
    return run.stdout.strip() if run.ok else None


def _summarize(run: GitRun, *, limit: int = 600) -> str:
    """Git's own error text, trimmed — what the T18 details carry."""
    text = run.stderr.strip() or run.stdout.strip() or f"git exit {run.returncode}"
    return text if len(text) <= limit else text[: limit - 1] + "\N{HORIZONTAL ELLIPSIS}"


def _conflict_details(run: GitRun) -> str:
    """The ``CONFLICT`` lines of the merge output (the file list contract)."""
    lines = _CONFLICT_LINE.findall(run.stdout + "\n" + run.stderr)
    return "\n".join(line.strip() for line in lines)


def apply_strategy(
    worktree: Path,
    *,
    branch: str,
    strategy: str,
    default_branch: str,
    starting_sha: str,
) -> StrategyOutcome:
    """Merge ``branch`` per ``strategy`` and land it on ``default_branch``.

    Everything runs inside ``worktree`` (MT-3.7-03's isolation); the
    developer's checkout is only touched through the single CAS ref
    update at the end. ``starting_sha`` is the tip the worktree was cut
    from — the landing's compare-and-swap old value.

    Returns a classification; it raises only for programming errors
    (an unknown strategy value), never for merge outcomes.
    """
    shape = merge_shape_for(strategy, branch)  # ValueError: unknown / manual
    merge = run_executor_git(worktree, shape)
    if not merge.ok:
        if "CONFLICT" in (merge.stdout + merge.stderr):
            # Best effort — always followed by the worktree's removal.
            run_executor_git(worktree, ["merge", "--abort"])
            return StrategyOutcome(
                result="conflict",
                details=_conflict_details(merge) or _summarize(merge),
            )
        return StrategyOutcome(result="failed", details=_summarize(merge))

    if strategy == SQUASH:
        commit = run_executor_git(worktree, ["commit", "--no-edit"])
        if not commit.ok:
            # Empty squash ("nothing to commit") or no resolvable commit
            # identity under the scrubbed config — either way T18, never
            # a forced or invented commit.
            return StrategyOutcome(result="failed", details=_summarize(commit))

    sha = worktree_head(worktree)
    if sha is None:
        return StrategyOutcome(
            result="failed",
            details="the merged HEAD could not be read after the merge",
        )
    if sha == starting_sha:
        return StrategyOutcome(
            result="failed",
            details=(
                "empty merge: the task branch tip is already part of the default "
                "branch — nothing to integrate (Section 11.4 step 4)"
            ),
        )

    landing = run_executor_git(
        worktree,
        ["update-ref", f"refs/heads/{default_branch}", sha, starting_sha],
    )
    if not landing.ok:
        return StrategyOutcome(
            result="failed",
            details=(
                f"the merged result {sha[:12]} could not be landed on "
                f"{default_branch!r} (the default branch moved concurrently — "
                f"refused, never forced): {_summarize(landing)}"
            ),
        )
    return StrategyOutcome(
        result="succeeded",
        sha=sha,
        details=f"{strategy}: {branch} merged into {default_branch}",
    )
