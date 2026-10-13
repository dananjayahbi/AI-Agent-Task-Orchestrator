"""Branch naming derivation and the create-or-switch operation (parent plan
gap G-09, Sections 10.5, 10.6 rule 1, 10.8; MT-2.10-02).

G-09 settles the canonical branch name: the manifest's ``auto_branch_prefix``
plus the task's **index part** — ``feat/PID00007-T004`` — with the documented
default prefix ``feat/{PID}-`` when the manifest key is absent. This module is
the *single* derivation source (Section 20.5 traceability): ``claim_task``'s
returned branch name, the ``start_work`` prompt's instruction and the
submission evidence must all name what :func:`derive_branch_name` produces.

Input validation rejects rather than sanitizes (MT-2.10-02 risk note): a task
id that does not parse to an index part, or a prefix that would form an
invalid ref, raises a structured error — silently "fixing" the name would
create a branch the plan never specified and break the three-way agreement.

:func:`ensure_branch` is the create-or-switch operation: refuse a dirty tree
(agent work never mixes with pre-existing changes), then create the branch
from the configured default branch or switch to it if it exists — through
the MT-2.10-01 capability guard, the only mutating Git the helper performs
besides worktree add.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..api_errors import ErrorCode
from .errors import GitHelperError
from .repo import clean_state
from .runner import run_git

__all__ = [
    "DEFAULT_BRANCH_PREFIX_TEMPLATE",
    "TASK_ID_PATTERN",
    "BranchSwitch",
    "create_or_switch_branch",
    "derive_branch_name",
]

#: The documented default prefix template (G-09 / Section 10.3 policy
#: default): ``{PID}`` is filled from the task id at derivation time.
DEFAULT_BRANCH_PREFIX_TEMPLATE: Final = "feat/{PID}-"

#: The canonical task id shape (Section 9.2 examples): project id, dash,
#: ``T`` + index digits. Group ``index`` is the ``-Txxxx`` segment itself
#: (G-09's "task index part").
TASK_ID_PATTERN: Final = re.compile(r"\A(?P<pid>PID[0-9]{5})-(?P<index>T[0-9]+)\Z")

# --- ref-name validation (mirrors git check-ref-format's forbidden shapes) ----

_BAD_REF_CHARS: Final[frozenset[str]] = frozenset(" ~^:?*[\\")


def _invalid_ref_problem(name: str) -> str | None:
    """Return why *name* is not a valid branch ref, or ``None`` when valid.

    The checks mirror ``git check-ref-format``'s documented rules for branch
    names — enough to guarantee the helper never asks Git to create an
    invalid ref (Git itself remains the final authority and its refusal is
    surfaced as a structured error).
    """
    if not name:
        return "the branch name is empty"
    if name == "@" or name.startswith("@{"):
        return "'@' and '@{' are reserved"
    if name.startswith("-"):
        return "the branch name starts with '-' (Git would read it as a flag)"
    if name.startswith("."):
        return "the branch name starts with '.'"
    if name.endswith("/") or name.endswith("."):
        return "the branch name ends with '/' or '.'"
    if name.endswith(".lock"):
        return "the branch name ends with '.lock'"
    if "/" in name and any(
        not part or part.startswith(".") or part.endswith(".lock") for part in name.split("/")
    ):
        return "a path segment is empty, starts with '.', or ends with '.lock'"
    if ".." in name:
        return "the branch name contains '..'"
    if "//" in name:
        return "the branch name contains '//'"
    if "@" + "{" in name:
        return "the branch name contains '@{'"
    if any(ch in _BAD_REF_CHARS or ord(ch) < 0x20 or ord(ch) == 0x7F for ch in name):
        return "the branch name contains whitespace, control, or ':^~?*[' characters"
    return None


def _reject_ref(name: str, problem: str, *, subject: str) -> GitHelperError:
    return GitHelperError(
        ErrorCode.VALIDATION_ERROR,
        f"cannot form a valid branch name from the {subject} ({name!r}): {problem}.",
        hint="G-09 fixes the canonical form: manifest 'auto_branch_prefix' plus "
        "the task index part (example: 'feat/PID00007-' + 'T004').",
        next_action="Fix the task id or the manifest's auto_branch_prefix so "
        "they match the canonical shapes; the helper never rewrites them.",
        details={"value": name, "problem": problem},
    )


@dataclass(frozen=True, slots=True)
class BranchSwitch:
    """What :func:`create_or_switch_branch` did."""

    branch: str
    created: bool
    head_sha: str

    def as_dict(self) -> dict[str, str | bool]:
        return {"branch": self.branch, "created": self.created, "head_sha": self.head_sha}


def derive_branch_name(task_id: str, *, auto_branch_prefix: str | None = None) -> str:
    """The G-09 canonical branch name for *task_id* (pure, no Git).

    ``derive_branch_name("PID00007-T004")`` with the documented default
    prefix yields ``"feat/PID00007-T004"``; a manifest
    ``auto_branch_prefix`` always wins over the default (MT-2.10-02
    acceptance) and is used verbatim — no placeholder substitution, no
    sanitizing.
    """
    parsed = TASK_ID_PATTERN.match(task_id)
    if parsed is None:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"task id {task_id!r} does not match the canonical shape 'PID#####-T###'.",
            hint="the branch index part comes from the task id's '-Txxxx' "
            "segment (Section 9.2 examples; G-09).",
            next_action="Pass the backend-issued task id verbatim (for example 'PID00007-T004').",
            details={"task_id": task_id},
        )
    prefix = (
        auto_branch_prefix
        if auto_branch_prefix is not None and auto_branch_prefix != ""
        else DEFAULT_BRANCH_PREFIX_TEMPLATE.replace("{PID}", parsed.group("pid"))
    )
    branch = f"{prefix}{parsed.group('index')}"
    problem = _invalid_ref_problem(branch)
    if problem is not None:
        raise _reject_ref(branch, problem, subject="derived branch name")
    return branch


def _verify_ref(root: Path, ref: str, *, role: str, hint_ref: str) -> str:
    result = run_git(root, ["rev-parse", "--verify", "--quiet", ref])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"the {role} {hint_ref!r} does not exist in this repository.",
            hint="branch creation starts from the manifest's default branch; "
            "a missing default means the local clone is behind or misconfigured.",
            next_action="Fetch or create the default branch locally (outside "
            "the helper), then retry the task workflow.",
            details={"ref": ref, "role": role},
        )
    return result.stdout.strip()


def create_or_switch_branch(
    root: Path,
    branch: str,
    *,
    default_branch: str,
) -> BranchSwitch:
    """Create *branch* from *default_branch* or switch to it (MT-2.10-02).

    Preconditions, in order: the branch name is a valid ref (never a Git
    flag), the working tree is clean, the default branch exists. Creation
    and switching run through the capability guard — reads plus branch
    creation only (Section 10.8).
    """
    problem = _invalid_ref_problem(branch)
    if problem is not None:
        raise _reject_ref(branch, problem, subject="branch name")
    if _invalid_ref_problem(default_branch) is not None:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"default branch name {default_branch!r} is not a valid ref.",
            hint="the default branch comes from the manifest's 'default_branch' "
            "key (Section 10.3).",
            next_action="Correct the manifest's default_branch, then retry.",
            details={"default_branch": default_branch},
        )

    state = clean_state(root)
    if not state.clean:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"the working tree of {str(root)!r} is not clean "
            f"({state.uncommitted_changes} uncommitted change(s), "
            f"{state.untracked_files} untracked file(s)"
            f"{', operation in progress' if state.operation_in_progress else ''}).",
            hint="Section 10.6 rule 1: an agent works only on its task branch — "
            "pre-existing changes must never be mixed into agent work "
            "(MT-2.10-02 clean-state precondition).",
            next_action="Commit, stash (outside the helper), or discard the "
            "pre-existing changes, then claim the task again.",
            details=state.as_dict(),
        )

    default_ref = f"refs/heads/{default_branch}"
    branch_ref = f"refs/heads/{branch}"
    _verify_ref(root, default_ref, role="default branch", hint_ref=default_branch)

    exists = run_git(root, ["rev-parse", "--verify", "--quiet", branch_ref]).ok
    if exists:
        switched = run_git(root, ["switch", branch])
        created = False
    else:
        switched = run_git(root, ["switch", "-c", branch, default_branch])
        created = True
    if not switched.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not {'switch to' if exists else 'create'} branch {branch!r}.",
            hint="'git switch' failed after the guard approved the operation — "
            "the repository state may have changed underneath the helper.",
            next_action="Retry the operation; if it persists, inspect the "
            "repository state ('git status') manually.",
            retryable=True,
            details={"git_error": switched.stderr.strip()[:500], "branch": branch},
        )

    head = run_git(root, ["rev-parse", "HEAD"])
    head_sha = head.stdout.strip() if head.ok else ""
    return BranchSwitch(branch=branch, created=created, head_sha=head_sha)
