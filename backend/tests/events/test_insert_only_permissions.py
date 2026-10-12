"""MT-1.9-04 — insert-only database permissions on both audit tables.

Section 12.5 ("the application database role cannot update or delete
audit rows") and Section 19.1's WP-1.9 acceptance, proven against a
**real PostgreSQL** — never a mock (Section 18's integration topology;
the SQLite unit layer keeps the model-level guards and this module
skips with the exact command):

    uv run --directory backend pytest tests/events --ds apps.core.settings.dev

Covered per table (``events_event`` and ``tasks_tasktransition``):

* INSERT succeeds (writers keep working) and SELECT succeeds (the
  replay/history readers keep working);
* UPDATE and DELETE attempted with raw SQL — bypassing the ORM guards
  on purpose — are denied by the database;
* the guard migration's statements run twice without failing (the
  one-shot migrate service must be idempotent);
* the trigger row is present in ``pg_trigger``, so a silently skipped
  guard cannot pass this suite.

The trigger is what holds the "cannot update or delete" promise even
when the application role owns the tables (an owner's inherent
privileges are not removable by REVOKE alone) — recorded in
``apps.events.migrations._guards`` and the WP changelog.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from apps.events.migrations._guards import guard_statements
from apps.events.models import Event
from tests.wp15_helpers import make_project, make_task

_RUN_COMMAND = "uv run --directory backend pytest tests/events --ds apps.core.settings.dev"


def _skip_reason() -> str | None:
    """``None`` when this is the reachable-Postgres integration layer."""
    if "postgresql" not in str(settings.DATABASES["default"]["ENGINE"]):
        return (
            "Section 18 integration layer only: run the privilege tests with "
            f"`{_RUN_COMMAND}` (unit layer stays on SQLite)"
        )
    if not _postgres_reachable():
        return (
            "Postgres not reachable with the configured "
            f"ORCHESTRATOR_DATABASE_URL — start the stack or CI services "
            f"(command: `{_RUN_COMMAND}`)"
        )
    return None


def _postgres_reachable() -> bool:
    """Raw driver probe (the ORM is blocked before the ``db`` fixture)."""
    database: dict[str, Any] = settings.DATABASES["default"]
    try:
        with psycopg.connect(
            host=database.get("HOST") or None,
            port=database.get("PORT") or None,
            dbname=database.get("NAME"),
            user=database.get("USER") or None,
            password=str(database.get("PASSWORD") or None),
            connect_timeout=3,
        ) as connection_:
            with connection_.cursor() as cursor:
                cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any driver failure means "not reachable"
        return False


pytestmark = [
    pytest.mark.skipif(
        _skip_reason() is not None,
        reason=_skip_reason() or "unreachable",
    )
]


def _execute(sql: str, params: Any = None) -> None:
    """Run one raw statement through the application role's connection."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)


def _fetchone(sql: str, params: Any = None) -> Any:
    """Run a raw SELECT and return its first row (or ``None``)."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchone()


def _fetchall(sql: str, params: Any = None) -> Any:
    """Run a raw SELECT and return every row."""
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        return cursor.fetchall()


def _assert_denied(sql: str, params: Any = None) -> None:
    """The statement must fail at the database — in its own savepoint."""
    with pytest.raises(DatabaseError), transaction.atomic():
        _execute(sql, params)


def test_guard_triggers_are_installed_on_both_audit_tables(db: None) -> None:
    """A skipped/absent guard must not read as success (pg_trigger row)."""
    rows = _fetchall(
        "SELECT tgname FROM pg_trigger WHERE tgname IN (%(event)s, %(transition)s)",
        {"event": "event_append_only", "transition": "transition_append_only"},
    )
    found = {row[0] for row in rows}
    assert found == {"event_append_only", "transition_append_only"}, found


def test_event_table_insert_and_select_work_but_update_and_delete_do_not(
    db: None,
) -> None:
    """Writers and readers keep their privileges; mutation is denied."""
    event = Event.objects.create(
        type="task.transitioned",
        project_id="PID00001",
        task_id="PID00001-T001",
        occurred_at=timezone.now(),
        actor_type="system",
        actor_ref="lease-sweeper",
        data={},
        correlation_id="corr-pg-1",
    )

    _execute("SELECT id FROM events_event WHERE id = %s", [event.pk])  # SELECT ok

    _assert_denied(
        "UPDATE events_event SET actor_ref = %s WHERE id = %s",
        ["tampered", event.pk],
    )
    _assert_denied("DELETE FROM events_event WHERE id = %s", [event.pk])

    row = _fetchone("SELECT actor_ref FROM events_event WHERE id = %s", [event.pk])
    assert row is not None and row[0] == "lease-sweeper", "the row never moved"
    assert Event.objects.filter(pk=event.pk).exists(), "nor disappeared"


def test_transition_table_insert_and_select_work_but_update_and_delete_do_not(
    db: None,
) -> None:
    """WP-1.5's history table gets the same database-level protection."""
    from apps.tasks.models import TaskTransition
    from apps.tasks.state_machine.dispatcher import dispatch_transition

    project = make_project(name="Insert-only PG")
    task = make_task(project, 1)
    dispatch_transition(
        task_id=task.pk,
        trigger="publish",
        actor_type="owner",
        actor_ref="user:1",
    )
    transition = TaskTransition.objects.get(task=task)

    _execute("SELECT id FROM tasks_tasktransition WHERE id = %s", [transition.pk])

    _assert_denied(
        "UPDATE tasks_tasktransition SET actor_ref = %s WHERE id = %s",
        ["tampered", transition.pk],
    )
    _assert_denied("DELETE FROM tasks_tasktransition WHERE id = %s", [transition.pk])

    stored = TaskTransition.objects.get(pk=transition.pk)
    assert stored.actor_ref == "user:1"
    assert Event.objects.filter(task_id=task.pk).count() == 1, (
        "the dispatch's INSERT path still works end to end on Postgres"
    )


def test_guard_setup_is_idempotent_when_run_twice(db: None) -> None:
    """Re-running the migrate service's statements must not fail (19.1)."""
    statements = guard_statements("events_event", "event_append_only") + guard_statements(
        "tasks_tasktransition", "transition_append_only"
    )

    for _ in range(2):
        for statement in statements:
            _execute(statement)

    # ...and the re-applied guard still denies while INSERT keeps working.
    event = Event.objects.create(
        type="project.created",
        project_id="PID00002",
        task_id=None,
        occurred_at=timezone.now(),
        actor_type="owner",
        actor_ref="user:1",
        data={},
        correlation_id="corr-pg-2",
    )
    _assert_denied("DELETE FROM events_event WHERE id = %s", [event.pk])
    assert Event.objects.filter(pk=event.pk).exists()
