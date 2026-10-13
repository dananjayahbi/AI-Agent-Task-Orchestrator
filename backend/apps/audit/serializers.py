"""Audit serializers — Section 9.2 Audit row, Section 10.5 verdict shape.

* ``AuditVerdictRequest`` — the Section 10.5 ``submit_audit_verdict``
  input contract, endpoint twin: ``task_id`` (required — validated equal
  to the addressed path id), ``verdict`` (``pass`` / ``flag_risk`` /
  ``fail``), ``confidence`` 1-5, ``notes``, ``evidence`` with its
  required structure (commands of label/command/exit_code; ``lint_clean``
  and friends pass through), and the optional
  ``acceptance_criteria_results`` sibling. Invalid input answers the
  catalog ``VALIDATION_ERROR`` with field details (Section 20.4 item 5);
  deep evidence-schema guidance stays WP-3.5's bridge step (MT-3.3-04
  risk note) — this layer checks only the §10.5 *required* structure.
* ``AuditReportSerializer`` — one stored row, the Section 7.2 field list
  as returned (MT-3.3-04 field parity).
* ``AuditVerdictResponse`` — the frozen 201 body: report, post-
  transition task identity, the row that fired, and the seam's decision
  (Section 10.5: "Policy Engine decides final state").
* list envelope/query — pagination.md's exact ``results`` +
  ``next_cursor`` shape with the canonical cursor/page_size params.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.core.pagination import MAX_PAGE_SIZE
from apps.core.serializers import StrictSerializerMixin

from .models import PolicyDecisionValue, VerdictChoice
from .services import VERDICT_VALUES


def _validate_commands(value: Any) -> None:
    """The §10.5 ``evidence.commands`` required structure, item by item."""
    if not isinstance(value, list) or not value:
        raise serializers.ValidationError("evidence.commands must be a non-empty array.")
    for index, command in enumerate(value):
        if not isinstance(command, dict):
            raise serializers.ValidationError(f"evidence.commands[{index}] must be an object.")
        label = command.get("label")
        text = command.get("command")
        exit_code = command.get("exit_code")
        if not isinstance(label, str) or not label:
            raise serializers.ValidationError(
                f"evidence.commands[{index}].label is required (string)."
            )
        if not isinstance(text, str) or not text:
            raise serializers.ValidationError(
                f"evidence.commands[{index}].command is required (string)."
            )
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            raise serializers.ValidationError(
                f"evidence.commands[{index}].exit_code is required (integer)."
            )


class AuditVerdictRequestSerializer(StrictSerializerMixin, serializers.Serializer[Any]):
    """``POST /tasks/{id}/audit-verdict`` input (Section 10.5 contract)."""

    session_id = serializers.CharField(
        max_length=255,
        help_text="Lease-holding auditor session id (G-18) — the fencing pair's "
        "identity half; becomes auditor_session_id (Section 7.2).",
    )
    lease_generation = serializers.IntegerField(
        min_value=0,
        help_text="Fencing generation from the claim response (Section 8.6; "
        "ADR-012 — the pair every agent mutation carries); a stale value "
        "answers LEASE_EXPIRED.",
    )
    task_id = serializers.CharField(
        help_text="The addressed task id — must equal the path id (Section 10.5 "
        "requires task_id in the payload; the path decides, the body echoes).",
    )
    verdict = serializers.ChoiceField(
        choices=VERDICT_VALUES,
        help_text="Section 10.5 enum: pass | flag_risk | fail — the proposal only; "
        "the Policy Engine decides the outcome (invariant 8.3.4).",
    )
    confidence = serializers.IntegerField(
        min_value=1,
        max_value=5,
        help_text="Section 10.5 / 7.2 confidence (1-5) — the input rule R7 reads.",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text="Auditor notes (Section 10.5 `notes` → Section 7.2 "
        "`auditor_notes`), shown in the review panel.",
    )
    evidence = serializers.JSONField(
        help_text="Section 10.5 evidence object: required `commands` array "
        "(label/command/exit_code per item); `lint_clean`, durations, "
        "changed files and diff stats pass through as supplied "
        "(FR-AUD-02 — stored verbatim, never reshaped).",
    )
    acceptance_criteria_results = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_null=True,
        default=None,
        help_text="Section 10.5 optional array of {criterion, met} — validated "
        "here and stored inside the report's evidence JSON (§7.2 gives it "
        "no column; recorded reading, MT-3.3-05).",
    )

    def validate_evidence(self, value: Any) -> dict[str, Any]:
        """Required structure of Section 10.5's evidence object."""
        if not isinstance(value, dict):
            raise serializers.ValidationError("evidence must be an object.")
        if "commands" not in value:
            raise serializers.ValidationError("evidence.commands is required.")
        _validate_commands(value["commands"])
        lint_clean = value.get("lint_clean")
        if lint_clean is not None and not isinstance(lint_clean, bool):
            raise serializers.ValidationError("evidence.lint_clean must be a boolean when present.")
        return value

    def validate_acceptance_criteria_results(self, value: Any) -> list[dict[str, Any]] | None:
        """The §10.5 sibling array: {criterion, met} per item when present."""
        if value is None:
            return None
        if not isinstance(value, list):
            raise serializers.ValidationError("acceptance_criteria_results must be an array.")
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    f"acceptance_criteria_results[{index}] must be an object."
                )
            criterion = item.get("criterion")
            met = item.get("met")
            if not isinstance(criterion, str) or not criterion:
                raise serializers.ValidationError(
                    f"acceptance_criteria_results[{index}].criterion is required (string)."
                )
            if not isinstance(met, bool):
                raise serializers.ValidationError(
                    f"acceptance_criteria_results[{index}].met is required (boolean)."
                )
        return [dict(item) for item in value]


