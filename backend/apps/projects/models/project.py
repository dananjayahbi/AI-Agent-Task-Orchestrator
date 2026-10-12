"""The Project entity (parent plan Sections 7.2, 7.4; MT-1.3-02; FR-PRJ-02).

Exactly the Section 7.2 "Project" table — **none added, dropped or
renamed**:

* ``id`` — ``PID[0-9]{5}``, immutable (Section 7.3), assigned from the
  sequence (MT-1.3-01) and double-guarded here by a database
  ``CheckConstraint`` (Section 7.4: ids are validated at API boundaries
  *and* by the database) plus an in-application immutability guard on
  ``save()``;
* ``active_status`` — the canonical FR-PRJ-04 triple
  ``active``/``paused``/``archived`` (ADR-010 snake-case values);
* ``agent_policy`` — the Section 7.1 one-to-one link to Project Policy
  (``PROTECT``: neither side of the pair is ever silently deleted;
  projects themselves are never deleted — PATCH transitions only,
  MT-1.3-03);
* ``task_counter`` — starts at 0, consumed by MT-1.4-02's atomic
  per-project task ids (Section 7.3);
* ``created_at``/``updated_at`` — server clock, UTC (Section 0.4, P7).

``repo_path`` is stored as informational (Section 7.2) — path enforcement
is Section 12.3/bridge territory, out of scope here.
"""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError
from django.db import models

from apps.projects.services.pids import PROJECT_ID_PATTERN, validate_project_id

from .policy import ProjectPolicy


class ActiveStatus(models.TextChoices):
    """FR-PRJ-04 canonical status triple — three values, none added."""

    ACTIVE = "active", "active"
    PAUSED = "paused", "paused"
    ARCHIVED = "archived", "archived"


class Project(models.Model):
    """One registered repository — Section 7.2 field for field."""

    id = models.CharField(
        max_length=8,
        primary_key=True,
        validators=[validate_project_id],
        help_text="PID + five digits (Section 7.3); server-assigned and immutable.",
    )
    name = models.CharField(max_length=200)
    repo_path = models.CharField(
        max_length=500,
        help_text="Path as seen by the bridge host (informational for the backend).",
    )
    active_status = models.CharField(
        max_length=8,
        choices=ActiveStatus.choices,
        default=ActiveStatus.ACTIVE,
    )
    default_branch = models.CharField(max_length=255)
    system_prompt_rules = models.TextField(
        blank=True,
        default="",
        help_text="Markdown text fed into the rules block (Section 10.6).",
    )
    # Section 7.1: Project 1:1 Project Policy; created as a pair by the
    # CRUD service (MT-1.3-03) — the model carries the reference only
    # (MT-1.3-02 out-of-scope note: pair creation is not this migration's
    # logic).
    agent_policy = models.OneToOneField(
        ProjectPolicy,
        on_delete=models.PROTECT,
        related_name="project",
    )
    # Section 7.2/7.3: atomic task index generation lands with MT-1.4-02.
    task_counter = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # The primary key this row was constructed with, for the immutability
    # guard (Section 7.3: "id ... immutable"). Not a field — Django ignores
    # non-Field class attributes.
    _original_pk: str | None = None

    class Meta:
        """Section 7.4 integrity: the id pattern is enforced by the database."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(id__regex=PROJECT_ID_PATTERN),
                name="project_id_format",
            ),
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Capture the primary key at construction (guard source).

        Django constructs database rows through ``__init__`` with the
        fetched field values, so this catches loaded *and* new instances
        without overriding ``from_db`` (whose stub signature carries a
        ``fetch_mode`` Django 5.2's runtime does not accept).
        """
        super().__init__(*args, **kwargs)
        self._original_pk = self.pk

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Immutability guard: a loaded row's id never changes (7.3/7.4).

        The API exposes id as read-only (MT-1.3-03), and this guard closes
        the ORM path for normal saves. ``queryset.update(...)`` bypasses
        ``save()`` like every Django model — noted as a documented
        application-level limitation in the WP changelog (DB triggers are
        out of Section 20.3's sizing for this MT).
        """
        if (
            not self._state.adding
            and self._original_pk is not None
            and self.pk != self._original_pk
        ):
            raise ValidationError({"id": "Project id is immutable (Section 7.3)."})
        super().save(*args, **kwargs)
        self._original_pk = self.pk

    def __str__(self) -> str:
        """Identify the row as its canonical id plus name."""
        return f"{self.id} {self.name}"
