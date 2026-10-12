"""The append-only Event log — Sections 9.6 and 12.5 (MT-1.9-01; FR-SEC-03).

One row per state-changing action, in the same transaction as the change
(P8; Section 9.3), append-only (Section 12.5: the application database
role cannot update or delete audit rows — enforced in layers like the
Task Transition history: no API surface, hard ORM errors here, and the
database-level guard migration of MT-1.9-04).

Field provenance — **exactly** the Section 9.6 envelope plus the
Section 12.5 correlation id, nothing else:

======================  ===================================================
Model field             Section 9.6 envelope key
======================  ===================================================
``id``                  ``id`` — monotonic sequence, *the* SSE event id
``type``                ``type`` — one of the Section 9.6 catalog strings
``project_id``          ``project_id`` (stored as a plain id: an event outlives
                        any retention question about its project, and a
                        foreign key would invite cascade deletes against an
                        append-only table)
``task_id``             ``task_id`` (nullable — project-level events)
``occurred_at``         ``occurred_at`` — server clock at write time, inside
                        the transaction (principle P7)
``actor_type`` ─┐       ``actor`` — structured ``{"type": ..., "ref": ...}``
``actor_ref``   ─┘       (the columns follow Section 7.2's Event Log row;
                         the envelope re-groups them — never flattened)
``data``                ``data`` (JSON payload)
``correlation_id``      *(no envelope key)* — Section 12.5's correlation id,
                        column only; the published envelope stays exactly
                        the seven Section 9.6 keys
======================  ===================================================

The ``id`` strategy: a ``BigAutoField`` primary key — the database's own
sequence. Ids are strictly increasing and never reused; gaps are allowed
(delivery guarantees in Section 9.6's resume clause refer to events, not
to contiguous ids), and replay orders rows by ``id`` for a total order
(input to MT-1.10-03). The plan's Section 7.2 field-name sketch
(``payload``/``created_at``) is superseded by the Section 9.6 envelope
names, as MT-1.9-01's acceptance requires.

Read shapes: ordered by ``id`` for replay; filtered by project or task
with the composite ``(project_id, id)`` / ``(task_id, id)`` indexes;
correlated with request logs through ``correlation_id``.
"""

from __future__ import annotations

from typing import Any

from django.db import models

from .catalog import SECTION_9_6_EVENT_TYPES


class EventImmutable(Exception):
    """Any attempt to mutate an event row after insert (Section 12.5)."""


class EventActorType(models.TextChoices):
    """Section 7.2/9.6 ``actor.type`` — the same canonical triad."""

    OWNER = "owner", "owner"
    AGENT = "agent", "agent"
    SYSTEM = "system", "system"


class EventType(models.TextChoices):
    """The Section 9.6 catalog as choices — one member per plan string.

    Mirrors :data:`apps.events.catalog.SECTION_9_6_EVENT_TYPES` member for
    member; the catalog test pins the two together, and the table's
    ``CheckConstraint`` freezes the same closed set at the database
    (catalog-first discipline, Section 20.4 item 5).
    """

    PROJECT_CREATED = "project.created", "project.created"
    PROJECT_UPDATED = "project.updated", "project.updated"
    TASK_CREATED = "task.created", "task.created"
    TASK_UPDATED = "task.updated", "task.updated"
    TASK_TRANSITIONED = "task.transitioned", "task.transitioned"
    TASK_CLAIMED = "task.claimed", "task.claimed"
    TASK_RELEASED = "task.released", "task.released"
    TASK_CHECKPOINT = "task.checkpoint", "task.checkpoint"
    TASK_LEASE_EXPIRING = "task.lease_expiring", "task.lease_expiring"
    TASK_LEASE_EXPIRED = "task.lease_expired", "task.lease_expired"
    ATTACHMENT_PROCESSING = "attachment.processing", "attachment.processing"
    ATTACHMENT_READY = "attachment.ready", "attachment.ready"
    ATTACHMENT_FAILED = "attachment.failed", "attachment.failed"
    AUDIT_CLAIMED = "audit.claimed", "audit.claimed"
    AUDIT_PASSED = "audit.passed", "audit.passed"
    AUDIT_ESCALATED = "audit.escalated", "audit.escalated"
    REVIEW_REQUESTED = "review.requested", "review.requested"
    REVIEW_DECIDED = "review.decided", "review.decided"
    MERGE_STARTED = "merge.started", "merge.started"
    MERGE_SUCCEEDED = "merge.succeeded", "merge.succeeded"
    MERGE_FAILED = "merge.failed", "merge.failed"
    AGENT_SESSION_STARTED = "agent.session_started", "agent.session_started"
    AGENT_SESSION_ENDED = "agent.session_ended", "agent.session_ended"
    SYSTEM_ALERT = "system.alert", "system.alert"


