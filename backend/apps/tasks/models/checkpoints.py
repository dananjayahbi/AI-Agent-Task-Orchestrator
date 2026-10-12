"""The Task Checkpoint entity — Section 7.2 (MT-1.8-01; FR-LEA-03; P8).

Exactly the Section 7.2 "Task Checkpoint" field list — **none added,
dropped or renamed**: ``id`` (UUID), ``task_id``, ``attempt_number``,
``session_id``, ``timestamp`` (server), ``message``, ``percent``
(0-100, nullable), ``token_usage`` (JSON), ``kind``
(``progress`` / ``liveness`` / ``system`` — ADR-010-style canonical
values, frozen at the database like ``state``/``priority``).

Glossary: a checkpoint is "a progress report from an agent" that "also
extends the lease"; G-17 makes the checkpoint stream the v1 live feed
and checkpoints (default) the only lease-extension path. The endpoint,
gate and listing arrive with MT-1.8-02/03/04; this MT is the model
layer only.

Layered decisions, each recorded so nothing is hidden:

* **Append-only (P8)** — same discipline as ``TaskTransition``: the
  queryset refuses ``update``/``delete``/``bulk_update``, the model
  refuses re-``save()`` and ``delete()``. The database-level
  insert-only grants are MT-1.9-04's pattern and land there for this
  table too (app-level only here — same recorded caveat).
* **``timestamp`` is a callable default, not ``auto_now_add``** — the
  value is still server-set in production (principle P7: the API never
  accepts a client timestamp — the create serializer has no timestamp
  field). The deviation from ``TaskTransition``'s ``auto_now_add`` is
  deliberate: cursor pagination (WP-0.5-04) must break same-timestamp
  ties deterministically, and the unit tests need *controlled* tied
  timestamps to prove the tiebreak — ``auto_now_add`` would make those
  rows unconstructable. Insert-time control only: the append-only
  guards still refuse any post-insert change.
* **Index** — ``checkpoint_task_time`` on ``(task, timestamp)`` serves
  the MT-1.8-04 per-task reverse-chronological listing (cursor
  pagination). The exact query plan at NFR-09 scale is WP-1.15's
  performance dataset check, not an ad-hoc offset here.
* **``attempt_number``** is copied from the task at write time
  (denormalized deliberately — pre-reclaim checkpoints stay
  attributable; MT-1.8-03 copies it, it is never joined lazily).
* **``token_usage``** is a free JSON blob per Section 7.2 — no schema
  invented here (MT-1.8-01 risk note; a fixed shape would be an OQ).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone

from .task import Task


class CheckpointKind(models.TextChoices):
    """Section 7.2 ``kind`` — the three canonical values, none added."""

    PROGRESS = "progress", "progress"
    LIVENESS = "liveness", "liveness"
    SYSTEM = "system", "system"


class CheckpointImmutable(Exception):
    """Any attempt to mutate a checkpoint row after insert (P8)."""


class CheckpointQuerySet(models.QuerySet["TaskCheckpoint"]):
    """Mutations are refused: checkpoints only ever come into existence."""

    def update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse in-place edits (P8 append-only)."""
        raise CheckpointImmutable("Task Checkpoint rows cannot be updated (P8).")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Refuse row deletion — progress history is never removed."""
        raise CheckpointImmutable("Task Checkpoint rows cannot be deleted (P8).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits — no ORM door around the insert-only rule."""
        raise CheckpointImmutable("Task Checkpoint rows cannot be updated (P8).")


class CheckpointManager(models.Manager.from_queryset(CheckpointQuerySet)):  # type: ignore[misc]
    """The default manager — queryset-level immutability rides through."""


class TaskCheckpoint(models.Model):
    """One progress report from an agent (Section 7.2; Section 3 glossary)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated, never client-supplied.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # checkpoints are never orphaned; tasks are never deleted (7.3)
        related_name="checkpoints",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    attempt_number = models.PositiveIntegerField(
        help_text="The task's coder claim attempt at write time (Section 7.2) — "
        "denormalized so pre-reclaim checkpoints stay attributable.",
    )
    session_id = models.CharField(
        max_length=255,
        help_text="Bridge-issued session id of the reporting agent (G-18; Section 7.2).",
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="Server clock at insertion (principle P7); the checkpoint's 'when'. "
        "Callable default instead of auto_now_add solely so the cursor "
        "tiebreak tests can construct controlled timestamps (module "
        "docstring); the API never accepts a client value.",
    )
    message = models.TextField(
        blank=True,
        default="",
        help_text="The agent's progress report text (Section 7.2).",
    )
    percent = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
        help_text="Optional 0-100 completion hint (Section 7.2); bounds enforced "
        "at the boundary (validator, serializer) and by the database "
        "check below.",
    )
    token_usage = models.JSONField(
        default=dict,
        blank=True,
        help_text="Free JSON token accounting blob (Section 7.2) — no schema "
        "invented; a fixed shape is an open question (MT-1.8-01 risk).",
    )
    kind = models.CharField(
        max_length=16,
        choices=CheckpointKind.choices,
        default=CheckpointKind.PROGRESS,
        help_text="progress | liveness | system (Section 7.2; ADR-010).",
    )

    objects = CheckpointManager()

    class Meta:
        """Append-only history: DB-frozen kind/percent, listing index."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(percent__isnull=True)
                | (models.Q(percent__gte=0) & models.Q(percent__lte=100)),
                name="checkpoint_percent_bounds",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=CheckpointKind.values),
                name="checkpoint_kind_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_number__gte=0),
                name="checkpoint_attempt_number_non_negative",
            ),
        ]
        indexes = [
            # MT-1.8-04's per-task reverse-chronological listing (cursor
            # pagination, WP-0.5-04); the uuid PK breaks timestamp ties.
            models.Index(fields=["task", "timestamp"], name="checkpoint_task_time"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Insert-only: allow the very first write, refuse every later one."""
        if not self._state.adding:
            raise CheckpointImmutable("Task Checkpoint rows cannot be updated (P8).")
        super().save(*args, **kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Delete is not a verb progress history has (P8)."""
        raise CheckpointImmutable("Task Checkpoint rows cannot be deleted (P8).")

    def __str__(self) -> str:
        """Identify the row as task, kind, percent and time."""
        return f"{self.task_id}: {self.kind} {self.percent}% at {self.timestamp}"
