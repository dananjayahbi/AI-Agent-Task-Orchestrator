"""MT-1.3-02 — Project and ProjectPolicy models (Sections 7.1, 7.2, 7.4).

Value-for-value proof against the plan's entity tables (FR-PRJ-02, FR-PRJ-04,
FR-PRJ-05): field sets match Section 7.2 exactly (none added, dropped or
renamed — Section 20.5 traceability), every policy default is the documented
literal (G-26 ``max_concurrent_tasks`` 1, G-09 ``branch_prefix``
``feat/{PID}-``), the status enum is the closed FR-PRJ-04 triple, the id is
check-constrained *and* immutable, ``task_counter`` starts at 0 for
MT-1.4-02, and the Section 7.1 pair is one-to-one and deletion-protected.

Run with
``pytest backend/tests -k "project and (model or policy or default)"``
(MT test command). The sequence migration's apply/reverse lives in
``test_pid_generation.py`` (it covers the whole app's migrations).

Projects here are created with explicit ids and never touch the sequence,
so this file runs deterministically regardless of test order (the API
suites assert the PID *pattern* instead of a hard-coded value).
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import ProtectedError

from apps.projects.models import ActiveStatus, Project, ProjectPolicy

# The Section 7.2 "Project" table, verbatim — the AC "none added, dropped
# or renamed" (FR-PRJ-02 traceability) is this exact set.
PROJECT_FIELDS = {
    "id",
    "name",
    "repo_path",
    "active_status",
    "default_branch",
    "system_prompt_rules",
    "agent_policy",
    "task_counter",
    "created_at",
    "updated_at",
}

# The Section 7.2 "Project Policy" table, verbatim (FR-PRJ-05) — the model
# carries exactly these columns plus its implicit primary key: no
# ``created_at``/``updated_at`` either (the table lists none).
POLICY_FIELDS = {
    "lease_duration_minutes",
    "lease_max_total_minutes",
    "lease_extension_mode",
    "max_retries",
    "max_concurrent_tasks",
    "autonomous_diff_threshold_lines",
    "auditor_min_confidence",
    "critical_path_globs",
    "migration_path_globs",
    "sensitive_config_globs",
    "auto_complete_enabled",
    "merge_strategy",
    "branch_prefix",
    "audit_required_default",
    "stalled_after_minutes",
}

# Section 7.2 defaults, literal — including the documented translations of
# the three prose glob lists (MT-1.3-02 risk note; flagged for owner
# confirmation in the WP changelog). Asserting the literals (rather than
# importing the model's constants) is what makes this a drift detector.
POLICY_DEFAULTS: dict[str, object] = {
    "lease_duration_minutes": 45,
    "lease_max_total_minutes": 240,
    "lease_extension_mode": "checkpoint_only",
    "max_retries": 3,
    "max_concurrent_tasks": 1,  # G-26
    "autonomous_diff_threshold_lines": 250,
    "auditor_min_confidence": 4,
    "critical_path_globs": [
        ".github/workflows/*",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        "migrations/*",
        "**/security*.py",
        "**/security*.yml",
        "**/security*.yaml",
    ],
    "migration_path_globs": [
        "**/migrations/*.py",
        "alembic/versions/*",
        "db/migrate/*",
        "db/schema.rb",
    ],
    "sensitive_config_globs": [
        ".env*",
        "**/*.env",
        "**/*.pem",
        "**/*.key",
        "**/*credentials*",
        "**/*secrets*",
        "**/security_rules*",
    ],
    "auto_complete_enabled": True,
    "merge_strategy": "squash",
    "branch_prefix": "feat/{PID}-",  # G-09
    "audit_required_default": True,
    "stalled_after_minutes": 20,
}


def _make_policy() -> ProjectPolicy:
    """A policy row with only its Section 7.2 defaults."""
    return ProjectPolicy.objects.create()


def _make_project(pid: str = "PID00042", policy: ProjectPolicy | None = None) -> Project:
    """A project row with explicit id (never the sequence) + its pair."""
    return Project.objects.create(
        id=pid,
        name="Registry Fixture",
        repo_path="/srv/repos/registry-fixture",
        default_branch="main",
        agent_policy=policy if policy is not None else _make_policy(),
    )


# --- Section 7.2 field-set traceability -------------------------------------


def test_project_model_fields_match_section_7_2_exactly() -> None:
    """FR-PRJ-02: no field added, dropped or renamed (Section 20.5)."""
    names = {field.name for field in Project._meta.fields}
    assert names == PROJECT_FIELDS


def test_project_policy_model_fields_match_section_7_2_exactly() -> None:
    """FR-PRJ-05: every table row exists, nothing else does."""
    names = {field.name for field in ProjectPolicy._meta.fields} - {"id"}
    assert names == POLICY_FIELDS


# --- Section 7.2 defaults, value for value ----------------------------------


def test_project_policy_defaults_match_section_7_2_value_for_value(db: None) -> None:
    """Every documented default, asserted literally (drift detector)."""
    policy = ProjectPolicy()  # unsaved: field defaults as Django applies them
    for name, expected in POLICY_DEFAULTS.items():
        assert getattr(policy, name) == expected, name

    persisted = _make_policy()
    reloaded = ProjectPolicy.objects.get(pk=persisted.pk)
    for name, expected in POLICY_DEFAULTS.items():
        assert getattr(reloaded, name) == expected, f"{name} (after save)"


def test_project_policy_glob_defaults_are_not_shared_between_rows(db: None) -> None:
    """Factory defaults: mutating one row's list never bleeds into another."""
    first = _make_policy()
    second = _make_policy()
    assert first.critical_path_globs is not second.critical_path_globs

    first.critical_path_globs.append("injected/*")
    first.save()  # persist the mutation, then prove it never bled over
    assert "injected/*" not in second.critical_path_globs
    second.refresh_from_db()
    first.refresh_from_db()
    assert "injected/*" not in second.critical_path_globs
    assert "injected/*" in first.critical_path_globs


