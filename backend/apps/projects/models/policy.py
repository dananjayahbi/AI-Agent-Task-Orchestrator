"""The Project Policy entity (parent plan Section 7.2; MT-1.3-02; FR-PRJ-05).

Exactly the Section 7.2 "Project Policy (new)" table — one row per project
(Section 7.1 shows Project 1:1 Project Policy), **no field added, dropped
or renamed**, each default literal from the plan:

* the defaults feed the Policy Engine, leases and merge behavior later — a
  wrong value here silently changes automation semantics (MT-1.3-02 risk
  note), so ``tests/test_project_models.py`` asserts them value-for-value;
* the three glob lists are described in prose in Section 7.2 ("CI/CD, root
  migrations, security config", "framework-specific", "env files, key
  material, security rules"), not enumerated — the conservative concrete
  globs below are a documented, owner-confirmable translation (Section
  20.1 item 5: no hidden decisions; recorded in the WP changelog);
* no ``created_at``/``updated_at`` here: Section 7.2's policy table lists
  neither, and the "never added" rule outranks convenience — policy-edit
  timestamps arrive with WP-1.9's event/audit trail;
* validation of enums/bounds on write is MT-1.3-04's endpoint work (the
  only supported way to change policy, Section 12.5); the choices below
  are the closed vocabularies the plan fixes.
"""

from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class LeaseExtensionMode(models.TextChoices):
    """Section 7.2 ``lease_extension_mode`` — two values, none added (OQ-04)."""

    CHECKPOINT_ONLY = "checkpoint_only", "checkpoint only"
    CHECKPOINT_AND_LIVENESS = "checkpoint_and_liveness", "checkpoint and liveness"


class MergeStrategy(models.TextChoices):
    """Section 7.2 ``merge_strategy`` — three values, none added."""

    SQUASH = "squash", "squash"
    MERGE_COMMIT = "merge_commit", "merge commit"
    FAST_FORWARD_ONLY = "fast_forward_only", "fast forward only"


# --- Section 7.2 prose glob defaults, translated concretely -----------------
# The plan describes the three lists ("CI/CD, root migrations, security
# config" / "framework-specific" / "env files, key material, security
# rules") without enumerating globs; these conservative translations are
# documented and flagged for owner confirmation in the WP changelog
# (Section 20.1 item 5 — no hidden decisions). Named factory functions
# (not list literals) keep Django's JSONField shared-default check quiet
# and serialize by dotted path into the migration.
CRITICAL_PATH_GLOBS_DEFAULT: list[str] = [
    ".github/workflows/*",  # GitHub Actions CI/CD
    ".gitlab-ci.yml",  # GitLab CI
    "Jenkinsfile",  # Jenkins CI
    "migrations/*",  # root migrations directory
    "**/security*.py",  # security configuration
    "**/security*.yml",
    "**/security*.yaml",
]

MIGRATION_PATH_GLOBS_DEFAULT: list[str] = [
    "**/migrations/*.py",  # Django migrations
    "alembic/versions/*",  # SQLAlchemy/Alembic
    "db/migrate/*",  # Rails migrations
    "db/schema.rb",  # Rails schema
]

SENSITIVE_CONFIG_GLOBS_DEFAULT: list[str] = [
    ".env*",  # env files
    "**/*.env",
    "**/*.pem",  # key material
    "**/*.key",
    "**/*credentials*",
    "**/*secrets*",
    "**/security_rules*",  # security rules
]


def default_critical_path_globs() -> list[str]:
    """Fresh copy of the critical-path default (never share one list)."""
    return list(CRITICAL_PATH_GLOBS_DEFAULT)


def default_migration_path_globs() -> list[str]:
    """Fresh copy of the migration-path default (never share one list)."""
    return list(MIGRATION_PATH_GLOBS_DEFAULT)


def default_sensitive_config_globs() -> list[str]:
    """Fresh copy of the sensitive-config default (never share one list)."""
    return list(SENSITIVE_CONFIG_GLOBS_DEFAULT)


class ProjectPolicy(models.Model):
    """One project's automation policy — the Section 7.2 defaults verbatim."""

    # --- lease shape (Section 7.2; consumed by WP-1.6/1.7) ----------------
    lease_duration_minutes = models.PositiveIntegerField(
        default=45, help_text="Lease length and per-checkpoint extension (7.2)."
    )
    lease_max_total_minutes = models.PositiveIntegerField(
        default=240, help_text="Hard cap on one continuous claim (7.2)."
    )
    lease_extension_mode = models.CharField(
        max_length=24,
        choices=LeaseExtensionMode.choices,
        default=LeaseExtensionMode.CHECKPOINT_ONLY,
    )
    # --- failure handling and concurrency (G-26) ---------------------------
    max_retries = models.PositiveIntegerField(
        default=3, help_text="Lease failures before escalation (7.2)."
    )
    max_concurrent_tasks = models.PositiveIntegerField(
        default=1,
        help_text="Simultaneous in_progress tasks in this project (G-26 default 1).",
    )
    # --- Policy Engine inputs (Section 9.4) -------------------------------
    autonomous_diff_threshold_lines = models.PositiveIntegerField(
        default=250, help_text="Max changed lines for auto-complete (7.2)."
    )
    auditor_min_confidence = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Minimum auditor confidence, 1-5 (7.2).",
    )
    # Section 7.2 describes these three glob lists in prose only; the
    # concrete conservative globs above are the documented translation
    # flagged for owner confirmation in the WP changelog (Section 20.1
    # item 5). Semantics (matching against real files) are the Policy
    # Engine's concern, WP-3.x — see MT-1.3-04's scope.
    critical_path_globs = models.JSONField(
        default=default_critical_path_globs,
        help_text=(
            "Touched paths that trigger escalation (7.2: CI/CD, root migrations, security config)."
        ),
    )
    migration_path_globs = models.JSONField(
        default=default_migration_path_globs,
        help_text="Framework-specific migration paths that trigger escalation (7.2).",
    )
    sensitive_config_globs = models.JSONField(
        default=default_sensitive_config_globs,
        help_text="Env/key/security-rule paths that trigger escalation (7.2).",
    )
    # --- completion and merge behavior (G-09) -----------------------------
    auto_complete_enabled = models.BooleanField(
        default=True, help_text="If false, every task goes to human review (7.2)."
    )
    merge_strategy = models.CharField(
        max_length=24,
        choices=MergeStrategy.choices,
        default=MergeStrategy.SQUASH,
    )
    branch_prefix = models.CharField(
        max_length=64,
        default="feat/{PID}-",
        help_text="Branch-name prefix template; {PID} resolves per project (G-09 default).",
    )
    audit_required_default = models.BooleanField(
        default=True, help_text="Default audit_required for new tasks (7.2)."
    )
    stalled_after_minutes = models.PositiveIntegerField(
        default=20, help_text="UI warning when no checkpoint arrives (7.2)."
    )

    def __str__(self) -> str:
        """Identify the row by its primary key (no project FK on this side)."""
        return f"policy:{self.pk}"
