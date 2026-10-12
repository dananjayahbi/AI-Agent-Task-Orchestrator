"""MT-1.5-05 — append-only Task Transition history (FR-TSK-04; P8; Section 7.4 rule 5).

Run with ``pytest backend/tests -k transition_history -q``. The suite
proves the MT's acceptance criteria against the model itself:

* the field set is **exactly** Section 7.2's nine fields (none added,
  dropped or renamed) with the ``task_id`` column spelling;
* ``from_state``/``to_state`` accept only the six canonical states and
  ``actor_type`` only the three canonical actors — at the boundary
  (choices) *and* at the database (CheckConstraints), ADR-010;
* update and delete fail at the application layer — model ``save()``
  after insert, model ``delete()``, queryset ``update``/``delete``/
  ``bulk_update`` all raise ``TransitionHistoryImmutable``;
* every dispatched transition writes **exactly one** row with actor,
  from, to, reason and timestamp populated (FR-TSK-04);
* the migration applies and reverses cleanly (Section 18 quality gates).

The remaining enforcement gap — a raw-SQL writer — closes with WP-1.9's
database grants (MT-1.9-04); recorded in the WP changelog, not papered
over here.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import cast

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction

from apps.projects.models import Project
from apps.tasks.models import (
    ActorType,
    ReviewReason,
    TaskState,
    TaskTransition,
    TransitionReason,
)
from apps.tasks.models.transitions import TransitionHistoryImmutable
from apps.tasks.state_machine.dispatcher import dispatch_transition

from .wp15_helpers import make_project, make_task, registered_registry, reset_hooks

# Section 7.2 "Task Transition", verbatim — the literal field-set assertion.
PLAN_7_2_TRANSITION_FIELDS: tuple[str, ...] = (
    "id",
    "task",  # Section 7.2 spells it task_id (column + attname)
    "from_state",
    "to_state",
    "actor_type",
    "actor_ref",
    "reason_code",
    "note",
    "timestamp",
)

# Section 8.2 trigger codes that double as reason codes (Section 8.4
# members are covered by ReviewReason.values below).
TRIGGER_REASON_CODES: frozenset[str] = frozenset(
    {
        "publish",
        "unpublish",
        "archive",
        "lease_expired",
        "claim",
        "voluntary_release",
        "submit",
        "submit_flagged",
    }
)


@pytest.fixture(autouse=True)
def registry_guard() -> Iterator[None]:
    """Dispatches in this suite use only the default rows."""
    with registered_registry():
        yield


@pytest.fixture(autouse=True)
def clean_hooks() -> Iterator[None]:
    reset_hooks()
    yield
    reset_hooks()


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the history tests."""
    return make_project(name="Transition history")


# --- field set and value catalogs (Section 7.2; ADR-010) ---------------------


def test_history_model_field_set_matches_section_7_2_exactly() -> None:
    """Nine fields, none added, none dropped, none renamed (20.5 traceability)."""
    names = tuple(field.name for field in TaskTransition._meta.get_fields() if field.concrete)
    assert names == PLAN_7_2_TRANSITION_FIELDS, set(names) ^ set(PLAN_7_2_TRANSITION_FIELDS)

    task_field = TaskTransition._meta.get_field("task")
    assert task_field.attname == "task_id", "the Section 7.2 FK column name"
    assert task_field.column == "task_id"
    assert TaskTransition._meta.pk.name == "id"


def test_state_and_actor_columns_are_canonical_by_choices() -> None:
    """Six states, three actors, reasons = 8.4 enum + trigger codes."""
    assert tuple(TaskState.values) == (
        "draft",
        "pending",
        "in_progress",
        "to_be_audited",
        "in_human_review",
        "completed",
    )
    assert tuple(ActorType.values) == ("owner", "agent", "system")
    reason_values = set(TransitionReason.values)
    assert set(ReviewReason.values) <= reason_values, "the Section 8.4 twelve"
    assert TRIGGER_REASON_CODES <= reason_values, "the Section 8.2 trigger codes"


