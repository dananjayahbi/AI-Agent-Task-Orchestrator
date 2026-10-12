"""MT-1.8-01 — the Task Checkpoint model (Section 7.2; P8; G-11; G-17).

Run with ``pytest backend/tests -k checkpoint_model -q``. The suite
proves the MT's acceptance criteria against the model itself:

* the field set is **exactly** Section 7.2's nine fields (none added,
  dropped or renamed) with the ``task_id`` column spelling;
* ``percent`` enforces the 0-100 bounds and nullability at the boundary
  *and* at the database (CheckConstraint — WP-1.8 acceptance);
* ``kind`` accepts only ``progress`` / ``liveness`` / ``system`` —
  choices *and* database check (ADR-010, frozen at the database);
* ``token_usage`` is a free JSON blob defaulting to ``{}`` (no schema
  invented — the MT-1.8-01 risk note);
* rows are append-only at the application layer (P8) with a
  server-stamped ``timestamp``;
* the ``(task, timestamp)`` listing index exists for MT-1.8-04's
  reverse-chronological cursor pagination;
* ``store_checkpoint`` is the task-side touch point: it copies
  ``attempt_number`` at write time and moves
  ``Task.last_checkpoint_at`` (Section 7.2; Section 8.6's stalled
  indicator input).

The remaining enforcement gap — a raw-SQL writer — closes with WP-1.9's
database grants (MT-1.9-04's pattern), same recorded caveat as the
transition history.
"""

from __future__ import annotations

from typing import cast

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.projects.models import Project
from apps.tasks.models import CheckpointImmutable, CheckpointKind, Task, TaskCheckpoint
from apps.tasks.services.checkpoints import store_checkpoint

from .wp15_helpers import make_project, make_task

# Section 7.2 "Task Checkpoint", verbatim — the literal field-set assertion.
PLAN_7_2_CHECKPOINT_FIELDS: tuple[str, ...] = (
    "id",
    "task",  # Section 7.2 spells it task_id (column + attname)
    "attempt_number",
    "session_id",
    "timestamp",
    "message",
    "percent",
    "token_usage",
    "kind",
)


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the model tests."""
    return make_project(name="Checkpoint model")


@pytest.fixture
def task(project: Project) -> Task:
    """One draft task row."""
    return make_task(project, 1)


# --- field set and value catalogs (Section 7.2; ADR-010) --------------------


def test_checkpoint_model_field_set_matches_section_7_2_exactly() -> None:
    """Nine fields, none added, none dropped, none renamed (20.5 traceability)."""
    names = tuple(field.name for field in TaskCheckpoint._meta.get_fields() if field.concrete)
    assert names == PLAN_7_2_CHECKPOINT_FIELDS, set(names) ^ set(PLAN_7_2_CHECKPOINT_FIELDS)

    task_field = TaskCheckpoint._meta.get_field("task")
    assert task_field.attname == "task_id", "the Section 7.2 FK column name"
    assert task_field.column == "task_id"
    assert TaskCheckpoint._meta.pk.name == "id"


def test_kind_catalog_is_the_three_canonical_values() -> None:
    """progress | liveness | system — nothing added (Section 7.2)."""
    assert tuple(CheckpointKind.values) == ("progress", "liveness", "system")


def test_token_usage_defaults_to_an_empty_object(task: Task) -> None:
    """Free JSON blob, default ``{}`` — no invented schema (risk note)."""
    checkpoint = TaskCheckpoint.objects.create(task=task, attempt_number=0, session_id="sess_model")
    assert checkpoint.token_usage == {}
    assert checkpoint.percent is None, "nullable per Section 7.2"
    assert checkpoint.kind == CheckpointKind.PROGRESS, "default progress"


# --- percent bounds and kind enum at the database (WP-1.8 acceptance) ------


def test_percent_bounds_hold_at_the_database(task: Task) -> None:
    """0 and 100 store; 101 and -1 are refused by the CheckConstraint."""
    for percent in (0, 50, 100):
        row = TaskCheckpoint.objects.create(
            task=task, attempt_number=0, session_id="sess_model", percent=percent
        )
        assert row.percent == percent

    for bad in (101, -1):
        with pytest.raises(IntegrityError):
            with transaction.atomic():  # contain the broken statement
                TaskCheckpoint.objects.create(
                    task=task,
                    attempt_number=0,
                    session_id="sess_model",
                    percent=bad,
                )


def test_percent_boundary_is_valid_but_101_is_not(task: Task) -> None:
    """Model-level full_clean mirrors the DB rule (boundary sanity)."""
    checkpoint = TaskCheckpoint(task=task, attempt_number=0, session_id="sess_model", percent=100)
    checkpoint.full_clean()  # 100 is inside the bounds
    checkpoint.percent = 101
    with pytest.raises(DjangoValidationError):
        checkpoint.full_clean()


def test_database_refuses_non_canonical_kind(task: Task) -> None:
    """The CheckConstraint holds the frozen set even against raw INSERTs."""
    for bad in ("ping", "PROGRESS", ""):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                TaskCheckpoint.objects.create(
                    task=task, attempt_number=0, session_id="sess_model", kind=bad
                )


def test_negative_attempt_number_is_refused(task: Task) -> None:
    """``attempt_number`` mirrors Task's non-negative CheckConstraint."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TaskCheckpoint.objects.create(task=task, attempt_number=-1, session_id="sess_model")


