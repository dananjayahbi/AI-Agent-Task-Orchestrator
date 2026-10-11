# MT-3.7-07 — Write the merge end-to-end test (success + conflict paths)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-07 |
| Title | Write the merge end-to-end test (success + conflict paths) |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-01 to MT-3.7-06 (whole WP implemented); WP-3.6 complete (approval entry point) |
| Parent sections | 18 (Testing and Quality Strategy), 19 (WP-3.7 acceptance), 8.1, 8.2 (T15, T17, T18), 11.4, 11.5, 20.4, 20.5; ADR-008 |

## Context
Section 19 WP-3.7 acceptance is a three-part end-to-end promise: "successful merge
completes the task; conflict leaves the developer's working tree untouched and
escalates with `merge_conflict`; crash mid-merge recovers cleanly on restart." Unit
tests in MT-3.7-01…06 cover each part in isolation; this micro-task wires the full
path — Owner approves (T15, Section 11.5), queue API, executor, worktree, strategy,
result, state machine — against the real backend per Section 18's integration
approach, and asserts both the success and conflict journeys plus a recovery re-run.

## Inputs / Prerequisites
* Parent plan Section 19 WP-3.7 — the exact acceptance criteria to encode.
* Parent plan Section 18 — testing strategy (integration against real services where
  required; Postgres-backed backend per Section 18).
* Parent plan Sections 8.1–8.2 — merge-pending sub-status note, T15, T17, T18.
* Parent plan Section 11.4–11.5 — executor and human review workflows as the script.
* All MT-3.7-01 … MT-3.7-06 deliverables — the system under test.
* WP-3.6 — the approve endpoint that starts the journey.

## Scope (in)
* An end-to-end test module exercising, against the real backend plus a scratch Git
  repository and the real executor:
  * **Success path:** task escalated to `in_human_review` → Owner approves (T15,
    `merge_status` = `pending`) → executor starts (`merging`) → strategy merge in the
    temp worktree succeeds → result reported → task `completed`, `merge_status`
    merged (T17), `merge.succeeded` + `task.completed` events observed.
  * **Conflict path:** same setup with overlapping changes → conflict aborts → result
    failure → task back to `in_human_review`, `review_reason` = `merge_conflict`
    (T18), `merge.failed` event observed, and the developer's working tree is
    byte-identical before/after (Section 19 WP-3.7 acceptance).
  * **Recovery check:** executor stopped between start and result, restarted, task
    converges to exactly one terminal outcome (MT-3.7-06 contract).
* Assertions on the invariant "never `completed` without `merge_status` = `merged`"
  (Section 8.3 invariant 2, ADR-008).
* Deterministic fixtures: seeded conflict between task branch and default branch;
  no network dependencies beyond the local stack.
* A WP changelog note.

## Out of scope
* Policy Engine/audit portions of the pipeline — covered by WP-3.4 tests; this test
  starts from review approval (Section 11.5 entry point) unless full-stack fixtures
  make the earlier stages cheaper to include (then assert, do not re-test them).
* Mobile/web UI observation of the conflict — WP-4.8 / WP-5.x tests.
* Performance/load testing — Section 18 scale concerns, not WP-3.7.

## Target paths
* `backend/` or `bridge/` integration test module (merge end-to-end suite, location
  per Section 18 layout)
* WP changelog entry

## Acceptance criteria
- [ ] Success path green end to end: approve → pending → merging → merged/completed
  (T15, T17) with `merge.succeeded` observed (Section 19 WP-3.7 acceptance).
- [ ] Conflict path green end to end: T18 applied, `review_reason` = `merge_conflict`
  verbatim, `in_human_review` reached, `merge.failed` observed, developer's working
  tree byte-identical (Section 19 WP-3.7 acceptance; Section 8.4 enum).
- [ ] Crash/restart scenario converges to exactly one terminal outcome per task
  (Section 19 WP-3.7 acceptance; MT-3.7-06 contract).
- [ ] Invariant 2 asserted: no `completed` without `merge_status` = `merged`
  (Section 8.3, ADR-008).
- [ ] The suite runs in CI alongside the existing suites (Section 20.4 item 2) and
  only canonical states/reasons/events are asserted (Sections 8.1, 8.4, 9.6, 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the end-to-end merge suite (for example
`uv run pytest bridge/tests/ -k merge_e2e` with the backend stack up per Section 18)
and confirm success, conflict, and restart-recovery scenarios all pass with the
invariant assertions; then the backend and bridge full suites stay green.

## Attachments
* [Section 19 — WP-3.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.1 — State diagram (merge pending sub-status)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* End-to-end Git tests are OS-sensitive (RISK-15): keep fixtures free of
  path/space/CRLF assumptions and include the suite in the OS matrix where feasible.
* A conflict test that mutates a shared fixture repository will flake — each scenario
  must build its own scratch clone (Section 18 isolation discipline).
* If the suite proves the `manual` path (OQ-06) also needs coverage, add it as a
  follow-up case rather than expanding this task beyond the Section 19 acceptance
  (sizing rule, Section 20.3).
