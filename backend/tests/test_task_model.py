"""MT-1.4-01 — the Task model with Section 7.2 fields and check constraints.

Executable proof of the model slice (Sections 7.2, 7.4; FR-TSK-01/02;
G-01, ADR-010):

* the field set is **exactly** the Section 7.2 "Task" table — none added,
  dropped or renamed (``project`` is the Django name whose column/attname
  is literally ``project_id``, the plan's FK spelling);
* canonical defaults: ``state`` ``draft`` (Section 8.2 T1), ``version`` 1
  (FR-TSK-06), counters 0, ``merge_status`` ``none``, ``audit_required``
  True (mirrors the policy default);
* the database refuses malformed ids (``PID[0-9]{5}-T[0-9]{3,}`` with
  natural growth to ``T1000``+), out-of-set ``state``/``priority`` and
  the ``version``/counter floors (Section 7.4: boundaries **and** DB);
* enum columns without DB checks still reject out-of-set values through
  ``full_clean`` (the boundary half, WP-1.3 precedent);
* Section 7.4 rule 4 — a loaded task's ``project_id`` never changes.

Run with ``pytest backend/tests -k "task and (model or constraint)"``
(MT test command); ``python manage.py migrate`` and
``makemigrations --check --dry-run`` cover the migration half.
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.models import JSONField

from apps.projects.models import Project, ProjectPolicy
from apps.tasks.models import (
    ClaimedRole,
    MergeStatus,
    ReviewReason,
    Task,
    TaskPriority,
    TaskState,
)
from apps.tasks.services.ids import TASK_ID_PATTERN, is_valid_task_id

# Section 7.2 "Task" table, verbatim — the literal field-set assertion.
PLAN_7_2_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "project",  # Section 7.2 spells it project_id (column + attname)
        "title",
        "description",
        "acceptance_criteria",
        "target_scope",
        "test_command",
        "priority",
        "state",
        "version",
        "worker_agent_id",
        "worker_session_id",
        "claimed_role",
        "lease_acquired_at",
        "lease_expires_at",
        "last_checkpoint_at",
        "failure_retry_count",
        "attempt_number",
        "audit_required",
        "review_reason",
        "latest_feedback",
        "merge_status",
        "archived_at",
        "created_by",
        "created_at",
        "updated_at",
    }
)


@pytest.fixture
def project(db: None) -> Project:
    """One project row for the model tests (explicit id keeps ids stable)."""
    return Project.objects.create(
        id="PID00042",
        name="Task model tests",
        repo_path="/srv/repos/task-model-tests",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )


def _new_task(project: Project, **overrides: object) -> Task:
    """Insert one task straight through the ORM (no API, no serializer)."""
    payload: dict[str, object] = {
        "id": f"{project.pk}-T001",
        "project": project,
        "title": "Model under test",
    }
    payload.update(overrides)
    return Task.objects.create(**payload)


def _insert_rejected(project: Project, **overrides: object) -> None:
    """Assert the INSERT itself fails on a check constraint (Section 7.4)."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():  # contain the broken statement
            _new_task(project, **overrides)


# --- field set and defaults (FR-TSK-02; Section 7.2) -----------------------


def test_task_model_field_set_matches_section_7_2_exactly(project: Project) -> None:
    """None added, none dropped, none renamed (MT-1.4-01 acceptance).

    Section 7.2 describes the *table*, so the set is the **concrete
    columns**. The reverse relations MT-1.4-05 attaches for the Section
    7.1 N:N dependency join are relation metadata, not columns — they are
    asserted as such instead of polluting the table's field set.
    """
    names = {field.name for field in Task._meta.get_fields() if field.concrete}
    # WP-1.6 adds `lease_generation` (MT-1.6-05): Section 8.6's *internal*
    # fencing counter — "every claim increments an internal lease generation"
    # — the one column outside the Section 7.2 table, recorded in the WP
    # changelog. Everything else stays verbatim (none added, dropped, renamed).
    expected = PLAN_7_2_FIELDS | {"lease_generation"}
    assert names == expected, sorted(names ^ expected)
    reverse = {field.name for field in Task._meta.get_fields() if not field.concrete}
    # WP-1.5 adds `transitions` (TaskTransition's FK, MT-1.5-05) — the
    # relation joins the two that the Section 7.1 dependency join owns;
    # still relation metadata, never a column of the Section 7.2 table.
    # WP-1.8 adds `checkpoints` (TaskCheckpoint's FK, MT-1.8-01) under the
    # same reading: a reverse relation the checkpoint history attaches,
    # recorded in the WP changelog alongside `transitions`.
    assert reverse == {"checkpoints", "dependency_edges", "dependent_edges", "transitions"}, sorted(
        reverse
    )

    project_field = Task._meta.get_field("project")
    assert project_field.attname == "project_id", "the Section 7.2 FK column name"
    assert project_field.column == "project_id"
    assert Task._meta.pk.name == "id", "the Section 7.3 string id is the pk"


