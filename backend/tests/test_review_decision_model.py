"""MT-3.6-02 — Review Decision model: Section 7.2 fields, constraints, append-only.

The executable half of MT-3.6-02's acceptance criteria:

* the field set is **exactly** Section 7.2's Review Decision row (``id``,
  ``task_id``, ``resolution_id``, ``decision``, ``note``, ``decided_by``,
  ``decided_via``, ``decided_at``) — none added, dropped or renamed
  (Section 20.5 traceability);
* ``decision`` is restricted to ``approve`` / ``request_changes`` /
  ``reassign`` and ``decided_via`` to ``web`` / ``mobile`` at every
  layer — serializer choices, model choices, and the database
  ``CheckConstraint``s a direct ORM write cannot bypass;
* an ``approve`` row without a ``resolution`` is refused by the
  database itself (MT-3.6-02's risk note — a silently optional column
  would disable MT-3.6-04's stale-resolution protection);
* the row is append-only (Section 12.5: decisions are recorded, not
  edited) — the ``TaskResolution`` insert-only discipline;
* the migration applies and reverses cleanly (Sections 20.3, 16.5).

Run with ``pytest backend/tests -k review_decision_model -q``.
"""

from __future__ import annotations

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from apps.audit.models import (
    ReviewDecision,
    ReviewDecisionImmutable,
    ReviewDecisionValue,
    ReviewVia,
)
from apps.projects.models import Project
from apps.tasks.models import Task, TaskResolution, TaskState

from .wp15_helpers import make_project, make_task

SECTION_7_2_FIELDS = {
    "id",
    "task",
    "resolution",
    "decision",
    "note",
    "decided_by",
    "decided_via",
    "decided_at",
}


@pytest.fixture
def task(db: None) -> Task:
    """One draft task (the decision rows below attach to it)."""
    project: Project = make_project(name="Review decision model")
    return make_task(project, 1, state=TaskState.IN_HUMAN_REVIEW)


def _resolution(task: Task) -> TaskResolution:
    """One stored submission the decision can bind to."""
    resolution: TaskResolution = TaskResolution.objects.create(
        task=task,
        attempt_number=task.attempt_number,
        branch_name=f"feat/{task.pk}",
        commit_sha="0123456789abcdef0123456789abcdef01234567",  # pragma: allowlist secret
        execution_summary="model test submission",
        submitted_by_session="sess-review-model",
    )
    return resolution


def _decision(task: Task, **overrides: object) -> ReviewDecision:
    """One valid recorded decision (the row every test mutates)."""
    payload: dict[str, object] = {
        "task": task,
        "decision": ReviewDecisionValue.APPROVE,
        "resolution": _resolution(task),
        "note": "looks good",
        "decided_by": "1",
        "decided_via": ReviewVia.WEB,
    }
    payload.update(overrides)
    row: ReviewDecision = ReviewDecision.objects.create(**payload)
    return row


# --- Section 7.2 field set ---------------------------------------------------


def test_field_set_matches_section_7_2_exactly(task: Task) -> None:
    """No extra fields, none dropped or renamed (Section 20.5)."""
    assert {field.name for field in ReviewDecision._meta.get_fields()} == SECTION_7_2_FIELDS
    columns = {field.column for field in ReviewDecision._meta.fields}
    assert {"task_id", "resolution_id"} <= columns, "Section 7.2 FK spellings"


def test_value_sets_are_the_section_7_2_enums() -> None:
    """decision: three values; decided_via: two — verbatim (7.2)."""
    assert set(ReviewDecisionValue.values) == {"approve", "request_changes", "reassign"}
    assert set(ReviewVia.values) == {"web", "mobile"}


def test_decided_at_is_server_side(db: None, task: Task) -> None:
    """The server clock stamps decided_at; no client value exists (P7)."""
    before = timezone.now()
    row = _decision(task)
    assert before <= row.decided_at <= timezone.now()


