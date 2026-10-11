# MT-6.2-01 — Automate Daily Database Backups

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.2-01 |
| Title | Automate daily database backups |
| Parent WP | WP-6.2 — Backup and restore drill (Milestone M6) |
| Requirements | NFR-05 |
| Priority | M |
| Dependencies | WP-0.2 (Compose stack and environment template), beat service scheduled per Section 9.9 |
| Parent sections | 5.2 (NFR-05), 9.9 (backup trigger), 16.1 (services), 16.3 (storage), 16.5 (backup/restore), 19 (WP-6.2), 20.4, 20.5; Appendix A |

## Context
NFR-05 requires a "daily automated database backup and attachment volume backup, with
a documented restore drill", and Section 9.9 already reserves a daily "Backup trigger"
row — "Database dump + media sync (WP-6.2)" — in the beat schedule. Section 16.5
requires the dump to land "to a second location", i.e. outside the Postgres data
volume, so losing the host does not lose the backup. This first slice implements the
database half of that trigger; the media half is MT-6.2-02, scheduling/retention
MT-6.2-03, and the proof of restorability MT-6.2-04.

## Inputs / Prerequisites
* Parent plan Section 9.9 — the backup trigger job row (daily, database dump + media
  sync) that this task makes real.
* Parent plan Section 16.5 — daily Postgres dump to a second location; the weekly
  restore drill this work feeds.
* Parent plan Section 16.1 — the `postgres` service (data volume) and `beat`
  scheduler that invokes the trigger; ADR-003 (Celery worker/beat on Redis).
* Parent plan Section 16.3 — storage abstraction and content-addressed keys (media
  half is MT-6.2-02; this task must not disturb it).
* WP-0.2 — Compose stack and environment template the dump procedure runs against.
* Section 20.4 item 3 — no secrets or environment-specific paths committed.

## Scope (in)
* Implement the database-dump half of the Section 9.9 backup trigger: a beat-scheduled
  job that produces a Postgres dump of the running stack and writes it to a second
  location outside the database data volume (Section 16.5).
* Place the dump procedure under `infra/backup/` (Appendix A reserves this directory)
  with a short README describing what runs, where output goes, and how to invoke it
  manually for verification.
* Wire the job so failure is detectable: a failed or skipped dump must not look like a
  success (non-zero failure surfaced from the job), so it can feed the observability
  work of WP-6.4 rather than failing silently.
* Ensure repeated runs are safe (a second run does not corrupt or truncate the previous
  day's dump) — idempotent daily execution in the spirit of Section 9.9's job notes.
* Add tests covering the job's behavior against the local Compose stack (Section 18
  Integration row) and a changelog note (Section 20.4 item 7).

## Out of scope
* Media/attachment volume backup — MT-6.2-02.
* The schedule matrix and documented retention policy — MT-6.2-03 (this task only
  registers the daily job the plan already fixes).
* Running a restore and recording the drill — MT-6.2-04.
* The retention cleanup job for checkpoints/patches/orphaned files — a different
  Section 9.9 row, not the backup trigger.
* S3-compatible offsite configuration beyond the Section 16.3 configuration-only
  abstraction — the second location is a configured target, not a new storage backend.

## Target paths
* `infra/backup/` — database dump procedure and README
* `backend/` — beat-scheduled backup trigger job wiring and its tests
* WP changelog entry

## Acceptance criteria
- [ ] A daily backup-trigger job performs a Postgres dump when invoked, writing the
  dump to a second location outside the database data volume (Section 9.9 backup
  trigger row; Section 16.5; NFR-05 "daily automated database backup").
- [ ] The dump procedure lives under `infra/backup/` with a README covering manual
  invocation (Appendix A; Section 19 WP-6.2 deliverable "scheduled backup" first half).
- [ ] A failed dump surfaces as a job failure rather than a silent no-op (Section 20.4
  item 1 verifiability; feeds WP-6.4 alerting).
- [ ] Two consecutive runs leave the previous dump intact (idempotent daily execution,
  Section 9.9 discipline).
- [ ] Tests for the job are green in CI (Section 20.4 item 2); no secrets or
  environment-specific paths committed (item 3); changelog note added (item 7).

## Test command
Run the backup job once against local Compose per `infra/backup/README.md` and confirm
a fresh dump file exists in the second location with a non-zero size and today's
timestamp; then run `pytest backend/tests/ -k backup -v` and confirm the job tests
pass, including the failure-surfacing case.

## Attachments
* [NFR-05 — Recoverability](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (backup trigger)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.5 — Backup, restore, upgrades](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan fixes "second location" but not which kind — a host path, mounted volume,
  or S3-compatible target (Section 16.3). Choose the simplest that survives losing the
  database volume, record the choice in the README/changelog; it must not live inside
  the volume being backed up.
* Postgres dumps that are never restored are false confidence — MT-6.2-04 proves the
  dump loads; until that drill passes, do not describe the backup as verified (Section
  20.4 item 1).
* Backup output can contain the whole database, including hashed tokens and audit
  rows — treat dump locations as sensitive, keep them out of Git and out of the media
  volume (Section 12.4; Section 20.4 item 3).
