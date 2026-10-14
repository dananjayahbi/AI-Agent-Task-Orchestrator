"""Audit Report — Section 7.2 (WP-3.3; FR-AUD-01, FR-AUD-02).

Exactly the Section 7.2 "Audit Report" field set — **none dropped or
renamed, one field added** (Section 20.5 traceability, asserted
field-for-field in ``tests/test_audit_report.py``):

``id``, ``task_id``, ``resolution_id``, ``auditor_session_id``,
``evidence`` (JSON: commands run, exit codes, durations, changed files,
diff stats, lint results), ``confidence`` (1-5), ``auditor_notes``,
``proposed_verdict``, ``policy_decision``, ``policy_rule_results``
(JSON listing every rule and pass/fail), ``created_at`` — plus
``policy_engine_version``, which Section 9.4 mandates ("the version is
stored on each Audit Report for traceability") and MT-3.4-06 directs
adding when MT-3.3-04 did not include it.

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
* **The engine's three columns are write-restricted** (MT-3.4-06;
  invariant 8.3.4): :class:`AuditReportQuerySet` refuses
  ``update()``/``bulk_update()`` touching them, and ``save()`` refuses
  changing them on an existing row unless the engine's persistence
  helper (:func:`apps.audit.policy.persist.persist_evaluation`) lifts
  the guard for its single transactional write — the Section 7.4
  "application role" discipline applied to policy fields. A database
  check keeps decision, results and version paired (no report shows
  one without the others).
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
from typing import Any

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.tasks.models import Task, TaskResolution

#: The Policy Engine's write-restricted columns (MT-3.4-06; invariant
#: 8.3.4) — only :func:`apps.audit.policy.persist.persist_evaluation`
#: may change them, and only inside the T13/T14 dispatch transaction.
POLICY_ENGINE_FIELDS: tuple[str, ...] = (
    "policy_decision",
    "policy_rule_results",
    "policy_engine_version",
)


class PolicyFieldsImmutable(Exception):
    """Any attempt to write the engine's columns outside the engine path."""