# --- FR-PRJ-04 status enum + FR-PRJ-01 id rules ------------------------------


def test_active_status_accepts_only_the_three_canonical_values(db: None) -> None:
    """``active``/``paused``/``archived`` — closed enum, default active."""
    assert ActiveStatus.values == ["active", "paused", "archived"]
    project = _make_project()
    assert project.active_status == ActiveStatus.ACTIVE

    invalid = Project(
        id="PID00043",
        name="Bad status",
        repo_path="/srv/repos/bad",
        default_branch="main",
        active_status="stopped",
        agent_policy=_make_policy(),
    )
    with pytest.raises(ValidationError) as excinfo:
        invalid.full_clean()
    assert "active_status" in excinfo.value.error_dict


def test_project_id_check_constraint_rejects_malformed_ids(db: None) -> None:
    """Section 7.4: the database rejects any id outside ``PID[0-9]{5}``."""
    for malformed in ("PID12", "pid00042", "PROJECT1", "PID0004200"):
        # DatabaseError, not IntegrityError: on Postgres an over-long id is
        # a DataError — the unit layer (SQLite) enforces the regex check;
        # either way the row must not exist.
        with pytest.raises(DatabaseError), transaction.atomic():
            Project.objects.create(
                id=malformed,
                name="Malformed",
                repo_path="/srv/repos/malformed",
                default_branch="main",
                agent_policy=_make_policy(),
            )
    constraint_names = {constraint.name for constraint in Project._meta.constraints}
    assert "project_id_format" in constraint_names


def test_project_id_is_immutable_after_creation(db: None) -> None:
    """Section 7.3/7.4: loading a row pins its id; ``save`` refuses changes."""
    project = _make_project(pid="PID00042")
    project.refresh_from_db()  # loaded row: guard source is the loaded pk

    project.id = "PID00077"
    with pytest.raises(ValidationError, match="immutable"):
        project.save()
    assert Project.objects.filter(pk="PID00042").exists()
    assert not Project.objects.filter(pk="PID00077").exists()

    # Ordinary updates still work once the id is untouched.
    project.id = "PID00042"
    project.name = "Renamed Fixture"
    project.save()
    project.refresh_from_db()
    assert project.name == "Renamed Fixture"
    assert project.id == "PID00042"


# --- Section 7.1 pair + Section 7.2 counters/timestamps ---------------------


def test_project_and_policy_form_a_one_to_one_protected_pair(db: None) -> None:
    """Section 7.1: one policy per project; neither side silently deleted."""
    policy = _make_policy()
    _make_project(pid="PID00042", policy=policy)
    assert policy.project.pk == "PID00042"  # reverse accessor of agent_policy

    with pytest.raises(DatabaseError), transaction.atomic():
        Project.objects.create(
            id="PID00043",
            name="Second claimant",
            repo_path="/srv/repos/second",
            default_branch="main",
            agent_policy=policy,  # OneToOne: already taken
        )

    with pytest.raises(ProtectedError):  # PROTECT, never CASCADE
        policy.delete()


def test_project_task_counter_starts_at_zero_for_mt_1_4_02(db: None) -> None:
    """Section 7.2: the counter exists, default 0, ready for task ids."""
    project = _make_project()
    assert project.task_counter == 0
    assert Project._meta.get_field("task_counter").default == 0


def test_project_model_timestamps_are_server_generated(db: None) -> None:
    """Section 0.4 (P7): UTC server clock on created_at/updated_at."""
    project = _make_project()
    assert project.created_at is not None
    assert project.updated_at is not None
    assert project.created_at <= project.updated_at

    original_updated = project.updated_at
    project.name = "Touched"
    project.save()
    assert project.updated_at >= original_updated
