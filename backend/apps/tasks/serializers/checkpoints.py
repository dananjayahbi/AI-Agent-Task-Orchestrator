"""Checkpoint serializers — Section 9.2 Progress row; Sections 7.2/10.5.

* ``CheckpointCreateSerializer`` — the ``POST /tasks/{id}/checkpoints``
  input: the Section 7.2 fields an agent supplies (``message``,
  ``percent``, ``token_usage``, ``kind``) plus the ADR-012 fencing pair
  (``session_id`` + ``lease_generation``). ``attempt_number`` and
  ``timestamp`` are **not** accepted from the caller — the server copies
  the attempt at write time and stamps the clock (P7; MT-1.8-01 risk).
* ``CheckpointSerializer`` — the stored row as the API returns it: the
  nine Section 7.2 fields, field for field (MT-1.8-04's listing uses the
  same shape, so web/mobile render one contract — G-11).
* ``CheckpointWriteResponseSerializer`` — MT-1.8-03's frozen response:
  the stored checkpoint's identity plus the new ``lease_expires_at``
  (Section 10.5: "Returns new expiry") and ``capped`` so the bridge can
  surface submit-or-release guidance (MT-1.6-03's flag, its docstring
  names this response as the consumer — no ad-hoc fields added).
* the listing envelope/query shapes — pagination.md's exact
  ``{results, next_cursor}`` contract (MT-1.8-04).
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin
from apps.tasks.models import CheckpointKind, TaskCheckpoint


class CheckpointCreateSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /tasks/{id}/checkpoints`` input (Section 10.5 tool contract)."""

    session_id = serializers.CharField(
        max_length=255,
        help_text="Lease-holding session id (G-18) — the fencing pair's identity half.",
    )
    lease_generation = serializers.IntegerField(
        min_value=0,
        help_text="Fencing generation from the claim response (Section 8.6; "
        "ADR-012); a stale value answers LEASE_EXPIRED.",
    )
    message = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="The agent's progress report text (Section 10.5 tool input).",
    )
    percent = serializers.IntegerField(
        min_value=0,
        max_value=100,
        required=False,
        allow_null=True,
        default=None,
        help_text="Optional 0-100 completion hint (Section 7.2 bounds; "
        "out-of-range answers VALIDATION_ERROR).",
    )
    token_usage = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Free JSON token accounting blob (Section 7.2) — no fixed "
        "schema is invented here (MT-1.8-01 risk note; an OQ would "
        "freeze one).",
    )
    kind = serializers.ChoiceField(
        choices=CheckpointKind.choices,
        required=False,
        default=CheckpointKind.PROGRESS,
        help_text="progress | liveness | system (Section 7.2); default "
        "progress — the extension-carrying kind (OQ-04 recorded reading).",
    )


class CheckpointSerializer(serializers.Serializer[Any]):
    """One stored checkpoint — the Section 7.2 field list, as returned."""

    id = serializers.UUIDField(help_text="Server-generated row identity (7.2).")
    task_id = serializers.CharField(help_text="The addressed task (Section 7.2).")
    attempt_number = serializers.IntegerField(
        help_text="The coder claim attempt at write time (copied, never joined — "
        "MT-1.8-01 risk note).",
    )
    session_id = serializers.CharField(
        help_text="Bridge-issued session id of the reporting agent (G-18)."
    )
    timestamp = serializers.DateTimeField(
        help_text="Server clock at insertion (P7) — the feed's 'when'."
    )
    message = serializers.CharField(allow_blank=True)
    percent = serializers.IntegerField(
        allow_null=True,
        help_text="0-100 hint, or null when the caller omitted it (7.2).",
    )
    token_usage = serializers.JSONField(help_text="Free JSON token accounting blob (Section 7.2).")
    kind = serializers.CharField(help_text="progress | liveness | system (7.2).")


class CheckpointWriteResponseSerializer(serializers.Serializer[Any]):
    """MT-1.8-03's frozen response — Section 10.5 "Returns new expiry"."""

    checkpoint = CheckpointSerializer(help_text="The stored row's identity and Section 7.2 fields.")
    lease_extended = serializers.BooleanField(
        help_text="False for a kind that does not extend under the project's "
        "lease_extension_mode (OQ-04 recorded reading).",
    )
    lease_expires_at = serializers.DateTimeField(
        allow_null=True,
        help_text="The Section 8.6 deadline after this call — the new expiry "
        "the bridge turns into its next_checkpoint_due hint.",
    )
    capped = serializers.BooleanField(
        help_text="True when the hard cap clamped the extension — the owner "
        "must submit or release (MT-1.6-03's flag, consumed here).",
    )


class CheckpointListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = CheckpointSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class CheckpointListQuerySerializer(serializers.Serializer[Any]):
    """``GET /tasks/{id}/checkpoints`` query parameters (MT-1.8-04)."""

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
            f"Items per page (default 25, maximum {MAX_PAGE_SIZE}; values "
            "above the maximum are clamped — pagination.md documented "
            "defaults, same per-endpoint choice as the other list routes)."
        ),
    )


def checkpoint_payload(checkpoint: TaskCheckpoint) -> dict[str, object]:
    """Build the API shape of one stored row (§7.2, field for field)."""
    return {
        "id": checkpoint.pk,
        "task_id": checkpoint.task_id,
        "attempt_number": checkpoint.attempt_number,
        "session_id": checkpoint.session_id,
        "timestamp": checkpoint.timestamp,
        "message": checkpoint.message,
        "percent": checkpoint.percent,
        "token_usage": checkpoint.token_usage,
        "kind": checkpoint.kind,
    }