def test_database_refuses_non_canonical_state_and_actor(project: Project) -> None:
    """CheckConstraints hold the frozen sets even against raw INSERTs."""
    task = make_task(project, 1)
    for field, bad_value in (
        ("from_state", "archived"),
        ("to_state", "done"),
        ("actor_type", "robot"),
    ):
        with pytest.raises(IntegrityError):
            with transaction.atomic():  # contain the broken statement
                TaskTransition.objects.create(
                    task=task,
                    actor_ref="x",
                    reason_code="publish",
                    **{field: bad_value},
                )


# --- append-only at the application layer (P8; rule 5) -----------------------


@pytest.fixture
def row(project: Project) -> TaskTransition:
    """One history row produced by a real dispatch (its natural write path)."""
    task = make_task(project, 1)
    dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref="user:1",
    )
    return cast(TaskTransition, TaskTransition.objects.get(task=task))


def test_update_attempts_fail_at_the_application_layer(row: TaskTransition) -> None:
    """save-after-insert, queryset update and bulk_update all refuse."""
    with pytest.raises(TransitionHistoryImmutable, match="cannot be updated"):
        row.save()

    with pytest.raises(TransitionHistoryImmutable, match="cannot be updated"):
        TaskTransition.objects.filter(pk=row.pk).update(note="tampered")

    with pytest.raises(TransitionHistoryImmutable, match="cannot be updated"):
        TaskTransition.objects.bulk_update([row], ["note"])

    row.refresh_from_db()
    assert row.note == "", "the refusal persisted nothing"


def test_delete_attempts_fail_at_the_application_layer(row: TaskTransition) -> None:
    """Model delete and queryset delete refuse; the row survives both."""
    with pytest.raises(TransitionHistoryImmutable, match="cannot be deleted"):
        row.delete()

    with pytest.raises(TransitionHistoryImmutable, match="cannot be deleted"):
        TaskTransition.objects.all().delete()

    assert TaskTransition.objects.filter(pk=row.pk).exists(), "history is never removed"


# --- completeness: one row per dispatched transition (FR-TSK-04) --------------


def test_every_dispatch_writes_exactly_one_complete_row(project: Project) -> None:
    """Actor, when, from, to and reason populated on the single row."""
    task = make_task(project, 1)

    dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref="user:1",
        note="goes to the agents",
    )
    first = TaskTransition.objects.get(task=task)
    assert (
        first.actor_type,
        first.actor_ref,
        first.from_state,
        first.to_state,
        first.reason_code,
        first.note,
    ) == ("owner", "user:1", "draft", "pending", "publish", "goes to the agents")
    assert first.timestamp is not None, "the 'when' of FR-TSK-04"

    dispatch_transition(
        task_id=task.pk,
        trigger="unpublish",
        actor_type="owner",
        actor_ref="user:1",
    )
    rows = list(TaskTransition.objects.filter(task=task).order_by("timestamp", "id"))
    assert len(rows) == 2, "exactly one row per successful transition"
    assert (rows[1].from_state, rows[1].to_state, rows[1].reason_code) == (
        "pending",
        "draft",
        "unpublish",
    )
    assert rows[0].timestamp is not None and rows[1].timestamp is not None


# --- migration applies and reverses (Section 18; Section 20.3) ----------------


def _transition_table_exists() -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
            ["tasks_tasktransition"],  # Django's default: {app_label}_{model}
        )
        found = cursor.fetchone()
    return found is not None and int(found[0]) == 1


@pytest.mark.django_db(transaction=True)
def test_migration_applies_and_reverses_cleanly() -> None:
    """``migrate tasks zero`` drops the history table; re-apply recreates it."""
    assert TaskTransition.objects.exists() is False  # fresh test database
    call_command("migrate", "tasks", "zero", verbosity=0)
    assert not _transition_table_exists(), "reverse must drop the history table"

    call_command("migrate", "tasks", verbosity=0)
    assert _transition_table_exists(), "re-apply must recreate the history table"


# --- guards against accidental re-export confusion ---------------------------


def test_task_transition_is_exported_from_the_model_surface() -> None:
    """``apps.tasks.models`` re-exports the history surface for consumers."""
    from apps.tasks import models as model_surface

    assert model_surface.TaskTransition is TaskTransition
    assert model_surface.ActorType is ActorType
    assert model_surface.TransitionReason is TransitionReason
