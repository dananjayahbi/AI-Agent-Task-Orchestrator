"""Unit tests for the Section 9.9 backup trigger (WP-6.2; NFR-05).

Three service layers plus the Celery wiring, in the order the daily trigger
runs them: database dump (MT-6.2-01), media sync (MT-6.2-02), retention
(MT-6.2-03), then the beat schedule registration. Everything runs hermetic
on the unit layer (Section 18): ``pg_dump`` is never executed — the
subprocess boundary is mocked — and the media tree lives in a tmp_path.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from django.test import override_settings

from apps.backup.dumping import build_pg_dump_command, dump_database
from apps.backup.exceptions import BackupError
from apps.backup.media_sync import sync_media
from apps.backup.retention import prune_old_backups
from apps.backup.tasks import run_daily_backup_task

# --- MT-6.2-01: database dump ------------------------------------------------


def _fake_pg_dump(success: bool = True, writes_bytes: int = 1024) -> Any:
    """A subprocess.run stand-in that writes a dump file like pg_dump would."""

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if success:
            destination = Path(command[command.index("--file") + 1])
            destination.write_bytes(b"\x00dump" * writes_bytes)
        return subprocess.CompletedProcess(
            command,
            0 if success else 1,
            stdout="",
            stderr="permission denied for table auth_user" if not success else "",
        )

    return run


@pytest.fixture()
def backup_root(tmp_path: Path) -> Iterator[Path]:
    """A per-test second-location root, wired into settings."""
    root = tmp_path / "backups"
    with override_settings(BACKUP_ROOT=str(root), MEDIA_ROOT=str(tmp_path / "media")):
        yield root
    Path(tmp_path / "media").mkdir(parents=True, exist_ok=True)


def test_dump_writes_timestamped_file_to_second_location(
    backup_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("apps.backup.dumping.subprocess.run", _fake_pg_dump())
    report = dump_database(now=datetime(2026, 3, 1, 2, 0, 0, tzinfo=UTC))
    assert report.path.parent == backup_root / "database"
    assert report.path.name == "orchestrator-20260301T020000Z.dump"
    assert report.size_bytes > 0


def test_dump_password_travels_via_env_never_argv(
    backup_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = command
        captured["env"] = kwargs["env"]
        Path(command[command.index("--file") + 1]).write_bytes(b"data")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("apps.backup.dumping.subprocess.run", run)
    dump_database(now=datetime(2026, 3, 1, 2, 0, 0, tzinfo=UTC))

    # Section 12.4: the credential never appears in the argv (process lists,
    # logs of the command line), only in the subprocess environment.
    assert all("PGPASSWORD" not in arg for arg in captured["argv"])
    assert "PGPASSWORD" in captured["env"]


def test_consecutive_dumps_keep_both_files(
    backup_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # MT-6.2-01 acceptance: two consecutive runs leave the previous dump
    # intact (idempotent daily execution, Section 9.9 discipline).
    monkeypatch.setattr("apps.backup.dumping.subprocess.run", _fake_pg_dump())
    first = dump_database(now=datetime(2026, 3, 1, 2, 0, 0, tzinfo=UTC))
    second = dump_database(now=datetime(2026, 3, 2, 2, 0, 0, tzinfo=UTC))

    assert first.path.exists() and second.path.exists()
    assert first.path != second.path


def test_failed_pg_dump_raises_and_leaves_no_scratch(
    backup_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Section 20.4 item 1: a failed dump surfaces as a job failure, and the
    # error text is scrubbed (Section 17) before it can reach a log.
    monkeypatch.setattr("apps.backup.dumping.subprocess.run", _fake_pg_dump(success=False))
    with pytest.raises(BackupError, match="pg_dump failed with exit code 1"):
        dump_database(now=datetime(2026, 3, 1, 2, 0, 0, tzinfo=UTC))

    dump_dir = backup_root / "database"
    assert list(dump_dir.iterdir()) == []  # temp file cleaned, nothing published


def test_empty_dump_is_refused(backup_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("apps.backup.dumping.subprocess.run", _fake_pg_dump(writes_bytes=0))
    with pytest.raises(BackupError, match="empty"):
        dump_database(now=datetime(2026, 3, 1, 2, 0, 0, tzinfo=UTC))
    assert list((backup_root / "database").iterdir()) == []


def test_build_command_carries_connection_but_no_password() -> None:
    command = build_pg_dump_command(Path("/tmp/x.dump"))
    assert command[0] == "pg_dump"
    assert "--format=custom" in command
    assert "--no-owner" in command and "--no-privileges" in command
    assert all("PGPASSWORD" not in arg for arg in command)


# --- MT-6.2-02: media sync ---------------------------------------------------


def _seed_media(root: Path) -> None:
    objects = root / "objects" / "ab"
    objects.mkdir(parents=True, exist_ok=True)
    (objects / ("c" * 64)).write_bytes(b"content-addressed object")
    (root / ".put-in-progress").write_bytes(b"half-written upload")


def test_sync_copies_new_objects_and_skips_in_progress(backup_root: Path, tmp_path: Path) -> None:
    media = tmp_path / "media"
    _seed_media(media)

    report = sync_media()
    assert report.copied_files == 1  # the .put- temp file is never read
    backed_up = backup_root / "media" / "objects" / "ab" / ("c" * 64)
    assert backed_up.read_bytes() == b"content-addressed object"
    assert not (backup_root / "media" / ".put-in-progress").exists()


def test_sync_rerun_is_a_noop(backup_root: Path, tmp_path: Path) -> None:
    # Content-addressed keys are immutable (Section 16.3): a repeat run
    # rewrites nothing and reports the object as skipped.
    _seed_media(tmp_path / "media")
    first = sync_media()
    second = sync_media()

    assert first.copied_files == 1
    assert second.copied_files == 0
    assert second.skipped_files == 1


def test_sync_never_deletes_from_second_location(backup_root: Path, tmp_path: Path) -> None:
    # MT-6.2-02 risk note: an over-eager sync can quietly turn a backup into
    # a mirror of a corrupted volume. A target-only file must survive.
    _seed_media(tmp_path / "media")
    sync_media()
    orphan = backup_root / "media" / "objects" / "ff" / "older-object"
    orphan.parent.mkdir(parents=True, exist_ok=True)
    orphan.write_bytes(b"deleted from the volume, still backed up")

    sync_media()
    assert orphan.exists()


def test_sync_recopies_size_mismatch(backup_root: Path, tmp_path: Path) -> None:
    # A same-key shorter file in the target can only be a partial artifact of
    # an interrupted manual copy — the sync repairs it.
    media = tmp_path / "media"
    _seed_media(media)
    sync_media()
    target = backup_root / "media" / "objects" / "ab" / ("c" * 64)
    target.write_bytes(b"trunc")

    report = sync_media()
    assert report.copied_files == 1
    assert target.read_bytes() == b"content-addressed object"


def test_sync_failure_surfaces(
    backup_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Section 20.4 item 1: a failed sync is a job failure, not a silent no-op.
    _seed_media(tmp_path / "media")

    def broken_copyfile(src: Any, dst: Any, **kwargs: Any) -> None:
        raise OSError("No space left on device")

    monkeypatch.setattr("apps.backup.media_sync.shutil.copyfile", broken_copyfile)
    with pytest.raises(BackupError, match="media sync failed"):
        sync_media()


# --- MT-6.2-03: retention -----------------------------------------------------


def _write_dump(directory: Path, name: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_bytes(b"dump bytes")
    return path


def test_retention_prunes_only_beyond_floor_and_age(
    backup_root: Path,
) -> None:
    dump_dir = backup_root / "database"
    # 20 daily generations, one per day, ending "now".
    now = datetime(2026, 3, 21, 2, 0, 0, tzinfo=UTC)
    for day in range(20):
        stamp = datetime(2026, 3, day + 1, 2, 0, 0, tzinfo=UTC).strftime("%Y%m%dT%H%M%SZ")
        _write_dump(dump_dir, f"orchestrator-{stamp}.dump")

    # Defaults: RETENTION_DAYS=14, MIN_KEEP=7 → days 0..13 (age <= 14) kept;
    # nothing else exists to prune. Now age out everything but the newest 10.
    with override_settings(BACKUP_RETENTION_DAYS=10, BACKUP_MIN_KEEP=7):
        report = prune_old_backups(now=now)

    # 20 dumps: days 0..9 are <= 10 days old → kept; days 10..19 are older but
    # the newest 7 (days 0..6) are already inside the age window, so pruned
    # are days 10..19 = 10 files.
    assert len(report.deleted) == 10
    remaining = sorted(p.name for p in dump_dir.iterdir())
    assert len(remaining) == 10


def test_retention_never_prunes_newest_n_regardless_of_age(
    backup_root: Path,
) -> None:
    # MT-6.2-03 risk note: a pruning bug must never destroy the only recent
    # copies — even a huge age window spares the newest MIN_KEEP.
    dump_dir = backup_root / "database"
    now = datetime(2026, 3, 21, 2, 0, 0, tzinfo=UTC)
    for day in range(5):
        stamp = datetime(2026, 1, day + 1, 2, 0, 0, tzinfo=UTC).strftime("%Y%m%dT%H%M%SZ")
        _write_dump(dump_dir, f"orchestrator-{stamp}.dump")

    with override_settings(BACKUP_RETENTION_DAYS=1, BACKUP_MIN_KEEP=3):
        report = prune_old_backups(now=now)

    # All five are far older than one day; the newest three survive.
    assert len(report.deleted) == 2
    assert len(list(dump_dir.iterdir())) == 3


def test_retention_leaves_unrecognized_files_alone(backup_root: Path) -> None:
    dump_dir = backup_root / "database"
    _write_dump(dump_dir, "orchestrator-20200101T000000Z.dump")
    _write_dump(dump_dir, "orchestrator-20260320T020000Z.dump")  # the newest, spared
    manual = _write_dump(dump_dir, "operator-manual-backup.dump")

    with override_settings(BACKUP_RETENTION_DAYS=1, BACKUP_MIN_KEEP=1):
        prune_old_backups(now=datetime(2026, 3, 21, 2, 0, 0, tzinfo=UTC))

    # The manual file matches no timestamped pattern → retention only ever
    # deletes artifacts it positively recognizes as its own generations.
    assert manual.exists()
    assert (dump_dir / "orchestrator-20260320T020000Z.dump").exists()
    assert not (dump_dir / "orchestrator-20200101T000000Z.dump").exists()


def test_retention_rejects_unusable_configuration(backup_root: Path) -> None:
    # Section 9.10 fail-fast: a typo'd zero must not silently delete every
    # backup on the next scheduled run.
    with override_settings(BACKUP_RETENTION_DAYS=0):
        with pytest.raises(BackupError, match="ORCHESTRATOR_BACKUP_RETENTION_DAYS"):
            prune_old_backups()
    with override_settings(BACKUP_MIN_KEEP=0):
        with pytest.raises(BackupError, match="ORCHESTRATOR_BACKUP_MIN_KEEP"):
            prune_old_backups()


# --- the daily trigger task and its beat schedule -----------------------------


def test_daily_task_runs_steps_in_order_and_reports(
    backup_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    def fake_dump(**kwargs: Any) -> Any:
        calls.append("dump")
        dump_dir = backup_root / "database"
        path = _write_dump(dump_dir, "orchestrator-20260301T020000Z.dump")

        class Report:
            size_bytes = path.stat().st_size

        return Report()

    def fake_sync() -> Any:
        calls.append("sync")

        class Report:
            copied_files = 1
            copied_bytes = 10
            skipped_files = 0

        return Report()

    def fake_prune(**kwargs: Any) -> Any:
        calls.append("prune")

        class Report:
            deleted: tuple[str, ...] = ()
            kept = 1

        return Report()

    monkeypatch.setattr("apps.backup.tasks.dump_database", fake_dump)
    monkeypatch.setattr("apps.backup.tasks.sync_media", fake_sync)
    monkeypatch.setattr("apps.backup.tasks.prune_old_backups", fake_prune)

    summary = run_daily_backup_task.run()
    assert calls == ["dump", "sync", "prune"]
    assert summary["synced_files"] == 1
    assert summary["kept_dumps"] == 1


def test_daily_task_stops_before_retention_when_dump_fails(
    backup_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A broken backup day must not shrink the set of restorable artifacts:
    # retention only runs after dump AND sync succeeded.
    calls: list[str] = []

    def failing_dump(**kwargs: Any) -> Any:
        calls.append("dump")
        raise BackupError("pg_dump failed")

    monkeypatch.setattr("apps.backup.tasks.dump_database", failing_dump)
    with pytest.raises(BackupError):
        run_daily_backup_task.run()
    assert calls == ["dump"]


def test_backup_trigger_registered_on_finalize_with_configured_time() -> None:
    # MT-6.2-03: the Section 9.9 daily entry exists, with the schedule time
    # coming from configuration rather than a literal.
    from django.conf import settings

    from config.celery import app as celery_app
    from config.celery import register_backup_schedule

    register_backup_schedule(celery_app)
    entry = celery_app.conf.beat_schedule["backup-trigger"]
    assert entry["task"] == "backup.run_daily_backup"
    schedule = entry["schedule"]
    assert schedule.hour == {settings.BACKUP_TRIGGER_HOUR}
    assert schedule.minute == {settings.BACKUP_TRIGGER_MINUTE}