def test_task_model_defaults_match_the_canonical_initial_values(
    project: Project,
) -> None:
    """draft / version 1 / medium / zeroed counters — the T1 starting point."""
    task = _new_task(project)
    row = Task.objects.get(pk=task.pk)

    assert row.state == "draft"  # Section 8.2 T1: create -> draft (G-01)
    assert row.priority == "medium"  # documented default, flagged in changelog
    assert row.version == 1  # FR-TSK-06 starting version
    assert row.failure_retry_count == 0
    assert row.attempt_number == 0
    assert row.merge_status == "none"
    assert row.audit_required is True  # mirrors audit_required_default
    assert row.description == ""
    assert row.test_command == ""
    assert row.latest_feedback == ""
    # Section 7.2 nullable-on-the-model fields start unset.
    for field_name in (
        "worker_agent_id",
        "worker_session_id",
        "claimed_role",
        "lease_acquired_at",
        "lease_expires_at",
        "last_checkpoint_at",
        "review_reason",
        "archived_at",
        "created_by",
    ):
        assert getattr(row, field_name) is None, field_name
    assert row.created_at is not None and row.updated_at is not None


def test_task_model_json_defaults_are_empty_lists_and_never_shared(
    project: Project,
) -> None:
    """Mutable JSON defaults must not alias across rows (Django E010 rule)."""
    first = _new_task(project)
    second = _new_task(project, id=f"{project.pk}-T002")

    assert first.acceptance_criteria == [] and first.target_scope == []
    assert isinstance(Task._meta.get_field("acceptance_criteria"), JSONField)
    assert isinstance(Task._meta.get_field("target_scope"), JSONField)

    first.acceptance_criteria.append("works end to end")
    first.target_scope.append("src/**")
    fresh_second = Task.objects.get(pk=second.pk)
    assert fresh_second.acceptance_criteria == []
    assert fresh_second.target_scope == []


def test_task_model_enums_expose_the_canonical_values() -> None:
    """G-01 six states; FR-TSK-05 four priorities; Section 8.4 twelve reasons."""
    assert TaskState.values == [
        "draft",
        "pending",
        "in_progress",
        "to_be_audited",
        "in_human_review",
        "completed",
    ]
    assert TaskPriority.values == ["urgent", "high", "medium", "low"]
    assert ClaimedRole.values == ["coder", "auditor"]
    assert MergeStatus.values == [
        "none",
        "pending",
        "merging",
        "merged",
        "conflict",
        "failed",
    ]
    assert len(ReviewReason.values) == 12
    assert "policy_forced_review" in ReviewReason.values  # Section 8.4 tail


# --- id constraint (FR-TSK-01; Section 7.3/7.4) ----------------------------


def test_task_constraint_rejects_malformed_ids_at_the_database(
    project: Project,
) -> None:
    """``PID[0-9]{5}-T[0-9]{3,}`` enforced by the DB, malformed rejected."""
    assert TASK_ID_PATTERN == r"^PID[0-9]{5}-T[0-9]{3,}$"
    for malformed in (
        "PID1-T1",  # short PID, short index (MT test command example)
        "PID00001-T1",  # one-digit index
        "PID00001-T01",  # two-digit index (MT test command example)
        "PID00001-A001",  # wrong separator letter
        "pid00001-t001",  # case matters
        "PID00001-T001-extra",  # trailing junk — the pattern is anchored
        "T001",  # missing PID entirely
    ):
        assert not is_valid_task_id(malformed), malformed
        _insert_rejected(project, id=malformed)


def test_task_constraint_accepts_ids_with_natural_growth(project: Project) -> None:
    """Three digits render first and grow beyond them — T1000 (Section 7.3)."""
    for index in ("001", "999", "1000", "123456789"):
        task_id = f"{project.pk}-T{index}"
        assert is_valid_task_id(task_id), task_id
        task = _new_task(project, id=task_id, title=f"index {index}")
        assert Task.objects.filter(pk=task.pk).exists()


