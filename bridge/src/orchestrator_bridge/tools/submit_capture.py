"""Merge-base patch capture with stats and changed-file list (parent plan
Sections 9.7, 10.8; FR-MCP-07; MT-2.6-03).

The Section 9.7 evidence bundle, produced **after** MT-2.6-02's verification
and keyed to the verified commit:

* the helper's :func:`~orchestrator_bridge.git_helper.diff.merge_base_diff`
  computes one consistent pair (merge-base of the task branch and the
  manifest's **default branch**, head at the branch tip) — never a naive
  branch-vs-default-HEAD or working-tree diff, so Policy Engine R2–R6 inputs
  stay honest.
* **re-verification at capture** (the MT's risk note): the captured head
  must equal the verified sha, or the branch moved between check and capture
  and the submission fails loudly with a structured error instead of mixing
  evidence. Working-tree edits cannot matter — the diff is ref-to-ref.
* **the 5 MB cap** is *reported*, not enforced, on the wire path:
  ``diff_too_large`` mirrors WP-3.2's ``PATCH_MAX_BYTES`` comparison
  (``size > 5 * 1024 * 1024``, inclusive cap — the exact backend boundary,
  so neither side assumes the other truncates). The evidence view replaces
  the body with the literal ``"diff too large"`` marker; the upload still
  carries the full patch text because the backend parses the *received*
  bytes for its authoritative stats and stores per Section 9.7 (WP-3.2:
  "bridge prepares, backend stores"). The backend's receive bound is far
  above the cap, and an oversized-for-the-backend body surfaces as its
  ``VALIDATION_ERROR`` — never a silently truncated diff.
* read-only throughout (Section 10.8): the helper's allowlist forbids push,
  reset and delete.

Missing merge-base (shallow clones, unrelated histories) fails with the
helper's clear ``VALIDATION_ERROR`` rather than a wrong diff (MT-2.6-03
risk note).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from ..api_errors import ErrorCode
from ..error_translation import TranslatedError
from ..git_helper.diff import merge_base_diff
from ..git_helper.errors import GitHelperError
from .errors import ToolFailure, failure_from_git_error

__all__ = ["CAP_DEFAULT_MAX_BYTES", "DIFF_TOO_LARGE_MARKER", "CapturedPatch", "capture_patch"]

#: The Section 9.7 cap, mirrored from WP-3.2's ``PATCH_MAX_BYTES`` (backend
#: ``apps/tasks/services/resolutions.py``) — inclusive: at exactly this size
#: the body is still kept, one byte more is oversize. One boundary, two
#: sides (MT-2.6-03 risk note; the boundary tests on both sides pin it).
CAP_DEFAULT_MAX_BYTES: Final = 5 * 1024 * 1024

#: The literal WP-3.2 serves on the oversize path — copied, not invented.
DIFF_TOO_LARGE_MARKER: Final = "diff too large"


@dataclass(frozen=True, slots=True)
class CapturedPatch:
    """One task's Section 9.7 evidence, keyed to the verified commit."""

    branch: str
    commit_sha: str
    merge_base_sha: str
    patch: str  # full unified text — the upload body (backend stores per 9.7)
    patch_size_bytes: int
    diff_too_large: bool  # size > cap: the backend will store stats/file list only
    stats: dict[str, int]  # provisional {insertions, deletions, files_changed}
    changed_files: tuple[str, ...]  # provisional repo-relative paths

    def evidence(self) -> dict[str, Any]:
        """The compact, body-free view for the agent and the changelog tests.

        Oversize bundles carry the literal marker *instead of* the body
        (Section 9.7's viewer contract); either way the multi-megabyte diff
        never rides a tool response (Section 10.5 compact outputs).
        """
        return {
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "merge_base_sha": self.merge_base_sha,
            "patch_size_bytes": self.patch_size_bytes,
            "diff_too_large": self.diff_too_large,
            "marker": DIFF_TOO_LARGE_MARKER if self.diff_too_large else None,
            "stats": dict(self.stats),
            "changed_files": list(self.changed_files),
        }


def capture_patch(
    root: Path,
    *,
    branch: str,
    default_branch: str,
    expected_head_sha: str,
    max_bytes: int = CAP_DEFAULT_MAX_BYTES,
) -> CapturedPatch:
    """Capture the merge-base evidence for *branch* at the verified sha.

    ``expected_head_sha`` is MT-2.6-02's resolved commit: if the branch tip
    is no longer that commit, capture refuses (re-verify and resubmit) — the
    bundle can never mix a verified sha with a moved head.
    """
    try:
        diff = merge_base_diff(root, branch, default_branch)
    except GitHelperError as exc:
        raise failure_from_git_error(exc) from None
    if diff.head_sha != expected_head_sha:
        raise ToolFailure(
            TranslatedError(
                code=ErrorCode.VALIDATION_ERROR,
                message=(
                    f"branch {branch!r} moved since verification: its tip is no longer "
                    f"the submitted commit {expected_head_sha!r}."
                ),
                hint=(
                    "verification and capture must describe the same commit "
                    "(MT-2.6-02 risk note); another process committed to the branch "
                    "in between."
                ),
                next_action=(
                    "Call submit_task_resolution again with the branch's current tip "
                    "commit sha from git log."
                ),
                retryable=False,
                details={
                    "branch": branch,
                    "expected_head_sha": expected_head_sha,
                    "actual_head_sha": diff.head_sha,
                },
                correlation_id=None,
            )
        )
    return CapturedPatch(
        branch=branch,
        commit_sha=diff.head_sha,
        merge_base_sha=diff.merge_base_sha,
        patch=diff.patch,
        patch_size_bytes=diff.patch_size_bytes,
        diff_too_large=diff.patch_size_bytes > max_bytes,
        stats=diff.stats.as_dict(),
        changed_files=tuple(entry.path for entry in diff.changed_files),
    )
