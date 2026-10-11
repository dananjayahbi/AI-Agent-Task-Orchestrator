# MT-1.4-02 — Implement Atomic Per-Project Task Counter for Gap-Tolerant Ids

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.4-02 |
| Title | Implement atomic per-project task counter for gap-tolerant ids |
| Parent WP | WP-1.4 — Task model, id sequencing and CRUD (Milestone M1) |
| Requirements | FR-TSK-01, NFR-01 (concurrency discipline applied to id allocation) |
| Priority | M |
| Dependencies | MT-1.4-01 (Task model and id constraint), MT-1.3-02 (`task_counter` field on Project) |
| Parent sections | 7.2 (`task_counter`), 7.3, 9.1, 9.3 (lock technique precedent), 19.1 (WP-1.4 acceptance), 20.4, 20.5 |

## Context
Section 7.3 fixes task-id allocation: "inside the creating transaction, the project
row is locked, `task_counter` is incremented, and the id is built from it", rendering
the index with at least 3 digits that grows naturally (`T1000`). FR-TSK-01 requires
ids to be unique **and gap-tolerant** — a failed/rolled-back create may leave a gap,
which is fine; reuse or collision is not. WP-1.4's acceptance states the bar: "100
concurrent creations yield unique, gap-tolerant ids." This task is the allocation
service that MT-1.4-03's create endpoint calls (and that WP-1.5's T1 transition side
effect "Allocate task id" reuses).

## Inputs / Prerequisites
* MT-1.4-01 — Task model whose id column is check-constrained to the pattern.
* MT-1.3-02 — Project `task_counter` integer field.
* Parent plan Section 7.3 — the allocation algorithm, verbatim.
* Parent plan Section 9.3 — precedent for exclusive row locks inside a transaction
  (claim algorithm uses the same discipline; row locking on Postgres is the plan's
  established technique).
* Parent plan Section 18 — concurrency test layer (real Postgres, multiple
  connections).

## Scope (in)
* Implement an id-allocation function/service: within the creating transaction, take
  an exclusive lock on the project row, increment `task_counter`, and build
  `{PID}-T{index:03d+}` from the new value (Section 7.3) — the index format must
  support 3+ digits.
* Ensure gaps are tolerated: a transaction that allocates then fails must not reuse a
  number **in a way that collides**, and must not require sequential perfection —
  document that gaps are expected (FR-TSK-01 "gap-tolerant").
* Expose the allocator as the single creation-path API so MT-1.4-03 (create
  endpoint) and later WP-1.5 (T1 side effect) cannot each roll their own (Section 9.1:
  one owner for sequencing logic in `tasks`).
* Concurrency test: 100 parallel creations against one project produce 100 unique,
  correctly formatted ids with no duplicates and no constraint violations
  (WP-1.4 acceptance; Section 18 concurrency layer with real Postgres).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* The create endpoint wiring — MT-1.4-03 (calls this allocator).
* PID allocation for projects — MT-1.3-01 (different mechanism: database sequence).
* Publish/T1 transition orchestration — WP-1.5 (uses this allocator as a side
  effect).
* Claim/skip-locked semantics — WP-1.6 (that is lease locking, not id locking).
* Repair of historic gaps — never; Section 7.3 tolerates them.

## Target paths
* `backend/apps/tasks/` — id allocation service
* `backend/tests/` — concurrency test (100 parallel creations) and format tests
* WP changelog entry

## Acceptance criteria
- [ ] Allocation follows Section 7.3 exactly: project row locked inside the creating
  transaction, `task_counter` incremented, id built from the counter — no separate
  sequence or UUID scheme.
- [ ] Rendered ids match `{PID}-T{index}` with index ≥ 3 digits and natural growth
  (`T1000`) — FR-TSK-01; Section 7.3.
- [ ] 100 concurrent creations on one project yield 100 unique ids, none violating the
  MT-1.4-01 check constraint (WP-1.4 acceptance; Section 18 concurrency tests).
- [ ] Gaps from failed transactions are documented as expected (FR-TSK-01
  gap-tolerant) — no "fill the gap" logic exists.
- [ ] The allocator is the single allocation entry point (referenced by
  MT-1.4-03/WP-1.5).
- [ ] Concurrency test runs on real Postgres (Section 18) in CI; lint/type green
  (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_task_id_allocation.py` — the 100-parallel-creations
test on real Postgres asserting uniqueness and format, plus serialization tests
(`T001`→`T999`, then `T1000`) and a rolled-back allocation leaves a tolerated gap
without reuse collisions.

## Attachments
* [Section 7.3 — Identifier generation rules](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing (concurrency layer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Lock duration matters: the project row is a hot row for a busy project — keep the
  locked section minimal (increment + build id, inside the caller's transaction) or
  creation throughput becomes the bottleneck; NFR-09 scale (10,000 tasks) should be
  cited if the test reveals contention.
* Deadlock potential with future writers of the Project row (policy PATCH, status
  change, MT-1.3-03) — always acquire the project lock first in a consistent order;
  note this in code comments for WP-1.5/1.6 reviewers.
