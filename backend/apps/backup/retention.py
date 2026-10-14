"""Backup retention step (MT-6.2-03; Section 9.9 sibling of the retention-cleanup job).

The plan fixes daily backups (Section 16.5) but names **no backup
retention period** anywhere — Section 22's OQ-10 covers *data* retention
(events, checkpoints, patches, attachments) and is deferred to M6 with a
recommended default, not a decided one. MT-6.2-03's risk note therefore
prescribes the process for this sibling decision: pick a conservative
default, record it as a decision next to OQ-10, and mark it for
plan-owner confirmation — never silently invent or silently drop it.

The recorded choice (see ``docs/plan/wp-6.2-backup-retention-decision.md``,
flagged for plan-owner confirmation):

* **Database dumps: keep 14 daily generations** (``*_RETENTION_DAYS``,
  default 14) — two weeks survives "noticed the corruption late" while
  bounding the second location's growth. Age is measured from the dump's
  UTC timestamp in its file name (the same clock the dump used).
* **Never prune the newest N** (``*_MIN_KEEP``, default 7) regardless of
  age configuration (MT-6.2-03 risk note: a pruning bug must not be able
  to destroy the only recent copies; a fresh-host drill needs at least a
  week of artifacts to choose from).
* **Media backup is not pruned.** The mirror is content-addressed
  (Section 16.3); objects are immutable and shared, and deletion of
  *data* is the Section 9.9 retention-cleanup job's decision under
  OQ-10 — the backup must not pre-delete what that future policy may
  still need (MT-6.2-02: "do not helpfully prune the second location").
  Growth is bounded by the OQ-10 attachment policy once decided; flagged
  in the decision note.

Pruning runs as the last step of the daily backup trigger, against the
second location only. It never runs before the day's dump and sync have
succeeded (the runner enforces the order): a broken backup day must not
shrink the set of restorable artifacts.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from .exceptions import BackupError

logger = logging.getLogger(__name__)

# Must mirror the name shape produced by dumping.dump_database().
_DUMP_NAME_PATTERN = re.compile(r"\Aorchestrator-(\d{8}T\d{6}Z)\.dump\Z")


@dataclass(frozen=True)
class PruneReport:
    """Outcome of one retention pass (names and counts only)."""

    deleted: tuple[str, ...]
    kept: int


def _dump_timestamp(name: str) -> datetime | None:
    """The UTC timestamp encoded in dump *name*, or ``None`` if unparseable.

    Unparseable files are never deleted — retention only ever touches
    artifacts it positively recognizes as its own generations.
    """
    match = _DUMP_NAME_PATTERN.match(name)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None


def prune_old_backups(*, now: datetime | None = None) -> PruneReport:
    """Delete database dumps older than the retention window, sparing the newest N.

    Raises :class:`BackupError` when the retention configuration is
    unusable (Section 9.10 fail-fast: a typo'd zero must not silently
    delete every backup on the next scheduled run).
    """
    retention_days = settings.BACKUP_RETENTION_DAYS
    min_keep = settings.BACKUP_MIN_KEEP
    if retention_days < 1:
        raise BackupError(f"ORCHESTRATOR_BACKUP_RETENTION_DAYS must be >= 1 (got {retention_days})")
    if min_keep < 1:
        raise BackupError(f"ORCHESTRATOR_BACKUP_MIN_KEEP must be >= 1 (got {min_keep})")

    dump_dir = Path(settings.BACKUP_ROOT) / "database"
    candidates: list[tuple[datetime, str]] = []
    unrecognized: list[str] = []
    for entry in Path(dump_dir).glob("*.dump"):
        timestamp = _dump_timestamp(entry.name)
        if timestamp is None:
            unrecognized.append(entry.name)
            continue
        candidates.append((timestamp, entry.name))
    # Newest first; the timestamp in the name is the ordering key (the dump
    # file name sorts lexicographically in time order, but parse explicitly
    # so an oddly-named file cannot shift the keep window).
    candidates.sort(key=lambda item: item[0], reverse=True)

    reference = now or datetime.now(UTC)
    deleted: list[str] = []
    kept = 0
    for index, (timestamp, name) in enumerate(candidates):
        age_days = (reference - timestamp).total_seconds() / 86400.0
        if index < min_keep or age_days <= retention_days:
            kept += 1
            continue
        try:
            (dump_dir / name).unlink()
        except OSError as exc:
            raise BackupError(f"failed to prune backup {name}: {exc}") from exc
        deleted.append(name)

    logger.info(
        "backup retention pass complete",
        extra={
            "pruned_dumps": len(deleted),
            "kept_dumps": kept,
            "unrecognized_files": len(unrecognized),
        },
    )
    return PruneReport(deleted=tuple(deleted), kept=kept)
