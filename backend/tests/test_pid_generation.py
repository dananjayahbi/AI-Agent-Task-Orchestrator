"""MT-1.3-01 — atomic PID identifier generation (Sections 7.3, 7.4; FR-PRJ-01).

Executable proof of the id slice: format, capacity, sequence start,
uniqueness under concurrent allocation, the catalog-mapped exhaustion
error, boundary validation, and the sequence migration's clean
apply/reverse (the plan's database-sequence authority, Section 7.3).

Decisions these tests pin down (recorded in the WP changelog):

* the sequence starts at **1** — ``PID00000`` is never issued, the first
  id on a fresh database is ``PID00001``;
* exhaustion answers ``SERVER_ERROR`` — the catalog candidate chosen over
  ``VALIDATION_ERROR`` because capacity is server-side, not request-fault;
* the fallback counter (hermetic SQLite unit layer) mirrors ``nextval``
  with one atomic ``UPDATE ... RETURNING`` — the concurrency test proves
  the *uniqueness* guarantee on whichever backend runs it;
* gaps are expected (Section 7.3) and never asserted away.

Run with ``pytest backend/tests -k "pid or project_id"`` (MT test command).

State note: tests that consume sequence values run inside a rolled-back
``db`` transaction, so every test that asserts a *specific* value sets the
sequence explicitly first — the two ``transaction=True`` tests commit (by
design: DDL/threads need it) and therefore re-seed or leave values behind
without breaking later files. No test outside this file may hard-code an
allocated PID (the registry's own suites assert the pattern instead).
"""

from __future__ import annotations

import threading
import time

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.utils import OperationalError
from rest_framework.exceptions import ValidationError as ApiValidationError

from apps.core.errors import CANONICAL_ERROR_CODES, SERVER_ERROR
from apps.projects.exceptions import PidSequenceExhausted
from apps.projects.services.pids import (
    PID_MAX,
    PROJECT_ID_PATTERN,
    allocate_project_id,
    ensure_valid_pid,
    is_valid_pid,
    render_pid,
)

# --- sequence helpers (vendor branch mirrors services.pids) -----------------

_POSTGRES_SEQUENCE = "project_pid_seq"
_FALLBACK_TABLE = "project_pid_sequence"


def _set_sequence_value(value: int) -> None:
    """Set the *last issued* number so the next allocation returns value + 1.

    ``db``-fixture tests roll this back; ``transaction=True`` tests commit
    it (their own assertions set the value they rely on, so ordering never
    matters). On Postgres a sequence is not transactional — the unit layer
    is SQLite (test.py's documented split), and the helper stays vendor-
    correct for the integration layer.
    """
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(f"SELECT setval('{_POSTGRES_SEQUENCE}', %s, true)", [value])
        else:
            cursor.execute(f"UPDATE {_FALLBACK_TABLE} SET value = %s WHERE id = 1", [value])


def _peek_next_value() -> int:
    """The number the next allocation will return, without consuming it."""
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(f"SELECT last_value, is_called FROM {_POSTGRES_SEQUENCE}")
            row = cursor.fetchone()
            assert row is not None
            last_value, is_called = int(row[0]), bool(row[1])
            return last_value if not is_called else last_value + 1
        cursor.execute(f"SELECT value FROM {_FALLBACK_TABLE} WHERE id = 1")
        row = cursor.fetchone()
        assert row is not None
        return int(row[0]) + 1


def _sequence_exists() -> bool:
    """Whether the generator's database object is present."""
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(
                "SELECT COUNT(*) FROM pg_class WHERE relname = %s AND relkind = 'S'",
                [_POSTGRES_SEQUENCE],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
                [_FALLBACK_TABLE],
            )
        row = cursor.fetchone()
        assert row is not None
        return int(row[0]) == 1


# --- format and capacity (Section 7.3) --------------------------------------


def test_pid_render_matches_the_section_7_3_pattern() -> None:
    """``PID`` + exactly five zero-padded digits, capacity included."""
    assert render_pid(1) == "PID00001"
    assert render_pid(7) == "PID00007"  # the plan's own example id
    assert render_pid(1234) == "PID01234"
    assert render_pid(99999) == "PID99999"
    for number in (1, 7, 42, 99999):
        assert is_valid_pid(render_pid(number))
        assert len(render_pid(number)) == 8


def test_pid_render_refuses_numbers_outside_capacity() -> None:
    """Zero (never issued) and > 99,999 are programming errors, not output."""
    for bad in (-1, 0, 100_000, 1_000_000):
        with pytest.raises(ValueError, match="outside capacity"):
            render_pid(bad)


def test_sequence_starts_at_one_so_pid00000_is_never_issued(db: None) -> None:
    """From the migration's seed (0), the first id is PID00001 — never 00000."""
    _set_sequence_value(0)
    first = allocate_project_id()
    assert first == "PID00001"
    assert allocate_project_id() == "PID00002"


def test_allocations_are_unique_and_match_the_pattern(db: None) -> None:
    """Consecutive allocation: unique, ordered, all canonical (FR-PRJ-01)."""
    _set_sequence_value(100)
    pids = [allocate_project_id() for _ in range(10)]
    assert len(set(pids)) == 10
    assert pids[0] == "PID00101"
    for pid in pids:
        assert is_valid_pid(pid)
        assert len(pid) == 8
    assert pids == sorted(pids)  # generation order, zero-padded lexicographic order