class AuditReportSerializer(serializers.Serializer[Any]):
    """One stored report — the Section 7.2 field list, as returned."""

    id = serializers.UUIDField(help_text="Server-generated row identity (Section 7.2).")
    task_id = serializers.CharField(help_text="The audited task (Section 7.2).")
    resolution_id = serializers.UUIDField(
        help_text="The audited submission (Section 7.2 — one report per verdict, "
        "accumulating across T12 audit retries)."
    )
    auditor_session_id = serializers.CharField(
        help_text="Bridge session that audited (Section 7.2; G-18 — always the "
        "auditor lease owner at submit time)."
    )
    evidence = serializers.JSONField(
        help_text="Section 7.2 evidence JSON — the Section 10.5 structure as "
        "supplied (commands with exit codes, lint_clean, stats…)."
    )
    confidence = serializers.IntegerField(help_text="Section 7.2 confidence (1-5; DB-constrained).")
    auditor_notes = serializers.CharField(allow_blank=True)
    proposed_verdict = serializers.ChoiceField(
        choices=VerdictChoice.choices,
        help_text="Section 10.5 enum the auditor proposed; the engine decides.",
    )
    policy_decision = serializers.ChoiceField(
        choices=PolicyDecisionValue.choices,
        allow_null=True,
        help_text="Section 9.4 engine output (approve | escalate) — null until "
        "the Policy Engine writes it (MT-3.4-06), never faked here.",
    )
    policy_rule_results = serializers.JSONField(
        allow_null=True,
        help_text="Section 7.2/9.4 per-rule pass/fail — null until the engine "
        "persists it (MT-3.4-06), never faked here.",
    )
    created_at = serializers.DateTimeField(help_text="Server clock at insertion (P7).")


class AuditDecisionSerializer(serializers.Serializer[Any]):
    """The seam's decision the 201 body reports (Section 9.4)."""

    approve = serializers.BooleanField(
        help_text="True only when the installed Policy Engine approved (T13); "
        "the fail-closed default always returns false (invariant 8.3.4).",
    )
    reason = serializers.CharField(
        allow_null=True,
        help_text="Section 8.4 escalation reason, or null on approval.",
    )


class VerdictTaskStateSerializer(serializers.Serializer[Any]):
    """The post-transition task identity the verdict response carries."""

    id = serializers.CharField()
    state = serializers.CharField(
        help_text="Canonical state after the dispatch — in_human_review (T14, "
        "the fail-closed escalate) or to_be_audited with merge_status "
        "pending (T13, engine-approved; Section 8.2).",
    )
    version = serializers.IntegerField(help_text="Optimistic-lock version after the row (7.2).")
    review_reason = serializers.CharField(
        allow_null=True,
        help_text="Section 8.4 member T14 set; null on the T13 approve branch.",
    )
    merge_status = serializers.CharField(
        help_text="none | pending | merging | merged | conflict | failed (7.2) — "
        "pending marks T13's merge-pending sub-status.",
    )


class AuditVerdictResponseSerializer(serializers.Serializer[Any]):
    """The frozen verdict response — report + outcome (Section 10.5)."""

    report = AuditReportSerializer(help_text="The stored Section 7.2 row.")
    task = VerdictTaskStateSerializer(
        help_text="Post-transition task identity — the outcome the agent is told "
        "(decided by the seam, never by this endpoint)."
    )
    trigger = serializers.CharField(
        help_text="Which Section 8.2 row fired: audit_verdict_escalated (T14) or "
        "audit_verdict_pass (T13, engine-only).",
    )
    decision = AuditDecisionSerializer(
        help_text="The Policy Engine seam's decision (approve/escalate + reason).",
    )


class AuditReportListEnvelopeSerializer(serializers.Serializer[Any]):
    """pagination.md envelope: exactly ``results`` + ``next_cursor``."""

    results = AuditReportSerializer(many=True)
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque cursor for the next page; null = end of list.",
    )


class AuditReportListQuerySerializer(serializers.Serializer[Any]):
    """``GET /tasks/{id}/audit-reports`` query parameters."""

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


__all__ = [
    "AuditDecisionSerializer",
    "AuditReportListEnvelopeSerializer",
    "AuditReportListQuerySerializer",
    "AuditReportSerializer",
    "AuditVerdictRequestSerializer",
    "AuditVerdictResponseSerializer",
    "VerdictTaskStateSerializer",
]
