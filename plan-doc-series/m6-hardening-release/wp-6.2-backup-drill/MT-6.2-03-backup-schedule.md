# MT-6.2-03 — Schedule Backups with Documented Retention

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.2-03 |
| Title | Schedule backups with documented retention |
| Parent WP | WP-6.2 — Backup and restore drill (Milestone M6) |
| Requirements | NFR-05 |
| Priority | M |
| Dependencies | MT-6.2-01 (database dump), MT-6.2-02 (media sync), MT-0.4 (OQ-10 retention decision context) |
| Parent sections | 5.2 (NFR-05), 9.9 (backup trigger, retention cleanup), 16.5 (backup/restore/upgrade), 19 (WP-6.2), 20.4, 20.5; 22 (OQ-10) |

## Context
NFR-05 requires the backups to be *daily and automated*, and Section 16.5 requires
"Daily Postgres dump and media sync to a second location; weekly restore drill
documented and rehearsed". Sections MT-6.2-01/02 build the dump and sync jobs; this
slice turns them into the schedule the plan specifies and writes down how long backups
are kept and how the weekly drill is repeated — the "documented" half of WP-6.2's
deliverables ("scheduled backup, restore procedure, drill record"). OQ-10 covers data
retention (events, checkpoints, patches, attachments) with a recommended default;
backup retention is a sibling decision that must be recorded explicitly rather than
assumed.

## Inputs / Prerequisites
* MT-6.2-01 and MT-6.2-02 — the dump and media-sync jobs to schedule.
* Parent plan Section 9.9 — beat is the scheduler (ADR-003); backup trigger row says
  daily; retention cleanup is a separate daily row.
* Parent plan Section 16.5 — the schedule contract: daily dump + sync to a second
  location, weekly restore drill documented and rehearsed.
* Parent plan Section 22 OQ-10 — retention decision context (recommended default:
  events 1 year; checkpoints/patches 180 days after completion; attachments until
  archive plus 30 days). Backup retention must be decided alongside it, not invented
  silently — see risk notes.
* Section 20.4 item 3 — no environment-specific paths or secrets in the documented
  schedule/config.

## Scope (in)
* Register both backup jobs on the daily beat schedule the plan already names
  (Section 9.9 "Backup trigger — daily"), with configuration (time window, second
  location target) driven by the environment template rather than hard-coded values.
* Define and document the backup retention policy in `docs/plan/` (or the
  `infra/backup/` README, choosing one home and linking it): how many daily dumps and
  media snapshots are kept, how pruning runs (delegated to a retention step in the
  backup procedure, kept separate from the Section 9.9 retention-cleanup job), and
  how the policy relates to OQ-10's data-retention defaults.
* Document the weekly restore-drill cadence from Section 16.5 ("weekly restore drill
  documented and rehearsed") and link the drill record format MT-6.2-04 will fill.
* Record the schedule and retention in the operator-facing documentation pointer set
  so WP-6.5's setup guide can reference it rather than restate it (Section 20.5).
* Verify the schedule actually fires (a triggered run, not just a config file) and add
  a changelog note (Section 20.4 item 7).

## Out of scope
* Implementing the dump or sync jobs — MT-6.2-01/02.
* Performing the first restore drill and writing its record — MT-6.2-04.
* Deciding OQ-10's data retention for events/checkpoints/attachments — the plan
  owner's call in WP-0.4; this task only aligns backup retention with whatever that
  table holds and flags conflicts.
* The Section 9.9 retention-cleanup job for old checkpoints/patches/orphaned files —
  a distinct existing job.
* Offsite/second-location vendor selection — configuration of the already-chosen
  target only.

## Target paths
* `infra/backup/` — schedule wiring, retention step, backup README (schedule +
  retention + drill cadence documented)
* `docs/plan/` — retention decision note if kept separate (linking OQ-10)
* `backend/` — beat schedule registration/tests if the trigger runs through Celery
  beat
* WP changelog entry

## Acceptance criteria
- [ ] Both the database dump and media sync run on the daily schedule from Section 9.9
  (NFR-05 "daily automated"); schedule parameters come from configuration, not
  literals (Section 16.2/9.10 discipline).
- [ ] A backup retention policy is written down: counts/ages kept, how pruning runs,
  and its relationship to OQ-10's defaults (Section 19 WP-6.2 deliverable "scheduled
  backup"; Section 20.4 item 1 — documented, not implied).
- [ ] The Section 16.5 weekly restore-drill cadence is documented with a pointer to the
  drill record format (Section 19 WP-6.2 "restore procedure").
- [ ] The schedule is demonstrated firing at least once end-to-end (test or triggered
  run), with evidence in the changelog (Section 20.4 item 1).
- [ ] No secrets or environment-specific paths in the schedule/config/docs (Section
  20.4 item 3); tests green in CI (item 2); changelog note added (item 7).

## Test command
Trigger the scheduled backup job through the beat/schedule entry point (documented in
`infra/backup/README.md`) and confirm both a dump and a media sync land in the second
location; run the schedule/retention tests (e.g. `pytest backend/tests/ -k backup
-v`), then grep the backup docs for the retention policy and the weekly drill cadence
terms to confirm both are documented.

## Attachments
* [NFR-05 — Recoverability](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.5 — Backup, restore, upgrades](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 22 — OQ-10 retention open question](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Backup retention is not named anywhere in the plan — only OQ-10's data-retention
  table exists. Pick a conservative default (e.g. keep enough daily points to survive
  noticing corruption late), record it as a decision next to OQ-10, and mark it for
  plan-owner confirmation; do not silently invent a number or silently drop the
  policy.
* Pruning runs against a *second location* — a pruning bug there destroys the only
  copies. Require the drill (MT-6.2-04) to run after any pruning change, and never
  prune the newest N backups regardless of age configuration.
* Beat-scheduled jobs fail quietly when the worker/beat container is down — the
  schedule config alone doesn't prove backups happen; the "fires once" acceptance and
  WP-6.4's sweeper/backup alerting are the countermeasure (Section 17 alerts).
