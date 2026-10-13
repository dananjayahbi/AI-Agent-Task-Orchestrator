"""Task Resolution + Task Artifact — Section 7.2 (WP-3.2; FR-AUD-01; FR-TSK-03).

Exactly the Section 7.2 field sets — **none added, dropped or renamed**:

* **Task Resolution** "one per submission attempt": ``id``, ``task_id``,
  ``attempt_number``, ``branch_name``, ``commit_sha``,
  ``execution_summary``, ``diff_summary`` (stats: files, insertions,
  deletions), ``changed_files`` (list), ``requires_human_attention``,
  ``risk_justification``, ``submitted_by_session``, ``submitted_at``.
* **Task Artifact**: ``id``, ``resolution_id``, ``kind`` (``patch``;
  ``output_tail`` reserved for the deferred MT-2.6-06 output tail),
  ``storage_key``, ``size_bytes``, ``sha256``.

Layered decisions, each recorded so nothing is hidden:

* **One resolution per (task, attempt)** — the uniqueness constraint is
  the database's half of MT-3.2-01's acceptance ("a later attempt cannot
  overwrite an earlier resolution"); the service's pre-check answers the
  catalog ``TASK_STATE_CONFLICT`` instead of leaking an ``IntegrityError``,
  and a distinct submission on the same attempt can never write a second
  row (Section 7.2 "one per submission attempt").
* **Stats arrive server-computed** (Section 9.7; MT-3.2-03): the service
  parses the stored patch *before* inserting, so the row is written once
  with the authoritative ``diff_summary``/``changed_files`` — any
  bridge-supplied provisional values are replaced, never merged (the
  insert-only guard below then keeps them frozen for the audit trail).
* **Insert-only (P8)** — same discipline as ``TaskCheckpoint``: the
  queryset refuses ``update``/``delete``/``bulk_update`` and the model
  refuses re-``save()``/``delete()``. Resolutions are submission history;
  the Policy Engine and the auditor read them as written.
  ``TaskArtifact`` deliberately does **not** copy that lock: artifacts
  are storage records, and Section 9.9's retention job must be able to
  prune old patch bodies later (MT-3.2-02 out-of-scope note) — its
  immutability is the service's (created once, never rewritten).
* **``submitted_at`` is a callable default** (server clock, principle
  P7) — the create serializer has no timestamp field, same as
  ``TaskCheckpoint.timestamp``.
* **No scope/marker columns** — the Section 20.5 field set is closed;
  the scope verdict rides the submission response (and is recomputed
  from these ``changed_files`` by the shared matcher), and "diff too
  large" is derived from ``size_bytes`` against the Section 9.7 cap
  (MT-3.2-02's recorded reading).
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .task import Task


class ArtifactKind(models.TextChoices):
    """Section 7.2 ``kind`` — ``patch`` now, ``output_tail`` deferred."""

    PATCH = "patch", "patch"
    OUTPUT_TAIL = "output_tail", "output_tail"


class ResolutionImmutable(Exception):
    """Any attempt to mutate a resolution row after insert (P8)."""


class ResolutionQuerySet(models.QuerySet["TaskResolution"]):
    """Mutations are refused: a stored submission is history (P8)."""

    def update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse in-place edits (P8 append-only)."""
        raise ResolutionImmutable("Task Resolution rows cannot be updated (P8).")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Refuse row deletion — submission history is never removed."""
        raise ResolutionImmutable("Task Resolution rows cannot be deleted (P8).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits — no ORM door around the insert-only rule."""
        raise ResolutionImmutable("Task Resolution rows cannot be updated (P8).")


class ResolutionManager(models.Manager.from_queryset(ResolutionQuerySet)):  # type: ignore[misc]
    """The default manager — queryset-level immutability rides through."""


