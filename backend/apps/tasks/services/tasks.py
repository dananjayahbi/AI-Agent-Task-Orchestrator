"""Task writes and lookups — the create/update paths of Section 9.2 (9.1).

Views stay thin: boundary resolution (``get_task_or_404``), creation
(T1's model-level step — allocate id, ``draft``, ``version`` 1, policy's
``audit_required``) and the version-checked update live here, so
MT-1.4-03's endpoints, MT-1.4-06's archive rules and WP-1.5's transition
service all compose the same primitives.

Decisions recorded here (WP changelog):

* **Creation composes the single allocator** (MT-1.4-02) inside one
  transaction with the INSERT — Section 7.3's "creating transaction"
  owns lock, increment and row together; a rollback refunds everything.
* **``task.created`` emission hook** — the comment at the end of
  ``create_task`` is the Section 9.6 event point WP-1.9 activates; this
  WP records it, never fakes it (MT-1.4-03 out-of-scope note).
* **Update is a compare-and-swap on ``version``** behind a row lock:
  read the row with ``select_for_update`` (Postgres serializes writers;
  SQLite's single-writer store serializes anyway), compare, apply,
  increment (FR-TSK-06 — a stale version must never overwrite).
* **``target_scope`` glob rules** (Section 12.3: "target_scope globs are
  validated on creation") are spelled out in
  :func:`validate_target_scope_globs` — the same helper the PATCH path
  reuses, so the rule cannot drift between the two writes.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any, NamedTuple

from django.db import transaction
from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.db.models.functions import Length
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.pagination import decode_str_cursor, encode_cursor
from apps.projects.models import Project

from ..exceptions import TaskNotFound, TaskStateConflict, VersionConflict
from ..models import Task, TaskPriority, TaskState
from .dependencies import set_dependencies
from .ids import allocate_task_id, ensure_valid_task_id, is_valid_task_id

# Section 12.3: payload paths are rejected if they escape the repo root
# (traversal, symlink, absolute). target_scope globs are validated on
# creation with the same intent — the concrete rules (a reading of the
# section's prose, recorded in the changelog): non-empty, relative, no
# `..` segment, no backslash (globs use forward slashes), no NUL.
_MAX_TARGET_SCOPE_GLOBS = 64
_MAX_GLOB_LENGTH = 500


def validate_target_scope_globs(globs: Iterable[Any]) -> list[str]:
    """Validate repo-relative globs (Section 12.3); return the clean list.

    Raises the DRF ``ValidationError`` the envelope handler maps to
    ``VALIDATION_ERROR`` with per-index details — never a 500, never a
    silently accepted escape pattern.
    """
    cleaned: list[str] = []
    errors: dict[str, list[str]] = {}
    entries = list(globs)
    if len(entries) > _MAX_TARGET_SCOPE_GLOBS:
        raise ValidationError({"target_scope": f"At most {_MAX_TARGET_SCOPE_GLOBS} globs."})
    for index, raw in enumerate(entries):
        if not isinstance(raw, str):
            errors[f"{index}"] = ["Each glob must be a string."]
            continue
        glob = raw.strip()
        problems: list[str] = []
        if not glob:
            problems.append("must not be empty")
        if len(glob) > _MAX_GLOB_LENGTH:
            problems.append(f"must be at most {_MAX_GLOB_LENGTH} characters")
        if "\\" in glob:
            problems.append("must use forward slashes, not backslashes")
        if "\x00" in glob:
            problems.append("must not contain NUL")
        if glob.startswith("/") or (len(glob) >= 2 and glob[1] == ":" and glob[0].isalpha()):
            problems.append("must be relative to the repo root (not absolute)")
        segments = {part for part in glob.replace("\\", "/").split("/")}
        if ".." in segments:
            problems.append("must not traverse outside the repo root ('..')")
        if problems:
            errors[str(index)] = problems
        else:
            cleaned.append(glob)
    if errors:
        raise ValidationError({"target_scope": errors})
    return cleaned


def get_task_or_404(task_id: str) -> Task:
    """Resolve ``{id}`` at the API boundary: validate, then look up.

    Malformed ids raise the DRF ``ValidationError`` → ``VALIDATION_ERROR``
    (Section 7.3: every boundary validates); well-formed but unknown ids
    raise ``TaskNotFound`` → ``TASK_NOT_FOUND`` (404) from the Section
    9.2 catalog — the catalog code the projects app had to go without
    (MT-1.3-03's recorded asymmetry, now used as designed).
    """
    ensure_valid_task_id(task_id)
    task = (
        Task.objects.filter(pk=task_id)
        .prefetch_related("dependency_edges")  # MT-1.4-05: one query, no N+1
        .first()
    )
    if task is None:
        raise TaskNotFound(f"Task {task_id} does not exist.")
    return task


def create_task(
    *,
    project: Project,
    title: str,
    created_by: str | None,
    description: str = "",
    acceptance_criteria: list[str] | None = None,
    target_scope: list[str] | None = None,
    test_command: str = "",
    priority: str = TaskPriority.MEDIUM,
    depends_on: list[str] | None = None,
) -> Task:
    """T1's model-level step (Section 8.2): allocate id, land in ``draft``.

    One transaction holds the Section 7.3 lock+increment (the MT-1.4-02
    allocator) and the INSERT, so id and row commit together or not at
    all. ``state``/``version`` are set here explicitly (never client
    input — the create serializer does not even declare them), and
    ``audit_required`` copies the project policy's
    ``audit_required_default`` (Section 7.2: "defaults from policy").
    """
    with transaction.atomic():
        task_id = allocate_task_id(project)
        task = Task.objects.create(
            id=task_id,
            project=project,
            title=title,
            description=description,
            acceptance_criteria=list(acceptance_criteria or []),
            target_scope=validate_target_scope_globs(target_scope or []),
            test_command=test_command,
            priority=priority,
            state=TaskState.DRAFT,
            version=1,
            audit_required=project.agent_policy.audit_required_default,
            created_by=created_by,
        )
        if depends_on is not None:
            # Same transaction: edges land with the row (or not at all) —
            # validation failure rolls the whole create back (MT-1.4-05).
            set_dependencies(task=task, dependency_ids=depends_on)
    # Event hook (WP-1.9): emit `task.created` after commit here — the
    # Section 9.6 catalog entry; this WP records the point, never fakes it.
    return task


def update_task(
    *,
    task: Task,
    validated: dict[str, Any],
    expected_version: int,
) -> Task:
    """Apply a partial update under FR-TSK-06 optimistic concurrency.

    Inside one transaction the row is locked, the client's ``version``
    compared, the allowlisted fields applied and ``version`` incremented.
    A mismatch raises ``VersionConflict`` (409, ``VERSION_CONFLICT``) —
    **the WP-1.4 acceptance** — so a stale writer never overwrites a
    newer change (the UI then refreshes, Section 8.2 rules).

    ``validated`` contains only fields the update serializer declared
    (the strict mixin rejects everything else at the boundary); the
    caller pops ``version`` out before calling. ``depends_on`` (MT-1.4-05)
    is not a model attribute: it pops out and goes through the dependency
    service as a replace-the-set write, still under the row lock and the
    same transaction — a change to the dependency set counts as a change
    and increments ``version`` like any other edit.
    """
    with transaction.atomic():
        locked = Task.objects.select_for_update().get(pk=task.pk)
        if locked.version != expected_version:
            raise VersionConflict(locked.pk, expected=expected_version, actual=locked.version)
        # MT-1.4-06: the update endpoint's write refusal (FR-TSK-08).
        # `completed` is read-only (Section 8.2 T17; Section 7.4 rule 3 —
        # immutable except archived_at, which is not a PATCH field) and
        # archived rows are historical records (Section 7.3). One catalog
        # code for both, recorded in the changelog. This guard lives at
        # the API write path only — WP-1.5's transition registry owns
        # state-machine guards (the boundary both must respect).
        if locked.state == TaskState.COMPLETED:
            raise TaskStateConflict(locked.pk, reason="is completed and read-only (FR-TSK-08)")
        if locked.archived_at is not None:
            raise TaskStateConflict(locked.pk, reason="is archived and no longer accepts edits")
        fields = dict(validated)
        dependency_ids = fields.pop("depends_on", None)
        if dependency_ids is not None:
            # Validated inside the locked transaction (Section 9.3's
            # "inside the lock" discipline); a refusal rolls everything back.
            set_dependencies(task=locked, dependency_ids=dependency_ids)
        for attribute, value in fields.items():
            setattr(locked, attribute, value)
        if fields or dependency_ids is not None:
            # "incremented on every change" (7.2) — no change, no bump
            locked.version += 1
            locked.save()
    return locked


def archive_task(*, task: Task, expected_version: int | None = None) -> Task:
    """T19's side effect — the ``archived_at`` setter for WP-1.5 (MT-1.5-02).

    Contract recorded for the transition service (Section 8.2 T19,
    "Sets ``archived_at``"; MT-1.4-06 hands T19 a settled field):

    * sets ``archived_at`` to the **server clock** (principle P7) and
      increments ``version`` (Section 7.2) in one transaction under the
      row lock;
    * ``expected_version`` optionally applies the same compare-and-swap
      PATCH uses — the Section 8.2 rule "the UI sends the version it
      saw; a stale version returns a conflict";
    * already archived → returns the row unchanged (the marker is a
      timestamp: first archive wins, never re-stamped, no double bump);
    * **state gating is not done here**: "any non-``completed``" is
      T19's registry rule and WP-1.5's guard owns it — this helper only
      performs the side effect, so the two implementations never compete
      (MT-1.4-06 boundary note). Section 7.3: archiving is the only
      end-of-life a task gets; nothing ever hard-deletes the row.
    """
    with transaction.atomic():
        locked = Task.objects.select_for_update().get(pk=task.pk)
        if expected_version is not None and locked.version != expected_version:
            raise VersionConflict(locked.pk, expected=expected_version, actual=locked.version)
        if locked.archived_at is not None:
            return locked  # first timestamp wins — idempotent re-archive
        locked.archived_at = timezone.now()
        locked.version += 1
        locked.save()
    return locked


# --- list query (MT-1.4-04; FR-TSK-05 ordering; NFR-09 scale) --------------

# FR-TSK-05 verbatim: urgent > high > medium > low. The sequence is spelled
# out here on purpose (MT-1.4-04 risk note): the stored enum must never be
# ordered alphabetically, and the declaration order of TaskPriority is not
# load-bearing for the sort — this tuple is.
FR_TSK_05_ORDER: tuple[str, ...] = ("urgent", "high", "medium", "low")

# rank 0 sorts first (urgent); a value outside FR-TSK-05 cannot exist (DB
# check constraint) — the default keeps the CASE total for safety.
PRIORITY_RANK: dict[str, int] = {value: rank for rank, value in enumerate(FR_TSK_05_ORDER)}

_PRIORITY_RANK_EXPR = Case(
    *[When(priority=value, then=Value(rank)) for value, rank in PRIORITY_RANK.items()],
    default=Value(len(FR_TSK_05_ORDER)),
    output_field=IntegerField(),
)


class TaskCursorKey(NamedTuple):
    """The composite sort key a list cursor resumes from (opaque outside)."""

    rank: int  # FR-TSK_05 priority rank
    created_at: datetime  # FIFO tie-break (server clock)
    id_length: int  # generation-order tie-break part 1 (Section 7.3 growth)
    task_id: str  # generation-order tie-break part 2 (final stable key)


def task_list_queryset(
    project: Project,
    *,
    states: Iterable[str] | None = None,
    priority: str | None = None,
    include_archived: bool = False,
) -> QuerySet[Task]:
    """One project's tasks in the canonical order — everything in SQL.

    Order (FR-TSK-05 + pagination.md rule 2): ``priority`` in the
    ``urgent > high > medium > low`` sequence, then oldest ``created_at``
    first (FIFO), then the id's **generation order** — a task id grows
    past three digits naturally (``T1000``), so raw lexicographic id
    comparison would sort ``T1000`` before ``T009``; ordering by
    ``(LENGTH(id), id)`` inside one project (shared ``{PID}-T`` prefix)
    reproduces ``T001 < ... < T999 < T1000`` exactly (pagination.md's
    rule-2 warning). The expression runs in the **database** (annotate +
    ``order_by``) so NFR-09's 10,000-task scale never sorts in Python.

    Archived tasks are excluded by default (T19 "hidden from boards by
    default"; MT-1.4-06 owns the behavior, this MT the default); results
    are always scoped to the path project (Section 12.2).
    """
    queryset = Task.objects.filter(project=project)
    if not include_archived:
        queryset = queryset.filter(archived_at__isnull=True)
    if states:
        queryset = queryset.filter(state__in=list(states))
    if priority is not None:
        queryset = queryset.filter(priority=priority)
    return (
        queryset.annotate(
            priority_rank=_PRIORITY_RANK_EXPR,
            id_length=Length("id"),
        )
        .order_by("priority_rank", "created_at", "id_length", "id")
        # MT-1.4-05: `depends_on` rides each page in one extra query — the
        # serializer reads the prefetch cache, never one query per row.
        .prefetch_related("dependency_edges")
    )


def encode_task_cursor(task: Task) -> str:
    """Opaque cursor carrying the full sort key of *task* (rule 1)."""
    material = "|".join(
        (
            str(PRIORITY_RANK[task.priority]),
            task.created_at.isoformat(),
            str(len(task.id)),
            task.id,
        )
    )
    return encode_cursor(material)


def decode_task_cursor(raw: str | None) -> TaskCursorKey | None:
    """Parse a cursor back into its sort key; ``None`` = first page.

    A cursor that does not decode into this endpoint's exact key shape
    (four parts, rank in range, canonical id, consistent length) answers
    ``VALIDATION_ERROR`` — cursors are opaque, and a mangled one is a
    client error drawn from the catalog (pagination.md rule 1).
    """
    material = decode_str_cursor(raw)
    if material is None:
        return None
    parts = material.split("|")
    if len(parts) != 4:
        raise ValidationError("Invalid cursor.")
    rank_text, created_text, length_text, task_id = parts
    try:
        rank = int(rank_text)
        id_length = int(length_text)
        created_at = datetime.fromisoformat(created_text)
    except ValueError as exc:
        raise ValidationError("Invalid cursor.") from exc
    if (
        rank not in PRIORITY_RANK.values()
        or id_length != len(task_id)
        or not is_valid_task_id(task_id)
    ):
        raise ValidationError("Invalid cursor.")
    return TaskCursorKey(rank=rank, created_at=created_at, id_length=id_length, task_id=task_id)


def filter_beyond_cursor(queryset: QuerySet[Task], cursor: TaskCursorKey) -> QuerySet[Task]:
    """Keyset continuation: rows strictly *after* the cursor in the sort.

    The OR-tree mirrors ``task_list_queryset``'s four sort columns, so
    paging never skips or duplicates rows regardless of ties — the
    cursor resumes at the next ``(rank, created_at, id_length, id)``.
    """
    return queryset.filter(
        Q(priority_rank__gt=cursor.rank)
        | Q(priority_rank=cursor.rank, created_at__gt=cursor.created_at)
        | Q(
            priority_rank=cursor.rank,
            created_at=cursor.created_at,
            id_length__gt=cursor.id_length,
        )
        | Q(
            priority_rank=cursor.rank,
            created_at=cursor.created_at,
            id_length=cursor.id_length,
            id__gt=cursor.task_id,
        )
    )
