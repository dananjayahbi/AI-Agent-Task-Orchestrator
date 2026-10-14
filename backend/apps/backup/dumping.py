"""Database dump half of the Section 9.9 backup trigger (MT-6.2-01; NFR-05).

Runs ``pg_dump`` against the stack's Postgres from the worker container and
writes a custom-format dump to the **second location** — the host-mounted
backup directory (``/backups`` by default), outside the Postgres data volume
(Section 16.5), so losing the database volume never loses the backup.

Recorded choices (MT-6.2-01 risk note; Section 20.1 item 5):

* **Second location = host bind mount** — the simplest target that survives
  losing any Docker volume; operators point ``ORCHESTRATOR_BACKUP_HOST_DIR``
  at a second disk or network mount for real off-host durability. Not inside
  the media volume either (the dump contains hashed tokens and audit rows —
  Section 12.4: dump locations are sensitive and stay out of Git).
* **Custom format (``-Fc``)** — compressed, single file, restored with
  ``pg_restore``; the client major must be >= the server major, so the
  backend image pins ``postgresql-client-16`` to match ``postgres:16``.
* **Credentials via env only** — ``PGPASSWORD`` is passed in the subprocess
  environment, never on the command line, so it can neither appear in logs
  nor in another user's process list (Section 12.4).
* **Idempotent daily execution** — each dump lands under a unique
  UTC timestamp name via a temp file plus ``os.replace``; a second run
  (or a crash mid-run) can never truncate or corrupt a previous dump
  (Section 9.9 discipline).
* **Failure is loud** — a non-zero ``pg_dump`` exit, an empty dump or an
  unwritable target raises :class:`~apps.backup.exceptions.BackupError`, so
  the Celery task fails instead of looking like a success (Section 20.4
  item 1; feeds WP-6.4 alerting).
"""

from __future__ import annotations

import logging
import os
import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings
from django.db import connections

from apps.core.scrub import scrub_text

from .exceptions import BackupError

logger = logging.getLogger(__name__)

_DUMP_SUFFIX = ".dump"


@dataclass(frozen=True)
class DumpReport:
    """Outcome of one database dump (paths and sizes only — never credentials)."""

    path: Path
    size_bytes: int
    duration_seconds: float


def database_dump_dir() -> Path:
    """Directory the dumps land in, under the configured backup root."""
    return Path(settings.BACKUP_ROOT) / "database"


def build_pg_dump_command(destination: Path) -> list[str]:
    """The ``pg_dump`` argv for the configured default database.

    The password is deliberately absent: it travels only through the
    subprocess environment (``run_pg_dump``), never the argv.
    """
    db = connections["default"].settings_dict
    return [
        "pg_dump",
        "--no-password",  # never fall back to an interactive prompt in a worker
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--host",
        str(db["HOST"]),
        "--port",
        str(db["PORT"]),
        "--username",
        str(db["USER"]),
        "--dbname",
        str(db["NAME"]),
        "--file",
        str(destination),
    ]


def run_pg_dump(command: Sequence[str]) -> None:
    """Execute *command* with ``PGPASSWORD`` supplied via environment only.

    Raises :class:`BackupError` on a non-zero exit; the error text carries a
    scrubbed stderr tail (Section 17 token scrubbing) so a misconfigured
    server string can never leak a credential through the failure path.
    """
    env = dict(os.environ)
    env["PGPASSWORD"] = connections["default"].settings_dict["PASSWORD"] or ""
    completed = subprocess.run(  # noqa: S603 - argv is built internally, never from input
        list(command),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr_tail = scrub_text(completed.stderr.strip()[-500:])
        raise BackupError(
            f"pg_dump failed with exit code {completed.returncode}: {stderr_tail or '(no stderr)'}"
        )


def dump_database(*, now: datetime | None = None) -> DumpReport:
    """Produce one timestamped Postgres dump in the second location.

    Safe to run repeatedly: every call writes a fresh unique file and leaves
    all previous dumps untouched (MT-6.2-01 acceptance: two consecutive runs
    keep the earlier dump intact).
    """
    import time

    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    target_dir = database_dump_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / f"orchestrator-{timestamp}{_DUMP_SUFFIX}"
    if final_path.exists():  # same-second re-run: never overwrite an existing dump
        raise BackupError(f"dump target already exists: {final_path.name}")
    temp_path = target_dir / f".{final_path.name}.tmp"

    command = build_pg_dump_command(temp_path)
    started = time.monotonic()
    try:
        run_pg_dump(command)
        size_bytes = temp_path.stat().st_size if temp_path.exists() else 0
        if size_bytes == 0:
            raise BackupError("pg_dump produced an empty file; refusing to publish it")
        os.replace(temp_path, final_path)
    except BackupError:
        temp_path.unlink(missing_ok=True)  # never leave scratch bytes behind
        raise
    duration = time.monotonic() - started

    logger.info(
        "database dump written",
        extra={
            "dump_file": final_path.name,
            "size_bytes": size_bytes,
            "duration_seconds": duration,
        },
    )
    return DumpReport(path=final_path, size_bytes=size_bytes, duration_seconds=duration)
