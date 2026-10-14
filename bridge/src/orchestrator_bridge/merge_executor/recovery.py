"""Startup reconciliation: lock, leftover cleanup, journal recovery (MT-3.7-06).

Section 19 WP-3.7: "crash mid-merge recovers cleanly on restart." Three
pieces, run at every executor startup (Section 10.2 — long-running *and*
``--once``) **before** the loop may claim new work:

1. **Single-worker lock** (RISK-03's single-worker assumption, the
   MT-3.7-06 risk note's "if no locking exists yet, add it"): an OS
   advisory byte-range lock on ``<temp-root>/merge-executor.lock`` held
   for the run's lifetime. Advisory locks vanish with the holding
   process, so a crash never leaves a stale lock — a *second* executor
   is refused with one operator-facing line.
2. **Leftover worktree cleanup** (MT-3.7-03 enumeration): every
   enumerated executor worktree of every allowlisted repository is
   removed before any new merge can start.
3. **Journal reconciliation**: for each journal entry still owed an
   outcome (claim accepted, result never confirmed), the live queue
   state decides *one* terminal outcome:
   * still ``merging`` → report ``failed`` (→ T18, ``merge_conflict``)
     with restart details — the risk note's safe default ("when in doubt
     report failure so a human decides"); the human re-approval then
     re-merges through the *normal* queue cycle from a fresh isolated
     worktree, so ADR-008's ``completed`` only via a genuine merge stays
     honest. Evidence cannot distinguish "merge landed, report lost"
     from "never merged" in general (a squash leaves no ancestry), so
     no completion is ever inferred;
   * already exited (``TASK_STATE_CONFLICT``/``VERSION_CONFLICT`` or a
     non-``merging`` read) → nothing to apply; the journal entry is
     closed (ADR-012: never a second apply).

Backend outages during recovery retry with Section 10.10 exponential
backoff (capped, bounded); a persistent outage raises
:class:`MergeRecoveryError` and stops startup — never a fabricated
result, and the next start resumes the same reconciliation.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Final

from ..api_errors import ApiError, ErrorCode
from ..config import Settings
from ..idempotency import new_key
from ..logging import get_logger
from . import worktree
from .errors import MergeExecutorError
from .journal import MergeJournal, journal_path
from .loop import MUTATION_BACKOFF_ATTEMPTS, OUTAGE_BACKOFF_CAP_SECONDS
from .queue import RESULT_FAILED, MergeQueueClient, QueueItem
from .worktree import list_leftover_worktrees, remove_leftover_worktree

__all__ = [
    "ExecutorLock",
    "MergeRecoveryError",
    "acquire_executor_lock",
    "cleanup_leftover_worktrees",
    "reconcile_on_startup",
    "startup_recovery",
]

_LOGGER_COMPONENT = "merge-executor"

#: The advisory lock's file under the executor temp root.
LOCK_FILE_NAME: Final = "merge-executor.lock"

#: One actor-style prefix for the recovery report's details (Section 9.2
#: carries free text — the reason travels there, no schema change).
_RECOVERY_DETAILS: Final = (
    "executor restart reconciliation: the previous merge attempt was "
    "interrupted and its outcome could not be verified; returning the task "
    "to human review (re-approve to re-merge from a fresh worktree)"
)

#: Catalog answers that *decide* the task for reconciliation purposes —
#: it already left `merging` by another path (or is unknown), so the
#: journal closes without applying anything (ADR-012: never a second apply).
_TERMINAL_CODES: frozenset[ErrorCode] = frozenset(
    {ErrorCode.TASK_STATE_CONFLICT, ErrorCode.VERSION_CONFLICT, ErrorCode.TASK_NOT_FOUND}
)


class MergeRecoveryError(MergeExecutorError):
    """Startup reconciliation stayed unconfirmed after every backoff attempt.

    The executor refuses to serve rather than run with unreconciled
    debris; the journal entry is still open, so the next start resumes
    the same decision (never a duplicate, never a fabrication).
    """


class ExecutorLock:
    """One held OS advisory lock (the single-worker guard of RISK-03).

    ``handle`` is kept alive for the run's lifetime; ``close`` releases
    early (tests, and CPython's refcount at process end).
    """

    __slots__ = ("_handle", "_kind")

    def __init__(self, handle: Any, kind: str) -> None:
        self._handle = handle
        self._kind = kind

    def close(self) -> None:
        if self._handle is None:
            return
        try:
            if self._kind == "nt":
                import msvcrt  # noqa: PLC0415 - platform-specific, imported on use

                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl  # noqa: PLC0415 - POSIX-only, imported on use

                # POSIX typeshed on any OS (this branch never runs on Windows):
                fcntl.flock(  # type: ignore[attr-defined]
                    self._handle.fileno(),
                    fcntl.LOCK_UN,  # type: ignore[attr-defined]
                )
        except OSError:
            pass  # the process is ending anyway — the OS releases it
        self._handle.close()
        self._handle = None

    def __enter__(self) -> ExecutorLock:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def acquire_executor_lock() -> ExecutorLock:
    """Take the single-worker lock or refuse (risk note: add locking here).

    Advisory (``flock``/``msvcrt.locking``): the kernel drops it when
    this process dies, so a crash never wedges the next start, while a
    *live* second executor answers with :class:`MergeRecoveryError`'s
    operator-facing refusal — one writer on one queue, always.
    """
    root = worktree.temp_worktree_root()
    root.mkdir(parents=True, exist_ok=True)
    path = root / LOCK_FILE_NAME
    handle = path.open("a+b")  # create-or-open; locks never truncate
    kind = "nt" if os.name == "nt" else "posix"
    try:
        if kind == "nt":
            import msvcrt  # noqa: PLC0415 - platform-specific

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl  # noqa: PLC0415 - POSIX-only

            # POSIX typeshed on any OS (this branch never runs on Windows):
            fcntl.flock(  # type: ignore[attr-defined]
                handle.fileno(),
                fcntl.LOCK_EX  # type: ignore[attr-defined]
                | fcntl.LOCK_NB,  # type: ignore[attr-defined]
            )
    except OSError as exc:
        handle.close()
        raise MergeRecoveryError(
            f"another Merge Executor already holds {str(path)}.",
            reason="RISK-03's single-worker assumption: two executors would "
            "double-claim the queue; stop the other instance first",
        ) from exc
    return ExecutorLock(handle, kind)


def cleanup_leftover_worktrees(repo_paths: Sequence[str | Path]) -> int:
    """Remove every leftover worktree of every allowlisted repository.

    Runs before any reconciliation API call (the MT scope: cleanup first)
    and never touches anything outside the executor temp root.
    """
    log = get_logger(_LOGGER_COMPONENT)
    removed = 0
    for raw in repo_paths:
        repo = Path(raw).resolve()
        for leftover in list_leftover_worktrees(repo):
            remove_leftover_worktree(leftover, repo)
            removed += 1
            log.warning(
                "leftover temporary worktree removed at startup",
                extra={"event": "merge_worktree_leftover_removed", "path": str(leftover)},
            )
    return removed


def reconcile_on_startup(
    settings: Settings,
    queue: MergeQueueClient,
    *,
    journal: MergeJournal | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Close every journal-open task with one terminal outcome; return the count.

    Leftovers are cleaned first (local, no API), then each open entry is
    decided against live queue state with bounded backoff. Every entry
    either closes (counted, journal compacted) or the whole call raises
    :class:`MergeRecoveryError` (outage exhausted) with the journal left
    intact — startup stops, the next start resumes, nothing is fabricated.
    """
    cleanup_leftover_worktrees(settings.merge_repo_paths)
    active = journal if journal is not None else MergeJournal(journal_path())
    unresolved = active.unresolved()
    if not unresolved:
        return 0
    decided = 0
    for task_id in sorted(unresolved):
        _reconcile_task(settings, queue, active, task_id, sleep=sleep)
        decided += 1
    active.compact()  # every open entry closed above — the file starts clean
    return decided


def _reconcile_task(
    settings: Settings,
    queue: MergeQueueClient,
    journal: MergeJournal,
    task_id: str,
    *,
    sleep: Callable[[float], None],
) -> None:
    """Decide one open journal entry (closes it, or raises for a later start)."""
    log = get_logger(_LOGGER_COMPONENT)
    key = new_key("merge-recovery", target=task_id)

    details, answered = _call_with_backoff(
        settings,
        sleep,
        lambda: queue.task(task_id),
        task_id=task_id,
        operation_name="task_details",
    )
    if answered or str(details.get("merge_status")) != "merging":
        # Already decided elsewhere (T17/T18 applied, the row exited, or
        # the task is unknown): close the entry, apply nothing (ADR-012).
        journal.record_reported(task_id, result="observed-exited")
        log.info(
            "reconciliation: task already left merging — nothing to apply",
            extra={"event": "merge_recovery_already_exited", "task_id": task_id},
        )
        return

    item = _item_from_details(task_id, details)
    _, answered = _call_with_backoff(
        settings,
        sleep,
        lambda: queue.report(
            item,
            result=RESULT_FAILED,
            details=_RECOVERY_DETAILS,
            version=int(details.get("version") or 0) or None,
            idempotency_key=key,
        ),
        task_id=task_id,
        operation_name="recovery_result",
    )
    if answered:
        journal.record_reported(task_id, result="observed-exited")
        log.info(
            "reconciliation: report refused by the catalog — already decided",
            extra={"event": "merge_recovery_already_exited", "task_id": task_id},
        )
        return
    journal.record_reported(task_id, result=RESULT_FAILED)
    log.warning(
        "reconciliation: interrupted merge reported as failed (T18 path)",
        extra={"event": "merge_recovery_reported_failed", "task_id": task_id},
    )


def _item_from_details(task_id: str, details: dict[str, Any]) -> QueueItem:
    """A ``QueueItem`` from a ``GET /tasks/{id}`` body (only identity matters here)."""
    return QueueItem(
        id=task_id,
        project_id=str(details.get("project_id") or ""),
        title=str(details.get("title") or task_id),
        state=str(details.get("state") or ""),
        version=int(details.get("version") or 0),
        merge_status=str(details.get("merge_status") or ""),
        branch_name=(
            str(details["branch_name"]) if details.get("branch_name") is not None else None
        ),
    )


def _call_with_backoff(
    settings: Settings,
    sleep: Callable[[float], None],
    operation: Callable[[], Any],
    *,
    task_id: str,
    operation_name: str,
) -> tuple[Any, bool]:
    """Run one queue call with Section 10.10 backoff.

    Returns ``(value, catalog_answered)``: ``catalog_answered`` is True
    when the catalog refused with a *terminal* answer for this task
    (TASK_STATE_CONFLICT / VERSION_CONFLICT / TASK_NOT_FOUND) — a
    decision, apply nothing (ADR-012). A retryable outage retries with
    capped exponential backoff; exhausted attempts or a non-retryable
    error raise :class:`MergeRecoveryError` — startup stops, the entry
    stays open, nothing is fabricated.
    """
    log = get_logger(_LOGGER_COMPONENT)
    for attempt in range(1, MUTATION_BACKOFF_ATTEMPTS + 1):
        try:
            return operation(), False
        except ApiError as exc:
            if exc.code in _TERMINAL_CODES:
                return None, True
            if not exc.retryable or attempt == MUTATION_BACKOFF_ATTEMPTS:
                raise MergeRecoveryError(
                    f"startup reconciliation ({operation_name}) for {task_id} "
                    f"stayed unconfirmed after {MUTATION_BACKOFF_ATTEMPTS} "
                    f"attempts ({exc.code}).",
                    reason="the journal entry remains open — the next start "
                    "resumes this decision (never a fabricated result)",
                ) from exc
            delay = min(
                settings.retry_base_delay_seconds * (2 ** (attempt - 1)),
                OUTAGE_BACKOFF_CAP_SECONDS,
            )
            log.warning(
                "backend unreachable during recovery — backing off",
                extra={
                    "event": "merge_recovery_backoff",
                    "operation": operation_name,
                    "task_id": task_id,
                    "attempt": attempt,
                    "delay_seconds": delay,
                    "error_code": str(exc.code),
                },
            )
            sleep(delay)
    raise AssertionError("unreachable: the backoff loop returns or raises")


def startup_recovery(
    settings: Settings,
    queue: MergeQueueClient,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[ExecutorLock, MergeJournal]:
    """The executor's startup seam: lock → cleanup + reconcile → journal.

    Returns the held lock (the caller keeps it alive for the whole run —
    the single-worker guard must outlast recovery) and the journal the
    loop records into.
    """
    lock = acquire_executor_lock()
    try:
        decided = reconcile_on_startup(settings, queue, sleep=sleep)
    except BaseException:
        lock.close()  # a failed startup must not wedge the next attempt
        raise
    get_logger(_LOGGER_COMPONENT).info(
        "startup reconciliation complete",
        extra={"event": "merge_startup_reconciled", "decided": decided},
    )
    return lock, MergeJournal(journal_path())
