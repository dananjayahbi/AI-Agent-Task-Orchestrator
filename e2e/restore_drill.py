#!/usr/bin/env python3
"""Full restore drill — MT-6.2-04 (WP-6.2; NFR-05).

Proves the WP-6.2 acceptance criterion on a local host: *a fresh host
restored from backups passes the smoke tests*. The drill is fully
self-contained and isolated from every other Compose project:

1. **Source phase** — brings up a disposable stack (project
   ``wp62-drill-src``) with its own fresh volumes, seeds a marker row and a
   media object, then triggers the real Section 9.9 backup task
   (``backup.run_daily_backup``) through the worker — the same task the
   daily beat entry dispatches — and records the artifacts it produced in
   the second location (``infra/compose/backup-data`` by default,
   git-ignored).
2. **Teardown** — destroys the source stack *and its volumes*: what remains
   is only the second-location artifacts (Section 16.5's whole point).
3. **Restore phase** — brings up a second stack under a fresh, timestamped
   project name (empty volumes **by construction** — new project = new
   volumes), *proves* the freshness (zero public tables, no media marker)
   before restoring, then restores the dump with ``pg_restore
   --exit-on-error`` and copies the media mirror back.
4. **Smoke** — HTTP checks (``/health/live``, ``/health/ready``,
   ``/api/v1/schema``) plus the marker controls: the seeded row must be
   absent before the restore (negative control) and present after it
   (positive control) — a drill that passed for the wrong reason (leftover
   volumes, silently re-used state) fails here.
5. **Teardown** (unless ``--keep``) and a JSON results document
   (``e2e/restore_drill_results.json``) — the Section 20.4 item 1 evidence
   the drill record (``docs/plan/wp-6.2-restore-drill-<date>.md``) cites.

Smoke scope is honest: the parent plan's Section 18 scenario suite did not
exist at drill time; these are the smoke-level checks the runbook documents
(``docs/runbooks/restore-from-backup.md`` §6). The record states exactly
what ran (MT-6.2-04 risk note: an incomplete suite is a finding to
escalate, never a reason to lower the bar).

Stdlib only (Python 3.10+), like ``e2e/route_verify.py``. Exit code 0 =
every executed check passed and both phases completed; 1 = any failure
(recorded in the results document either way). Secrets are never printed or
committed: database credentials reach the containers only through
``infra/compose/.env`` (Section 16.2), and the drill passes no secret value
on any command line or into the record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

REPO_ROOT = Path(__file__).resolve().parent.parent
COMPOSE_FILE = REPO_ROOT / "infra" / "compose" / "compose.yaml"
COMPOSE_DEV_FILE = REPO_ROOT / "infra" / "compose" / "compose.dev.yaml"
ENV_FILE = REPO_ROOT / "infra" / "compose" / ".env"
RESULTS_PATH = REPO_ROOT / "e2e" / "restore_drill_results.json"
DEFAULT_BACKUP_DIR = REPO_ROOT / "infra" / "compose" / "backup-data"

SOURCE_PROJECT = "wp62-drill-src"
RESTORE_PROJECT_PREFIX = "wp62-drill-restore"
WAIT_TIMEOUT_SECONDS = 180


class DrillError(RuntimeError):
    """A drill step failed; the results document records where."""


def _utcnow() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(
    cmd: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int = 900,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run *cmd* (never through a shell), capturing output for the record."""
    merged = dict(os.environ)
    if env:
        merged.update(env)
    completed = subprocess.run(  # noqa: S603 - fixed argv, never from input
        cmd,
        cwd=REPO_ROOT,
        env=merged,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        raise DrillError(
            f"command failed ({completed.returncode}): {' '.join(cmd[:8])}...\n{tail}"
        )
    return completed


class Drill:
    """One drill run: phases, timing, evidence."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.started = time.monotonic()
        self.record: dict[str, Any] = {
            "drill": "wp-6.2-restore-drill",
            "started_utc": _utcnow(),
            "backup_dir": str(args.backup_dir),
            "environment": {
                "host_os": platform.system(),
                "python": platform.python_version(),
            },
            "projects": {},
            "artifacts": {},
            "freshness": {},
            "smoke": [],
            "phases": [],
            "findings": [],
            "outcome": "fail",
        }
        # Compose project names allow only [a-z0-9][a-z0-9_-]* — the UTC stamp
        # is lowercase (the trailing Z would violate the charset).
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        self.restore_project = f"{RESTORE_PROJECT_PREFIX}-{stamp}"
        self.record["marker_id"] = f"drill-marker-{stamp}"
        self.record["projects"]["restore_will_be"] = self.restore_project

    # --- plumbing -----------------------------------------------------------

    def compose(self, project: str, *args: str, env: dict[str, str] | None = None) -> str:
        """Run a compose command in *project*; return stdout."""
        cmd = [
            "docker",
            "compose",
            "-p",
            project,
            "--env-file",
            str(ENV_FILE),
            "-f",
            str(COMPOSE_FILE),
            "-f",
            str(COMPOSE_DEV_FILE),
            "--profile",
            "dev",
            *args,
        ]
        overrides = {
            # Isolation from every other stack on this host: drill-owned ports
            # on loopback only (the host .env may bind a LAN address, which
            # would break the 127.0.0.1 smoke checks).
            "ORCHESTRATOR_PORT_BACKEND": str(self.args.backend_port),
            "ORCHESTRATOR_PORT_WEB": str(self.args.web_port),
            "ORCHESTRATOR_BIND_ADDR": "127.0.0.1",
            # The second location the drill writes to and restores from.
            "ORCHESTRATOR_BACKUP_HOST_DIR": str(self.args.backup_dir.resolve()),
        }
        if env:
            overrides.update(env)
        return run(cmd, env=overrides).stdout

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        entry: dict[str, Any] = {"phase": name, "started_utc": _utcnow()}
        began = time.monotonic()
        self.record["phases"].append(entry)
        try:
            yield
        except Exception as exc:  # noqa: BLE001 - recorded, then re-raised
            entry["status"] = "fail"
            entry["error"] = str(exc)[:2000]
            entry["duration_seconds"] = round(time.monotonic() - began, 1)
            raise
        else:
            entry["status"] = "pass"
            entry["duration_seconds"] = round(time.monotonic() - began, 1)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.record["smoke"].append(
            {"check": name, "status": "pass" if ok else "fail", "detail": detail[:500]}
        )
        if not ok:
            raise DrillError(f"check failed: {name}: {detail}")

    # --- phase 1: source stack produces the artifacts ------------------------

    def preflight(self) -> None:
        with self.phase("preflight"):
            if shutil.which("docker") is None:
                raise DrillError("docker is not on PATH")
            if not ENV_FILE.exists():
                raise DrillError(
                    f"{ENV_FILE} missing — the drill needs the documented env file "
                    "template instance (see infra/compose/README.md)"
                )
            # Structural validation of both compose files with the drill's
            # overrides — catches YAML/env errors before any container starts.
            self.compose(SOURCE_PROJECT, "config", "--quiet")
            version = run(["docker", "compose", "version"], check=False).stdout.strip()
            self.record["environment"]["compose"] = version
            if not self.args.skip_build:
                # worker/beat run *image* code (infra/compose/README.md), so the
                # backup task and pg_dump only exist in a freshly built image.
                self.compose(SOURCE_PROJECT, "build", "backend")

    def source_stack(self) -> None:
        marker = self.record["marker_id"]
        with self.phase("source_stack_up"):
            self.compose(
                SOURCE_PROJECT,
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                str(WAIT_TIMEOUT_SECONDS),
            )
            self.record["projects"]["source"] = SOURCE_PROJECT

        with self.phase("seed_markers"):
            # Marker row: a user with an unusable password (no secret material).
            self.compose(
                SOURCE_PROJECT,
                "exec",
                "-T",
                "backend",
                "python",
                "manage.py",
                "shell",
                "-c",
                (
                    "from django.contrib.auth import get_user_model; "
                    f"u = get_user_model().objects.create(username='{marker}'); "
                    "u.set_unusable_password(); u.save()"
                ),
            )
            # Media marker under the content-addressed layout (Section 16.3):
            # key derived from the marker text, written straight into the
            # backend_media volume the backup sync mirrors.
            digest = hashlib.sha256(marker.encode()).hexdigest()
            media_key = f"objects/{digest[:2]}/{digest}"
            self.record["artifacts"]["media_marker_key"] = media_key
            self.compose(
                SOURCE_PROJECT,
                "exec",
                "-T",
                "backend",
                "sh",
                "-c",
                f"mkdir -p /media/objects/{digest[:2]} && printf '%s' '{marker}' "
                f"> /media/{media_key}",
            )

        with self.phase("backup_trigger_run"):
            # The triggered run the MT-6.2-03 acceptance asks for: the exact
            # task name the daily beat entry dispatches, invoked on a live
            # worker (evidence that the job runs, not merely that it is
            # scheduled).
            summary = self.compose(
                SOURCE_PROJECT,
                "exec",
                "-T",
                "worker",
                "celery",
                "-A",
                "config.celery",
                "call",
                "backup.run_daily_backup",
            )
            self.record["backup_task_summary_raw"] = summary.strip()[-2000:]

        with self.phase("beat_schedule_check"):
            # In-container proof that the beat process itself sees the daily
            # entry (config/celery.py registers it on finalize).
            listing = self.compose(
                SOURCE_PROJECT,
                "exec",
                "-T",
                "beat",
                "python",
                "-c",
                (
                    "from config.celery import app; app.finalize(); "
                    "e = app.conf.beat_schedule['backup-trigger']; "
                    "assert e['task'] == 'backup.run_daily_backup', e; "
                    "print(e['schedule'])"
                ),
            )
            self.record["beat_schedule_entry"] = listing.strip()

    def collect_artifacts(self) -> None:
        with self.phase("collect_artifacts"):
            dumps = sorted((self.args.backup_dir / "database").glob("orchestrator-*.dump"))
            if not dumps:
                raise DrillError("backup trigger produced no database dump")
            dump = dumps[-1]
            payload = dump.read_bytes()
            self.record["artifacts"]["dump"] = {
                "name": dump.name,
                "size_bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "mtime_utc": datetime.fromtimestamp(
                    dump.stat().st_mtime, UTC
                ).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            media_key = self.record["artifacts"]["media_marker_key"]
            mirrored = self.args.backup_dir / "media" / media_key
            if not mirrored.exists():
                raise DrillError(f"media sync did not mirror the marker at {media_key}")
            self.record["artifacts"]["media_marker_mirrored"] = True

    def source_teardown(self) -> None:
        with self.phase("source_teardown_with_volumes"):
            # The proof's backbone: nothing but the second location survives.
            self.compose(SOURCE_PROJECT, "down", "-v", "--remove-orphans")

    # --- phase 2: fresh stack restored from the artifacts --------------------

    def restore_stack(self) -> None:
        project = self.restore_project
        with self.phase("restore_stack_up_fresh"):
            # Fresh project name = fresh volumes, networks (Compose contract);
            # only postgres + redis start — migrate must NOT have created the
            # schema before the restore, or the drill would prove nothing.
            self.compose(project, "up", "-d", "--wait", "postgres", "redis")
            self.record["projects"]["restore"] = project
            volumes = run(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ],
                check=False,
            ).stdout.split()
            self.record["freshness"]["restore_volumes"] = sorted(volumes)

        with self.phase("freshness_proof"):
            # Negative control, before any restore byte: the fresh database
            # has no public tables and the media marker is absent.
            tables = self.compose(
                project,
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc '
                "\"select count(*) from pg_tables where schemaname = 'public'\"",
            ).strip()
            self.record["freshness"]["public_tables_before_restore"] = int(tables)
            if tables != "0":
                raise DrillError(
                    f"fresh stack already has {tables} public tables — not a fresh host"
                )
            absence = self.compose(
                project,
                "run",
                "--rm",
                "--no-deps",
                "--no-TTY",
                "--entrypoint",
                "sh",
                "backend",
                "-c",
                f"test ! -e /media/{self.record['artifacts']['media_marker_key']} "
                "&& echo ABSENT",
            )
            if "ABSENT" not in absence:
                raise DrillError("media marker present before restore — not a fresh host")
            self.record["freshness"]["media_marker_before_restore"] = False

        with self.phase("restore_database"):
            dump_name = self.record["artifacts"]["dump"]["name"]
            # PGPASSWORD is sourced from the run container's own env (the
            # image-mandated POSTGRES_PASSWORD the service definition injects);
            # it never appears in argv, in the record, or on the host.
            self.compose(
                project,
                "run",
                "--rm",
                "--no-deps",
                "--no-TTY",
                "-v",
                f"{(self.args.backup_dir / 'database').resolve().as_posix()}:/restore:ro",
                "--entrypoint",
                "sh",
                "postgres",
                "-c",
                'PGPASSWORD="$POSTGRES_PASSWORD" exec pg_restore '
                '--host postgres --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" '
                "--no-owner --no-privileges --exit-on-error "
                f"/restore/{dump_name}",
            )

        with self.phase("restore_media"):
            self.compose(
                project,
                "run",
                "--rm",
                "--no-deps",
                "--no-TTY",
                "-v",
                f"{(self.args.backup_dir / 'media').resolve().as_posix()}:/restore:ro",
                "--entrypoint",
                "sh",
                "backend",
                "-c",
                "cp -a /restore/. /media/",
            )

        with self.phase("restore_stack_full_up"):
            # migrate runs here and must be a no-op: the restored schema is
            # already current (schema/image drift would surface loudly).
            output = self.compose(
                project,
                "up",
                "-d",
                "--wait",
                "--wait-timeout",
                str(WAIT_TIMEOUT_SECONDS),
            )
            self.record["restore_up_output_tail"] = output.strip()[-1500:]

    def smoke(self) -> None:
        base_url = f"http://127.0.0.1:{self.args.backend_port}"
        with self.phase("smoke_http"):
            for path in ("/health/live", "/health/ready", "/api/v1/schema"):
                ok, detail = _http_ok(f"{base_url}{path}")
                self.check(path, ok, detail)

        with self.phase("smoke_data_controls"):
            # Positive control: the marker row survived the artifact round-trip.
            # Django's `shell` prints an auto-import banner to stdout before
            # running -c code ("N objects imported automatically..."), so the
            # capture is parsed to its last non-empty line; --no-imports
            # suppresses the banner at the source (regression: the 2026-10-14
            # run compared the whole stdout and failed a successful restore).
            raw_count = self.compose(
                self.restore_project,
                "exec",
                "-T",
                "backend",
                "python",
                "manage.py",
                "shell",
                "--no-imports",
                "-c",
                (
                    "from django.contrib.auth import get_user_model; "
                    "print(get_user_model().objects.filter("
                    f"username='{self.record['marker_id']}').count())"
                ),
            )
            count = _last_output_line(raw_count)
            self.check(
                "marker row restored",
                count == "1",
                f"marker user count after restore = {count!r} "
                f"(raw stdout: {raw_count.strip()!r})",
            )
            presence = self.compose(
                self.restore_project,
                "exec",
                "-T",
                "backend",
                "sh",
                "-c",
                f"cat /media/{self.record['artifacts']['media_marker_key']}",
            ).strip()
            self.check(
                "media object restored",
                presence == self.record["marker_id"],
                f"media marker content = {presence!r}",
            )
            # Worker liveness on the restored stack (beat/worker are part of
            # the Section 16.1 topology the restored host must reproduce).
            ping = self.compose(
                self.restore_project,
                "exec",
                "-T",
                "worker",
                "celery",
                "-A",
                "config.celery",
                "inspect",
                "ping",
                "--timeout",
                "10",
            )
            self.check("worker ping", "pong" in ping, ping.strip()[-300:])

    # --- orchestration ---------------------------------------------------------

    def run_all(self) -> int:
        failed = False
        try:
            self.preflight()
            self.source_stack()
            self.collect_artifacts()
            self.source_teardown()
            self.restore_stack()
            self.smoke()
        except Exception as exc:  # noqa: BLE001 - recorded, reported, exit 1
            failed = True
            self.record["findings"].append(str(exc)[:2000])
            print(f"DRILL FAILED: {exc}", file=sys.stderr)
        finally:
            if not self.args.keep:
                with self.phase("restore_teardown"):
                    try:
                        self.compose(
                            self.restore_project, "down", "-v", "--remove-orphans"
                        )
                    except DrillError as exc:
                        self.record["findings"].append(f"teardown: {exc}"[:500])
            self.record["finished_utc"] = _utcnow()
            self.record["duration_seconds"] = round(time.monotonic() - self.started, 1)
            self.record["outcome"] = "fail" if failed else "pass"
            RESULTS_PATH.write_text(
                json.dumps(self.record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            print(f"results: {RESULTS_PATH}")
            print(f"outcome: {self.record['outcome']} ({self.record['duration_seconds']}s)")
        return 1 if failed else 0


def _last_output_line(output: str) -> str:
    """Value a ``manage.py shell -c`` command printed, or ``""``.

    The capture is never a bare value: Django's ``shell`` writes an
    auto-import banner to stdout before executing ``-c`` code
    (``N objects imported automatically (use -v 2 for details).``), so the
    printed value is the last non-empty line.
    """
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _http_ok(url: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:  # noqa: S310
            return response.status == 200, f"HTTP {response.status}"
    except (urllib.error.URLError, TimeoutError) as exc:
        return False, str(exc)[:300]


def check_only(args: argparse.Namespace) -> int:
    """Runbook §6 mode: smoke an already-running restored stack over HTTP."""
    base_url = args.base_url.rstrip("/")
    failed = False
    for path in ("/health/live", "/health/ready", "/api/v1/schema"):
        ok, detail = _http_ok(f"{base_url}{path}")
        print(f"{'PASS' if ok else 'FAIL'} {path} ({detail})")
        failed = failed or not ok
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(os.environ.get("ORCHESTRATOR_BACKUP_HOST_DIR") or DEFAULT_BACKUP_DIR),
        help="second location to write to and restore from "
        "(default: infra/compose/backup-data)",
    )
    parser.add_argument(
        "--backend-port",
        type=int,
        default=int(os.environ.get("DRILL_BACKEND_PORT", "8017")),
        help="host port published for the restored backend (default 8017)",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=int(os.environ.get("DRILL_WEB_PORT", "3017")),
        help="host port published for the restored web stub (default 3017)",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="reuse the current backend image (it must already contain "
        "apps.backup and pg_dump — otherwise the drill fails loudly)",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="leave the restored stack running for inspection after the drill",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="smoke an already-running stack over HTTP (runbook §6) and exit",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="backend base URL for --check-only (default: http://127.0.0.1:<backend-port>)",
    )
    args = parser.parse_args()
    if args.check_only:
        if args.base_url is None:
            args.base_url = f"http://127.0.0.1:{args.backend_port}"
        return check_only(args)
    return Drill(args).run_all()


if __name__ == "__main__":
    sys.exit(main())
