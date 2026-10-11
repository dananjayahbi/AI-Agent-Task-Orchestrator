# MT-1.6-02 — Implement Next-Available Selection Ordered by Priority Then Creation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-02 |
| Title | Implement next-available selection ordered by priority then creation |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-01, FR-TSK-05, GOAL-1 |
| Priority | M |
| Dependencies | MT-1.6-01 (claim transaction and lock helpers) |
| Parent sections | 9.2 (`GET /projects/{pid}/work`), 9.3, 19 (WP-1.6), 20.4, 20.5 |

## Context
Section 9.3's last paragraph: "'Next available' selection (used by `start_work`)
applies the same lock with ordering by priority then creation time, so concurrent
agents receive different tasks automatically." The bridge's `start_work` tool
(WP-2.4) will call this path via `GET /projects/{pid}/work`; selecting the candidate
with the same `FOR UPDATE SKIP LOCKED` discipline means two agents asking
simultaneously are handed different tasks without any coordinator.

## Inputs / Prerequisites
* MT-1.6-01 — claim transaction, lock helpers and in-lock re-validation to reuse.
* Parent plan Section 9.3 — selection ordering rule (priority, then creation time).
* Section 7.2 — Task `priority` enum (`urgent` / `high` / `medium` / `low`) and
  `created_at`; Section 9.2 — `GET /projects/{pid}/work` accepts `role` and filters.
* Section 19 (WP-1.6 deliverable): "'next available' selection".
* WP-1.4 — list filters and priority/FIFO ordering exist for plain reads; this task
  adds the locking, claim-integrated variant.

## Scope (in)
* Implement the next-available candidate query: tasks in `pending` for the caller's
  project (project resolved from the token, Section 9.3 step 1), ordered by priority
  (`urgent` > `high` > `medium` > `low`) then `created_at` ascending, honoring
  dependency-completion and project-active filters.
* Apply `FOR UPDATE SKIP LOCKED` while evaluating candidates so concurrent selectors
  never block or pick the same row; a selected candidate is then claimed through the
  MT-1.6-01 transaction (single round trip, no state between select and claim).
* Surface the filter parameters required by Section 9.2 (`role`, state/priority
  filters) for the work-list read path used by the bridge.
* Tests: deterministic ordering by priority then creation; two concurrent selectors
  receive different tasks; filters exclude unmet-dependency and non-active-project
  tasks.
* Add a WP changelog note.

## Out of scope
* The HTTP endpoint and response contract — MT-1.6-07 wires this into
  `GET /projects/{pid}/work`.
* The bridge `start_work` tool — WP-2.4 (consumes this).
* Concurrency-limit accounting — MT-1.6-06.
* Worktree/repo placement decisions — WP-2.10 (OQ-03).
* Owner-facing task list ordering — WP-1.4 `MT-1.4-04` (separate, non-locking path).

## Target paths
* `backend/apps/leases/` (next-available selection using claim lock helpers)
* `backend/tests/` (ordering and concurrent-selection tests)
* WP changelog entry

## Acceptance criteria
- [ ] Candidate ordering is exactly priority (`urgent`→`low`) then `created_at`
  ascending, per Section 9.3 (no other sort keys introduced).
- [ ] Selection and claim happen under one `SKIP LOCKED` lock — two concurrent
  selectors never receive the same task (FR-LEA-01).
- [ ] Only `pending` tasks of the caller's token project, with completed
  dependencies, in `active` projects are eligible (Section 8.2 T4 guards).
- [ ] A project with no eligible task returns an empty result (the bridge maps it to
  its no-work response; no error invented here).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k next_available -q` against real Postgres and confirm the
priority-then-creation order, dependency/project filters, and that two concurrent
selections return disjoint tasks; full suite stays green.

## Attachments
* [Section 9.3 — Claim algorithm and next-available selection](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Agent work endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Priority ordering across many equal-priority tasks must be stable — tie-break only
  by `created_at` as the plan states; if fairness/starvation concerns appear, raise
  an OQ instead of adding hidden randomization.
* Combining "list for display" and "select for claim" in one query risks showing a
  task that is gone by render time — keep the display list non-locking (WP-1.4) and
  the claim selection locking; document the distinction.
