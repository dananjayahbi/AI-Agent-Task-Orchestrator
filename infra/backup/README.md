# Backups — daily dump + media sync (Section 9.9 "Backup trigger"; NFR-05, WP-6.2)

This directory documents the backup procedure the plan reserves here (Appendix A).
The code that runs it lives in `backend/apps/backup/`; the artifacts land on the
host under the second location described below.

## What runs

The daily **Backup trigger** (Section 9.9; registered as beat entry
`backup-trigger`, task `backup.run_daily_backup` in `backend/config/celery.py`)
executes three steps in order:

| Step | Service | What it does |
|---|---|---|
| 1. Database dump | `apps/backup/dumping.py` | `pg_dump --format=custom --no-owner --no-privileges` against the stack's Postgres, written to `<BACKUP_ROOT>/database/orchestrator-<UTC timestamp>.dump` via temp file + atomic rename |
| 2. Media sync | `apps/backup/media_sync.py` | Incremental copy of the media volume (`MEDIA_ROOT`) to `<BACKUP_ROOT>/media/`, skipping in-progress `.put-*` temp files; never deletes |
| 3. Retention | `apps/backup/retention.py` | Prunes dumps older than `ORCHESTRATOR_BACKUP_RETENTION_DAYS`, sparing the newest `ORCHESTRATOR_BACKUP_MIN_KEEP` regardless of age (decision: `docs/plan/wp-6.2-backup-retention-decision.md`) |

Any failure raises `BackupError` and **fails the Celery task** — a broken
backup day never looks like a success (Section 20.4 item 1; feeds WP-6.4
alerting), and retention never runs after a failed dump/sync, so a broken day
cannot shrink the set of restorable artifacts.

The schedule time is configuration (`ORCHESTRATOR_BACKUP_TRIGGER_HOUR`/`_MINUTE`,
UTC), not a literal; both steps and their order are fixed by Section 9.9's
single "Database dump + media sync" row.

## Where output goes — the second location

Section 16.5 requires the backup to land "to a second location" **outside the
database volume and the media volume**, so losing either volume never loses the
backup. The second location is a **host directory**:

| | |
|---|---|
| In-container path (read by the tasks) | `/backups` (`ORCHESTRATOR_BACKUP_ROOT`) |
| Host path (Compose mount, worker service only) | `./backup-data` relative to `infra/compose/`, or `ORCHESTRATOR_BACKUP_HOST_DIR` |
| Database dumps | `<second location>/database/*.dump` (custom format, restored with `pg_restore`) |
| Media mirror | `<second location>/media/...` (same content-addressed keys as the volume) |

The default directory `infra/compose/backup-data/` is git-ignored: dumps carry
hashed tokens and audit rows (Section 12.4) and are treated as sensitive. For
real off-host durability, point `ORCHESTRATOR_BACKUP_HOST_DIR` at a second disk
or network mount — the plan's "second location" is a configured target, not a
vendor choice (S3 remains a Section 16.3 configuration concern).

## Manual invocation (verification)

Prerequisite: the Compose stack is up (including `worker` and `beat`).

```sh
# From the repository root — run the full trigger once and print its summary:
docker compose -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  exec worker celery -A config.celery call backup.run_daily_backup
```

Then confirm both halves landed:

```sh
ls -la infra/compose/backup-data/database/   # a fresh orchestrator-<UTC>.dump, non-zero size
ls -R infra/compose/backup-data/media/       # every media object key, mirrored
```

Re-running the command is safe: each run writes a **new** timestamped dump and
leaves every previous one intact (idempotent daily execution, Section 9.9); the
media sync copies nothing when nothing changed. Running the task when the
second location is unwritable fails loudly instead of writing nothing.

To watch the schedule itself (beat must be running):

```sh
docker compose -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml \
  logs beat | grep -i backup     # beat logs each scheduled dispatch
```

## Schedule and retention (MT-6.2-03)

* **Cadence:** daily (Section 16.5), at `ORCHESTRATOR_BACKUP_TRIGGER_HOUR`:
  `ORCHESTRATOR_BACKUP_TRIGGER_MINUTE` UTC (defaults 02:00 UTC).
* **Retention:** dumps older than `ORCHESTRATOR_BACKUP_RETENTION_DAYS`
  (default 14) are pruned by the third step of the same trigger, **never** the
  newest `ORCHESTRATOR_BACKUP_MIN_KEEP` (default 7) regardless of age. The
  media mirror is not pruned — see the decision note for why. Full rationale
  and its relationship to OQ-10:
  `docs/plan/wp-6.2-backup-retention-decision.md`.
* **Any change to the retention step requires re-running the restore drill**
  (MT-6.2-03 risk note: pruning runs against the second location, where a bug
  destroys the only copies).

## Weekly restore drill (Section 16.5)

The restore drill is **documented and rehearsed weekly**. The procedure and
the drill record live at:

* Procedure: [`docs/runbooks/restore-from-backup.md`](../../docs/runbooks/restore-from-backup.md)
* Drill runner: `e2e/restore_drill.py` (fresh Compose project, empty volumes,
  restore from the second location only, smoke checks, teardown)
* Drill records: `docs/plan/wp-6.2-restore-drill-*.md`

The procedure in the runbook is also the source for the Section 17
"restore from backup" runbook page (MT-6.5-03) and the restore step of the
VPS rehearsal (MT-6.6-02) — Section 20.5 traceability.
