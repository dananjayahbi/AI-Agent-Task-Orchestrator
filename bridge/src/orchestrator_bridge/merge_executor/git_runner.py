"""Executor-scoped Git runner (parent plan Sections 10.8, 11.4, 12.3; WP-3.7).

Sibling of :mod:`orchestrator_bridge.git_helper.runner` with a *different*
capability envelope: the Git helper is agent-facing (reads plus branch
creation only), while the Merge Executor must create and destroy its own
temporary worktrees (Section 11.4 steps 2/5 and WP-3.7's "cleanup
guarantees" deliverable). The invocation discipline is identical —
sequence arguments only (never a shell string), ``shell=False``, a
scrubbed environment (no aliases, prompts, pager or user/system config),
runner-owned global options, a bounded timeout — and the allowlist is
again structural (default-deny before any process exists):

* ``worktree list --porcelain`` — leftover detection (the enumerable
  input MT-3.7-06's reconciliation consumes);
* ``worktree add --detach`` — the isolated merge workspace; ``--detach``
  creates **no branch and no ref**, so cleanup never has a ref to delete;
* ``worktree remove [--force]`` — cleanup on every exit path;
  ``--force`` exists only because a conflicted merge legitimately leaves
  the worktree dirty, and callers must containment-check the path
  against the executor's temp directory *before* invoking (worktree.py);
* ``rev-parse --verify`` — guards: the repo is a repository, the default
  branch exists, the merged result is a commit.
* ``merge --squash | --ff-only | --no-ff [--no-edit] <branch>`` — the
  three executable strategies' merge shapes (MT-3.7-04; each strategy
  must carry exactly one of the three mode flags), plus ``merge --abort``
  — the clean conflict unwind (the worktree removal that follows is the
  guaranteed cleanup either way; a squash conflict leaves no MERGE_HEAD
  so ``--abort`` there is best-effort, recorded);
* ``commit --no-edit`` — the squash commit, message from Git's own
  default (``SQUASH_MSG``; the risk note's "reuse the default Git
  behavior"). Authorship resolves through Git's normal identity chain
  under this runner's scrubbed config: repo-local ``user.*`` first, then
  OS autodetect — global/system config never leaks in (Section 10.8), so
  a repository with neither identity fails cleanly into the T18 report
  path rather than inventing metadata;
* ``update-ref refs/heads/<branch> <sha> <sha>`` — landing the merged
  result on the default branch (Section 11.4 "merge into the default
  branch"; MT-3.7-04). Exactly three arguments — a ``refs/heads/`` name
  and two hex object ids — so the old-value (CAS) form is the *only*
  shape accepted: a concurrent move of the branch refuses the landing
  instead of being forced over. This is a ref update, never a push, a
  reset or a delete (Section 10.8's discipline, inherited).

No ``push``, no ``reset``, no branch/tag deletion — Section 10.8's
discipline, inherited by the executor (ADR-008: the backend never
touches repos; the executor touches only its throwaway worktrees and
advances the local default branch only through the CAS form above).
"""

from __future__ import annotations

import os
import re  # noqa: S405 - compile-time literals only, never user input
import subprocess  # noqa: S404 - arguments are a list, shell=False, env scrubbed
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .errors import MergeExecutorError

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "GitRun",
    "run_executor_git",
]

#: One local Git operation should never take longer; a lock or a broken
#: repository degrades to a structured error, never a hung executor.
DEFAULT_TIMEOUT_SECONDS: Final = 30.0

#: Fixed ``-c`` options every invocation carries (machine-format output is
#: locale- and quoting-stable). The runner owns its prefix; callers can
#: never add or override global options.
_FIXED_GIT_OPTIONS: Final[tuple[str, ...]] = (
    "-c",
    "core.quotepath=false",
    "-c",
    "color.ui=false",
    "--no-pager",
)

#: Subcommands this runner will ever see (MT-3.7-03's lifecycle plus
#: MT-3.7-04's strategy shapes). Anything else — push, reset, fetch,
#: branch -D, clean, … — is refused by structure, before a process exists.
_ALLOWED_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {"rev-parse", "worktree", "merge", "commit", "update-ref"}
)

#: Per-verb flag allowlists (everything else refused, including short-flag
#: and ``--flag=value`` spellings via the shared prefix check below).
_WORKTREE_LIST_FLAGS: Final[frozenset[str]] = frozenset({"--porcelain"})
_WORKTREE_ADD_FLAGS: Final[frozenset[str]] = frozenset({"--detach"})
_WORKTREE_REMOVE_FLAGS: Final[frozenset[str]] = frozenset({"--force"})
_REV_PARSE_FLAGS: Final[frozenset[str]] = frozenset(
    {"--verify", "--quiet", "--end-of-options", "--git-dir"}
)
_MERGE_FLAGS: Final[frozenset[str]] = frozenset(
    {"--squash", "--ff-only", "--no-ff", "--no-edit", "--abort"}
)
_COMMIT_FLAGS: Final[frozenset[str]] = frozenset({"--no-edit"})
#: ``update-ref`` admits no flags at all — only the exact three-argument
#: ref/new/old (CAS) shape the validator below demands.
_UPDATE_REF_FLAGS: Final[frozenset[str]] = frozenset()

