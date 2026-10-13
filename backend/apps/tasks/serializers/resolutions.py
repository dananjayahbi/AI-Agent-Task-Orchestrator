"""Resolution serializers — Section 9.2 Submission row; Sections 7.2/10.5.

* ``ResolutionSubmitSerializer`` — the ``POST /tasks/{id}/resolution``
  input: Section 10.5's ``submit_task_resolution`` field names
  (``git_branch``, ``commit_sha``, ``execution_summary``,
  ``requires_human_attention``, ``risk_justification``) plus the
  ADR-012 fencing pair, the captured ``patch`` text, and the bridge's
  provisional ``changed_files``/``diff_summary`` claims — accepted for
  wire compatibility with MT-2.6-04 and **ignored** by the service
  (Section 9.7: the server's parse is the only authority). The server
  never accepts ``attempt_number``, ``submitted_by_session`` or
  ``submitted_at`` (P7; MT-3.2-01 risk note).
* ``ResolutionSerializer`` — the stored row as the API returns it: the
  twelve Section 7.2 fields, field for field (Section 20.5 traceability
  — nothing outside that set exists on the model or the wire).
* ``ResolutionWriteResponseSerializer`` — the frozen response: the
  stored row, the post-transition task identity (the bridge reports
  ``to_be_audited``/``in_human_review`` from it — Section 10.5) and the
  computed ``scope_violations`` (MT-3.2-04: offending paths captured on
  the submission path so the UI can show *why* review happened).
* ``ResolutionPatchSerializer`` — the ``GET /resolutions/{id}/patch``
  body: exactly one shape covering the stored patch and the Section 9.7
  "diff too large" degraded path.
* the listing envelope/query shapes — pagination.md's exact
  ``{results, next_cursor}`` contract.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin
from apps.tasks.models import Task, TaskResolution
from apps.tasks.services.resolutions import DIFF_TOO_LARGE_MARKER


class ResolutionSubmitSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /tasks/{id}/resolution`` input (Section 10.5 tool contract)."""

    session_id = serializers.CharField(
        max_length=255,
        help_text="Lease-holding session id (G-18) — the fencing pair's identity half; "
        "becomes submitted_by_session (Section 7.2).",
    )
    lease_generation = serializers.IntegerField(
        min_value=0,
        help_text="Fencing generation from the claim response (Section 8.6; "
        "ADR-012); a stale value answers LEASE_EXPIRED.",
    )
    git_branch = serializers.CharField(
        max_length=255,
        help_text="Verified branch the patch was captured from (Section 10.5; "
        "stored as the Section 7.2 branch_name).",
    )
    commit_sha = serializers.CharField(
        max_length=64,
        help_text="Commit the submission points at (Section 10.5; the bridge "
        "verified it matches the branch — stored verbatim).",
    )
    execution_summary = serializers.CharField(
        allow_blank=True,
        help_text="The coder's summary of what ran (Section 10.5).",
    )
    requires_human_attention = serializers.BooleanField(
        required=False,
        default=False,
        help_text="The coder's self-flag (Section 10.5) — true routes the "
        "submission to T8 with review_reason self_flagged (8.2/8.4).",
    )
    risk_justification = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="The coder's justification when self-flagging (Section 7.2).",
    )
    patch = serializers.CharField(
        allow_blank=True,
        trim_whitespace=False,
        help_text="The captured unified patch, branch vs. default-branch merge-base "
        "(Section 9.7) — parsed server-side for the authoritative "
        "changed_files and diff_summary; subject to the 5 MB cap with a "
        "degraded stats-only path, never a rejection. Whitespace (the "
        "trailing newline) is content: the sha256 the bridge computes "
        "locally must match the bytes stored here.",
    )
    changed_files = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_null=True,
        default=None,
        help_text="Bridge-captured file list (Section 10.5) — provisional: the "
        "server's patch parse replaces it outright (Section 9.7).",
    )
    diff_summary = serializers.DictField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Bridge-captured stats (Section 10.5) — provisional: the "
        "server's patch parse replaces it outright (Section 9.7).",
    )


class ResolutionSerializer(serializers.Serializer[Any]):
    """One stored resolution — the Section 7.2 field list, as returned."""

    id = serializers.UUIDField(help_text="Server-generated row identity (7.2).")
    task_id = serializers.CharField(help_text="The addressed task (Section 7.2).")
    attempt_number = serializers.IntegerField(
        help_text="The submission attempt this row answers (Section 7.2; unique per task)."
    )
    branch_name = serializers.CharField(help_text="Branch the patch came from (7.2).")
    commit_sha = serializers.CharField(help_text="Commit the submission points at (7.2).")
    execution_summary = serializers.CharField(allow_blank=True)
    diff_summary = serializers.JSONField(
        help_text="Authoritative {files, insertions, deletions} parsed from the stored "
        "patch (Section 9.7).",
    )
    changed_files = serializers.ListField(
        child=serializers.CharField(),
        help_text="Authoritative repo-relative paths touched (Section 9.7).",
    )
    requires_human_attention = serializers.BooleanField(
        help_text="The coder's self-flag (Section 7.2; T8's guard input)."
    )
    risk_justification = serializers.CharField(allow_blank=True)
    submitted_by_session = serializers.CharField(
        help_text="Bridge session that submitted (Section 7.2; always the lease owner)."
    )
    submitted_at = serializers.DateTimeField(help_text="Server clock at insertion (P7).")


