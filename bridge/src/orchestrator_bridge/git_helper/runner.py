"""Capability-guarded Git invocation (parent plan Sections 10.8, 12.3;
MT-2.10-01).

One entry point for every Git call the helper makes — :func:`run_git` — and
the guard is **structural**: an explicit subcommand allowlist (read-only
operations plus branch creation, exactly Section 10.8's "read operations plus
branch creation") with a per-subcommand argument validator, default-deny for
everything else. ``push``, ``reset``, ``clean``, ``rebase``, ``commit``,
``fetch``, ``tag -d``, ``branch -D``, ``worktree remove`` and friends cannot
be issued through the helper, on any platform, by any caller — the refusal
happens before a process exists.

Invocation discipline (Section 12.3):

* arguments are always a sequence — never a shell string; ``shell=False``;
* the command runs with ``cwd`` set to the repository root and no caller
  global options (``--git-dir``, ``--work-tree``, ``-c`` …) — ``args[0]``
  must be the subcommand itself;
* the environment is scrubbed: no interactive prompts, no pager, no
  user/system config (aliases or ``core.*`` settings cannot redefine an
  allowed subcommand into a different behavior), fixed locale;
* a timeout bounds every call so a locked repository degrades to a
  structured error instead of a hung agent.

Failures raise :class:`~git_helper.errors.GitHelperError`; a non-zero exit
that the guard permits is returned to the caller as
:class:`GitResult` (expected outcomes like "branch does not exist yet" are
data, not exceptions).
"""

from __future__ import annotations

import os
import subprocess  # noqa: S404 - arguments are a list, shell=False, env scrubbed
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..api_errors import ErrorCode
from .errors import GitHelperError

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "GitResult",
    "run_git",
]

#: A local Git operation should never take longer; a lock contention or a
#: pathological repository surfaces as a structured error, not a hang.
DEFAULT_TIMEOUT_SECONDS: Final = 30.0

_LOGGER_COMPONENT = "git.helper"

#: Fixed ``-c`` options every invocation carries (machine-format outputs are
#: locale- and quoting-stable: non-ASCII paths arrive verbatim, not octal
#: escaped — MT-2.10-06's path contract). Applied by the runner itself;
#: callers cannot add or override ``-c`` options (args[0] must be a
#: subcommand).
_FIXED_GIT_OPTIONS: Final[tuple[str, ...]] = (
    "-c",
    "core.quotepath=false",
    "-c",
    "color.ui=false",
    "--no-pager",
)

#: Subcommands that read state only — no flag they accept can mutate refs or
#: the working tree. ``--output`` (``log``/``diff`` file output) and the
#: external-diff/textconv switches are rejected globally below, so even these
#: cannot be steered into a write.
_READ_ONLY_SUBCOMMANDS: Final[frozenset[str]] = frozenset(
    {
        "cat-file",
        "describe",
        "diff",
        "ls-files",
        "ls-tree",
        "log",
        "merge-base",
        "rev-list",
        "rev-parse",
        "show",
        "status",
    }
)

#: Flags no subcommand may ever carry through this runner (global write or
#: code-execution vectors).
_GLOBALLY_FORBIDDEN_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--output",
        "--ext-diff",
        "--textconv",
    }
)

#: ``branch`` mutation flags — delete/move/copy/force/upstream edits are all
#: outside Section 10.8 (branch *creation* is ``git branch <name> [<start>]``).
_BRANCH_FORBIDDEN_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "-d",
        "-D",
        "--delete",
        "-m",
        "-M",
        "--move",
        "-c",
        "-C",
        "--copy",
        "-f",
        "--force",
        "--edit-description",
        "--set-upstream-to",
        "--unset-upstream",
    }
)

#: ``tag`` is list-only here: tag creation is not "branch creation", and
#: ``tag -d`` is a named Section 10.8 violation (refusal test).
_TAG_LIST_FLAGS: Final[frozenset[str]] = frozenset({"-l", "--list", "-n"})

#: ``switch`` mutation flags: ``-f``/``-C`` can discard work or re-point an
#: existing branch by force.
_SWITCH_FORBIDDEN_FLAGS: Final[frozenset[str]] = frozenset(
    {"-f", "--force", "--discard-changes", "-C", "--force-create"}
)

#: ``worktree`` sub-operations the helper may use (MT-2.10-05): list and add.
#: ``remove``/``prune``/``move``/``repair`` are deletions or mutations —
#: denied (worktree removal is a recorded OQ, not an implemented operation).
_WORKTREE_ALLOWED_SUBCOMMANDS: Final[frozenset[str]] = frozenset({"list", "add"})
_WORKTREE_ALLOWED_FLAGS: Final[frozenset[str]] = frozenset(
    {"--porcelain", "-b", "--detach", "-d", "--no-checkout", "--track", "--no-track"}
)


def _refusal(operation: str, reason: str) -> GitHelperError:
    return GitHelperError(
        ErrorCode.VALIDATION_ERROR,
        f"The Git helper refuses to run 'git {operation}'.",
        hint=f"the helper's capability allowlist (Section 10.8) forbids it: {reason}.",
        next_action="Perform destructive or network Git operations yourself, outside "
        "the orchestrator; the helper only reads and creates branches.",
        details={"operation": operation, "reason": reason},
    )


def _validate_read_only(args: Sequence[str]) -> None:
    """No extra rules beyond the global ones for pure read subcommands."""
    return None


def _validate_branch(args: Sequence[str]) -> None:
    for arg in args:
        if arg in _BRANCH_FORBIDDEN_FLAGS:
            raise _refusal(f"branch {arg}", "branch mutation flags are not allowed")
        if arg == "--":
            # `branch --` separates refs from pathspecs in ways this helper
            # never needs; deny rather than reason about each form.
            raise _refusal("branch --", "pathspec forms are not allowed")


