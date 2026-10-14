# WP-6.2 — Backup and restore drill: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-6.2-01 (daily database backup)** — the Section 9.9 "Backup trigger"
  database half: `backend/apps/backup/` (new app, no models) with
  `dumping.py` running `pg_dump --format=custom --no-owner --no-privileges`
  from the worker against the stack's Postgres into the **second location**
  outside every Docker volume (Section 16.5; NFR-05). Recorded choice (MT
  risk note): the second location is a **host bind mount** — worker-only
  volume `${ORCHESTRATOR_BACKUP_HOST_DIR:-./backup-data}:/backups` in
  `infra/compose/compose.yaml` (default `infra/compose/backup-data/`,
  git-ignored; dumps carry hashed tokens/audit rows — Section 12.4);
  operators point `ORCHESTRATOR_BACKUP_HOST_DIR` at a second disk or network
  mount for real off-host durability — S3 stays a Section 16.3
  configuration concern, not a new storage backend. Credentials travel only
  via `PGPASSWORD` in the subprocess environment, never in argv; failures
  (non-zero exit, empty dump, unwritable target) raise `BackupError` and
  **fail the Celery task** (Section 20.4 item 1), with stderr scrubbed
  (Section 17) before it can reach a log. Idempotent daily execution:
  unique UTC-timestamped name, temp file + `os.replace`, previous dumps
  never truncated (two consecutive runs leave both intact — asserted).
  `backend/Dockerfile` adds `postgresql-client-16` from the PGDG apt
  repository (pg_dump major must be >= the server's `postgres:16`; the
  Debian trixie repository alone ships an older client) so worker/beat and
  any backend-family container can dump or restore. `infra/backup/README.md`
  documents the procedure and manual invocation. Settings add the
  `BACKUP_` Section 9.10 group (`ORCHESTRATOR_BACKUP_ROOT` and the trigger
  names below) and `apps.backup` to `INSTALLED_APPS`; task name
  `backup.run_daily_backup` (thin wrapper over the services, sweeper
  precedent).
- **MT-6.2-02 (media volume backup)** — the media half of the same daily
  trigger: `apps/backup/media_sync.py` mirrors `MEDIA_ROOT` into
  `<BACKUP_ROOT>/media/` leveraging Section 16.3's content-addressed keys —
  an object already present at the same size is skipped, so re-running
  never rewrites or duplicates unchanged objects (asserted: second run
  copies 0, reports skipped). Dot-prefixed entries (the local backend's
  `.put-*` in-progress temp files, MT-1.11-01) are **never read**, so an
  interrupted upload can't be captured (risk note); the sync **never
  deletes** from the second location (risk note: an over-eager sync turns a
  backup into a mirror of a corrupted volume — deletion belongs to the
  retention job under OQ-10). Copy errors raise `BackupError` (surfaced job
  failure). The one daily task (`backup.run_daily_backup`) runs dump →
  sync → retention, and a failure in either half stops the chain — a broken
  backup day never shrinks the set of restorable artifacts.
- **MT-6.2-03 (schedule + retention)** — the daily beat entry
  `backup-trigger` (`config/celery.py`, registered on `on_after_finalize`
  because the time is configuration read through the settings module — the
  module is imported before `DJANGO_SETTINGS_MODULE` resolves on every host
  path; worker and beat both finalize before consuming the schedule) with
  `crontab(hour=ORCHESTRATOR_BACKUP_TRIGGER_HOUR,
  minute=ORCHESTRATOR_BACKUP_TRIGGER_MINUTE)` — UTC (P7,
  `CELERY_TIMEZONE`), defaults 02:00, validated 0–23/0–59 at settings
  import (Section 9.10). **Retention policy recorded** in
  `docs/plan/wp-6.2-backup-retention-decision.md` next to OQ-10 and
  **flagged for plan-owner confirmation** (MT risk note: the plan names no
  backup retention): dumps older than `ORCHESTRATOR_BACKUP_RETENTION_DAYS`
  (default 14) pruned by the trigger's third step
  (`apps/backup/retention.py`, kept separate from the Section 9.9
  retention-cleanup job), **never the newest
  `ORCHESTRATOR_BACKUP_MIN_KEEP` (default 7) regardless of age**; files
  not matching the timestamped dump name are never touched; unusable
  config (`< 1`) fails loudly rather than wiping the location; the media
  mirror is deliberately not pruned (rationale in the decision note —
  bounded by OQ-10's attachment policy once decided). Weekly restore-drill
  cadence (Section 16.5) documented in `infra/backup/README.md` with the
  drill-record pointer. Schedule firing evidenced end-to-end: the drill's
  source stack asserts the beat entry inside the beat container and runs
  the canonical task on a live worker (drill record below);
  `docs/plan/conventions/configuration.md` gains the `BACKUP_` group row
  and the six metadata rows (Section 20.5 operator-docs pointer set).
- **MT-6.2-04 (full restore drill)** — `docs/runbooks/restore-from-backup.md`
  replaces the WP-6.5 stub with the derived procedure (pick artifacts →
  fresh project/empty volumes → `pg_restore --exit-on-error` → media copy →
  full stack → smoke → teardown; failure handling; weekly cadence; the
  drill-record format), explicitly the source for the MT-6.5-03 runbook
  page and the MT-6.6-02 VPS restore step (Section 20.5).
  `e2e/restore_drill.py` (stdlib, like `route_verify.py`) automates the
  whole drill on an isolated Compose project: disposable source stack with
  fresh volumes seeds a marker row + content-addressed media object, runs
  the real `backup.run_daily_backup` task on the live worker, verifies the
  beat entry in-container, tears the source stack **including volumes**,
  then restores into a *new timestamped project* (empty volumes by
  construction) after **proving** freshness (zero public tables, media
  marker absent — the MT's "passed for the wrong reason" risk note), runs
  smoke (`/health/live`, `/health/ready`, `/api/v1/schema`, marker row +
  media object positive controls, worker ping) and writes
  `e2e/restore_drill_results.json` (Section 20.4 item 1 evidence). Drill
  ports (8017/3017) and project names keep it clear of every other stack
  on the host. **Smoke-scope finding (for the Section 18 suite owners,
  per the MT's risk note — escalate, do not lower the bar):** the
  parent-plan Section 18 scenario suite (happy path, crashed agent,
  escalation, merge conflict, screenshot, cross-project access) did not
  exist at drill time; the drill runs the smoke-level checks the runbook
  documents and the drill record states exactly what ran. Full local drill
  **executed twice on 2026-10-14**: the first run completed every restore
  phase but failed the `marker row restored` check — root-caused to the
  *drill check itself*, not the restore path (Django 5.2's `shell` command
  prints an auto-import banner to stdout, and the check compared the whole
  capture to `1`; the count was the capture's last line and the marker row
  was present — the record documents this finding and fix). Fixed in
  `e2e/restore_drill.py` (`shell --no-imports` + last-line parse, with a
  regression test at `backend/tests/test_restore_drill_marker_check.py`);
  the re-run passed end-to-end — all 15 phases, all 6 smoke checks,
  `"findings": []`. Results and drill record (outcome: pass):
  `e2e/restore_drill_results.json`, `docs/plan/wp-6.2-restore-drill-2026-10-14.md`.