class ResolutionTaskStateSerializer(serializers.Serializer[Any]):
    """The post-transition task identity the bridge reports (Section 10.5)."""

    id = serializers.CharField()
    state = serializers.CharField(
        help_text="Canonical state after the dispatch — to_be_audited (T7), "
        "in_human_review (T8/T10 escalate) or to_be_audited with "
        "merge_status pending (T10 approve, Section 8.5).",
    )
    version = serializers.IntegerField(help_text="Optimistic-lock version after the row (7.2).")
    review_reason = serializers.CharField(
        allow_null=True,
        help_text="Section 8.4 member set by T8/T10-escalate; null on the clean T7 path.",
    )
    merge_status = serializers.CharField(
        help_text="none | pending | merging | merged | conflict | failed (7.2) — "
        "pending marks T10's merge-pending branch.",
    )


class ResolutionWriteResponseSerializer(serializers.Serializer[Any]):
    """The frozen submission response — Section 10.5 outcome reporting."""

    resolution = ResolutionSerializer(help_text="The stored Section 7.2 row.")
    task = ResolutionTaskStateSerializer(
        help_text="Post-transition task identity — the outcome the agent is told."
    )
    trigger = serializers.CharField(
        help_text="Which Section 8.2 row fired: submit (T7), submit_flagged (T8), "
        "submit_unreviewed / submit_policy_approved (T10's two branches).",
    )
    scope_violations = serializers.ListField(
        child=serializers.CharField(),
        help_text="Changed files outside target_scope (Section 12.3; empty when clean) "
        "— the offending paths captured for review_reason scope_violation.",
    )


class ResolutionPatchSerializer(serializers.Serializer[Any]):
    """``GET /resolutions/{id}/patch`` body — one shape, both paths (9.2)."""

    resolution_id = serializers.UUIDField()
    kind = serializers.CharField(help_text="Artifact kind (Section 7.2): patch.")
    sha256 = serializers.CharField(
        help_text="Server-computed SHA-256 of the patch bytes (Section 7.2; 9.7)."
    )
    size_bytes = serializers.IntegerField(
        help_text="Server-computed size in bytes (Section 7.2) — compared against "
        "the Section 9.7 5 MB cap (inclusive) for diff_too_large.",
    )
    diff_too_large = serializers.BooleanField(
        help_text="True when the patch exceeded the 5 MB cap and only stats/file "
        "list were kept (Section 9.7's degraded path).",
    )
    patch = serializers.CharField(
        allow_null=True,
        help_text="The stored unified patch, or null on the oversize path (9.7).",
    )
    marker = serializers.CharField(
        allow_null=True,
        help_text=f"Literal viewers render on the oversize path: {DIFF_TOO_LARGE_MARKER!r} "
        "(Section 9.7; null when the body is served).",
    )


class ResolutionListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = ResolutionSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class ResolutionListQuerySerializer(serializers.Serializer[Any]):
    """``GET /tasks/{id}/resolutions`` query parameters."""

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor; valid "
        "only for this task's listing (pagination.md rule 1).",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values above "
            "the maximum are clamped — pagination.md documented defaults, "
            "same per-endpoint choice as the other list routes)."
        ),
    )


def resolution_payload(resolution: TaskResolution) -> dict[str, Any]:
    """Build the API shape of one stored row (§7.2, field for field)."""
    return {
        "id": resolution.pk,
        "task_id": resolution.task_id,
        "attempt_number": resolution.attempt_number,
        "branch_name": resolution.branch_name,
        "commit_sha": resolution.commit_sha,
        "execution_summary": resolution.execution_summary,
        "diff_summary": resolution.diff_summary,
        "changed_files": resolution.changed_files,
        "requires_human_attention": resolution.requires_human_attention,
        "risk_justification": resolution.risk_justification,
        "submitted_by_session": resolution.submitted_by_session,
        "submitted_at": resolution.submitted_at,
    }


def task_state_payload(task: Task) -> dict[str, Any]:
    """The four post-transition task fields the response carries (7.2)."""
    return {
        "id": task.pk,
        "state": task.state,
        "version": task.version,
        "review_reason": task.review_reason,
        "merge_status": task.merge_status,
    }