class AuditReportQuerySet(models.QuerySet["AuditReport"]):
    """The engine's columns never move through queryset writes (MT-3.4-06).

    ``update()``/``bulk_update()`` are the ORM doors around ``save()``;
    both refuse the policy-engine columns so the only writer left is the
    engine's own guarded instance save (Section 7.4 application-role
    discipline, invariant 8.3.4).
    """

    def update(self, **kwargs: Any) -> int:
        """Refuse in-place edits of the engine's columns."""
        if set(kwargs) & set(POLICY_ENGINE_FIELDS):
            raise PolicyFieldsImmutable(
                "policy engine columns are written only by the Policy Engine (MT-3.4-06)."
            )
        return super().update(**kwargs)

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits touching the engine's columns."""
        fields: Any = kwargs.get("fields")
        if fields is None and len(args) > 1:
            fields = args[1]
        if set(fields or ()) & set(POLICY_ENGINE_FIELDS):
            raise PolicyFieldsImmutable(
                "policy engine columns are written only by the Policy Engine (MT-3.4-06)."
            )
        return super().bulk_update(*args, **kwargs)


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
    policy_engine_version = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Section 9.4 engine version stored on each Audit Report for "
        "traceability — written with the engine's decision (MT-3.4-06), "
        "nullable until then.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Server clock at insertion (principle P7); the listing's newest-first sort key.",
    )

    objects = AuditReportQuerySet.as_manager()

    class Meta:
        """Confidence floor/ceiling, enums and engine-pairing checks (7.4)."""

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
            # MT-3.4-06: a decision never lands without its engine version
            # or its rule results (and vice versa) — the pairing the
            # T13/T14 transaction writes in one save.
            models.CheckConstraint(
                condition=(
                    models.Q(policy_decision__isnull=True, policy_engine_version__isnull=True)
                    | models.Q(policy_decision__isnull=False, policy_engine_version__isnull=False)
                ),
                name="audit_report_engine_version_with_decision",
            ),
            models.CheckConstraint(
                condition=models.Q(policy_decision__isnull=True)
                | models.Q(policy_rule_results__isnull=False),
                name="audit_report_results_with_decision",
            ),
        ]
        indexes = [
            # The §9.2 listing (newest first per task); the uuid PK breaks
            # created_at ties deterministically (pagination.md rule 2).
            models.Index(fields=["task", "created_at"], name="audit_report_task_time"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Engine-only policy writes (MT-3.4-06): guard, then lift once.

        An existing row may change the engine's columns only through
        :func:`apps.audit.policy.persist.persist_evaluation`, which sets
        the one-shot ``_policy_engine_write`` flag; every other update
        that would move those columns raises
        :class:`PolicyFieldsImmutable`. The flag resets here so later
        saves are guarded again.
        """
        engine_write = bool(self.__dict__.pop("_policy_engine_write", False))
        if not self._state.adding and not engine_write:
            current = type(self).objects.filter(pk=self.pk).values(*POLICY_ENGINE_FIELDS).first()
            if current is not None and any(
                getattr(self, name) != current[name] for name in POLICY_ENGINE_FIELDS
            ):
                raise PolicyFieldsImmutable(
                    "policy engine columns are written only by the Policy Engine (MT-3.4-06)."
                )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """One readable line for the admin/debug surface (no secrets)."""
        return f"{self.task_id} verdict={self.proposed_verdict} confidence={self.confidence}"


# --- Review Decision — Section 7.2 (WP-3.6; FR-AUD-05; MT-3.6-02) -----------


class ReviewDecisionValue(models.TextChoices):
    """Section 7.2 ``decision`` — the three Section 9.2 review actions."""

    APPROVE = "approve", "approve"
    REQUEST_CHANGES = "request_changes", "request_changes"
    REASSIGN = "reassign", "reassign"


class ReviewVia(models.TextChoices):
    """Section 7.2 ``decided_via`` — the web board or the mobile sheet."""

    WEB = "web", "web"
    MOBILE = "mobile", "mobile"


class ReviewDecisionImmutable(Exception):
    """Any attempt to mutate a recorded review decision (Section 12.5)."""


class ReviewDecisionQuerySet(models.QuerySet["ReviewDecision"]):
    """Mutations are refused: a recorded decision is audit history (12.5)."""

    def update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse in-place edits — decisions are recorded, never edited."""
        raise ReviewDecisionImmutable("Review Decision rows cannot be updated (Section 12.5).")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Refuse row deletion — the review trail is never removed."""
        raise ReviewDecisionImmutable("Review Decision rows cannot be deleted (Section 12.5).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits — no ORM door around the append-only rule."""
        raise ReviewDecisionImmutable("Review Decision rows cannot be updated (Section 12.5).")


class ReviewDecisionManager(models.Manager.from_queryset(ReviewDecisionQuerySet)):  # type: ignore[misc]
    """The default manager — queryset-level append-only rides through."""


class ReviewDecision(models.Model):
    """One recorded review decision (Section 7.2 "Review Decision").

    Exactly the Section 7.2 field set — none added, dropped or renamed
    (MT-3.6-02; Section 20.5). T15/T16's side effect writes the row
    inside the dispatch transaction (Section 8.2 rule 2), and Section
    12.5's "all decisions are recorded" makes it append-only — the same
    insert-only discipline ``TaskResolution`` established (P8).

    ``resolution_id`` is **nullable by design**: ``request_changes`` /
    ``reassign`` may answer a retry-exhaustion escalation (T9) that has
    no submission to bind, while an ``approve`` without a resolution is
    impossible — a database check enforces presence for ``approve``
    (MT-3.6-02's risk note: a silently optional column would disable
    the stale-resolution protection MT-3.6-04 builds on this FK).
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated, never client-supplied.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # decisions are never orphaned (7.3: no deletes)
        related_name="review_decisions",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    resolution = models.ForeignKey(
        TaskResolution,
        on_delete=models.PROTECT,  # the reviewed submission outlives every read
        null=True,
        blank=True,
        related_name="review_decisions",
        help_text="Section 7.2 ``resolution_id`` — the FK column is "
        "resolution_id; the current attempt's resolution the reviewer "
        "was looking at (mandatory for ``approve`` — MT-3.6-04's binding; "
        "nullable for note actions that may fire without one, e.g. T9).",
    )
    decision = models.CharField(
        max_length=16,
        choices=ReviewDecisionValue.choices,
        help_text="Section 7.2 ``decision``: approve | request_changes | reassign "
        "(Section 9.2's three review actions — no fourth value).",
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="Section 7.2 ``note`` — mandatory for request_changes "
        "(T16 guard), optional elsewhere; the request-changes note "
        "becomes the Task's ``latest_feedback`` (Section 11.5).",
    )
    decided_by = models.CharField(
        max_length=255,
        help_text="Section 7.2 ``decided_by`` — the acting user/principal "
        "(owner user id or device id, Section 12.2 Review decisions row).",
    )
    decided_via = models.CharField(
        max_length=8,
        choices=ReviewVia.choices,
        help_text="Section 7.2 ``decided_via``: web | mobile — the board or "
        "the review sheet channel (Sections 13/14).",
    )
    decided_at = models.DateTimeField(
        default=timezone.now,
        help_text="Server clock at insertion (principle P7); the API never accepts a client value.",
    )

    objects = ReviewDecisionManager()

    class Meta:
        """Enum checks plus the approve-requires-resolution pairing (7.4)."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(decision__in=ReviewDecisionValue.values),
                name="review_decision_value_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(decided_via__in=ReviewVia.values),
                name="review_decision_via_canonical",
            ),
            # MT-3.6-02/04: an approve without its resolution binding would
            # silently disable the stale-resolution guard — refused at the
            # database, not only at the endpoint.
            models.CheckConstraint(
                condition=(~models.Q(decision="approve") | models.Q(resolution__isnull=False)),
                name="review_decision_approve_needs_resolution",
            ),
        ]
        indexes = [
            # The review panel reads a task's decisions newest first; the
            # uuid PK breaks decided_at ties deterministically.
            models.Index(fields=["task", "decided_at"], name="review_decision_task_time"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Append-only: allow the very first write, refuse every later one."""
        if not self._state.adding:
            raise ReviewDecisionImmutable("Review Decision rows cannot be updated (Section 12.5).")
        super().save(*args, **kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Delete is not a verb a recorded decision has (Section 12.5)."""
        raise ReviewDecisionImmutable("Review Decision rows cannot be deleted (Section 12.5).")

    def __str__(self) -> str:
        """One readable line for the admin/debug surface (no secrets)."""
        return f"{self.task_id} {self.decision} via {self.decided_via}"


__all__ = [
    "AuditReport",
    "AuditReportQuerySet",
    "POLICY_ENGINE_FIELDS",
    "PolicyDecisionValue",
    "PolicyFieldsImmutable",
    "ReviewDecision",
    "ReviewDecisionImmutable",
    "ReviewDecisionManager",
    "ReviewDecisionQuerySet",
    "ReviewDecisionValue",
    "ReviewVia",
    "VerdictChoice",
]
