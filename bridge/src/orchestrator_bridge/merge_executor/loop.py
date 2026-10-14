"""The Section 11.4 Merge Executor loop (parent plan Sections 10.2, 10.10, 11.4; WP-3.7).

The five-step workflow as a skeleton with one seam: the actual Git work
is delegated to an injected *merge step* (MT-3.7-03's isolated temp
worktree plus MT-3.7-04's strategy dispatch plug in there), so this
module owns only the loop contract:

1. poll ``GET /merge/pending`` (Section 11.4 allows poll **or** event —
   polling is the v1 choice, recorded in the WP changelog);
2. claim one entry with ``POST /merge/{task}/start`` (→ ``merging``);
3. resolve the project's ``repo_path`` and hand (item, repo, project
   context) to the merge step — **repos outside the configured
   allowlist are never opened** (Section 10.2), checked *before* the
   claim so an unclaimable task is never touched;
4. report the outcome (``succeeded`` + sha, or ``conflict``/``failed``
   + details) through ``POST /merge/{task}/result``;
5. never touch the developer's working directory — every Git action
   lives inside the injected step (Principle P2 / ADR-008; the loop
   itself performs none).

Execution is strictly sequential (one task at a time — RISK-03 repo
contention). Every mutation carries one ADR-012 idempotency key minted
per logical operation and **reused across loop-level retries**, so a
backend outage (Section 10.10) yields backoff + retry and can never
duplicate a completed claim or a second transition. Only canonical
catalog codes drive control flow (Section 20.4 item 5).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Protocol

from ..api_errors import ApiError, ErrorCode
from ..config import Settings
from ..idempotency import new_key
from ..logging import get_logger
from .journal import MergeJournal
from .queue import (
    RESULT_FAILED,
    RESULT_SUCCEEDED,
    RESULT_VALUES,
    MergeQueueClient,
    MergeStart,
    QueueItem,
)

__all__ = [
    "DEFAULT_POLL_SECONDS",
    "MUTATION_BACKOFF_ATTEMPTS",
    "OUTAGE_BACKOFF_CAP_SECONDS",
    "MergeExecutorLoop",
    "MergeOutcome",
    "MergeReportError",
    "MergeStep",
]

#: Poll interval when the queue is idle. The plan fixes no number
#: (Section 11.4 "poll (or receive event)"); 30 s balances freshness
#: against backend load and is recorded in the WP changelog as the
#: executor's default (the MT-3.7-02 risk note's "defaults belong to the
#: executor config" — the value is a constructor parameter).
DEFAULT_POLL_SECONDS: Final = 30.0

#: Loop-level attempts per logical mutation, *beyond* the transport's own
#: per-call retry (MT-2.3-02). Backoff doubles between attempts.
MUTATION_BACKOFF_ATTEMPTS: Final = 3

#: Upper bound for one loop-level backoff sleep (Section 10.10).
OUTAGE_BACKOFF_CAP_SECONDS: Final = 60.0

_LOGGER_COMPONENT: Final = "merge-executor"


class MergeReportError(RuntimeError):
    """A result report stayed unconfirmed after every backoff attempt.

    The task is left ``merging`` on purpose: the report's idempotency key
    survived in the log line, and MT-3.7-06's restart reconciliation is
    the designed recovery for exactly this window — the loop stops
    instead of guessing (never a duplicate completion, P6).
    """


@dataclass(frozen=True, slots=True)
class MergeOutcome:
    """What one merge step determined (Section 11.4 steps 3–4)."""

    result: str  # succeeded | conflict | failed (Section 7.2 values)
    sha: str | None = None  # the resulting sha on success (T17 guard)
    details: str = ""  # conflict file list / error summary (T18 details)

    def __post_init__(self) -> None:
        """Catalog values only — the loop never invents a fourth flavor."""
        if self.result not in RESULT_VALUES:
            raise ValueError(
                f"merge outcome must be one of {sorted(RESULT_VALUES)}; got {self.result!r}"
            )
        if self.result == RESULT_SUCCEEDED and not self.sha:
            raise ValueError("a 'succeeded' outcome requires the resulting sha (T17 guard)")


class MergeStep(Protocol):
    """The MT-3.7-03/04 seam: do the merge work, report what happened.

    ``project`` is the ``GET /projects/{pid}`` payload (repo identity and
    ``default_branch``); ``repo_path`` is the allowlist-verified checkout
    the step may open. The step must never raise for *merge* outcomes —
    return ``conflict``/``failed`` — but an unexpected exception is
    contained by the loop and reported as ``failed`` (T18 path), never a
    crash (MT-3.7-03 risk note).
    """

    def __call__(
        self, item: QueueItem, repo_path: Path, project: Mapping[str, Any]
    ) -> MergeOutcome: ...


class MergeExecutorLoop:
    """One worker's sequential pass over the merge queue (Section 10.2)."""

    def __init__(
        self,
        settings: Settings,
        queue: MergeQueueClient,
        merge_step: MergeStep,
        *,
        sleep: Callable[[float], None] = time.sleep,
        journal: MergeJournal | None = None,
    ) -> None:
        """Wire the loop; ``sleep`` is the backoff/poll seam for tests.

        ``journal`` is MT-3.7-06's crash evidence: when present, every
        accepted claim and every settled report appends one durable line
        the next start's reconciliation reads back (None = journaling
        off — test seams and contexts that reconcile elsewhere).
        """
        self._settings = settings
        self._queue = queue
        self._step = merge_step
        self._sleep = sleep
        self._journal = journal
        self._log = get_logger(_LOGGER_COMPONENT)
        # Section 10.2 binding source: the configured allowlist, path-
        # normalized once so comparisons cannot be defeated by spelling.
        self._allowed_repos: frozenset[Path] = frozenset(
            Path(raw).resolve() for raw in settings.merge_repo_paths
        )

    # --- long-running and on-demand forms (Section 10.2) ---------------------

    def run_forever(self, *, poll_seconds: float = DEFAULT_POLL_SECONDS) -> None:
        """Serve the queue until interrupted (the long-running run mode)."""
        self._log.info(
            "merge executor loop started",
            extra={
                "event": "executor_started",
                "poll_seconds": poll_seconds,
                "allowed_repos": len(self._allowed_repos),
            },
        )
        while True:
            try:
                handled = self.run_once()
            except ApiError as exc:
                if not exc.retryable:
                    # e.g. a revoked token (AUTH_REQUIRED): retrying the
                    # same call can never succeed — stop, loudly.
                    raise
                self._backoff(exc, attempt=1, operation="poll")
                continue
            if handled == 0:
                self._log.info("merge queue idle", extra={"event": "merge_queue_idle"})
                self._sleep(poll_seconds)

    def run_once(self) -> int:
        """Process the current queue snapshot once; return tasks handled.

        One page, one task at a time, fully (claim → merge → report)
        before the next — sequential by construction (RISK-03). Returns
        the number of tasks whose outcome was **reported** (skipped or
        conflicted claims do not count).
        """
        page = self._queue.pending()
        self._log.info(
            "merge queue polled",
            extra={
                "event": "merge_queue_poll",
                "page_items": len(page.items),
                "has_more": page.next_cursor is not None,
            },
        )
        handled = 0
        for item in page.items:
            if self._handle(item):
                handled += 1
        return handled

    # --- one queue entry -----------------------------------------------------

    def _handle(self, item: QueueItem) -> bool:
        """Claim, merge and report one entry; True when the report landed."""
        project = self._project_for(item)
        if project is None:
            return False
        repo_raw = project.get("repo_path")
        if not isinstance(repo_raw, str) or not repo_raw:
            self._log.error(
                "queue entry's project declares no repo_path — skipping",
                extra={
                    "event": "merge_repo_missing",
                    "task_id": item.id,
                    "project_id": item.project_id,
                },
            )
            return False
        repo_path = Path(repo_raw).resolve()
        if repo_path not in self._allowed_repos:
            # Section 10.2: outside the allowlist the repo is never
            # opened — and never claimed either (checked pre-claim).
            self._log.warning(
                "repo not in the executor allowlist — skipping without claiming",
                extra={
                    "event": "merge_repo_not_allowed",
                    "task_id": item.id,
                    "project_id": item.project_id,
                    "repo_path": str(repo_path),
                },
            )
            return False

        start = self._claim(item)
        if start is None:
            return False

        outcome = self._attempt(item, repo_path, project)
        self._report(item, start.version, outcome)
        return True

    def _project_for(self, item: QueueItem) -> dict[str, Any] | None:
        """The project context payload, or None when it cannot be read."""
        try:
            return self._queue.project(item.project_id)
        except ApiError as exc:
            self._log.error(
                "project context unreadable — skipping queue entry",
                extra={
                    "event": "merge_project_unreadable",
                    "task_id": item.id,
                    "project_id": item.project_id,
                    "error_code": str(exc.code),
                    "retryable": exc.retryable,
                },
            )
            return None

    def _claim(self, item: QueueItem) -> MergeStart | None:
        """POST /merge/{task}/start with one ADR-012 key across retries."""
        key = new_key("merge-start", target=item.id)
        for attempt in range(1, MUTATION_BACKOFF_ATTEMPTS + 1):
            try:
                start = self._queue.start(item, idempotency_key=key)
            except ApiError as exc:
                if exc.code in (ErrorCode.TASK_STATE_CONFLICT, ErrorCode.VERSION_CONFLICT):
                    # Another executor claimed it (or the version moved):
                    # the catalog's designed answer — leave it alone.
                    self._log.info(
                        "claim refused by the catalog — skipping",
                        extra={
                            "event": "merge_claim_conflict",
                            "task_id": item.id,
                            "error_code": str(exc.code),
                        },
                    )
                    return None
                if not exc.retryable or attempt == MUTATION_BACKOFF_ATTEMPTS:
                    self._log.error(
                        "claim failed — skipping queue entry",
                        extra={
                            "event": "merge_claim_failed",
                            "task_id": item.id,
                            "error_code": str(exc.code),
                            "retryable": exc.retryable,
                            "attempt": attempt,
                        },
                    )
                    return None
                self._backoff(exc, attempt=attempt, operation="start")
                continue
            self._log.info(
                "queue entry claimed",
                extra={
                    "event": "merge_claimed",
                    "task_id": item.id,
                    "version": start.version,
                },
            )
            self._journal_write("started", item.id, version=start.version)
            return start
        return None

    def _attempt(
        self, item: QueueItem, repo_path: Path, project: Mapping[str, Any]
    ) -> MergeOutcome:
        """Run the injected merge step; contain unexpected exceptions (T18 path)."""
        self._log.info(
            "merge attempt starting",
            extra={
                "event": "merge_attempt",
                "task_id": item.id,
                "branch_name": item.branch_name,
                "repo_path": str(repo_path),
            },
        )
        try:
            outcome = self._step(item, repo_path, project)
        except Exception as exc:  # noqa: BLE001 - worktree/git failures become T18 reports
            self._log.error(
                "merge step raised — reporting failure (T18 path)",
                extra={
                    "event": "merge_step_failed",
                    "task_id": item.id,
                    "error": f"{type(exc).__name__}: {exc}",
                },
                exc_info=True,
            )
            return MergeOutcome(
                result=RESULT_FAILED, details=f"merge step failed: {type(exc).__name__}: {exc}"
            )
        if outcome.result == RESULT_SUCCEEDED and not outcome.sha:
            # Defensive: a step bug must not reach T17's Guard un-sha'd.
            return MergeOutcome(
                result=RESULT_FAILED, details="merge step returned success without a sha"
            )
        return outcome

    def _report(self, item: QueueItem, version: int, outcome: MergeOutcome) -> None:
        """POST /merge/{task}/result; one key across retries, never a second apply."""
        key = new_key("merge-result", target=item.id)
        for attempt in range(1, MUTATION_BACKOFF_ATTEMPTS + 1):
            try:
                self._queue.report(
                    item,
                    result=outcome.result,
                    sha=outcome.sha,
                    details=outcome.details,
                    version=version,
                    idempotency_key=key,
                )
            except ApiError as exc:
                if not exc.retryable or exc.code in (
                    ErrorCode.TASK_STATE_CONFLICT,
                    ErrorCode.VERSION_CONFLICT,
                ):
                    # The task already left `merging` by another path —
                    # the catalog answered; nothing further to apply.
                    self._log.warning(
                        "report refused by the catalog — nothing applied",
                        extra={
                            "event": "merge_report_conflict",
                            "task_id": item.id,
                            "result": outcome.result,
                            "error_code": str(exc.code),
                        },
                    )
                    self._journal_write("reported", item.id, result="observed-exited")
                    return
                if attempt == MUTATION_BACKOFF_ATTEMPTS:
                    self._log.error(
                        "merge report unconfirmed — stopping for crash recovery",
                        extra={
                            "event": "merge_report_unconfirmed",
                            "task_id": item.id,
                            "result": outcome.result,
                            "idempotency_key": key,
                            "attempt": attempt,
                        },
                    )
                    raise MergeReportError(
                        f"merge result for {item.id} stayed unconfirmed after "
                        f"{MUTATION_BACKOFF_ATTEMPTS} attempts ({exc.code}); "
                        "the task remains merging for MT-3.7-06 reconciliation"
                    ) from exc
                self._backoff(exc, attempt=attempt, operation="result")
                continue
            self._log.info(
                "merge outcome reported",
                extra={
                    "event": "merge_reported",
                    "task_id": item.id,
                    "result": outcome.result,
                    "sha": outcome.sha,
                },
            )
            self._journal_write("reported", item.id, result=outcome.result)
            return

    # --- crash-recovery evidence (MT-3.7-06) --------------------------------

    def _journal_write(self, phase: str, task_id: str, **fields: Any) -> None:
        """Append one durable queue-mutation line (claim settled / report settled).

        A journal write failure must not take down a *live* merge whose
        queue mutations already succeeded — the log line of the same
        event still fired, and the worst case degrades to today's
        unobservable state, never to a fabricated recovery. The error is
        loud, never silent.
        """
        if self._journal is None:
            return
        try:
            if phase == "started":
                self._journal.record_started(task_id, version=int(fields["version"]))
            else:
                self._journal.record_reported(task_id, result=str(fields.get("result", "")))
        except OSError as exc:
            self._log.error(
                "journal write failed — crash recovery may miss this task",
                extra={
                    "event": "merge_journal_write_failed",
                    "task_id": task_id,
                    "phase": phase,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )

    # --- backoff (Section 10.10) ---------------------------------------------

    def _backoff(self, exc: ApiError, *, attempt: int, operation: str) -> None:
        """One exponential backoff sleep, capped, never indefinite."""
        delay = min(
            self._settings.retry_base_delay_seconds * (2 ** (attempt - 1)),
            OUTAGE_BACKOFF_CAP_SECONDS,
        )
        self._log.warning(
            "backend unreachable — backing off",
            extra={
                "event": "merge_outage_backoff",
                "operation": operation,
                "attempt": attempt,
                "delay_seconds": delay,
                "error_code": str(exc.code),
            },
        )
        self._sleep(delay)
