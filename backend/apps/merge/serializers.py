"""Request/response serializers for the merge queue surface (MT-3.7-01).

Shapes follow the Section 9.2 conventions: the list envelope is the
canonical ``results`` + ``next_cursor`` two-member object (pagination.md;
the contract test enforces it), the POST bodies are strict (unknown
fields are a 400, never silently ignored), and the mutation responses
carry the five-field task identity the other endpoints echo (Section
7.2), plus the reported result and its sha (Section 11.4's "report the
resulting sha" — Section 7.2 has no column, so payload/note/event are
the three carriers, never a schema change from a micro-task).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin

from .services import RESULT_CONFLICT, RESULT_FAILED, RESULT_SUCCEEDED

_RESULT_CHOICES = (
    (RESULT_SUCCEEDED, RESULT_SUCCEEDED),
    (str(RESULT_CONFLICT), str(RESULT_CONFLICT)),
    (str(RESULT_FAILED), str(RESULT_FAILED)),
)


class QueueTaskStateSerializer(serializers.Serializer[Any]):
    """The post-mutation task identity the start/result responses carry."""

    id = serializers.CharField(help_text="Section 7.3 task id.")
    state = serializers.CharField(
        help_text="Canonical state after the mutation — in_human_review or "
        "to_be_audited on start; completed (T17) or in_human_review (T18) "
        "after a result.",
    )
    version = serializers.IntegerField(help_text="Optimistic-lock version after the row (7.2).")
    review_reason = serializers.CharField(
        allow_null=True,
        help_text="Section 8.4 member — merge_conflict after T18, else unchanged.",
    )
    merge_status = serializers.CharField(
        help_text="none | pending | merging | merged | conflict | failed (7.2).",
    )


class MergeQueueItemSerializer(serializers.Serializer[Any]):
    """One pending task in the queue (Section 9.2 GET /merge/pending)."""

    id = serializers.CharField(help_text="Section 7.3 task id — the `{task}` path segment.")
    project_id = serializers.CharField(help_text="Project the entry belongs to (ADR-004 scope).")
    title = serializers.CharField(help_text="Section 7.2 title — the queue's human label.")
    state = serializers.CharField(
        help_text="Carrier state: in_human_review (T15 approve) or to_be_audited "
        "(T10/T13 engine-approved) — Section 8.1's sub-status rides these two.",
    )
    version = serializers.IntegerField(
        help_text="Optimistic-lock version (7.2) — chain it onto start/result.",
    )
    merge_status = serializers.CharField(
        help_text="Always 'pending' in this listing (the Section 8.1 sub-status).",
    )
    branch_name = serializers.CharField(
        allow_null=True,
        help_text="Current attempt's branch (Section 7.2) the executor merges into "
        "the default branch; null only if the carrier somehow lost its resolution.",
    )
    merge_strategy = serializers.CharField(
        help_text="The project policy's Section 7.2 strategy riding the row "
        "(squash | merge_commit | fast_forward_only; default squash) — the "
        "executor never configures strategy itself; manual entries are resolved "
        "by the queue-side guard and never appear here (OQ-06).",
    )


class MergeQueueListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = MergeQueueItemSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class MergeQueueListQuerySerializer(serializers.Serializer[Any]):
    """``GET /merge/pending`` query parameters."""

    cursor = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Opaque cursor from the previous page's next_cursor; FIFO by "
        "task id so polling is stable (pagination.md rule 1).",
    )
    page_size = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text=(
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values above "
            "the maximum are clamped — pagination.md documented defaults)."
        ),
    )


class MergeStartRequestSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /merge/{task}/start`` input — no required fields (claim is id-less)."""

    version = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Optional task ``version`` the executor saw in the listing "
        "(FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and "
        "claims nothing.",
    )


class MergeStartResponseSerializer(serializers.Serializer[Any]):
    """Start's response — the post-claim identity the executor chains on."""

    task = QueueTaskStateSerializer(
        help_text="merge_status is now 'merging' and version incremented (7.2).",
    )


class MergeResultRequestSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /merge/{task}/result`` input (Section 9.2; MT-3.7-01)."""

    result = serializers.ChoiceField(
        choices=_RESULT_CHOICES,
        help_text="succeeded | conflict | failed — the executor's reported outcome; "
        "succeeded applies T17, the other two apply T18 with that flavor "
        "(Section 7.2 values, never inferred).",
    )
    sha = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="The resulting merge sha — **required for succeeded** "
        "(T17's Guard column; Section 11.4). Section 7.2 has no sha "
        "column, so it rides this payload, the history note and the "
        "event data (recorded reading; no silent schema change).",
    )
    details = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Free-text outcome detail (conflict file list, error summary) — "
        "carried into the history note and the merge.failed event data.",
    )
    version = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Optional task ``version`` the executor saw at start "
        "(FR-TSK-06) — a stale value answers VERSION_CONFLICT (409) and "
        "applies nothing.",
    )


class MergeResultResponseSerializer(serializers.Serializer[Any]):
    """Result's response — the post-transition identity plus the echo."""

    task = QueueTaskStateSerializer(
        help_text="completed + merged (T17) or in_human_review + conflict/failed "
        "with review_reason merge_conflict (T18).",
    )
    result = serializers.ChoiceField(
        choices=_RESULT_CHOICES,
        help_text="The reported outcome, echoed.",
    )
    sha = serializers.CharField(
        allow_null=True,
        help_text="The resulting sha on success; null on the T18 failure branches.",
    )


__all__ = [
    "MergeQueueItemSerializer",
    "MergeQueueListEnvelopeSerializer",
    "MergeQueueListQuerySerializer",
    "MergeResultRequestSerializer",
    "MergeResultResponseSerializer",
    "MergeStartRequestSerializer",
    "MergeStartResponseSerializer",
    "QueueTaskStateSerializer",
]