class EventQuerySet(models.QuerySet["Event"]):
    """Mutations are refused: events only ever come into existence."""

    def update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse in-place edits (Section 12.5 append-only)."""
        raise EventImmutable("Event rows cannot be updated (Section 12.5).")

    def delete(self) -> tuple[int, dict[str, int]]:
        """Refuse row deletion — the audit trail is never removed by the app."""
        raise EventImmutable("Event rows cannot be deleted (Section 12.5).")

    def bulk_update(self, *args: Any, **kwargs: Any) -> int:
        """Refuse bulk edits — no ORM door around the insert-only rule."""
        raise EventImmutable("Event rows cannot be updated (Section 12.5).")


class EventManager(models.Manager.from_queryset(EventQuerySet)):  # type: ignore[misc]
    """The default manager — queryset-level immutability rides through."""


class Event(models.Model):
    """One audit event: the Section 9.6 envelope, written in-transaction."""

    id = models.BigAutoField(
        primary_key=True,
        help_text="Monotonic sequence — the event's SSE id (Section 9.6).",
    )
    type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        help_text="One of the 24 Section 9.6 catalog types (closed set).",
    )
    project_id = models.CharField(
        max_length=8,
        help_text="Section 9.6 ``project_id`` — the addressed PID (plain id, "
        "not an FK: audit rows are never cascade-deleted).",
    )
    task_id = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Section 9.6 ``task_id``; null for project-level events.",
    )
    occurred_at = models.DateTimeField(
        help_text="Server clock at write time, inside the committing "
        "transaction (Section 9.6; principle P7).",
    )
    actor_type = models.CharField(
        max_length=8,
        choices=EventActorType.choices,
        help_text="Envelope ``actor.type`` — owner | agent | system (Section 7.2).",
    )
    actor_ref = models.CharField(
        max_length=255,
        help_text="Envelope ``actor.ref`` — owner user id, agent session/token "
        "id, or a system label like 'lease-sweeper' (Section 9.6).",
    )
    data = models.JSONField(
        default=dict,
        help_text="Envelope ``data`` — free JSON payload (Section 9.6).",
    )
    correlation_id = models.CharField(
        max_length=64,
        help_text="Section 12.5 correlation id — links the row to the "
        "request's structured log lines; column only, not an envelope key.",
    )

    objects = EventManager()

    class Meta:
        """Append-only audit trail: closed catalogs, replay/filter indexes."""

        constraints = [
            models.CheckConstraint(
                condition=models.Q(type__in=SECTION_9_6_EVENT_TYPES),
                name="event_type_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(actor_type__in=EventActorType.values),
                name="event_actor_type_canonical",
            ),
        ]
        indexes = [
            # Replay: WHERE project_id/task_id ... ORDER BY id (MT-1.10-03).
            models.Index(fields=["project_id", "id"], name="event_project_id"),
            models.Index(fields=["task_id", "id"], name="event_task_id"),
            # Section 12.5: correlate an event with its request log lines.
            models.Index(fields=["correlation_id"], name="event_correlation"),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Insert-only: allow the very first write, refuse every later one."""
        if not self._state.adding:
            raise EventImmutable("Event rows cannot be updated (Section 12.5).")
        super().save(*args, **kwargs)

    def delete(self) -> tuple[int, dict[str, int]]:  # type: ignore[override]
        """Delete is not a verb the audit trail has (Section 12.5)."""
        raise EventImmutable("Event rows cannot be deleted (Section 12.5).")

    def __str__(self) -> str:
        """Identify the row as event, project and time."""
        return f"{self.id}: {self.type} for {self.project_id} at {self.occurred_at}"