def test_fk_integrity_rows_reference_existing_task_and_resolution(db: None, task: Task) -> None:
    """task_id / resolution_id reference live rows (Section 7.2)."""
    row = _decision(task)
    assert row.task_id == task.pk
    assert row.resolution is not None and row.resolution.task_id == task.pk


# --- out-of-contract values rejected at every layer --------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [("decision", "reject"), ("decision", "Approve"), ("decided_via", "ios")],
)
def test_out_of_contract_values_fail_model_validation(
    db: None, task: Task, field: str, value: str
) -> None:
    """full_clean refuses a value outside the Section 7.2 sets.

    Built unsaved — the database check below already refuses the row at
    INSERT, so the ORM-level gate is proven on the in-memory instance.
    """
    row = ReviewDecision(
        task=task,
        decision=ReviewDecisionValue.APPROVE,
        resolution=_resolution(task),
        decided_by="1",
        decided_via=ReviewVia.WEB,
    )
    setattr(row, field, value)
    with pytest.raises(ValidationError) as excinfo:
        row.full_clean()
    assert field in excinfo.value.error_dict


@pytest.mark.parametrize(
    ("field", "value"),
    [("decision", "reject"), ("decided_via", "ios")],
)
def test_out_of_contract_values_fail_the_database_check(
    db: None, task: Task, field: str, value: str
) -> None:
    """The CheckConstraint refuses a raw ORM write (no full_clean)."""
    with pytest.raises(IntegrityError), transaction.atomic():
        _decision(task, **{field: value})


def test_approve_without_resolution_is_refused_by_the_database(db: None, task: Task) -> None:
    """MT-3.6-02 risk note: approve always carries its resolution binding."""
    with pytest.raises(IntegrityError), transaction.atomic():
        ReviewDecision.objects.create(
            task=task,
            decision=ReviewDecisionValue.APPROVE,
            resolution=None,
            note="",
            decided_by="1",
            decided_via=ReviewVia.WEB,
        )


def test_note_action_without_resolution_is_recordable(db: None, task: Task) -> None:
    """A T9-anchored request_changes has no submission to bind (nullable FK)."""
    row = ReviewDecision.objects.create(
        task=task,
        decision=ReviewDecisionValue.REQUEST_CHANGES,
        resolution=None,
        note="retry with smaller scope",
        decided_by="1",
        decided_via=ReviewVia.MOBILE,
    )
    assert row.resolution_id is None


# --- append-only (Section 12.5) ----------------------------------------------


def test_recorded_decisions_are_append_only(db: None, task: Task) -> None:
    """Update, bulk_update and delete are refused — audit history (12.5)."""
    row = _decision(task)
    with pytest.raises(ReviewDecisionImmutable):
        row.note = "edited"
        row.save()
    with pytest.raises(ReviewDecisionImmutable):
        ReviewDecision.objects.filter(pk=row.pk).update(note="edited")
    with pytest.raises(ReviewDecisionImmutable):
        ReviewDecision.objects.bulk_update([row], ["note"])
    with pytest.raises(ReviewDecisionImmutable):
        row.delete()
    assert ReviewDecision.objects.filter(pk=row.pk).exists()


# --- migration applies and reverses (Sections 20.3, 16.5) ---------------------


@pytest.mark.django_db(transaction=True)
def test_migration_applies_and_reverses_cleanly() -> None:
    """The standalone WP-3.6 migration round-trips on this database."""
    previous = ("audit", "0002_auditreport_policy_engine_version_and_more")

    executor = MigrationExecutor(connection)
    executor.migrate([previous])

    executor = MigrationExecutor(connection)  # rebuild the graph after reversing
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
    assert ReviewDecision._meta.db_table not in tables, "0003 reversed away"

    leaf = executor.loader.graph.leaf_nodes("audit")
    executor.migrate(leaf)
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names(cursor)
    assert ReviewDecision._meta.db_table in tables, "0003 applied again"


def test_row_identity_is_a_server_uuid(db: None, task: Task) -> None:
    """Section 7.3 assigns ids only to Project/Task — the UUID pattern here."""
    row = _decision(task)
    assert isinstance(row.pk, uuid.UUID)
