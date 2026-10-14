"""Celery task entry point for the Section 9.9 backup trigger (WP-6.2).

Thin wrapper in the ``apps.leases.tasks`` style: all logic lives in the
service modules (``dumping``, ``media_sync``, ``retention``) so unit tests
exercise the services directly and the worker only provides scheduling and
failure reporting. The task name is the canonical one registered on the
daily beat schedule in ``config/celery.py``.

Order matters and is fixed here: dump first, then media sync, then the
retention pass. A failure in either half raises
:class:`~apps.backup.exceptions.BackupError`, which fails the Celery task
(Section 20.4 item 1 — a failed or skipped backup never looks like a
success); the retention pass consequently only ever runs after a
*successful* dump and sync, so a broken backup day can never shrink the set
of restorable artifacts.
"""

from __future__ import annotations

from celery import shared_task

from .dumping import dump_database
from .media_sync import sync_media
from .retention import prune_old_backups


# Celery ships no type hints (pyproject's mypy override ignores its imports);
# the decorator is Any — the service functions it wraps are fully typed,
# which is where the correctness lives.
@shared_task(name="backup.run_daily_backup")  # type: ignore[untyped-decorator]
def run_daily_backup_task() -> dict[str, int]:
    """Section 9.9 "Backup trigger" — daily dump + media sync + retention."""
    dump = dump_database()
    sync = sync_media()
    prune = prune_old_backups()
    return {
        "dump_bytes": dump.size_bytes,
        "synced_files": sync.copied_files,
        "synced_bytes": sync.copied_bytes,
        "skipped_files": sync.skipped_files,
        "pruned_dumps": len(prune.deleted),
        "kept_dumps": prune.kept,
    }
