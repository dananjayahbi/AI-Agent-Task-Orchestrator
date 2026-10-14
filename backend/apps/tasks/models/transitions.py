"""The append-only Task Transition history — Section 7.2 (MT-1.5-05; FR-TSK-04; P8).

Exactly the Section 7.2 "Task Transition" field list — **none added,
dropped or renamed**: ``id``, ``task_id``, ``from_state``, ``to_state``,
``actor_type`` (``owner`` / ``agent`` / ``system``), ``actor_ref``,
``reason_code``, ``note``, ``timestamp``. The FK is named ``task`` so its
column/attname is literally ``task_id`` (the WP-1.4 ``project_id``
naming decision, applied again).

Immutability is layered (P8; Section 7.4 integrity rule 5):

1. **No API surface** — no serializer, no endpoint, no admin; the only
   write path is ``dispatcher.dispatch_transition`` creating the row
   inside the state-machine transaction (Section 8.2 rule 2).
2. **Application-level hard errors** — this module's manager/queryset
   refuse ``update``/``delete``/``bulk_update``, and the model refuses
   ``save()`` on a loaded row and any ``delete()``: history is
   insert-only, enforced where every ORM writer passes through.
3. **Database-level value checks** — ``from_state``/``to_state`` accept
   only the six canonical states and ``actor_type`` only the three
   canonical actors, at the database (CheckConstraints), ADR-010.

The remaining gap — a raw-SQL writer — closes when WP-1.9 applies the
REVOKE UPDATE/DELETE grants (MT-1.9-04); recorded in the WP changelog
so the split enforcement is visible, never assumed.

``reason_code`` spans the Section 8.4 review reasons **and** the
Section 8.2 trigger codes (the plan's example event carries
``"reason_code": "lease_expired"``, a trigger code), published as the
closed :class:`TransitionReason` choices the dispatcher validates
against. The choices are boundary-level (no DB check): the trigger set
grows with WP-3.x's rows, and a frozen column would block the catalog-
first extension the plan prescribes — the six/three sets are frozen, so
they *are* DB-checked.

Indexed per-task chronologically (``task``, ``timestamp``) for the
Section 13.1 task-detail transitions history.
"""

from __future__ import annotations

from typing import Any

from django.db import models

from .task import Task, TaskState


class TransitionHistoryImmutable(Exception):
    """Any attempt to mutate a history row after insert (P8; rule 5)."""


class ActorType(models.TextChoices):
    """Section 7.2 ``actor_type`` — exactly three canonical values."""

    OWNER = "owner", "owner"
    AGENT = "agent", "agent"
    SYSTEM = "system", "system"


class TransitionReason(models.TextChoices):
    """``reason_code`` = Section 8.4 enum + Section 8.2 trigger codes.

    The twelve review reasons come verbatim from Section 8.4; the
    trigger codes are the snake_case Trigger column of the rows
    WP-1.5 registers (``retry_exhausted`` is both a trigger and an 8.4
    member — one entry covers both). Later rows extend this class first
    (catalog-first, Section 20.4 item 5), never a free-text write.
    """

    # Section 8.4 — the canonical twelve, verbatim.
    SELF_FLAGGED = "self_flagged", "self_flagged"
    SCOPE_VIOLATION = "scope_violation", "scope_violation"
    TEST_FAILURE = "test_failure", "test_failure"
    MIGRATION_DETECTED = "migration_detected", "migration_detected"
    SENSITIVE_CONFIG_CHANGED = "sensitive_config_changed", "sensitive_config_changed"
    CRITICAL_PATH_CHANGED = "critical_path_changed", "critical_path_changed"
    DIFF_OVER_THRESHOLD = "diff_over_threshold", "diff_over_threshold"
    LOW_CONFIDENCE = "low_confidence", "low_confidence"
    RETRY_EXHAUSTED = "retry_exhausted", "retry_exhausted"
    MERGE_CONFLICT = "merge_conflict", "merge_conflict"
    AUDITOR_FLAGGED = "auditor_flagged", "auditor_flagged"
    POLICY_FORCED_REVIEW = "policy_forced_review", "policy_forced_review"
    # Section 8.2 trigger codes of the WP-1.5 rows.
    PUBLISH = "publish", "publish"
    UNPUBLISH = "unpublish", "unpublish"
    ARCHIVE = "archive", "archive"
    LEASE_EXPIRED = "lease_expired", "lease_expired"
    CLAIM = "claim", "claim"
    VOLUNTARY_RELEASE = "voluntary_release", "voluntary_release"
    SUBMIT = "submit", "submit"
    SUBMIT_FLAGGED = "submit_flagged", "submit_flagged"
    # WP-3.2 rows: T10's §8.2 To column reads "policy decision" — a
    # decision, not a state — so the row's trigger codes name its two
    # documented §8.5 outcomes (escalate / merge-pending), registered
    # through the same extension point as every other row.
    SUBMIT_UNREVIEWED = "submit_unreviewed", "submit_unreviewed"
    SUBMIT_POLICY_APPROVED = "submit_policy_approved", "submit_policy_approved"
    # WP-3.3 rows (T11-T14): catalog-first (Section 20.4 item 5) — the new
    # codes are the Section 9.6 event strings verbatim as ADR-010 snake_case
    # machine values (`audit.claimed`/`audit.passed`/`audit.escalated`), never
    # free text; T12 reuses the existing `lease_expired` code (its Section
    # 9.6 event is the same `task.lease_expired` string T5 emits).
    AUDIT_CLAIMED = "audit_claimed", "audit_claimed"
    AUDIT_PASSED = "audit_passed", "audit_passed"
    AUDIT_ESCALATED = "audit_escalated", "audit_escalated"
    # WP-3.6 rows (T15/T16): the Review-row trigger codes as ADR-010
    # snake_case machine values — catalog-first (Section 20.4 item 5),
    # added with the rows that use them.
    APPROVE = "approve", "approve"
    REQUEST_CHANGES = "request_changes", "request_changes"
    REASSIGN = "reassign", "reassign"
    # WP-3.7 rows (T17/T18): the merge executor's two trigger codes as
    # ADR-010 snake_case machine values — catalog-first (Section 20.4
    # item 5), added with the rows that use them.
    MERGE_SUCCEEDED = "merge_succeeded", "merge_succeeded"
    MERGE_FAILED = "merge_failed", "merge_failed"
    # WP-3.7 / OQ-06 queue-side guard: the manual-strategy resolution
    # row's trigger code, added with the row that uses it (catalog-first).
    MERGE_MANUAL = "merge_manual", "merge_manual"


