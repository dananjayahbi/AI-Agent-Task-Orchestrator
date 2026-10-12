# MT-1.3-01 — atomic PID identifier generation (parent plan Sections 7.3, 7.4).
#
# The sequence is created in its OWN migration (Section 20.3: never combine a
# migration with unrelated logic; MT-1.3-01 out-of-scope note: the Project
# model that consumes it lands in a later migration which depends on this
# one — the dependency is automatic within the app and recorded in the WP
# changelog so migration order cannot be silently changed).

from __future__ import annotations

from typing import ClassVar

from django.apps.registry import Apps
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor


def create_pid_sequence(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Create the database sequence that supplies project numbers (7.3).

    PostgreSQL (dev/prod/integration): a real ``CREATE SEQUENCE`` starting
    at 1 — ``PID00000`` is never issued. The hermetic unit layer runs
    SQLite (apps/core/settings/test.py), which has no sequences; there the
    same migration creates a single-row fallback counter table whose
    ``UPDATE ... RETURNING`` is atomic for the same reason ``nextval`` is.
    The runtime picks the branch in ``apps.projects.services.pids`` — one
    migration, both backends, no vendor-specific migration state.
    """
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            "CREATE SEQUENCE IF NOT EXISTS project_pid_seq START WITH 1 MINVALUE 1"
        )
        return
    schema_editor.execute(
        "CREATE TABLE project_pid_sequence ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "value INTEGER NOT NULL, "
        "CHECK (id = 1))"
    )
    schema_editor.execute("INSERT INTO project_pid_sequence (id, value) VALUES (1, 0)")


def drop_pid_sequence(apps: Apps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Reverse of :func:`create_pid_sequence` (verified apply + reverse)."""
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP SEQUENCE IF EXISTS project_pid_seq")
        return
    schema_editor.execute("DROP TABLE project_pid_sequence")


class Migration(migrations.Migration):
    """Generator support only — no models, no constraints (Section 20.3)."""

    initial = True

    dependencies: ClassVar[list[tuple[str, str]]] = []

    operations = [
        migrations.RunPython(create_pid_sequence, drop_pid_sequence),
    ]
