"""Merge-base diff, stats and changed-file list (parent plan Sections 9.7,
10.8; MT-2.10-03).

The evidence bundle Section 9.7 defines for submission: a unified patch of
the task branch **versus the merge-base** of the task branch and the
manifest's default branch — never a naive branch-vs-default-HEAD or worktree
diff (the divergent-base fixture test is the guard that keeps every
downstream Policy Engine rule, R2–R6, honest). The backend recomputes
authoritative stats from the uploaded patch; this module reports the same
numbers locally plus the patch byte size callers use for the 5 MB cap
decision (truncation is the upload path's job, not this helper's).

Output-path normalization is the Section 12.3 / MT-2.10-06 contract:
repository-relative, forward-slash paths on every OS. Git emits forward
slashes natively; :func:`_normalize_repo_path` is the belt-and-braces
normalization the contract pins by test.

Read-only through the capability guard — every call is ``rev-parse``,
``merge-base`` or ``diff``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api_errors import ErrorCode
from .errors import GitHelperError
from .runner import run_git

__all__ = ["ChangedFile", "DiffStats", "MergeBaseDiff", "merge_base_diff"]


def _normalize_repo_path(raw: str) -> str:
    """Repository-relative, forward-slash path (the cross-OS contract)."""
    return raw.replace("\\", "/")


@dataclass(frozen=True, slots=True)
class ChangedFile:
    """One file in the changed-file list (name-status + numstat merged)."""

    path: str
    status: str  # A / M / D / T / etc. from `git diff --name-status`
    insertions: int
    deletions: int
    binary: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "status": self.status,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "binary": self.binary,
        }


@dataclass(frozen=True, slots=True)
class DiffStats:
    """Insertions/deletions totals plus the changed-file count."""

    insertions: int
    deletions: int
    files_changed: int

    def as_dict(self) -> dict[str, int]:
        return {
            "insertions": self.insertions,
            "deletions": self.deletions,
            "files_changed": self.files_changed,
        }


@dataclass(frozen=True, slots=True)
class MergeBaseDiff:
    """The Section 9.7 evidence bundle for one task branch."""

    merge_base_sha: str
    head_sha: str
    default_branch: str
    branch: str
    patch: str
    patch_size_bytes: int
    stats: DiffStats
    changed_files: tuple[ChangedFile, ...]

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe view minus the patch body (large; carried separately)."""
        return {
            "merge_base_sha": self.merge_base_sha,
            "head_sha": self.head_sha,
            "default_branch": self.default_branch,
            "branch": self.branch,
            "patch_size_bytes": self.patch_size_bytes,
            "stats": self.stats.as_dict(),
            "changed_files": [entry.as_dict() for entry in self.changed_files],
        }


def _verify_branch(root: Path, branch: str, role: str) -> str:
    if not branch or branch.startswith("-") or "\x00" in branch:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"{role} name {branch!r} is not usable as a Git ref argument.",
            hint="the helper takes plain branch names; the manifest supplies "
            "the default branch and the G-09 derivation the task branch.",
            next_action="Pass the branch name exactly as the manifest or the "
            "derivation produced it.",
            details={"ref": branch, "role": role},
        )
    ref = f"refs/heads/{branch}"
    result = run_git(root, ["rev-parse", "--verify", "--quiet", ref])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            f"the {role} {branch!r} does not exist in this repository.",
            hint="the diff needs both the task branch and the default branch "
            "to exist locally (Section 9.7).",
            next_action="Fetch or create the branch locally (outside the helper), then retry.",
            details={"ref": ref, "role": role},
        )
    return ref


def _resolve(root: Path, ref: str) -> str:
    result = run_git(root, ["rev-parse", ref])
    if not result.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            f"could not resolve {ref!r} to a commit sha.",
            hint="'git rev-parse' failed after --verify succeeded — the ref "
            "moved or the repository became unreadable.",
            next_action="Retry; if it persists, inspect the repository state.",
            retryable=True,
            details={"ref": ref},
        )
    return result.stdout.strip()