class TransitionQuerySet(models.QuerySet["TaskTransition"]):
    """Mutations are refused: history rows only ever come into existence."""

    def update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse in-place edits (P8 append-only; Section 7.4 rule 5)."""
        raise TransitionHistoryImmutable("Task Transition rows cannot be updated (P8).")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Refuse row deletion — history is never removed by the app role."""
        raise TransitionHistoryImmutable("Task Transition rows cannot be deleted (P8).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits — no ORM door around the insert-only rule."""
        raise TransitionHistoryImmutable("Task Transition rows cannot be updated (P8).")


class TransitionManager(models.Manager.from_queryset(TransitionQuerySet)):  # type: ignore[misc]
    """The default manager — queryset-level immutability rides through."""


class TaskTransition(models.Model):
    """One history row per successful dispatch (FR-TSK-04; Section 7.2)."""

    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # history is never orphaned; tasks are never deleted (7.3)
        related_name="transitions",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    from_state = models.CharField(
        max_length=16,
        choices=TaskState.choices,
        help_text="The state the row fired from (six canonical values, ADR-010).",
    )
    to_state = models.CharField(
        max_length=16,
        choices=TaskState.choices,
        help_text="The state the row landed in; equals from_state for flag-only rows "
        "(T19 archive — Section 8.1: never a seventh state).",
    )
    actor_type = models.CharField(
        max_length=8,
        choices=ActorType.choices,
        help_text="owner | agent | system (Section 7.2; Section 8.2's O/C/A/S/M map here).",
    )
    actor_ref = models.CharField(
        max_length=255,
        help_text="Who fired it: owner user id, agent session/token id, or a system "
        "label like 'lease-sweeper' (Section 9.6 actor ref).",
    )
    reason_code = models.CharField(
        max_length=32,
        choices=TransitionReason.choices,
        help_text="Section 8.4 review reason or Section 8.2 trigger code.",
    )
    note = models.TextField(
        blank=True,
        default="",
        help_text="Free-text accompaniment (e.g. a request-changes note; Section 7.2).",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text="Server clock at insertion (principle P7); the transition's 'when'.",
    )

    objects = TransitionManager()

    class Meta:
        """Append-only history: DB-frozen state/actor sets, per-task chronology."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(from_state__in=TaskState.values),
                name="transition_from_state_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(to_state__in=TaskState.values),
                name="transition_to_state_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(actor_type__in=ActorType.values),
                name="transition_actor_type_canonical",
            ),
        ]
        indexes = [
            models.Index(fields=["task", "timestamp"], name="transition_task_time"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Insert-only: allow the very first write, refuse every later one."""
        if not self._state.adding:
            raise TransitionHistoryImmutable("Task Transition rows cannot be updated (P8).")
        super().save(*args, **kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Delete is not a verb history has (Section 7.4 rule 5)."""
        raise TransitionHistoryImmutable("Task Transition rows cannot be deleted (P8).")

    def __str__(self) -> str:
        """Identify the row as task, move and time."""
        return f"{self.task_id}: {self.from_state} -> {self.to_state} at {self.timestamp}"
