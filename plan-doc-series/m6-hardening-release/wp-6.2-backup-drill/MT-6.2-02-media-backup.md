# MT-6.2-02 — Automate Media Volume Backups

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.2-02 |
| Title | Automate media volume backups |
| Parent WP | WP-6.2 — Backup and restore drill (Milestone M6) |
| Requirements | NFR-05 |
| Priority | M |
| Dependencies | MT-6.2-01 (database dump half of the backup trigger implemented) |
| Parent sections | 5.2 (NFR-05), 9.9 (backup trigger), 16.1 (services), 16.3 (storage), 16.5 (backup/restore), 19 (WP-6.2), 20.4, 20.5; Appendix A |

## Context
NFR-05 requires an attachment volume backup alongside the database backup, and Section
9.9's backup trigger row is explicitly "Database dump + media sync (WP-6.2)". The
media volume holds attachments and patch artifacts stored through the Section 16.3
storage abstraction with content-addressed keys — content is immutable by key, which
makes the sync naturally incremental: already-backed-up objects need no rewrite. This
slice completes the backup-trigger pair MT-6.2-01 started, so the Section 16.5 "daily
… media sync to a second location" requirement is met.

## Inputs / Prerequisites
* MT-6.2-01 — the database dump half and its `infra/backup/` procedure; this task
  extends the same trigger and documentation rather than creating a parallel path.
* Parent plan Section 16.3 — media volume semantics: content-addressed keys, storage
  abstraction (local volume default, S3-compatible by configuration only).
* Parent plan Section 16.1 — `backend` and `worker` both mount the media volume; the
  sync must capture what the pipeline writes.
* Parent plan Section 9.9 — the daily backup trigger row this completes.
* Parent plan Section 16.5 — daily media sync to a second location; restore drill
  (MT-6.2-04) proves the pair.

## Scope (in)
* Implement the media-sync half of the Section 9.9 backup trigger: a daily sync of the
  media volume to a second location outside that volume (Section 16.5).
* Leverage content-addressed keys (Section 16.3) so the sync is incremental and
  repeatable — re-running does not rewrite unchanged objects and never deletes recent
  data without the documented retention policy (which MT-6.2-03 defines).
* Extend the `infra/backup/` README with the media procedure: what is synced, where it
  lands, how to invoke it manually, and how it pairs with the database dump.
* Make failure detectable the same way as MT-6.2-01 (surfaced job failure, not a
  silent no-op), and ensure the database dump and media sync both run under the one
  daily trigger the plan describes.
* Add tests/verification against the local Compose stack (Section 18 Integration row)
  and a changelog note (Section 20.4 item 7).

## Out of scope
* The database dump itself — MT-6.2-01.
* The schedule matrix and documented retention policy (how many days/generations are
  kept) — MT-6.2-03.
* Running a restore drill of media plus database — MT-6.2-04.
* Implementing the S3-compatible storage backend — Section 16.3 already makes it a
  configuration concern; this task only syncs to the configured second location.
* User-initiated deletion semantics — deletions are retention-job driven only
  (Section 16.3), never part of backup handling.

## Target paths
* `infra/backup/` — media sync procedure and README additions
* `backend/` — backup trigger wiring for the media sync job and its tests
* WP changelog entry

## Acceptance criteria
- [ ] The daily backup trigger performs a media-volume sync to a second location
  outside the volume (Section 9.9 backup trigger row; Section 16.5; NFR-05
  "attachment volume backup").
- [ ] The sync is incremental/idempotent against content-addressed keys: a repeat run
  does not duplicate or clobber unchanged objects (Section 16.3).
- [ ] A failed sync surfaces as a job failure rather than a silent no-op (Section 20.4
  item 1; feeds WP-6.4 alerting).
- [ ] `infra/backup/README.md` documents both halves of the backup trigger — dump and
  media sync — with manual invocation steps (Section 19 WP-6.2 deliverable).
- [ ] Tests green in CI (Section 20.4 item 2); no secrets or environment-specific paths
  committed (item 3); changelog note added (item 7).

## Test command
Seed a few attachments through the local Compose stack, run the media sync per
`infra/backup/README.md`, and confirm every seeded object key appears in the second
location with matching content; re-run the sync and confirm no duplicates or changes;
then run `pytest backend/tests/ -k backup -v` for the trigger tests.

## Attachments
* [NFR-05 — Recoverability](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs (backup trigger)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.3 — Storage](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Media sync that runs while the attachment pipeline is writing must not capture a
  half-written object — content-addressed keys help (objects are immutable once
  written), but verify the sync never reads an in-progress temp file; if it can, order
  the sync after writes or filter by key state and record the rule in the README.
* Backups accumulate: without retention (MT-6.2-03) the second location grows without
  bound — do not ship the sync without the retention task landing in the same WP.
* Do not "helpfully" prune the second location in this task; deletion is the retention
  job's job (Section 16.3), and an over-eager sync can quietly turn a backup into a
  mirror of a corrupted volume.