#: ``rev-parse --git-dir`` is the repo-identity guard (worktree.py's
#: pre-creation probe): a bare flag-only query that prints the git dir
#: and exits non-zero outside a repository — no ref to verify, so it is
#: the one flag-only invocation the validator admits.
_REPO_QUERY_FLAGS: Final[frozenset[str]] = frozenset({"--git-dir"})


@dataclass(frozen=True, slots=True)
class GitRun:
    """One completed, guard-approved executor Git invocation."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _refusal(operation: str, reason: str) -> MergeExecutorError:
    return MergeExecutorError(
        f"The Merge Executor refuses to run 'git {operation}'.",
        reason=f"the executor's capability allowlist (Section 10.8) forbids it: {reason}",
    )


def _validate_worktree(args: Sequence[str]) -> None:
    """Exactly list/add/remove, each with its own narrow flag set."""
    if not args:
        raise _refusal("worktree", "a worktree sub-operation is required (list/add/remove)")
    verb = args[0]
    flags_by_verb: dict[str, frozenset[str]] = {
        "list": _WORKTREE_LIST_FLAGS,
        "add": _WORKTREE_ADD_FLAGS,
        "remove": _WORKTREE_REMOVE_FLAGS,
    }
    allowed_flags = flags_by_verb.get(verb)
    if allowed_flags is None:
        raise _refusal(
            f"worktree {verb}",
            "only 'worktree list', 'worktree add --detach' and 'worktree remove' "
            "exist for the executor (move/repair/prune are never issued here)",
        )
    for arg in args[1:]:
        if not arg.startswith("-"):
            continue  # positional (path, commitish)
        if arg.split("=", 1)[0] not in allowed_flags:
            raise _refusal(f"worktree {verb} {arg}", "flag outside the verb's allowlist")
    if verb == "add" and "--detach" not in args[1:]:
        # A non-detached add would create a branch (a ref cleanup debt);
        # --detach keeps the worktree ref-free by construction.
        raise _refusal("worktree add", "--detach is required (no temporary refs)")


def _validate_rev_parse(args: Sequence[str]) -> None:
    for arg in args:
        if arg.startswith("-") and arg.split("=", 1)[0] not in _REV_PARSE_FLAGS:
            raise _refusal(f"rev-parse {arg}", "flag outside the allowlist")
    if any(not arg.startswith("-") for arg in args):
        return  # a ref to verify is present
    if any(arg.split("=", 1)[0] in _REPO_QUERY_FLAGS for arg in args if arg.startswith("-")):
        return  # flag-only repo-identity query (``--git-dir``), no ref needed
    raise _refusal("rev-parse", "a ref to verify is required")


#: The four merge shapes MT-3.7-04 ever issues: the three strategy modes
#: (each exactly one mode flag + the task branch) and the conflict abort.
#: Anything else (plain ``git merge``, extra flags, pathspecs) is refused
#: by structure — a strategy never falls back to Git's default mode.
_MERGE_SHAPES: Final[tuple[frozenset[str], ...]] = (
    frozenset({"--squash"}),
    frozenset({"--ff-only"}),
    frozenset({"--no-ff", "--no-edit"}),
)


def _validate_merge(args: Sequence[str]) -> None:
    """Exactly the strategy shapes above, or a lone ``--abort``."""
    if not args:
        raise _refusal("merge", "a merge shape is required (strategy flag or --abort)")
    for arg in args:
        if arg.startswith("-") and arg.split("=", 1)[0] not in _MERGE_FLAGS:
            raise _refusal(f"merge {arg}", "flag outside the allowlist")
    if args == ["--abort"]:
        return  # the clean conflict unwind — no branch, no mode
    flags = frozenset(arg for arg in args if arg.startswith("-"))
    positionals = [arg for arg in args if not arg.startswith("-")]
    if len(positionals) != 1:
        raise _refusal(
            f"merge {' '.join(args)}",
            "exactly one task-branch positional is required (no pathspecs, no ranges)",
        )
    if flags not in _MERGE_SHAPES:
        raise _refusal(
            f"merge {' '.join(args)}",
            "only the three strategy shapes (one of --squash/--ff-only/--no-ff) "
            "or a lone --abort exist for the executor",
        )


def _validate_commit(args: Sequence[str]) -> None:
    """Exactly ``commit --no-edit`` — Git's default message, no editor."""
    if list(args) != ["--no-edit"]:
        raise _refusal(
            f"commit {' '.join(args)}",
            "only 'commit --no-edit' exists for the executor (the squash commit; "
            "no staged-path selection, no message authoring)",
        )