class TaskResolution(models.Model):
    """One submission attempt (Section 7.2 "Task Resolution")."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated, never client-supplied.",
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,  # resolutions are never orphaned (7.3: no deletes)
        related_name="resolutions",
        help_text="Section 7.2 ``task_id`` — the FK column is task_id.",
    )
    attempt_number = models.PositiveIntegerField(
        validators=[MinValueValidator(0)],
        help_text="The task's coder claim attempt this submission answers "
        "(Section 7.2) — copied from the locked task at write time; "
        "unique per task (one resolution per submission attempt).",
    )
    branch_name = models.CharField(
        max_length=255,
        help_text="Git branch the patch was captured from (Section 7.2; "
        "the bridge's verified ``git_branch`` of Section 10.5).",
    )
    commit_sha = models.CharField(
        max_length=64,
        help_text="Commit the submission points at (Section 7.2; verified "
        "by the bridge per Section 10.5, stored here verbatim).",
    )
    execution_summary = models.TextField(
        help_text="The coder's summary of what ran (Section 7.2).",
    )
    diff_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Authoritative stats {files, insertions, deletions} parsed "
        "server-side from the stored patch (Section 9.7; MT-3.2-03) — "
        "bridge-supplied values are provisional until this parse.",
    )
    changed_files = models.JSONField(
        default=list,
        blank=True,
        help_text="Authoritative repo-relative paths touched, parsed from the "
        "stored patch (Section 9.7) — the input the scope check and "
        "Policy Engine R2 read (never an agent-supplied claim).",
    )
    requires_human_attention = models.BooleanField(
        default=False,
        help_text="The coder's self-flag (Section 7.2; T8's guard input).",
    )
    risk_justification = models.TextField(
        blank=True,
        default="",
        help_text="The coder's justification when self-flagging (Section 7.2).",
    )
    submitted_by_session = models.CharField(
        max_length=255,
        help_text="Bridge session that submitted (Section 7.2; G-18) — "
        "always the current lease owner (Section 9.2).",
    )
    submitted_at = models.DateTimeField(
        default=timezone.now,
        help_text="Server clock at insertion (principle P7); the API never accepts a client value.",
    )

    objects = ResolutionManager()

    class Meta:
        """One row per (task, attempt) — Section 7.2's cardinality rule."""

        constraints = [
            models.UniqueConstraint(
                fields=["task", "attempt_number"],
                name="resolution_one_per_attempt",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_number__gte=0),
                name="resolution_attempt_number_non_negative",
            ),
        ]
        indexes = [
            # MT-3.2-01's listing (newest usable for the auditor flow,
            # FR-AUD-01): per-task reverse-chronological paging; the uuid
            # PK breaks submitted_at ties deterministically.
            models.Index(fields=["task", "submitted_at"], name="resolution_task_time"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Insert-only: allow the very first write, refuse every later one."""
        if not self._state.adding:
            raise ResolutionImmutable("Task Resolution rows cannot be updated (P8).")
        super().save(*args, **kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Delete is not a verb submission history has (P8)."""
        raise ResolutionImmutable("Task Resolution rows cannot be deleted (P8).")

    def __str__(self) -> str:
        """Identify the row as task, attempt and commit."""
        return f"{self.task_id} attempt {self.attempt_number} @ {self.commit_sha[:12]}"


class TaskArtifact(models.Model):
    """The stored unified patch (Section 7.2 "Task Artifact"; Section 9.7)."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Section 7.2 ``id`` (UUID) — server-generated.",
    )
    resolution = models.ForeignKey(
        TaskResolution,
        on_delete=models.PROTECT,
        related_name="artifacts",
        help_text="Section 7.2 ``resolution_id`` — the FK column is resolution_id.",
    )
    kind = models.CharField(
        max_length=16,
        choices=ArtifactKind.choices,
        default=ArtifactKind.PATCH,
        help_text="patch | output_tail (Section 7.2; ADR-010 canonical values).",
    )
    storage_key = models.CharField(
        max_length=255,
        help_text="Content-derived key in the configured storage backend "
        "(Section 9.10) — empty when the Section 9.7 oversize path kept "
        "stats and file list only (no body stored).",
    )
    size_bytes = models.PositiveBigIntegerField(
        help_text="Server-computed size of the received patch bytes "
        "(Section 7.2); above the 5 MB cap it records what arrived "
        "while no body is stored (Section 9.7).",
    )
    sha256 = models.CharField(
        max_length=64,
        help_text="Server-computed SHA-256 hex of the received patch bytes "
        "(Section 7.2) — computed from the bytes, never trusted from "
        "the client.",
    )

    class Meta:
        """One patch artifact per resolution (Section 9.7's single patch)."""

        constraints = [
            models.UniqueConstraint(
                fields=["resolution", "kind"],
                name="artifact_one_per_resolution_kind",
            ),
            models.CheckConstraint(
                condition=models.Q(kind__in=ArtifactKind.values),
                name="artifact_kind_canonical",
            ),
        ]

    def __str__(self) -> str:
        """Identify the row as resolution kind and size."""
        return f"{self.resolution_id} {self.kind} ({self.size_bytes} bytes)"
