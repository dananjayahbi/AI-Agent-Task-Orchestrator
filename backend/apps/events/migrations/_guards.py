"""Shared insert-only guard for the append-only audit tables (MT-1.9-04).

One implementation, two tables: ``events_event`` and
``tasks_tasktransition`` — WP-1.9 owns the append-only concern
(Section 12.5), so both migrations import the statements from here
rather than duplicating security-critical SQL.

What the PostgreSQL statements do, layer by layer:

1. **Row trigger** — refuses ``UPDATE`` and ``DELETE`` with SQLSTATE
   ``42501``. This is the layer that holds in *every* topology,
   including dev/Compose where the application role also **owns** the
   tables: an owner's inherent privileges cannot be removed by
   ``REVOKE`` alone, so the trigger is the actual enforcement
   (recorded reading, WP changelog).
2. **REVOKE** — strips ``UPDATE``/``DELETE`` from ``PUBLIC`` and from
   the executing role's ACL entry, closing shared-grant topologies
   (Section 16.1's one-shot migrate runs this with sufficient rights).
3. **GRANT** — restates ``INSERT``/``SELECT`` for the executing role:
   writers and the replay/history readers keep working (Section 19.1
   WP-1.9 acceptance).

Idempotent by construction — ``CREATE OR REPLACE``, ``DROP ... IF
EXISTS``, ``REVOKE``, ``GRANT`` — so running the migrate service twice
never fails (MT-1.9-04 acceptance; statements verified against
PostgreSQL 16, the Section 16.1 image).

Vendor scope: statements run only when the schema editor's connection
is PostgreSQL (Section 18's integration topology). The SQLite unit
layer keeps the model-level guards (``EventImmutable`` /
``TransitionHistoryImmutable`` — every ORM writer passes through
them), and the privilege tests skip outside Postgres with the exact
command to run them (``tests/events/test_insert_only_permissions``).

Statements deliberately contain no ``%`` characters (some drivers treat
them as parameter placeholders even in literal SQL).
"""

from __future__ import annotations

from typing import Any

#: Shared plpgsql function name (drop it only with the trigger set).
GUARD_FUNCTION = "orchestrator_append_only_guard"

_GUARD_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION {GUARD_FUNCTION}() RETURNS trigger AS $guard$
BEGIN
    RAISE EXCEPTION 'append-only audit table (Section 12.5): UPDATE and DELETE are denied'
        USING ERRCODE = '42501', DETAIL = TG_OP;
END;
$guard$ LANGUAGE plpgsql;
"""


def guard_statements(table: str, trigger: str) -> tuple[str, ...]:
    """The idempotent apply sequence for *table* (PostgreSQL only)."""
    return (
        _GUARD_FUNCTION_SQL,
        f"DROP TRIGGER IF EXISTS {trigger} ON {table};",
        f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
        f"FOR EACH ROW EXECUTE FUNCTION {GUARD_FUNCTION}();",
        f"REVOKE UPDATE, DELETE ON {table} FROM PUBLIC;",
        f"REVOKE UPDATE, DELETE ON {table} FROM CURRENT_USER;",
        f"GRANT INSERT, SELECT ON {table} TO CURRENT_USER;",
    )


def reverse_statements(table: str, trigger: str) -> tuple[str, ...]:
    """Drop the DDL guard; privilege rows are left as found.

    The trigger and function are the reversible part. The revokes need
    no reversal: ``PUBLIC`` had no default grant to restore, and the
    role-level entries only ever *lose* UPDATE/DELETE — a downgrade path
    that re-opens an audit table must be an explicit, reviewed change,
    not an automatic ``migrate`` backwards.
    """
    return (
        f"DROP TRIGGER IF EXISTS {trigger} ON {table};",
        f"DROP FUNCTION IF EXISTS {GUARD_FUNCTION}();",
    )


def _apply(schema_editor: Any, table: str, trigger: str) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return  # SQLite unit layer: model-level guards only (docstring above)
    for statement in guard_statements(table, trigger):
        schema_editor.execute(statement)


def _revert(schema_editor: Any, table: str, trigger: str) -> None:
    if schema_editor.connection.vendor != "postgresql":
        return
    for statement in reverse_statements(table, trigger):
        schema_editor.execute(statement)


# --- RunPython entry points (one per table, imported by both migrations) ----


def add_event_guard(apps: Any, schema_editor: Any) -> None:
    """Apply the insert-only guard to ``events_event`` (Section 12.5)."""
    _apply(schema_editor, "events_event", "event_append_only")


def remove_event_guard(apps: Any, schema_editor: Any) -> None:
    """Remove the insert-only guard from ``events_event`` (reverse)."""
    _revert(schema_editor, "events_event", "event_append_only")


def add_transition_guard(apps: Any, schema_editor: Any) -> None:
    """Apply the insert-only guard to ``tasks_tasktransition`` (Section 7.4.5)."""
    _apply(schema_editor, "tasks_tasktransition", "transition_append_only")


def remove_transition_guard(apps: Any, schema_editor: Any) -> None:
    """Remove the insert-only guard from ``tasks_tasktransition`` (reverse)."""
    _revert(schema_editor, "tasks_tasktransition", "transition_append_only")
