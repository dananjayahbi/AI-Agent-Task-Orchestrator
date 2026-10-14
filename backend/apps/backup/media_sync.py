"""Media sync half of the Section 9.9 backup trigger (MT-6.2-02; NFR-05).

Mirrors the media volume (``MEDIA_ROOT``) into the same second-location
backup root the database dump uses (``BACKUP_ROOT/media``), so one target
directory holds everything a restore needs (Section 16.5: "daily Postgres
dump **and media sync** to a second location").

Recorded choices (MT-6.2-02; Section 16.3):

* **Incremental by content-addressed key** — storage keys are derived from
  the content hash and immutable once written (MT-1.11-01), so an object
  already present in the target at the same size is skipped: re-running the
  sync never rewrites unchanged objects and never duplicates or clobbers
  them. Mismatched size re-copies (a target file can only be a partial
  artifact of an interrupted manual copy — the sync itself writes via
  temp + ``os.replace``, so a published target object is always complete).
* **In-progress writes are never read** — the local backend writes temp
  files named ``.put-*`` inside the destination directory and renames them
  into place (MT-1.11-01); the sync skips every dot-prefixed entry, so a
  half-written upload can never be captured.
* **No deletion, ever** — the target accumulates; pruning the second
  location is the retention step's job with the documented policy
  (MT-6.2-03), never the sync's. An over-eager sync that deleted
  "extra" target files could silently turn the backup into a mirror of a
  corrupted volume (MT-6.2-02 risk note).
* **Failure is loud** — any copy error raises
  :class:`~apps.backup.exceptions.BackupError` so the Celery task fails
  (Section 20.4 item 1).
"""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .exceptions import BackupError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyncReport:
    """Outcome of one media sync (counts and bytes only)."""

    copied_files: int
    copied_bytes: int
    skipped_files: int


def media_backup_dir() -> Path:
    """Directory the media mirror lands in, under the configured backup root."""
    return Path(settings.BACKUP_ROOT) / "media"


def sync_media() -> SyncReport:
    """Incrementally mirror ``MEDIA_ROOT`` into ``BACKUP_ROOT/media``.

    Idempotent: a repeat run with no changed objects copies nothing and
    leaves every target file untouched.
    """
    source_root = Path(settings.MEDIA_ROOT)
    target_root = media_backup_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    copied_files = 0
    copied_bytes = 0
    skipped_files = 0
    try:
        for source_path in sorted(source_root.rglob("*")):
            if not source_path.is_file():
                continue
            relative = source_path.relative_to(source_root)
            # In-progress temp files are dot-prefixed (module docstring); a
            # dot anywhere in the relative path can never be a storage key.
            if any(part.startswith(".") for part in relative.parts):
                continue
            target_path = target_root / relative
            source_size = source_path.stat().st_size
            if target_path.exists() and target_path.stat().st_size == source_size:
                # Content-addressed and immutable: same key + same size means
                # the bytes are already backed up (Section 16.3).
                skipped_files += 1
                continue
            target_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = target_path.parent / f".{target_path.name}.sync-tmp"
            try:
                shutil.copyfile(source_path, temp_path)
                os.replace(temp_path, target_path)
            except OSError:
                temp_path.unlink(missing_ok=True)
                raise
            copied_files += 1
            copied_bytes += source_size
    except OSError as exc:
        raise BackupError(f"media sync failed: {exc}") from exc

    logger.info(
        "media sync complete",
        extra={
            "copied_files": copied_files,
            "copied_bytes": copied_bytes,
            "skipped_files": skipped_files,
        },
    )
    return SyncReport(
        copied_files=copied_files,
        copied_bytes=copied_bytes,
        skipped_files=skipped_files,
    )