# --- append-only at the application layer (P8) -----------------------------


@pytest.fixture
def row(task: Task) -> TaskCheckpoint:
    """One checkpoint row through its natural write path."""
    return store_checkpoint(task, session_id="sess_p8", message="halfway")


def test_update_attempts_fail_at_the_application_layer(row: TaskCheckpoint) -> None:
    """save-after-insert, queryset update and bulk_update all refuse."""
    with pytest.raises(CheckpointImmutable, match="cannot be updated"):
        row.save()

    with pytest.raises(CheckpointImmutable, match="cannot be updated"):
        TaskCheckpoint.objects.filter(pk=row.pk).update(message="tampered")

    with pytest.raises(CheckpointImmutable, match="cannot be updated"):
        TaskCheckpoint.objects.bulk_update([row], ["message"])

    row.refresh_from_db()
    assert row.message == "halfway", "the refusal persisted nothing"


def test_delete_attempts_fail_at_the_application_layer(row: TaskCheckpoint) -> None:
    """Model delete and queryset delete refuse; the row survives both."""
    with pytest.raises(CheckpointImmutable, match="cannot be deleted"):
        row.delete()

    with pytest.raises(CheckpointImmutable, match="cannot be deleted"):
        TaskCheckpoint.objects.all().delete()

    assert TaskCheckpoint.objects.filter(pk=row.pk).exists(), "history is never removed"


def test_timestamp_is_server_stamped_and_stable(task: Task) -> None:
    """P7: the server stamps ``timestamp`` at insert; it never re-stamps."""
    before = timezone.now()
    checkpoint = TaskCheckpoint.objects.create(task=task, attempt_number=0, session_id="sess_p7")
    assert checkpoint.timestamp is not None
    assert before <= checkpoint.timestamp <= timezone.now()

    # ...and an append-only row never re-stamps: the stored value is identical.
    stored = TaskCheckpoint.objects.get(pk=checkpoint.pk)
    assert stored.timestamp == checkpoint.timestamp


# --- the listing index for MT-1.8-04 (cursor pagination) --------------------


def test_listing_index_serves_per_task_reverse_chronological_scans(db: None) -> None:
    """``checkpoint_task_time`` on (task, timestamp) exists in the migration."""
    index_names = [index.name for index in TaskCheckpoint._meta.indexes]
    assert "checkpoint_task_time" in index_names
    index = next(i for i in TaskCheckpoint._meta.indexes if i.name == "checkpoint_task_time")
    assert tuple(index.fields) == ("task", "timestamp")

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'index' AND name = %s",
            ["checkpoint_task_time"],  # the declared name, used verbatim
        )
        found = cursor.fetchone()
    assert found is not None and int(found[0]) == 1, "the index must exist in the DB"


# --- the task-side touch point (Section 7.2; Section 8.6) -------------------


def test_store_checkpoint_copies_attempt_and_touches_last_checkpoint_at(
    task: Task,
) -> None:
    """The MT-1.8-01 touch point: attempt copied, ``last_checkpoint_at`` moves."""
    assert task.attempt_number == 0
    assert task.last_checkpoint_at is None

    checkpoint = store_checkpoint(task, session_id="sess_touch", message="50%", percent=50)

    assert checkpoint.attempt_number == task.attempt_number, "copied at write time"
    assert checkpoint.session_id == "sess_touch"
    task.refresh_from_db()
    assert task.last_checkpoint_at == checkpoint.timestamp
    assert task.version == 2, "the touch is a row change (Section 7.2 bump)"


def test_touch_point_tracks_the_current_attempt(task: Task) -> None:
    """A later attempt's checkpoints carry the later number (denormalized)."""
    Task.objects.filter(pk=task.pk).update(attempt_number=3)
    task.refresh_from_db()

    checkpoint = store_checkpoint(task, session_id="sess_touch")

    assert checkpoint.attempt_number == 3


# --- migration applies cleanly in the test database (Section 18) -----------


def test_checkpoint_table_exists_after_migrations(db: None) -> None:
    """The migration landed: the table and its constraints are present."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
            ["tasks_taskcheckpoint"],
        )
        found = cursor.fetchone()
    assert found is not None and int(found[0]) == 1


def test_checkpoint_is_exported_from_the_model_surface() -> None:
    """``apps.tasks.models`` re-exports the checkpoint surface for consumers."""
    from apps.tasks import models as model_surface

    assert model_surface.TaskCheckpoint is TaskCheckpoint
    assert model_surface.CheckpointKind is CheckpointKind
    assert model_surface.CheckpointImmutable is CheckpointImmutable
    assert cast(str, CheckpointKind.PROGRESS) == "progress"