def _validate_tag(args: Sequence[str]) -> None:
    # Listing only: `git tag`, `git tag -l [pattern]`. Without a list flag a
    # positional would *create* a tag (a ref write outside "branch
    # creation"); with `-l`/`--list` positionals are just name patterns.
    listing = any(arg in {"-l", "--list"} for arg in args)
    for arg in args:
        if not arg.startswith("-"):
            if not listing:
                raise _refusal("tag <name>", "tag creation is not branch creation")
            continue  # a list-filter pattern
        if arg in {"-n1", "-n2", "-n3"} or (arg.startswith("-n") and arg[2:].isdigit()):
            continue  # -n<num> list decorations
        if arg not in _TAG_LIST_FLAGS:
            raise _refusal(f"tag {arg}", "only listing ('tag -l') is allowed")


def _validate_switch(args: Sequence[str]) -> None:
    for arg in args:
        if arg in _SWITCH_FORBIDDEN_FLAGS:
            raise _refusal(f"switch {arg}", "forced switches can discard work")


def _validate_worktree(args: Sequence[str]) -> None:
    if not args:
        raise _refusal("worktree", "a worktree sub-operation is required (list/add)")
    subcommand = args[0]
    if subcommand not in _WORKTREE_ALLOWED_SUBCOMMANDS:
        raise _refusal(
            f"worktree {subcommand}",
            "only 'worktree list' and 'worktree add' exist for the helper "
            "(removal is an unimplemented OQ, never a silent delete)",
        )
    for arg in args[1:]:
        if arg.startswith("-") and arg not in _WORKTREE_ALLOWED_FLAGS:
            raise _refusal(f"worktree {subcommand} {arg}", "flag outside the allowlist")


_SUBCOMMAND_VALIDATORS: Final[dict[str, Callable[[Sequence[str]], None]]] = {
    **{name: _validate_read_only for name in _READ_ONLY_SUBCOMMANDS},
    "branch": _validate_branch,
    "switch": _validate_switch,
    "tag": _validate_tag,
    "worktree": _validate_worktree,
}


@dataclass(frozen=True, slots=True)
class GitResult:
    """One completed, guard-approved Git invocation."""

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _clean_env() -> dict[str, str]:
    """A deterministic environment: no aliases, no prompts, no pager.

    ``GIT_CONFIG_GLOBAL``/``GIT_CONFIG_SYSTEM``/``GIT_CONFIG_NOSYSTEM``
    neutralize user and system config so an allowed subcommand cannot be
    redefined (alias) or re-behaved (``core.*``) from outside the helper.
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


def run_git(
    repo_root: Path,
    args: Sequence[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> GitResult:
    """Run one allowlisted Git command inside *repo_root*.

    Raises :class:`GitHelperError` for a guard refusal (before any process
    runs), an unusable ``repo_root``, or a timeout. A permitted command that
    exits non-zero is *returned* (:class:`GitResult`) — callers decide what
    "branch does not exist" means for their flow.
    """
    if not args:
        raise _refusal("(no arguments)", "a Git subcommand is required")
    if any("\x00" in arg for arg in args):
        raise _refusal("(binary argument)", "NUL bytes are not valid Git arguments")
    subcommand = args[0]
    if subcommand.startswith("-"):
        # Global options (--git-dir, --work-tree, -c, --exec-path, …) could
        # redirect or redefine the command; the runner owns its own prefix.
        raise _refusal(subcommand, "global Git options are not accepted from callers")
    validator = _SUBCOMMAND_VALIDATORS.get(subcommand)
    if validator is None:
        raise _refusal(subcommand, "subcommand is not on the allowlist")
    for arg in args:
        if arg in _GLOBALLY_FORBIDDEN_FLAGS or arg.split("=", 1)[0] in _GLOBALLY_FORBIDDEN_FLAGS:
            raise _refusal(f"{subcommand} {arg}", "flag can write files or run programs")
    validator(args[1:])  # the subcommand itself is args[0]; validators see the rest

    root = Path(repo_root)
    if not root.is_dir():
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"repository root {str(root)!r} is not an existing directory.",
            hint="the helper only runs Git inside an existing repository root "
            "(Section 12.3 — no operation outside it).",
            next_action="Point the helper at the manifest-discovered repository root.",
        )

    # The command line must *start* with the program name: Windows parses
    # the executable from the first token, and the runner's fixed ``-c``
    # prefix would be mistaken for it. "git" is resolved through the normal
    # PATH/PATHEXT search on every OS.
    command = ["git", *_FIXED_GIT_OPTIONS, *args]
    try:
        completed = subprocess.run(  # noqa: S603 - list args, shell=False, scrubbed env
            command,
            cwd=root,
            env=_clean_env(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"'git {subcommand}' exceeded its {timeout:g}s budget in {str(root)!r}.",
            hint="a Git lock or an unresponsive filesystem held the command "
            "past the helper's timeout.",
            next_action="Check for stale index/refs locks in .git and retry.",
            retryable=True,
            details={"subcommand": subcommand},
        ) from exc
    except OSError as exc:  # git binary missing / not executable
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not execute Git in {str(root)!r} ({type(exc).__name__}).",
            hint="the 'git' executable must be installed and on PATH — the "
            "helper shells out to the system Git (Section 10.8).",
            next_action="Install Git and ensure 'git' resolves on PATH, then retry.",
            details={"subcommand": subcommand},
        ) from exc

    return GitResult(
        args=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
