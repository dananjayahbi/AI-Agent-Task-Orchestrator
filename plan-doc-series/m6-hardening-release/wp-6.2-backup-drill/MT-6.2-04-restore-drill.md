# MT-6.2-04 — Run and Record a Full Restore Drill

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.2-04 |
| Title | Run and record a full restore drill |
| Parent WP | WP-6.2 — Backup and restore drill (Milestone M6) |
| Requirements | NFR-05 |
| Priority | M |
| Dependencies | MT-6.2-01 (database dump), MT-6.2-02 (media sync), MT-6.2-03 (schedule and retention), Section 18 smoke/e2e suite |
| Parent sections | 5.2 (NFR-05), 16.5 (backup/restore/upgrade), 18 (End-to-end row, Chaos row), 19 (WP-6.2 goal, deliverables, acceptance), 20.4, 20.5 |

## Context
Section 19 (WP-6.2): goal "Automate backups and prove restore", deliverables
"scheduled backup, restore procedure, drill record", acceptance "a fresh host restored
from backups passes the smoke tests". NFR-05 requires "a documented restore drill".
This final slice is the proof: take the backups the earlier slices produced, restore
them onto a fresh/disposable stack, run the smoke tests, and write the drill record.
A backup that has never been restored is a hypothesis, not a backup — this task
converts the WP's hypothesis into evidence, and the same procedure becomes the
Section 17 "restore from backup" runbook input (MT-6.5-03) and the restore step of
the VPS rehearsal (MT-6.6-02).

## Inputs / Prerequisites
* MT-6.2-01/02/03 — working, scheduled database dump and media sync producing
  artifacts in the second location.
* Parent plan Section 16.5 — "weekly restore drill documented and rehearsed"; the
  restore procedure this task documents and rehearses.
* Parent plan Section 18 — the smoke/e2e scenario suite (happy path, crashed agent,
  escalation, merge conflict, text-only with screenshot, cross-project access) that
  the restored stack must pass; the Chaos row's expectations (no lost state, NFR-04).
* Parent plan Section 16.1 — Compose service topology and health checks used to bring
  the fresh stack up.
* WP-6.2 acceptance — "a fresh host restored from backups passes the smoke tests",
  the exact bar this task must demonstrate locally (the VPS variant is WP-6.6).

## Scope (in)
* Write the restore procedure: exact ordered steps to take a fresh environment,
  restore the latest database dump, restore the media volume from the sync target,
  bring up the Section 16.1 stack, and verify readiness — derived by actually doing
  it, not by writing it first.
* Execute the drill on a fresh host or disposable Compose project (empty volumes),
  from the second-location artifacts only — no reliance on the original volumes.
* Run the Section 18 smoke test suite against the restored stack; record the outcome,
  including anything that failed and the fix applied (WP-6.2 acceptance).
* Produce the drill record (`docs/plan/`): date, artifacts used (dump/sync
  identifiers), environment, steps executed, smoke-suite result, duration, findings
  and follow-ups — the WP-6.2 "drill record" deliverable.
* Link the procedure from the `infra/backup/` README and note it as the source for
  the MT-6.5-03 "restore from backup" runbook and MT-6.6-02 VPS restore step
  (Section 20.5 traceability).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Building the backup jobs or the schedule — MT-6.2-01/02/03.
* The VPS restore rehearsal — MT-6.6-02 (same procedure, different host; this drill
  is the local/fresh-host proof the WP acceptance names).
* Publishing the Section 17 runbook page — MT-6.5-03 (consumes this procedure and
  record).
* Automating the drill itself as a recurring CI job — the plan says weekly and
  rehearsed (Section 16.5); automation beyond a documented repeatable procedure is
  not required here (note feasibility in risk notes instead).
* Restoring to the *same* stack in place — the drill must use fresh volumes to prove
  recoverability from the artifacts alone.

## Target paths
* `docs/plan/` — restore procedure and drill record (WP-6.2 deliverables)
* `infra/backup/README.md` — pointer to the restore procedure
* `e2e/` — invocation of the smoke suite during the drill (no new scenarios)
* WP changelog entry

## Acceptance criteria
- [ ] A restore procedure exists documenting the full sequence from artifacts to a
  running, verified stack (Section 19 WP-6.2 deliverable "restore procedure").
- [ ] The drill was executed on fresh/empty volumes using only second-location
  backup artifacts, and the drill record captures date, inputs, steps and outcome
  (Section 19 WP-6.2 deliverable "drill record"; Section 20.4 item 1).
- [ ] The restored stack passes the Section 18 smoke test suite — WP-6.2 acceptance
  "a fresh host restored from backups passes the smoke tests".
- [ ] Findings from the drill are fixed or logged with follow-up ids before closing
  (an unaddressed failure means the acceptance is not met).
- [ ] Procedure is linked from `infra/backup/README.md` as the source for the
  Section 17 restore runbook and the MT-6.6-02 VPS step (Section 20.5).
- [ ] Tests/lint remain green in CI (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
Follow the written restore procedure on a fresh Compose project (empty volumes) from
the current backup artifacts, then run the Section 18 smoke suite entry point against
it (documented under `e2e/`); confirm every scenario passes and the drill record's
outcome row reads pass, with procedure and record present under `docs/plan/`.

## Attachments
* [NFR-05 — Recoverability](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.5 — Backup, restore, upgrades](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (End-to-end, Chaos rows)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.2 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The drill can pass for the wrong reason — e.g. leftover volumes, config still
  pointing at old data, or the stack silently reusing state. Prove freshness before
  restoring (empty volumes, new project name) and state that proof in the drill
  record; otherwise the acceptance is not honestly met.
* A drill that only ever runs moments after a backup proves little — record backup
  artifact age in the drill record, and (per Section 16.5) rehearse weekly so drift
  between backup and restore paths is caught between milestones, not at the next
  incident.
* Secrets are needed to bring the stack up but must never appear in the procedure or
  record — reference the environment template by name (Section 16.2; Section 20.4
  item 3).
* If the smoke suite itself is broken or incomplete at this point, that is a finding
  for the suite's owners, not a reason to lower the bar — record it and escalate
  rather than declaring a partial pass (Section 20.4 item 1).