# --- floors and enum constraints (Section 7.2; FR-TSK-05) ------------------


def test_task_constraint_enforces_version_and_counter_floors(
    project: Project,
) -> None:
    """version >= 1, failure_retry_count >= 0, attempt_number >= 0."""
    _insert_rejected(project, id=f"{project.pk}-T101", version=0)
    _insert_rejected(project, id=f"{project.pk}-T102", failure_retry_count=-1)
    _insert_rejected(project, id=f"{project.pk}-T103", attempt_number=-1)


def test_task_constraint_rejects_out_of_set_state_and_priority(
    project: Project,
) -> None:
    """The six G-01 states and four FR-TSK-05 priorities, checked in the DB."""
    _insert_rejected(project, id=f"{project.pk}-T201", state="archived")
    _insert_rejected(project, id=f"{project.pk}-T202", state="PENDING")  # case
    _insert_rejected(project, id=f"{project.pk}-T203", priority="critical")
    # The canonical boundary values are accepted.
    assert _new_task(project, id=f"{project.pk}-T204", state="completed").state == "completed"
    assert _new_task(project, id=f"{project.pk}-T205", priority="urgent").priority == "urgent"


def test_task_model_boundary_validation_rejects_out_of_set_enums(
    project: Project,
) -> None:
    """The boundary half (Section 7.4): full_clean on every choice column."""
    for overrides in (
        {"state": "bogus"},
        {"priority": "critical"},
        {"claimed_role": "robot"},
        {"merge_status": "queued"},
        {"review_reason": "because"},
        {"id": "PID1-T1"},  # boundary id validation, not only the DB
        {"version": 0},
    ):
        task = Task(
            id=str(overrides.get("id", f"{project.pk}-T301")),
            project=project,
            title="boundary",
            **{k: v for k, v in overrides.items() if k != "id"},
        )
        with pytest.raises(DjangoValidationError):
            task.full_clean()


def test_task_model_constraints_and_indexes_are_declared() -> None:
    """The six Section 7.4 checks plus the NFR-09 list indexes exist."""
    assert {constraint.name for constraint in Task._meta.constraints} == {
        "task_id_format",
        "task_state_canonical",
        "task_priority_canonical",
        "task_version_at_least_one",
        "task_failure_retry_count_non_negative",
        "task_attempt_number_non_negative",
    }
    assert {index.name for index in Task._meta.indexes} == {
        "task_proj_prio_created",  # default list sort (priority -> created_at)
        "task_proj_state",  # state filter
    }


# --- Section 7.4 rule 4: project immutability ------------------------------


def test_task_model_project_never_changes_after_creation(project: Project) -> None:
    """Rule 4: a loaded row refuses a project reassignment on save()."""
    task = _new_task(project)
    other = Project.objects.create(
        id="PID00043",
        name="Another project",
        repo_path="/srv/repos/another",
        default_branch="main",
        agent_policy=ProjectPolicy.objects.create(),
    )

    loaded = Task.objects.get(pk=task.pk)
    loaded.project = other
    with pytest.raises(DjangoValidationError, match="project"):
        loaded.save()

    loaded.refresh_from_db()
    assert loaded.project_id == project.pk
    # A *new* row still chooses its project freely (create path unaffected).
    assert _new_task(project, id=f"{project.pk}-T401").project_id == project.pk


# --- migration hygiene (Section 18; Section 20.3 apply + reverse) ----------


def _task_table_exists() -> bool:
    """Whether the task table is present (vendor-neutral name lookup)."""
    table = Task._meta.db_table
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s",
                [table],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
                [table],
            )
        row = cursor.fetchone()
        assert row is not None
        return int(row[0]) == 1


@pytest.mark.django_db(transaction=True)
def test_task_migration_applies_and_reverses_cleanly() -> None:
    """``migrate`` to zero drops the task tables; re-apply recreates them."""
    assert Task.objects.exists() is False  # fresh test database
    call_command("migrate", "tasks", "zero", verbosity=0)
    assert not _task_table_exists(), "reverse must drop the model table"

    call_command("migrate", "tasks", verbosity=0)
    assert _task_table_exists(), "re-apply must recreate the model table"
