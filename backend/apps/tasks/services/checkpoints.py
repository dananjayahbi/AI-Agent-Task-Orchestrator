"""The checkpoint write path — Section 6.5 Flow B; Sections 7.2/8.6/9.6.

Three layers, one module, each landing with its micro-task:

* :class:`CheckpointSubmission` / :func:`store_checkpoint` (MT-1.8-01) —
  the insert plus the task-side touch point (``last_checkpoint_at``).
* :func:`submit_checkpoint` (MT-1.8-02 + MT-1.8-03) — the full Flow B
  sequence in **one transaction**: lock the task row, scope check,
  re-run the MT-1.6-05 fencing gate *under the lock* (a sweeper reclaim
  racing the checkpoint must lose cleanly — TOCTOU closed), insert the
  row, apply the MT-1.6-03 extension for extension-carrying kinds, emit
  ``task.checkpoint`` in-transaction (WP-1.9's writer), commit.
* the listing query + cursor helpers (MT-1.8-04) — reverse-chronological
  keyset pagination per docs/plan/conventions/pagination.md.

Recorded readings (Section 20.1 item 5 — no hidden decisions):

* **Kind gating** (OQ-04 outcome): ``progress`` and ``system`` carry the
  lease extension; ``liveness`` extends only under the project's
  ``checkpoint_and_liveness`` mode. A stored liveness checkpoint under
  the default ``checkpoint_only`` mode still writes its row and event —
  it simply does not extend. Section 8.6's stalled indicator keys on
  ``progress`` checkpoints specifically.
* **Rejections write nothing** (Section 8.6 "no resurrection"): the
  gate raises before any insert, touch, extension or event — the whole
  transaction rolls back with it.
* **version bumps twice** on an extending checkpoint (the touch point
  and the extension are two row changes; Section 7.2 increments on
  *every* change — recorded, not optimized away).
* **attempt_number is copied at write time** from the locked task row
  (MT-1.8-01 risk note — pre-reclaim checkpoints stay attributable).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, NamedTuple, cast
from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework.exceptions import ValidationError

from apps.accounts.exceptions import AuthForbiddenProject
from apps.core.pagination import decode_str_cursor, encode_cursor
from apps.events.services import write_event
from apps.leases.extension import extend_lease
from apps.leases.fencing import require_current_lease
from apps.projects.models import LeaseExtensionMode

from ..exceptions import TaskNotFound
from ..models import CheckpointKind, Task, TaskCheckpoint
from .ids import ensure_valid_task_id


@dataclass(frozen=True)
class CheckpointSubmission:
    """One accepted checkpoint's outcome (the endpoint's response source)."""

    checkpoint: TaskCheckpoint
    lease_extended: bool
    lease_expires_at: datetime | None
    capped: bool


def store_checkpoint(
    task: Task,
    *,
    session_id: str,
    message: str = "",
    percent: int | None = None,
    token_usage: Mapping[str, Any] | None = None,
    kind: str = CheckpointKind.PROGRESS,
) -> TaskCheckpoint:
    """MT-1.8-01: insert one checkpoint row + touch ``last_checkpoint_at``.

    The task-side touch point Section 7.2/8.6 expect: the row's
    ``attempt_number`` is copied from the *current* task value at write
    time (denormalized deliberately — MT-1.8-01 risk note), and
    ``Task.last_checkpoint_at`` moves to the new row's server timestamp
    with a version bump (Section 7.2: every change increments).
    """
    checkpoint = cast(
        TaskCheckpoint,
        TaskCheckpoint.objects.create(
            task=task,
            attempt_number=task.attempt_number,
            session_id=session_id,
            message=message,
            percent=percent,
            token_usage=dict(token_usage or {}),
            kind=kind,
        ),
    )
    task.last_checkpoint_at = checkpoint.timestamp
    task.version += 1
    task.save(update_fields=["last_checkpoint_at", "version", "updated_at"])
    return checkpoint


def _kind_extends_lease(kind: str, mode: str) -> bool:
    """Which kinds carry the extension (OQ-04's recorded outcome)."""
    if kind in (CheckpointKind.PROGRESS, CheckpointKind.SYSTEM):
        return True
    return kind == CheckpointKind.LIVENESS and mode == LeaseExtensionMode.CHECKPOINT_AND_LIVENESS


def submit_checkpoint(
    task_id: str,
    *,
    session_id: str,
    lease_generation: int,
    message: str = "",
    percent: int | None = None,
    token_usage: Mapping[str, Any] | None = None,
    kind: str = CheckpointKind.PROGRESS,
    caller_project_id: str | None = None,
) -> CheckpointSubmission:
    """Flow B in one transaction: verify, store, extend, emit (MT-1.8-02/03).

    The MT-1.6-05 fencing gate runs **after** ``select_for_update`` so a
    sweeper reclaim racing this call always wins (Section 18): the gate
    reads the locked row, and every rejection path raises before a single
    write. ``TASK_NOT_FOUND`` (unknown id), ``AUTH_FORBIDDEN_PROJECT``
    (foreign project) and the two lease codes flow from the shared
    helpers — this module never re-implements fencing.
    """
    ensure_valid_task_id(task_id)
    with transaction.atomic():
        task = Task.objects.select_for_update().filter(pk=task_id).first()
        if task is None:
            raise TaskNotFound(f"Task {task_id} does not exist.")
        if caller_project_id is not None and task.project_id != caller_project_id:
            raise AuthForbiddenProject(
                f"Token is scoped to {caller_project_id!r}, not {task.project_id!r}."
            )
        # MT-1.8-02: the gate, re-checked under the row lock (ADR-012).
        require_current_lease(task, session_id=session_id, lease_generation=lease_generation)

        checkpoint = store_checkpoint(
            task,
            session_id=session_id,
            message=message,
            percent=percent,
            token_usage=token_usage,
            kind=kind,
        )

        # MT-1.6-03 extension, kind-gated (OQ-04). extend_lease opens a
        # nested atomic block on this same transaction and re-runs the
        # fencing helper on the freshly locked row — one implementation,
        # no drift; its save bumps version a second time (recorded).
        policy = task.project.agent_policy
        if _kind_extends_lease(kind, policy.lease_extension_mode):
            extension = extend_lease(
                task_id=task.pk,
                session_id=session_id,
                lease_generation=lease_generation,
                caller_project_id=caller_project_id,
            )
            lease_extended = True
            lease_expires_at: datetime | None = extension.lease_expires_at
            capped = extension.capped
        else:
            lease_extended = False
            lease_expires_at = task.lease_expires_at
            capped = False

        # Section 9.6 / Section 20.4 item 6: in-transaction emission so the
        # event and the row commit (or roll back) together; publishing is
        # post-commit inside the writer (MT-1.9-03).
        write_event(
            type="task.checkpoint",
            project_id=task.project_id,
            task_id=task.pk,
            actor_type="agent",
            actor_ref=session_id,
            data={
                "checkpoint_id": str(checkpoint.pk),
                "attempt_number": checkpoint.attempt_number,
                "kind": checkpoint.kind,
                "percent": checkpoint.percent,
                "session_id": checkpoint.session_id,
                "message": checkpoint.message,
                "token_usage": checkpoint.token_usage,
            },
            occurred_at=checkpoint.timestamp,
        )
        return CheckpointSubmission(
            checkpoint=checkpoint,
            lease_extended=lease_extended,
            lease_expires_at=lease_expires_at,
            capped=capped,
        )


# --- listing (MT-1.8-04; WP-0.5-04 cursor conventions) ----------------------


class CheckpointCursorKey(NamedTuple):
    """The composite sort key a listing cursor resumes from (opaque outside)."""

    timestamp: datetime  # server clock (P7) — the primary sort column
    checkpoint_id: UUID  # stable tiebreak for identical timestamps


def checkpoint_list_queryset(task: Task) -> QuerySet[TaskCheckpoint]:
    """One task's checkpoints, newest first (Section 13.2 feed order).

    Ordering is ``(-timestamp, -id)``: the server timestamp leads, the
    UUID primary key breaks ties deterministically (pagination.md rule 2
    — an id-less timestamp cursor would skip or repeat rows the moment
    two checkpoints share a microsecond). The MT-1.8-01
    ``checkpoint_task_time`` index serves the per-task scan; the exact
    plan at NFR-09 scale is WP-1.15's dataset check (flagged there, not
    papered over with offsets — the conventions forbid them).
    """
    return cast(
        "QuerySet[TaskCheckpoint]",
        TaskCheckpoint.objects.filter(task=task).order_by("-timestamp", "-id"),
    )


def encode_checkpoint_cursor(checkpoint: TaskCheckpoint) -> str:
    """Opaque cursor carrying the full sort key of *checkpoint* (rule 1)."""
    material = f"{checkpoint.timestamp.isoformat()}|{checkpoint.pk}"
    return encode_cursor(material)


def decode_checkpoint_cursor(raw: str | None) -> CheckpointCursorKey | None:
    """Parse a cursor back into its sort key; ``None`` = first page.

    A cursor that does not decode into this endpoint's exact key shape
    (two parts, a parseable instant, a valid UUID) answers
    ``VALIDATION_ERROR`` — cursors are opaque, and a mangled one is a
    client error from the closed catalog (rule 1).
    """
    material = decode_str_cursor(raw)
    if material is None:
        return None
    parts = material.split("|")
    if len(parts) != 2:
        raise ValidationError("Invalid cursor.")
    timestamp_text, checkpoint_id_text = parts
    try:
        timestamp = datetime.fromisoformat(timestamp_text)
        checkpoint_id = UUID(checkpoint_id_text)
    except ValueError as exc:
        raise ValidationError("Invalid cursor.") from exc
    return CheckpointCursorKey(timestamp=timestamp, checkpoint_id=checkpoint_id)


def filter_beyond_cursor(
    queryset: QuerySet[TaskCheckpoint], cursor: CheckpointCursorKey
) -> QuerySet[TaskCheckpoint]:
    """Keyset continuation: rows strictly *before* the cursor (newest-first).

    The OR-tree mirrors ``checkpoint_list_queryset``'s two sort columns,
    so paging never skips or duplicates rows regardless of timestamp
    ties — the cursor resumes at the next ``(timestamp, id)``.
    """
    return queryset.filter(
        Q(timestamp__lt=cursor.timestamp)
        | Q(timestamp=cursor.timestamp, id__lt=cursor.checkpoint_id)
    )


def checkpoint_page(
    task: Task, *, cursor: CheckpointCursorKey | None, page_size: int
) -> tuple[list[TaskCheckpoint], str | None]:
    """One page of *task*'s history plus its ``next_cursor``.

    Fetch-one-lookahead (pagination.md): ``next_cursor`` is ``None``
    exactly when the page is the last one — clients stop on that signal
    alone.
    """
    queryset = checkpoint_list_queryset(task)
    if cursor is not None:
        queryset = filter_beyond_cursor(queryset, cursor)
    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    rows = rows[:page_size]
    next_cursor = encode_checkpoint_cursor(rows[-1]) if has_more and rows else None
    return rows, next_cursor


__all__ = [
    "CheckpointCursorKey",
    "CheckpointSubmission",
    "checkpoint_list_queryset",
    "checkpoint_page",
    "decode_checkpoint_cursor",
    "encode_checkpoint_cursor",
    "filter_beyond_cursor",
    "store_checkpoint",
    "submit_checkpoint",
]
