# MT-6.6-02 — Restore Database and Media Backups on the VPS

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.6-02 |
| Title | Restore database and media backups on the VPS |
| Parent WP | WP-6.6 — VPS migration rehearsal and v1 release (Milestone M6) |
| Requirements | NFR-05, NFR-06 |
| Priority | M |
| Dependencies | MT-6.6-01 (VPS provisioned, stack healthy), MT-6.2-01/02 (backups exist), MT-6.2-04 (restore procedure rehearsed locally) |
| Parent sections | 1.4 (success criterion 5), 5.2 (NFR-05, NFR-06), 16.3 (storage), 16.4 (VPS checklist, step 2), 16.5 (backup/restore), 19 (WP-6.6), 20.4, 20.5 |

## Context
Section 16.4 step 2: "Restore the latest database dump and media backup." This is
where the two M6 threads meet — WP-6.2 proved the restore procedure on a fresh local
host (MT-6.2-04), and WP-6.6 now runs that same procedure on the VPS as part of the
GOAL-5 rehearsal. Section 19 (WP-6.6) keeps the deliverables honest: the rehearsal
log continues, and any friction found here becomes a "fix" entry. Because NFR-06
requires the stack to be identical and configured only by environment variables, the
restore must work with the same procedure and only environment-level differences
(media path, storage settings) — a VPS-specific restore procedure would itself be a
finding.

## Inputs / Prerequisites
* MT-6.6-01 — VPS host with the Section 16.1 stack up and health checks green; the
  rehearsal log to append to.
* MT-6.2-04 — the restore procedure (the source of truth for steps) and drill record
  format; this run appends the VPS variant of that evidence.
* MT-6.2-01/02 — latest database dump and media sync in the second location,
  reachable from the VPS (transfer path is part of this task — see scope).
* Parent plan Section 16.3 — media volume semantics (content-addressed keys) so the
  restored media is verifiable object-for-object.
* Parent plan Section 16.5 — "weekly restore drill documented and rehearsed"; this
  is the migration rehearsal's restore, feeding the same discipline.
* Parent plan Section 16.4 step 3 — "Start the stack; run the readiness checks"
  immediately follows the restore and closes this slice.

## Scope (in)
* Transfer the latest backup artifacts to the VPS second-location target (documented
  method, no secrets in transit artifacts or logs), or confirm direct access if the
  second location is already reachable from the VPS — record which.
* Restore the database dump into the VPS Postgres per MT-6.2-04's procedure, then
  restore the media volume contents, adapting only environment-level settings
  (paths/locations per Section 16.4 step 1's storage settings).
* Execute Section 16.4 step 3 as the verification of this slice: start the stack,
  run the readiness checks, and confirm the restored data is what the app sees
  (projects/tasks/attachments present, health green).
* Verify media integrity per Section 16.3 (content-addressed keys match between
  source backup and restored volume — spot-check or count, recorded).
* Append to the rehearsal log: artifacts used (identifiers/ages), transfer method,
  steps executed from the restore procedure, readiness results, deviations and fixes
  (Section 19 WP-6.6 deliverables "rehearsal log, fixes").
* Changelog note (Section 20.4 item 7).

## Out of scope
* Creating the backups — MT-6.2-01/02; local drill — MT-6.2-04 (this reuses their
  procedure; it does not rewrite it).
* Tunnel, manifests and token reissue — MT-6.6-03.
* The full smoke suite — MT-6.6-04 (readiness checks here are the step-3 gate; the
  scenario suite follows).
* Fixing code/Compose to make the restore work — any need for a tracked-file change
  is a blocking config-only finding logged for the owner (Section 1.4 criterion 5).
* Ongoing VPS backup scheduling — not in the Section 16.4 checklist for the
  rehearsal; note it as a follow-up observation rather than expanding scope.

## Target paths
* `docs/plan/` — rehearsal log (appended: restore steps, evidence, findings)
* Host environment (outside Git) — storage settings for restored volumes as needed
  (Section 16.4 step 1 envelope)
* WP changelog entry

## Acceptance criteria
- [ ] The latest database dump and media backup from the second location are restored
  on the VPS following MT-6.2-04's procedure, with only environment-level
  adaptations (Section 16.4 steps 2–3; NFR-05; NFR-06).
- [ ] The stack starts and all Section 16.1 readiness checks pass on restored data
  (Section 16.4 step 3).
- [ ] Media restoration is verified against content-addressed keys (Section 16.3;
  Section 20.4 item 1 — evidence, not assertion).
- [ ] No tracked files were edited for the restore; deviations logged as findings
  (Section 1.4 criterion 5; WP-6.6 "fixes" deliverable).
- [ ] Rehearsal log records artifacts, steps, results and duration (Section 19
  WP-6.6 deliverable; Section 20.4 item 1).
- [ ] No secrets in transfer notes or log (Section 20.4 item 3); changelog note added
  (item 7).

## Test command
After restore, run the Section 16.4 step-3 readiness checks on the VPS (service
health plus `/health/ready`) and confirm application-visible data matches the source
environment (task/attachment counts compared against the pre-transfer source);
verify restored media key counts against the backup manifest; confirm `git status`
on the checkout shows no tracked-file modifications.

## Attachments
* [Section 16.4 — VPS migration checklist (steps 2–3)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.5 — Backup, restore, upgrades](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-05, NFR-06 — Recoverability and Portability](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Restoring into a *running* stack risks the app reading half-restored state —
  follow the procedure's ordering (restore before first app traffic, migrations
  applied via the `migrate` one-shot per Section 16.1) and record the actual order
  in the log.
* The transfer path is the untested link: MT-6.2-04 drilled restore from artifacts
  the local host could already read; getting them to the VPS (size, integrity,
  confidentiality in transit) is new. Verify checksums after transfer and treat the
  artifacts as sensitive data (Section 12.4).
* Count mismatches after restore can be innocent (retention pruned rows) or fatal
  (partial restore) — investigate before marking green; a "close enough" restore
  fails both WP-6.2's and this WP's acceptance (Section 20.4 item 1).
* If the restore procedure needs a VPS-only step, don't fork it — amend the shared
  procedure (MT-6.2-04's document) so the next drill and the next migration use one
  truth (Section 20.5).
