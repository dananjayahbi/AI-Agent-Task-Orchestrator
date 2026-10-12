"""Task identifier rules — ``{PID}-T{index}`` (Section 7.3; FR-TSK-01).

Section 7.3 fixes the task id: ``PID[0-9]{5}-T[0-9]{3,}`` where the index
renders with **at least** three digits and grows beyond them naturally
(``T1000``); ids are validated at every API boundary (DRF-style helper
below) and by a database ``CheckConstraint`` on the Task row (MT-1.4-01;
Section 7.4).

Responsibility split across the WP (recorded in the changelog):

* **MT-1.4-01** consumes the pattern/validators for the model constraint;
* **MT-1.4-02** adds :func:`render_task_id` and :func:`allocate_task_id`
  — the *single* allocation entry point (Section 7.3: inside the creating
  transaction the project row is locked, ``task_counter`` incremented and
  the id built from it). Create (MT-1.4-03) and WP-1.5's T1 side effect
  both call that one function; nothing else may roll its own allocator
  (Section 9.1: the ``tasks`` module owns sequencing) — a structural test
  guards that ``task_counter`` is written nowhere else.

Gap tolerance (FR-TSK-01), stated once here so no caller "repairs"
anything:

* the counter increment is **transactional** — a create that rolls back
  refunds its number, and reusing an uncommitted number cannot collide
  because no task row ever carried it;
* a committed increment whose task row never materializes (allocator
  called outside the eventual insert transaction, manual bumps) leaves a
  **permanent gap** — expected, never back-filled, never re-sequenced
  (Section 7.3: "Deleting a task is not supported; archiving preserves id
  continuity" — the same continuity for ids).

Lock discipline (MT-1.4-02 risk note, for WP-1.5/1.6 reviewers): the
project row is a hot row — this module keeps the locked section to
*one atomic UPDATE + render*, inside the caller's transaction. On
Postgres the UPDATE **is** the Section 7.3 row lock (an exclusive row
lock held until commit — stronger and earlier than a following
``SELECT ... FOR UPDATE``, in a single statement); one statement also
matters on the SQLite unit layer, where a SELECT-then-UPDATE transaction
would let every worker hold a shared-cache read lock and livelock the
upgrade (recorded in the WP changelog — this is why the increment is not
written as ORM read + write). Always acquire the project lock **before**
any task-row locks, in that order everywhere, so future writers of the
Project row (policy PATCH, status change) cannot deadlock against
allocation.
"""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.db import connection, transaction
from rest_framework.exceptions import ValidationError

from apps.projects.models import Project

# Section 7.3 / FR-TSK-01: PID + five digits, then -T and a 3+ digit index.
TASK_ID_PATTERN = r"^PID[0-9]{5}-T[0-9]{3,}$"

# Callable validator for serializer/model full_clean paths (API boundaries).
# Registered in migrations by value, so the definition can evolve without
# changing serialized migration state (the migration check guards the pair).
validate_task_id = RegexValidator(
    TASK_ID_PATTERN,
    message="Task id must be {PID}-T{index} with a 3+ digit index (Section 7.3).",
)

_TASK_ID_RE = re.compile(TASK_ID_PATTERN)

# The embedded project id: eight leading characters (Section 7.3).
_TASK_PROJECT_PREFIX_LEN = 8


def is_valid_task_id(value: str) -> bool:
    """Whether *value* matches the Section 7.3 task-id pattern exactly."""
    return bool(_TASK_ID_RE.match(value))


def project_id_of_task(task_id: str) -> str | None:
    """The ``PID[0-9]{5}`` prefix of *task_id*, or ``None`` if malformed.

    Lets an ADR-004 scope guard resolve the addressed project from a
    ``/tasks/{id}`` route without importing the model layer (Section 9.3
    step 1: the project comes from the URL, never the body).
    """
    if len(task_id) < _TASK_PROJECT_PREFIX_LEN:
        return None
    prefix = task_id[:_TASK_PROJECT_PREFIX_LEN]
    if prefix.startswith("PID") and prefix[3:].isdigit():
        return prefix
    return None


def ensure_valid_task_id(task_id: str) -> str:
    """Validate *task_id* at an API boundary (Section 7.3), DRF-style.

    Mirrors ``apps.projects.services.pids.ensure_valid_pid``: Django's
    ``ValidationError`` (model/full_clean world) becomes the DRF
    ``ValidationError`` so the envelope handler answers
    ``VALIDATION_ERROR`` (Section 9.2 catalog) instead of letting the
    exception fall through to ``SERVER_ERROR``. Returns the validated
    value for chaining.
    """
    try:
        validate_task_id(task_id)
    except DjangoValidationError as exc:
        raise ValidationError({"id": exc.messages}) from exc
    return task_id


def render_task_id(pid: str, index: int) -> str:
    """Render *index* as ``{pid}-T{index}`` — at least 3 digits, natural growth.

    Pure formatting (FR-TSK-01 / Section 7.3): ``1`` → ``T001``,
    ``999`` → ``T999``, ``1000`` → ``T1000`` — zero-padding is a *minimum*
    width, so a fourth digit never breaks the pattern. Index ``0`` (or
    negative) is a programming error, never output: the counter starts at
    0 and the first allocation increments **before** rendering, so
    ``T000`` is never issued (the PID sequence's "never 0" reading,
    MT-1.3-01, mirrored).
    """
    if index < 1:
        raise ValueError(f"task index must be >= 1 (got {index}); 0 is never issued")
    return f"{pid}-T{index:03d}"


def allocate_task_id(project: Project) -> str:
    """Next task id for *project* — Section 7.3's algorithm, verbatim.

    Inside one transaction (the caller's, when the caller already opened
    one — ``atomic`` nests as a savepoint so the lock and the increment
    live in the **creating** transaction together with the task INSERT):

    1. lock the project row exclusively — the ``UPDATE`` itself takes the
       exclusive row lock on Postgres (held until commit, exactly the
       Section 7.3 "project row is locked" guarantee);
    2. increment ``task_counter``;
    3. read the new value back from the same statement (``RETURNING``)
       and build the id via :func:`render_task_id`.

    Lock + increment + read-back in **one statement** is deliberate
    (module docstring): it keeps the locked section minimal, and it avoids
    the SQLite shared-cache upgrade deadlock a preceding ``SELECT`` would
    create (a read lock held to end-of-transaction blocks every other
    worker's upgrade — the unit layer livelocked on exactly that pattern
    until this shape was adopted; recorded in the changelog).

    This is the **single allocation entry point** (MT-1.4-02): the create
    endpoint (MT-1.4-03) and WP-1.5's T1 side effect call this function;
    a structural test fails the build if any other module writes
    ``task_counter``. Gaps from rolled-back or failed creations are
    expected and never repaired (module docstring; FR-TSK-01).
    """
    with transaction.atomic():
        table = Project._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE {table} SET task_counter = task_counter + 1 "
                "WHERE id = %s RETURNING task_counter",
                [project.pk],
            )
            row = cursor.fetchone()
        if row is None:  # pragma: no cover - defensive: the caller resolved the row
            raise Project.DoesNotExist(f"Project {project.pk} does not exist.")
        return render_task_id(str(project.pk), int(row[0]))
