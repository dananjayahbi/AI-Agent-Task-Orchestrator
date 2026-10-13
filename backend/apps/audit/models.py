"""Audit Report — Section 7.2 (WP-3.3; FR-AUD-01, FR-AUD-02).

Exactly the Section 7.2 "Audit Report" field set — **none added, dropped
or renamed** (Section 20.5 traceability, asserted field-for-field in
``tests/test_audit_report.py``):

``id``, ``task_id``, ``resolution_id``, ``auditor_session_id``,
``evidence`` (JSON: commands run, exit codes, durations, changed files,
diff stats, lint results), ``confidence`` (1-5), ``auditor_notes``,
``proposed_verdict``, ``policy_decision``, ``policy_rule_results``
(JSON listing every rule and pass/fail), ``created_at``.

Recorded readings (Section 20.1 item 5 — no hidden decisions):

* **UUID id** — Section 7.3 fixes id generation only for Project and
  Task; the other §7.2 new entities (Task Resolution, Task Artifact,
  Task Attachment, Task Checkpoint) all chose UUID primary keys, and
  this row follows them (the pattern precedent, not a new rule).
* **``confidence`` is constrained at every layer** — serializer
  ``min_value``/``max_value`` (API boundary), model validators, and a
  database ``CheckConstraint`` (Section 7.4's enum/floor discipline),
  so a direct ORM write cannot bypass the 1-5 range.
* **``proposed_verdict`` is the Section 10.5 enum** — ``pass`` /
  ``flag_risk`` / ``fail``, written once by the verdict endpoint and
  DB-checked; ``policy_decision`` (``approve`` / ``escalate`` per
  Section 9.4) and ``policy_rule_results`` are **nullable** and stay
  ``null`` until the Policy Engine writes them (MT-3.4-06) — never
  faked here (invariant 8.3.4: only the engine fills them).
* **Not insert-only (P8)** — unlike ``TaskResolution``, this row is
  *born* incomplete: the engine fills ``policy_decision`` /
  ``policy_rule_results`` after creation (Section 9.4; MT-3.4-06), so
  the resolution-style update lock would make the plan unimplementable.
  The auditor-authored half is written exactly once by the verdict
  service inside the dispatch transaction; nothing in the API rewrites
  it.
* **Reports accumulate per resolution** (MT-3.3-04 risk note): a T12
  audit-lease expiry lets a *new* independent auditor re-claim the same
  resolution, and each accepted verdict stores its own report row —
  the listing shows them newest first so the review panel can compare
  passes and retries (the plan pins no "replace" rule; recorded as an
  OQ in the WP changelog if supersession is ever wanted).
"""

from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.tasks.models import Task, TaskResolution


class VerdictChoice(models.TextChoices):
    """Section 10.5 ``verdict`` enum — the auditor's proposed verdict."""

    PASS = "pass", "pass"
    FLAG_RISK = "flag_risk", "flag_risk"
    FAIL = "fail", "fail"


class PolicyDecisionValue(models.TextChoices):
    """Section 9.4 engine output — ``approve`` or ``escalate``."""

    APPROVE = "approve", "approve"
    ESCALATE = "escalate", "escalate"


class AuditReport(models.Model):
    """One auditor's structured record for one resolution (Section 7.2)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated, never client-supplied.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # reports are never orphaned (7.3: no deletes)
        related_name="audit_reports",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    resolution = models.ForeignKey(
        TaskResolution,
        on_delete=models.PROTECT,  # the audited submission outlives every read
        related_name="audit_reports",
        help_text="Section 7.2 ``resolution_id`` — the FK column is resolution_id; "
        "the current attempt's resolution the auditor was reviewing.",
    )
    auditor_session_id = models.CharField(
        max_length=255,
        help_text="Bridge session that audited (Section 7.2; G-18) — the "
        "lease owner that submitted the verdict (Section 9.2).",
    )
    evidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Section 7.2 ``evidence`` (JSON): commands run, exit codes, "
        "durations, changed files, diff stats, lint results — stored as "
        "supplied (Section 10.5 shape round-trips verbatim; deep schema "
        "validation is WP-3.5's bridge step, not this column's).",
    )
    confidence = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Section 7.2 ``confidence`` (1-5) — serializer range plus "
        "the database check below; the input rule R7 later reads.",
    )
    auditor_notes = models.TextField(
        blank=True,
        default="",
        help_text="Section 7.2 ``auditor_notes`` — free text shown in the "
        "review panel (Section 13.2).",
    )
    proposed_verdict = models.CharField(
        max_length=10,
        choices=VerdictChoice.choices,
        help_text="Section 10.5 enum: pass | flag_risk | fail — the auditor's "
        "proposal; the Policy Engine, never this row, decides the outcome "
        "(invariant 8.3.4).",
    )
    policy_decision = models.CharField(
        max_length=10,
        choices=PolicyDecisionValue.choices,
        null=True,
        blank=True,
        help_text="Section 9.4 engine output (approve | escalate) — nullable, "
        "written only by the Policy Engine (MT-3.4-06), never faked here.",
    )
    policy_rule_results = models.JSONField(
        null=True,
        blank=True,
        help_text="Section 7.2/9.4 JSON listing every rule and pass/fail — "
        "nullable until the engine persists its evaluation (MT-3.4-06).",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Server clock at insertion (principle P7); the listing's newest-first sort key.",
    )

    class Meta:
        """Confidence floor/ceiling and the enum in the database (7.4)."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(confidence__gte=1) & models.Q(confidence__lte=5),
                name="audit_report_confidence_1_to_5",
            ),
            models.CheckConstraint(
                condition=models.Q(proposed_verdict__in=VerdictChoice.values),
                name="audit_report_verdict_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(policy_decision__isnull=True)
                | models.Q(policy_decision__in=PolicyDecisionValue.values),
                name="audit_report_policy_decision_canonical",
            ),
        ]
        indexes = [
            # The §9.2 listing (newest first per task); the uuid PK breaks
            # created_at ties deterministically (pagination.md rule 2).
            models.Index(fields=["task", "created_at"], name="audit_report_task_time"),
        ]

    def __str__(self) -> str:
        """One readable line for the admin/debug surface (no secrets)."""
        return f"{self.task_id} verdict={self.proposed_verdict} confidence={self.confidence}"


__all__ = ["AuditReport", "PolicyDecisionValue", "VerdictChoice"]