def _merge_base(root: Path, branch_ref: str, default_ref: str) -> str:
    result = run_git(root, ["merge-base", branch_ref, default_ref])
    if not result.ok or not result.stdout.strip():
        raise GitHelperError(
            ErrorCode.VALIDATION_ERROR,
            "the branch and its default branch share no common ancestor — "
            "their histories are unrelated.",
            hint="a merge-base diff is undefined across unrelated histories "
            "(Section 9.7); a mis-created branch or an unrelated default "
            "produces this state.",
            next_action="Recreate the task branch from the default branch, or "
            "report the repository situation to the owner.",
            details={"branch_ref": branch_ref, "default_ref": default_ref},
        )
    return result.stdout.strip()


def _parse_name_status(raw: str) -> dict[str, str]:
    """``-z`` name-status: ``STATUS\\0path\\0`` pairs (renames disabled)."""
    statuses: dict[str, str] = {}
    tokens = raw.split("\0")
    index = 0
    while index + 1 < len(tokens):
        status, path = tokens[index], tokens[index + 1]
        if status and path:
            statuses[_normalize_repo_path(path)] = status[:1]
        index += 2
    return statuses


def _parse_numstat(raw: str) -> dict[str, tuple[int, int, bool]]:
    """``-z`` numstat: ``added\\tdeleted\\tpath\\0``; binary rows are ``-``."""
    stats: dict[str, tuple[int, int, bool]] = {}
    for entry in raw.split("\0"):
        if not entry:
            continue
        added, deleted, path = entry.split("\t", 2)
        binary = added == "-" or deleted == "-"
        stats[_normalize_repo_path(path)] = (
            0 if binary else int(added),
            0 if binary else int(deleted),
            binary,
        )
    return stats


def _unified_patch(root: Path, merge_base: str, head: str) -> str:
    result = run_git(
        root,
        [
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--unified=3",
            "--no-renames",
            merge_base,
            head,
        ],
    )
    if not result.ok:
        raise GitHelperError(
            ErrorCode.SERVER_ERROR,
            "could not compute the unified patch for the task branch.",
            hint="'git diff' failed after both refs resolved — the repository "
            "became unreadable or a diff driver misbehaved.",
            next_action="Retry; if it persists, inspect the repository state.",
            retryable=True,
            details={"git_error": result.stderr.strip()[:500]},
        )
    return result.stdout


def merge_base_diff(root: Path, branch: str, default_branch: str) -> MergeBaseDiff:
    """The Section 9.7 evidence bundle for *branch* vs *default_branch*.

    All four evidence products — merge-base sha, head sha, unified patch
    with byte size, and stats/changed-file lists — come from one consistent
    pair of resolved refs, so downstream consumers (WP-2.6 submission,
    Policy Engine R2–R6 inputs) never see mixed bases.
    """
    base = Path(root)
    branch_ref = _verify_branch(base, branch, "task branch")
    default_ref = _verify_branch(base, default_branch, "default branch")

    merge_base = _merge_base(base, branch_ref, default_ref)
    head = _resolve(base, branch_ref)

    name_status_result = run_git(
        base, ["diff", "--name-status", "--no-renames", "-z", merge_base, head]
    )
    numstat_result = run_git(base, ["diff", "--numstat", "--no-renames", "-z", merge_base, head])
    for failed in (name_status_result, numstat_result):
        if not failed.ok:
            raise GitHelperError(
                ErrorCode.SERVER_ERROR,
                "could not compute the changed-file evidence for the task branch.",
                hint="'git diff' failed after both refs resolved — the "
                "repository became unreadable.",
                next_action="Retry; if it persists, inspect the repository state.",
                retryable=True,
                details={"git_error": failed.stderr.strip()[:500]},
            )
    name_status = _parse_name_status(name_status_result.stdout)
    numstat = _parse_numstat(numstat_result.stdout)

    changed_files: list[ChangedFile] = []
    for path in sorted(name_status):
        insertions, deletions, binary = numstat.get(path, (0, 0, False))
        changed_files.append(
            ChangedFile(
                path=path,
                status=name_status[path],
                insertions=insertions,
                deletions=deletions,
                binary=binary,
            )
        )

    patch = _unified_patch(base, merge_base, head)
    stats = DiffStats(
        insertions=sum(entry.insertions for entry in changed_files),
        deletions=sum(entry.deletions for entry in changed_files),
        files_changed=len(changed_files),
    )
    return MergeBaseDiff(
        merge_base_sha=merge_base,
        head_sha=head,
        default_branch=default_branch,
        branch=branch,
        patch=patch,
        patch_size_bytes=len(patch.encode("utf-8")),
        stats=stats,
        changed_files=tuple(changed_files),
    )