#: ``update-ref`` targets: a real branch ref name and hex object ids
#: (40-hex SHA-1, or 64-hex SHA-256 repositories).
_SHA_PATTERN: Final = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def _is_branch_ref(ref: str) -> bool:
    """True when *ref* is a structurally safe ``refs/heads/`` name."""
    if not ref.startswith("refs/heads/"):
        return False
    name = ref.removeprefix("refs/heads/")
    if not name or name.startswith("/") or name.endswith(("/", ".")):
        return False
    if ".." in name or "@{" in name or name.endswith(".lock") or " " in name:
        return False
    if any(char in name for char in "~^:?*[\\" + "\x7f"):
        return False
    return re.fullmatch(r"[A-Za-z0-9._/-]+", name) is not None


def _validate_update_ref(args: Sequence[str]) -> None:
    """Exactly ``<refs/heads/…> <new-sha> <old-sha>`` — the CAS form only.

    The old-value argument is mandatory: the landing either moves the
    branch from the exact tip the worktree was cut from, or refuses —
    never force-overwrites a concurrent move (Section 10.8's no-force
    discipline carried into the ref update itself).
    """
    if len(args) != 3:
        raise _refusal(
            f"update-ref {' '.join(args)}",
            "exactly ref, new sha and old sha (the CAS form) are accepted — "
            "no deletions (-d), no dereference flags, no bare updates",
        )
    ref, new, old = args
    if not _is_branch_ref(ref):
        raise _refusal(f"update-ref {ref}", "only refs/heads/… targets are landed")
    if not _SHA_PATTERN.match(new) or not _SHA_PATTERN.match(old):
        raise _refusal(
            f"update-ref {' '.join(args)}",
            "both the new and old values must be full hex commit ids",
        )


_SUBCOMMAND_VALIDATORS: Final[dict[str, Callable[[Sequence[str]], None]]] = {
    "worktree": _validate_worktree,
    "rev-parse": _validate_rev_parse,
    "merge": _validate_merge,
    "commit": _validate_commit,
    "update-ref": _validate_update_ref,
}


def _clean_env() -> dict[str, str]:
    """A deterministic environment: no aliases, no prompts, no pager.

    ``GIT_CONFIG_GLOBAL``/``GIT_CONFIG_SYSTEM``/``GIT_CONFIG_NOSYSTEM``
    neutralize user and system config so an allowed subcommand cannot be
    redefined (alias) or re-behaved (``core.*``) from outside the runner.
    """
    env = dict(os.environ)
    null = os.devnull
    env.update(
        {
            "GIT_CONFIG_GLOBAL": null,
            "GIT_CONFIG_SYSTEM": null,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_PAGER": "cat",
            "LC_ALL": "C",
        }
    )
    return env


def run_executor_git(
    cwd: Path,
    args: Sequence[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> GitRun:
    """Run one allowlisted Git command with *cwd* as the working directory.

    Raises :class:`MergeExecutorError` for a guard refusal (before any
    process exists) or a timeout. A permitted command that exits non-zero
    is *returned* — callers decide what "branch missing" or "worktree
    busy" means for their flow (Section 11.4 reports, never retries
    blindly).
    """
    if not args:
        raise _refusal("(no arguments)", "a Git subcommand is required")
    if any("\x00" in arg for arg in args):
        raise _refusal("(binary argument)", "NUL bytes are not valid Git arguments")
    subcommand = args[0]
    if subcommand.startswith("-"):
        # Global options (--git-dir, --work-tree, -c, …) could redirect or
        # redefine the command; the runner owns its own prefix.
        raise _refusal(subcommand, "global Git options are not accepted from callers")
    if subcommand not in _ALLOWED_SUBCOMMANDS:
        raise _refusal(subcommand, "subcommand is not on the allowlist")
    _SUBCOMMAND_VALIDATORS[subcommand](args[1:])

    directory = Path(cwd)
    if not directory.is_dir():
        raise MergeExecutorError(
            f"working directory {str(directory)!r} is not an existing directory.",
            reason="the executor only runs Git inside existing directories "
            "(Section 12.3 — no operation outside the repo/worktree)",
        )

    command = ["git", *_FIXED_GIT_OPTIONS, *args]
    try:
        completed = subprocess.run(  # noqa: S603 - list args, shell=False, env scrubbed
            command,
            cwd=directory,
            env=_clean_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MergeExecutorError(
            f"git {' '.join(args)} timed out after {timeout}s.",
            reason="a locked or pathological repository must degrade to a "
            "structured error, never a hung executor (Section 12.3)",
        ) from exc
    return GitRun(
        args=tuple(args),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