# --- uniqueness under concurrency (Section 7.3 database-sequence authority) -


@pytest.mark.django_db(transaction=True)
def test_concurrent_allocation_never_reuses_a_number() -> None:
    """Parallel workers pull distinct numbers from one atomic statement.

    Threads on the shared in-memory SQLite database meet real table locks;
    the retry loop absorbs ``database is locked`` (a *failed* statement
    consumes nothing), then asserts the only property the plan promises:
    no number is ever issued twice. On Postgres the same call is ``nextval``
    and needs no retry — the integration layer exercises that path.
    """
    _set_sequence_value(0)
    threads_count, per_thread = 6, 5
    barrier = threading.Barrier(threads_count, timeout=15)
    collected: list[str] = []
    failures: list[str] = []
    lock = threading.Lock()

    def allocate_with_retry() -> str:
        for _ in range(1000):
            try:
                return allocate_project_id()
            except OperationalError:
                time.sleep(0.005)
        raise AssertionError("allocation never got past the database lock")

    def worker() -> None:
        try:
            barrier.wait()
            mine = [allocate_with_retry() for _ in range(per_thread)]
            with lock:
                collected.extend(mine)
        except Exception as exc:  # surfaced to the main thread below
            with lock:
                failures.append(repr(exc))
        finally:
            connection.close()

    workers = [threading.Thread(target=worker) for _ in range(threads_count)]
    for thread in workers:
        thread.start()
    for thread in workers:
        thread.join(timeout=60)
        assert not thread.is_alive(), "worker thread hung"

    assert not failures, failures
    assert len(collected) == threads_count * per_thread
    assert len(set(collected)) == len(collected), "a number was reused"
    for pid in collected:
        assert is_valid_pid(pid), pid


# --- exhaustion (Section 7.3 "exhaustion raises a clear error") -------------


def test_exhaustion_beyond_capacity_raises_the_catalog_mapped_error(db: None) -> None:
    """Last usable id renders; the next raises SERVER_ERROR — catalog only."""
    _set_sequence_value(PID_MAX - 1)
    assert allocate_project_id() == "PID99999"

    with pytest.raises(PidSequenceExhausted) as excinfo:
        allocate_project_id()
    error = excinfo.value
    assert error.status_code == 500
    assert error.default_code == SERVER_ERROR
    assert error.default_code in CANONICAL_ERROR_CODES, "Section 20.4 item 5"
    assert "99,999" in str(error.default_detail)  # the message is clear


# --- boundary validation (Section 7.3 "every API boundary") -----------------


def test_boundary_validator_accepts_canonical_pids_and_rejects_the_rest() -> None:
    """``ensure_valid_pid`` is the view-facing wrapper over the shared regex.

    Valid ids pass through; invalid ones raise the DRF ValidationError the
    envelope handler maps to ``VALIDATION_ERROR`` (never a 500).
    """
    assert ensure_valid_pid("PID00001") == "PID00001"
    for bad in ("PID0001", "PID000001", "pid00001", "PID0000A", "00001", "", "PID999990"):
        with pytest.raises(ApiValidationError) as excinfo:
            ensure_valid_pid(bad)
        assert excinfo.value.status_code == 400
        # The envelope handler maps this exact class to VALIDATION_ERROR
        # (apps/core/exceptions.py); the wire-level assertion lives in
        # tests/test_project_api.py where the boundary is exercised over HTTP.
        assert "pid" in excinfo.value.detail


# --- migration hygiene (Section 18; Section 20.3 apply + reverse) -----------


@pytest.mark.django_db(transaction=True)
def test_pid_sequence_migration_applies_and_reverses_cleanly() -> None:
    """``migrate`` to zero drops the sequence; re-apply recreates it seeded."""
    assert _sequence_exists(), "0001_pid_sequence must have applied at setup"

    call_command("migrate", "projects", "zero", verbosity=0)
    assert not _sequence_exists(), "reverse must drop the generator object"

    # Plain `migrate`, not `migrate projects`: unmigrating projects also
    # unapplies its dependents (the `tasks` app's migrations), and re-applying
    # only `projects` would leave `tasks` unapplied — dropping its tables for
    # every later test in the session. Restore the whole schema here.
    call_command("migrate", verbosity=0)
    assert _sequence_exists(), "re-apply must recreate the generator object"
    assert _peek_next_value() == 1, "a fresh sequence issues 1 (never 0)"


# --- guard: the reusable validator is one object, not two copies ------------


def test_pid_pattern_is_single_sourced_with_the_accounts_reexport() -> None:
    """WP-1.2's public names re-export the projects-owned definitions (9.1)."""
    from apps.accounts.models import PROJECT_ID_PATTERN as accounts_pattern
    from apps.accounts.models import validate_project_id as accounts_validator
    from apps.projects.services.pids import validate_project_id as projects_validator

    assert accounts_pattern == PROJECT_ID_PATTERN
    assert accounts_validator is projects_validator
