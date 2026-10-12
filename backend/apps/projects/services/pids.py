"""Atomic PID identifier generation — ``PID[0-9]{5}`` (Section 7.3; FR-PRJ-01).

Section 7.3 fixes the rule: the project id is **assigned from a database
sequence** and rendered as ``PID`` plus five zero-padded digits, capacity
99,999 projects, exhaustion raising a clear error; ids are validated against
their regular expression at every API boundary and by a database check
constraint (Section 7.4 — the constraint itself lives on the Project row,
MT-1.3-02's migration).

Decisions recorded here (MT-1.3-01 risk notes, WP changelog):

* **Sequence name** ``project_pid_seq`` — a real PostgreSQL ``CREATE
  SEQUENCE`` created by this app's ``0001_pid_sequence`` migration and
  consumed by ``nextval`` in a single atomic statement, so concurrent
  allocations never reuse a number (the plan's database-sequence authority).
* **Start value 1**: ``PID00000`` is never issued; the first project created
  on a fresh database is ``PID00001``. Sequence gaps are expected and never
  "repaired" (Section 7.3 gap tolerance).
* **Hermetic unit layer**: the test settings run SQLite in-memory
  (``apps/core/settings/test.py``), which has no sequences — the same
  migration creates a single-row fallback counter table there, and
  ``next_project_number`` picks the vendor branch. Both paths reduce to one
  atomic database statement (``nextval`` / ``UPDATE ... RETURNING``), so the
  uniqueness guarantee does not depend on the backend; Postgres-specific
  behaviour stays in the integration layer by Section 18's split.
* **Exhaustion mapping**: values outside ``1..99999`` raise
  ``PidSequenceExhausted`` (``SERVER_ERROR``, chosen between the catalog's
  two candidates per MT-1.3-01 — recorded in the changelog).
* **Canonical home**: this module owns the pattern/validator (Section 9.1 —
  the ``projects`` module owns ids); ``apps.accounts.models.tokens``
  re-exports them, so WP-1.2's public names keep working unchanged.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import connection
from rest_framework.exceptions import ValidationError

from ..exceptions import PidSequenceExhausted

# Section 7.3 / Glossary: PID plus exactly five digits.
PROJECT_ID_PATTERN = r"^PID[0-9]{5}$"

# Section 7.3 capacity: five zero-padded digits, sequence starts at 1.
PID_MIN = 1
PID_MAX = 99_999

# Callable validator for serializer/model full_clean paths (API boundaries).
# Registered in migrations by value, so moving the definition here changed no
# serialized migration state (WP changelog records the move).
validate_project_id = RegexValidator(
    PROJECT_ID_PATTERN,
    message="Project id must be PID plus five digits (Section 7.3).",
)

_PID_RE = re.compile(PROJECT_ID_PATTERN)

# Must match the name created by migrations/0001_pid_sequence.py (kept as a
# literal on both sides — migrations freeze their SQL, they never import
# live code; the migration check in CI guards the pair from drifting apart).
_POSTGRES_SEQUENCE = "project_pid_seq"
# SQLite fallback table in the hermetic unit layer (see module docstring).
_FALLBACK_TABLE = "project_pid_sequence"


def is_valid_pid(value: str) -> bool:
    """Whether *value* matches the Section 7.3 pattern exactly."""
    return bool(_PID_RE.match(value))


def render_pid(number: int) -> str:
    """Render *number* as ``PID`` + five zero-padded digits (Section 7.3).

    Pure formatting: raises ``ValueError`` for a number outside the capacity
    span — that is a programming error here, not a client-facing condition;
    the sequence-driven exhaustion path callers see is
    ``allocate_project_id`` raising ``PidSequenceExhausted``.
    """
    if not PID_MIN <= number <= PID_MAX:
        raise ValueError(f"PID number {number} outside capacity {PID_MIN}..{PID_MAX}")
    return f"PID{number:05d}"


def next_project_number() -> int:
    """Consume the next sequence value — one atomic database statement.

    PostgreSQL: ``nextval('project_pid_seq')``. Unit-layer SQLite: a
    single-row ``UPDATE ... RETURNING`` counter (the fallback table's write
    lock makes the increment atomic for the same reason ``nextval`` is).
    A rolled-back caller transaction refunds the SQLite value but not a
    Postgres sequence — both are consistent with Section 7.3's acceptance
    of gaps.
    """
    with connection.cursor() as cursor:
        if connection.vendor == "postgresql":
            cursor.execute(f"SELECT nextval('{_POSTGRES_SEQUENCE}')")
        else:
            cursor.execute(
                f"UPDATE {_FALLBACK_TABLE} SET value = value + 1 WHERE id = 1 RETURNING value"
            )
        row = cursor.fetchone()
    if row is None:  # pragma: no cover - defensive: migration always seeds the row
        raise RuntimeError(
            f"{_FALLBACK_TABLE} row missing — run `manage.py migrate` before allocating ids."
        )
    return int(row[0])


def allocate_project_id() -> str:
    """Next usable project id: sequence value, rendered and capacity-checked.

    Raises ``PidSequenceExhausted`` (``SERVER_ERROR``) once the sequence
    would emit a value above ``PID_MAX`` — a malformed id is never returned
    (Section 7.3 "exhaustion raises a clear error").
    """
    number = next_project_number()
    if not PID_MIN <= number <= PID_MAX:
        raise PidSequenceExhausted()
    return render_pid(number)


def ensure_valid_pid(pid: str) -> str:
    """Validate *pid* at an API boundary (Section 7.3), DRF-style.

    The reusable ``validate_project_id`` raises Django's ``ValidationError``
    (model/full_clean world); a view needs the DRF exception so the envelope
    handler answers ``VALIDATION_ERROR`` (Section 9.2 catalog) instead of
    the exception falling through to ``SERVER_ERROR``. Returns the validated
    value for chaining.
    """
    try:
        validate_project_id(pid)
    except DjangoValidationError as exc:
        raise ValidationError({"pid": exc.messages}) from exc
    return pid
