# MT-1.7-05 — Write the Sweeper Chaos Test (Dead Worker Reclaim, Double-Sweeper Safety)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.7-05 |
| Title | Write the sweeper chaos test (dead worker reclaim, double-sweeper safety) |
| Parent WP | WP-1.7 — Lease sweeper and retry policy (Milestone M1) |
| Requirements | FR-LEA-04, FR-LEA-05, FR-LEA-07, NFR-01, NFR-04 |
| Priority | M |
| Dependencies | MT-1.7-02, MT-1.7-03, MT-1.7-04 (sweeper, escalation, warning complete) |
| Parent sections | 6.5 (Flow B), 8.6, 18 (Concurrency + Chaos rows), 19 (WP-1.7), 20.4, 20.5 |

## Context
WP-1.7's acceptance is a chaos statement: "simulated dead worker returns task to
`pending` within lease plus 60 s; running two sweepers concurrently produces one
transition; after `max_retries` the task is in `in_human_review` with
`retry_exhausted`." Section 18 lists the concurrency trio — claim vs sweeper race,
checkpoint vs expiry race, double submit with same idempotency key — on real
Postgres, and the chaos layer expects "kill worker mid-job … expect no lost state
(NFR-04)". This micro-task is the WP's proof under adversarial timing.

## Inputs / Prerequisites
* MT-1.7-02/03/04 — sweeper, escalation and warning jobs complete and scheduled.
* MT-1.6-08 — race-test harness to reuse (barrier-based concurrency, real Postgres).
* Parent plan Section 18 — concurrency and chaos rows; NFR-04 (no lost state on
  component failure).
* Section 8.6 — expiry/fencing semantics; Section 8.3 — invariants asserted after
  every scenario.

## Scope (in)
* **Dead-worker reclaim:** claim a task, simulate the worker vanishing (no
  checkpoints/releases), advance past `lease_expires_at`, run sweepers; assert the
  task is back in `pending` with `failure_retry_count` + 1, worker cleared, one
  `task.lease_expired` event — within lease + 60 s (WP-1.7 acceptance; model time or
  use short test policy durations rather than real 45-minute waits).
* **Double-sweeper safety:** run two sweepers concurrently over the same expired
  set; assert exactly one T5 per task, one event per task, no lost or duplicated
  increments (FR-LEA-05).
* **Retry-exhaustion path:** loop dead-worker cycles to `max_retries`; assert
  `in_human_review` with `review_reason` = `retry_exhausted` and sweeper ceases
  touching the task (FR-LEA-07, G-10).
* **Claim vs sweeper race:** a claim attempt racing the sweep of an expired lease —
  assert exactly one coherent outcome (reclaim-then-reclaim-by-new-owner, or claim
  rejected) with Section 8.3 invariants intact (NFR-01).
* **Checkpoint vs expiry race:** a checkpoint arriving as the sweeper reclaims —
  assert the late checkpoint is rejected with `LEASE_EXPIRED` and cannot resurrect
  the lease (Section 8.6); full endpoint-level coverage belongs to WP-1.15, harness
  here reuses the same driver.
* After every scenario, assert invariants 1 and 2 (Section 8.3) and that history
  rows match events one-to-one.
* Add a WP changelog note.

## Out of scope
* The 50-claimant suite — MT-1.6-08 (prerequisite harness, not duplicated).
* Kill-worker chaos at the container level and full restart drills — Section 18
  chaos/e2e, WP-1.15 / WP-6.x.
* SSE resume under backend restart — WP-1.10 tests.
* Performance/latency assertions (NFR-02, NFR-03) — WP-1.15 / WP-6.3.
* Bridge mid-submission chaos — Section 18 e2e (WP-2.x / M6).

## Target paths
* `backend/tests/` (chaos/race modules extending the MT-1.6-08 harness)
* WP changelog entry

## Acceptance criteria
- [ ] Dead-worker reclaim test passes: task returns to `pending` within lease + 60 s
  of expiry with correct increments, cleared worker and exactly one
  `task.lease_expired` (WP-1.7 acceptance; FR-LEA-04).
- [ ] Two concurrent sweepers produce exactly one transition per expired task
  (WP-1.7 acceptance; FR-LEA-05).
- [ ] Exhaustion loop lands in `in_human_review` / `retry_exhausted` and the sweeper
  stops touching it (WP-1.7 acceptance; FR-LEA-07).
- [ ] Claim-vs-sweeper and checkpoint-vs-expiry races preserve Section 8.3
  invariants; the late checkpoint gets `LEASE_EXPIRED` with no writes
  (Section 8.6; NFR-04).
- [ ] Suite runs on real Postgres in CI (Section 18) and is deterministic across
  repeated runs (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k sweeper_chaos -q` against CI Postgres three times in a
row — all runs green with identical assertions; full suite (`pytest backend/tests -q`)
stays green.

## Attachments
* [Section 18 — Testing and Quality Strategy (Concurrency, Chaos rows)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 6.5 Flow B — Sweep cycle](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Time-dependent tests are flake-prone — use injectable clocks or compressed policy
  durations (`lease_duration_minutes` small in fixtures); sleeping 45+ minutes is
  unacceptable in CI, and mocking time must not hide real Postgres lock behavior.
* "Within lease plus 60 s" couples sweeper interval and expiry — assert on the job's
  scheduling contract (beat entry) plus a triggered run, not on wall-clock beat
  timing alone; if CI cannot express this reliably, raise an OQ about the test
  strategy rather than weakening the assertion.
