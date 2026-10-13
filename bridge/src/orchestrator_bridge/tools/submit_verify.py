"""Branch and commit-sha verification before submission (parent plan Sections
10.5, 10.8, 11.1; FR-MCP-07; ADR-007; MT-2.6-02).

Host-side only: the backend never accesses repositories (ADR-007) — the
bridge confirms, against the session's own working tree, that the evidence
the agent is about to submit is real and belongs to this task:

* **repository identity first** (Section 10.8): :func:`repo_identity` runs
  from the manifest's directory, so every later git call provably happens in
  the repository the session is bound to (WP-2.2); a path outside any work
  tree is rejected before a single status/diff call.
* **assigned branch**: the submitted ``git_branch`` must equal the WP-2.10
  strict derivation for this task (manifest prefix + task id, G-09) and must
  exist locally — rules block items 1 and 4 are what the agent is held to.
* **real, reachable commit**: ``commit_sha`` must be a hex object id that
  resolves to a commit and is an ancestor of the assigned branch — a
  non-existent sha or a sha from another branch/repository fails. Reachable,
  not necessarily the tip: capture re-verifies the tip at capture time
  (MT-2.6-03 risk note), so a branch that moves between check and capture
  fails loudly instead of submitting mixed evidence.
* **clean state** is *consumed* from WP-2.10's :func:`clean_state`, never
  re-implemented: an in-progress merge/rebase/cherry-pick/revert rejects
  (the tree is not in a committable state); dirty or untracked files are
  reported in the result so the submission outcome carries them (the patch
  is commit-keyed — working-tree state cannot leak into the evidence), and
  "commit work before submission" stays the agent's rule-4 obligation
  (recorded reading, WP-2.6 changelog).

Rejections use ``VALIDATION_ERROR`` — the plan names no dedicated code for a
bad branch/sha and Section 9.2 is a closed catalog (MT-2.6-02 risk note; the
choice is recorded in the WP changelog). Every rejection carries a hint and a
next action telling the agent to commit on the assigned branch and resubmit
(Section 10.5 tool rules).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..api_errors import ErrorCode
from ..error_translation import TranslatedError
from ..git_helper.branch import derive_branch_name
from ..git_helper.errors import GitHelperError
from ..git_helper.repo import clean_state, repo_identity
from ..git_helper.runner import run_git
from ..manifest import StartupBinding
from .errors import ToolFailure, failure_from_git_error

__all__ = ["SHA_PATTERN", "VerifiedSubmission", "verify_submission"]

#: Commit object ids the bridge accepts before any git call sees the string
#: (4–64 hex characters: abbreviated through full sha256-length ids; the
#: leading-dash rejection keeps flag injection out of the git argv).
SHA_PATTERN = re.compile(r"\A[0-9a-fA-F]{4,64}\Z")


@dataclass(frozen=True, slots=True)
class VerifiedSubmission:
    """What verification proved — the input capture and upload consume."""

    root: Path
    branch: str
    commit_sha: str  # the full, resolved object id (never the agent's spelling)
    working_tree: dict[str, Any]  # WP-2.10 clean-state report, JSON-safe


def _reject(message: str, *, hint: str, next_action: str, **details: Any) -> ToolFailure:
    """One structured VALIDATION_ERROR rejection (catalog code, MT-2.6-02)."""
    return ToolFailure(
        TranslatedError(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            hint=hint,
            next_action=next_action,
            retryable=False,
            details=details or None,
            correlation_id=None,
        )
    )


def _resolve_commit(root: Path, commit_sha: str, branch: str) -> str:
    """The full object id for *commit_sha*, reachable on *branch*."""
    resolved = run_git(root, ["rev-parse", "--verify", "--quiet", f"{commit_sha}^{{commit}}"])
    if not resolved.ok:
        raise _reject(
            f"commit_sha {commit_sha!r} does not resolve to a commit in this repository.",
            hint=(
                "the submission must point at a real commit on the assigned branch "
                "(rules item 4); a typo'd, garbage-collected or other-repository sha "
                "cannot be verified."
            ),
            next_action=(
                "Commit your work on the assigned branch, take the commit sha from "
                "git log, then call submit_task_resolution again."
            ),
            commit_sha=commit_sha,
            branch=branch,
        )
    full_sha = resolved.stdout.strip()
    reachable = run_git(root, ["merge-base", "--is-ancestor", full_sha, f"refs/heads/{branch}"])
    if not reachable.ok:
        raise _reject(
            f"commit {commit_sha!r} is not reachable on branch {branch!r}.",
            hint=(
                "the patch must come from the assigned branch (rules items 1 and 4); "
                "a commit from another branch or repository fails here."
            ),
            next_action=(
                "Submit the tip commit of the assigned branch, or merge your work into "
                "it, then call submit_task_resolution again."
            ),
            commit_sha=full_sha,
            branch=branch,
        )
    return full_sha


def verify_submission(
    binding: StartupBinding,
    *,
    task_id: str,
    git_branch: str,
    commit_sha: str,
) -> VerifiedSubmission:
    """Verify the agent's branch/sha claim against the bound repository.

    Raises a structured ``VALIDATION_ERROR`` tool failure (hint + next
    action) for every rejection; succeeds with the resolved evidence handed
    to :func:`orchestrator_bridge.tools.submit_capture.capture_patch`.
    Every WP-2.10 helper refusal (guard, unreadable repository) becomes the
    same structured failure — a git hiccup never reaches the model as a
    crash.
    """
    try:
        return _verify(binding, task_id=task_id, git_branch=git_branch, commit_sha=commit_sha)
    except GitHelperError as exc:
        raise failure_from_git_error(exc) from None


def _verify(
    binding: StartupBinding,
    *,
    task_id: str,
    git_branch: str,
    commit_sha: str,
) -> VerifiedSubmission:
    """The verification steps (identity → branch → sha → clean state)."""
    identity = repo_identity(binding.manifest_path.parent)
    expected_branch = derive_branch_name(
        task_id, auto_branch_prefix=str(binding.manifest["auto_branch_prefix"])
    )
    root = identity.toplevel

    if git_branch != expected_branch:
        raise _reject(
            f"git_branch {git_branch!r} is not this task's assigned branch.",
            hint=(
                f"the assigned branch for {task_id} is {expected_branch!r} (G-09: the "
                "manifest's auto_branch_prefix plus the task id); working outside it "
                "breaks rules item 1 and the evidence chain."
            ),
            next_action=(
                f"Commit your work on {expected_branch!r}, then call "
                "submit_task_resolution with that branch and its tip commit sha."
            ),
            task_id=task_id,
            submitted_branch=git_branch,
            assigned_branch=expected_branch,
        )
    branch_exists = run_git(root, ["rev-parse", "--verify", "--quiet", f"refs/heads/{git_branch}"])
    if not branch_exists.ok:
        raise _reject(
            f"the assigned branch {git_branch!r} does not exist in this repository.",
            hint=(
                "verification runs against the local repository (Section 10.8); the "
                "branch claim_task returned must exist before work is submitted."
            ),
            next_action=(
                "Create and switch to the assigned branch (claim_task returns its "
                "name), commit your work, then call submit_task_resolution again."
            ),
            branch=git_branch,
        )
    if SHA_PATTERN.fullmatch(commit_sha) is None:
        raise _reject(
            f"commit_sha {commit_sha!r} is not a usable commit object id.",
            hint=(
                "the bridge accepts 4–64 hexadecimal characters (abbreviated through "
                "full-length sha256 ids); anything else is refused before git sees it."
            ),
            next_action=(
                "Take the commit sha from git log on the assigned branch and call "
                "submit_task_resolution again."
            ),
            commit_sha=commit_sha,
        )
    full_sha = _resolve_commit(root, commit_sha, git_branch)

    state = clean_state(root)
    if state.operation_in_progress:
        raise _reject(
            "a merge, rebase, cherry-pick or revert is in progress in this repository.",
            hint=(
                "submission evidence must be a settled commit state; an in-progress "
                "operation (e.g. unresolved conflicts) cannot be honestly captured."
            ),
            next_action=(
                "Finish or abort the in-progress operation, commit the result on the "
                "assigned branch, then call submit_task_resolution again."
            ),
            working_tree=state.as_dict(),
        )
    return VerifiedSubmission(
        root=root,
        branch=git_branch,
        commit_sha=full_sha,
        working_tree=state.as_dict(),
    )
