"""The executor's durable start/report journal (MT-3.7-06 crash recovery).

Section 19 WP-3.7: "a crash mid-merge recovers cleanly on restart." The
loop's structured logging is *stream* only (``logging.py``: "No log files
or rotation — host-owned", MT-2.1-03), so it cannot be the restart's
evidence; ``GET /merge/pending`` by contract lists only ``pending`` rows
and can never show a task the executor crashed *while* ``merging``.
The missing evidence is therefore the executor's own — a small
append-only JSON Lines journal it writes at the two queue mutations it
performs (claim accepted, result applied/refused):

* one line per event: ``{"task": …, "phase": "started" | "reported", …}``;
* recovery reads it back on the next start, cross-checks each
  started-but-unreported task against live queue state (``task_details``),
  and decides one terminal outcome (ADR-012 — exactly once);
* a partially written last line (the crash shape) is skipped, never a
  parse failure;
* :meth:`MergeJournal.compact` rewrites the journal to the still-open
  entries only, so the file stays bounded — one atomic replace, written
  beside the journal itself (never a foreign directory).

The file lives under the executor's temp root
(``<temp-root>/merge-executor-journal.jsonl``), next to the worktrees it
describes; :func:`journal_path` is the single accessor (tests redirect
the temp root and read the same path back).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Final

from . import worktree

__all__ = ["JOURNAL_FILE_NAME", "MergeJournal", "journal_path"]

#: Under the executor temp root (survives process restarts; the leftover
#: worktree enumerator only ever considers *directories* there).
JOURNAL_FILE_NAME: Final = "merge-executor-journal.jsonl"


def journal_path() -> Path:
    """This host's executor journal location (temp-root scoped, like worktrees).

    Resolved through the :mod:`worktree` module *at call time* so the
    temp root stays a single redirectable seam (tests point it at
    ``tmp_path`` and the journal follows).
    """
    return worktree.temp_worktree_root() / JOURNAL_FILE_NAME


class MergeJournal:
    """Append-only claim/report evidence for restart reconciliation.

    ``path`` is injected (tests point it into ``tmp_path``); all writes
    flush to the OS so a *process* crash leaves the durable line behind
    (the recovery scenario), while a *power* loss may lose the last
    line — which degrades exactly to today's unobservable state, never
    to a fabricated report.
    """

    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        return self._path

    def _append(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def record_started(self, task_id: str, *, version: int) -> None:
        """The claim succeeded (``merge_claimed``): the task is now ``merging``."""
        self._append({"task": task_id, "phase": "started", "version": version, "ts": time.time()})

    def record_reported(self, task_id: str, *, result: str) -> None:
        """The result reached the catalog (or was refused as already applied)."""
        self._append({"task": task_id, "phase": "reported", "result": result, "ts": time.time()})

    def _events(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        events: list[dict[str, Any]] = []
        with self._path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue  # a torn final line from the crash — skip it
                if isinstance(payload, dict) and payload.get("task"):
                    events.append(payload)
        return events

    def unresolved(self) -> dict[str, dict[str, Any]]:
        """Tasks whose latest event is ``started`` (still owed one outcome)."""
        latest: dict[str, dict[str, Any]] = {}
        for event in self._events():
            latest[str(event["task"])] = event
        return {
            task_id: event for task_id, event in latest.items() if event.get("phase") == "started"
        }

    def compact(self, *, keep: tuple[str, ...] = ()) -> None:
        """Rewrite the journal keeping only ``keep`` tasks' events (atomic).

        Recovery calls this once reconciliation finished: resolved tasks
        leave the file, open ones stay (their ``started`` line survives
        for the next restart), and a crash *during* the rewrite leaves
        either the old or the new file — both parseable.
        """
        keep_set = set(keep)
        events = [event for event in self._events() if str(event["task"]) in keep_set]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        staged = self._path.with_suffix(self._path.suffix + ".tmp")
        with staged.open("w", encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, self._path)
