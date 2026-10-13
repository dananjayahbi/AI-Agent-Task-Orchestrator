"""The Task entity (parent plan Sections 7.2, 7.4; MT-1.4-01; FR-TSK-01/02).

Exactly the Section 7.2 "Task" table — **none added, dropped or renamed**:

* ``id`` — ``{PID}-T{index}``, check-constrained to ``PID[0-9]{5}-T[0-9]{3,}``
  (Section 7.3/7.4, FR-TSK-01) and **server-assigned**: allocation is
  MT-1.4-02's ``services.ids.allocate_task_id`` (project row locked,
  ``task_counter`` incremented — no client ever supplies an id);
* ``project`` — the Django name of Section 7.2's ``project_id`` FK (the
  database column and instance attname are literally ``project_id``; the
  API renders ``project_id``). ``PROTECT``: a task is never cascade-deleted
  (Section 7.3: deleting a task is not supported);
* ``state`` — the six canonical G-01/ADR-010 values, default ``draft``
  (Section 8.2 T1: create → ``draft``), stored as the machine value only —
  no display strings in the column;
* ``version`` — FR-TSK-06 optimistic locking: starts at 1, **incremented
  by every write path** (PATCH, transitions, archive). The write contract:
  the state-machine service (WP-1.5, Section 9.1 ``tasks`` owns state
  changes) is the only writer of ``state``; the enforcement test arrives
  with WP-1.5 — this model records the contract only (MT-1.4-01 scope);
* lease/worker/merge/review fields — Section 7.2 defines the entity once,
  so the fields exist here although their owning services arrive later
  (WP-1.6 leases, M3 merge/audit). **No behavior** for them ships in this
  WP (Section 20.3: one concept per task);
* ``archived_at`` — the single soft-archive marker (MT-1.4-06 reads/writes
  it; there is no delete path at all).

Enum columns are constrained twice over (Section 7.4: boundaries *and*
the database): ``choices`` + ``full_clean``/serializer ChoiceFields at the
API boundary, plus ``CheckConstraint``s on ``state`` and ``priority`` at
the database. The remaining choice columns (``claimed_role``,
``review_reason``, ``merge_status``) are boundary-checked only — their
services do not exist yet and a DB check would freeze enum evolution
before the owning WPs land (recorded in the WP changelog).
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from apps.projects.models import Project
from apps.tasks.services.ids import TASK_ID_PATTERN, validate_task_id

# --- canonical enums (G-01 / ADR-010; Section 8.1, 8.4; FR-TSK-05) ---------


class TaskState(models.TextChoices):
    """The six canonical states — G-01, none added (Section 8.1)."""

    DRAFT = "draft", "draft"
    PENDING = "pending", "pending"
    IN_PROGRESS = "in_progress", "in_progress"
    TO_BE_AUDITED = "to_be_audited", "to_be_audited"
    IN_HUMAN_REVIEW = "in_human_review", "in_human_review"
    COMPLETED = "completed", "completed"


class TaskPriority(models.TextChoices):
    """FR-TSK-05 priority values — four, in plan order."""

    URGENT = "urgent", "urgent"
    HIGH = "high", "high"
    MEDIUM = "medium", "medium"
    LOW = "low", "low"


class ClaimedRole(models.TextChoices):
    """Section 7.2 ``claimed_role``: coder or auditor, nullable."""

    CODER = "coder", "coder"
    AUDITOR = "auditor", "auditor"


class MergeStatus(models.TextChoices):
    """Section 7.2 ``merge_status`` triple-plus (``none`` is the default)."""

    NONE = "none", "none"
    PENDING = "pending", "pending"
    MERGING = "merging", "merging"
    MERGED = "merged", "merged"
    CONFLICT = "conflict", "conflict"
    FAILED = "failed", "failed"


class ReviewReason(models.TextChoices):
    """Section 8.4 review reasons — the canonical twelve, verbatim."""

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


class Task(models.Model):
    """One work item — Section 7.2 field for field."""

    id = models.CharField(
        max_length=32,
        primary_key=True,
        validators=[validate_task_id],
        help_text="{PID}-T{index}, index 3+ digits growing naturally (Section 7.3); "
        "server-assigned by services.ids.allocate_task_id.",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="tasks",
        help_text="Section 7.2 ``project_id``: the FK column is project_id; "
        "a task's project never changes (Section 7.4 rule 4).",
    )
    title = models.CharField(
        max_length=200,
        help_text="Short task title (FR-TSK-02). 200 mirrors Project.name — "
        "documented default, the plan states no limit.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Markdown description (FR-TSK-02; Section 7.2).",
    )
    acceptance_criteria = models.JSONField(
        default=list,
        help_text="List of acceptance-criteria strings (Section 7.2).",
    )
    target_scope = models.JSONField(
        default=list,
        help_text="Path globs relative to the repo root, validated on creation (Section 12.3).",
    )
    test_command = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="The command the coder and auditor must run (Section 7.2).",
    )
    priority = models.CharField(
        max_length=6,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        help_text="FR-TSK-05 enum; default medium — documented default (the plan "
        "states none), flagged for owner confirmation in the WP changelog.",
    )
    state = models.CharField(
        max_length=16,
        choices=TaskState.choices,
        default=TaskState.DRAFT,
        help_text="Canonical G-01 state (machine value, ADR-010); default draft "
        "(Section 8.2 T1). Written only by WP-1.5's state-machine service.",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="FR-TSK-06 optimistic locking: starts at 1, incremented by "
        "every write path; a stale value answers VERSION_CONFLICT.",
    )
    worker_agent_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Human-readable label of the current lease holder (WP-1.6).",
    )
    worker_session_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Bridge-issued session id of the lease holder (G-18; WP-1.6).",
    )
    claimed_role = models.CharField(
        max_length=8,
        choices=ClaimedRole.choices,
        null=True,
        blank=True,
        help_text="coder | auditor while claimed, else null (Section 7.2).",
    )
    lease_acquired_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Lease start (Section 8.6; WP-1.6 owns the behavior).",
    )
    lease_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Lease deadline (Section 8.6; WP-1.6 owns the behavior).",
    )
    lease_generation = models.PositiveIntegerField(
        default=0,
        help_text="Fencing counter (Section 8.6, not part of the Section 7.2 "
        "column list — recorded in MT-1.6-05): every successful claim "
        "increments it, and mutating agent calls carry it so a slow former "
        "owner can never overwrite state after reclamation (ADR-012).",
    )
    last_checkpoint_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Most recent checkpoint time (WP-1.8 owns checkpoints).",
    )
    failure_retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Canonical name for the spec's retry_count (Section 7.2).",
    )
    audit_retry_count = models.PositiveIntegerField(
        default=0,
        help_text="WP-3.3 (Section 8.2 T12): audit leases released by expiry "
        "increment this counter — the audit-side twin of failure_retry_count, "
        "kept separate so an audit retry never consumes the coder retry budget "
        "(Section 8.3 invariant 1). Section 7.2 prints no such column; "
        "MT-3.3-03 requires T12 to increment one (recorded in the WP "
        "changelog as the plan's missing-field gap fill).",
    )
    attempt_number = models.PositiveIntegerField(
        default=0,
        help_text="Increments on each new coder claim (Section 7.2; WP-1.6).",
    )
    audit_required = models.BooleanField(
        default=True,
        help_text="Defaults from the project policy's audit_required_default at "
        "creation (Section 7.2) — the model default mirrors that value.",
    )
    review_reason = models.CharField(
        max_length=32,
        choices=ReviewReason.choices,
        null=True,
        blank=True,
        help_text="Section 8.4 canonical enum, nullable on the model.",
    )
    latest_feedback = models.TextField(
        blank=True,
        default="",
        help_text="Auditor/human text shown to the next coder (Section 7.2).",
    )
    merge_status = models.CharField(
        max_length=12,
        choices=MergeStatus.choices,
        default=MergeStatus.NONE,
        help_text="none | pending | merging | merged | conflict | failed "
        "(Section 7.2; merge-pending is this sub-status, not a state — 8.1).",
    )
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Soft-archive timestamp — the single archive marker; "
        "archiving preserves id continuity (Section 7.3; MT-1.4-06).",
    )
    created_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Actor reference of the creator (user id for an owner "
        "session) — Section 7.2 'Standard', actor-ref convention per 9.6/12.5.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The project this row was constructed with, for the immutability guard
    # (Section 7.4 rule 4: "A task's project_id never changes"). Not a
    # field — Django ignores non-Field class attributes.
    _original_project_id: str | None = None

    class Meta:
        """Section 7.4 integrity: id pattern + enums + floors, in the DB.

        The composite indexes serve the MT-1.4-04 list shape at NFR-09
        scale (10,000 tasks): the project-scoped default sort
        (priority → created_at) and the state filter.
        """

        constraints = [
            models.CheckConstraint(
                condition=models.Q(id__regex=TASK_ID_PATTERN),
                name="task_id_format",
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=TaskState.values),
                name="task_state_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(priority__in=TaskPriority.values),
                name="task_priority_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(version__gte=1),
                name="task_version_at_least_one",
            ),
            models.CheckConstraint(
                condition=models.Q(failure_retry_count__gte=0),
                name="task_failure_retry_count_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(audit_retry_count__gte=0),
                name="task_audit_retry_count_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_number__gte=0),
                name="task_attempt_number_non_negative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["project", "priority", "created_at"],
                name="task_proj_prio_created",
            ),
            models.Index(fields=["project", "state"], name="task_proj_state"),
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Capture the project this row was constructed with (guard source).

        Django constructs database rows through ``__init__`` with the
        fetched field values, so this catches loaded *and* new instances
        (the same approach as ``Project.__init__`` for its id guard — see
        its docstring for why not ``from_db``).
        """
        super().__init__(*args, **kwargs)
        self._original_project_id = self.project_id

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Section 7.4 rule 4: a loaded row's project never changes.

        The API exposes no project reassignment (the writable-field
        allowlist of MT-1.4-03 omits it), and this guard closes the ORM
        path for normal saves. ``queryset.update(...)`` bypasses
        ``save()`` like every Django model — the documented
        application-level limitation recorded in the WP changelog (same
        reading as Project's id-immutability guard, MT-1.3-02).
        """
        if (
            not self._state.adding
            and self._original_project_id is not None
            and self.project_id != self._original_project_id
        ):
            raise ValidationError({"project": "A task's project never changes (Section 7.4)."})
        super().save(*args, **kwargs)
        self._original_project_id = self.project_id

    def __str__(self) -> str:
        """Identify the row as its canonical id plus title."""
        return f"{self.id} {self.title}"
