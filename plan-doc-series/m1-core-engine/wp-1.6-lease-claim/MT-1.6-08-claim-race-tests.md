# MT-1.6-08 — Write Claim Race Tests (50 Concurrent Claimants, Exactly One Winner)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-08 |
| Title | Write claim race tests (50 concurrent claimants, exactly one winner) |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-01, NFR-01, NFR-12 |
| Priority | M |
| Dependencies | MT-1.6-01 … MT-1.6-07 (claim path and endpoints complete) |
| Parent sections | 9.3, 18 (Concurrency layer), 19 (WP-1.6), 20.4, 20.5 |

## Context
WP-1.6's acceptance is the plan's headline correctness test: "NFR-01 test passes (50
concurrent claims, exactly one winner); late owner calls return `LEASE_EXPIRED` after
reclaim." NFR-01 demands zero duplicate claims under at least 50 concurrent claim
attempts on one task, verified by test, on real Postgres with multiple connections
(Section 18 concurrency layer). This micro-task is that proof — the suite that keeps
GOAL-2 ("no two agents can ever work the same task") honest forever.

## Inputs / Prerequisites
* MT-1.6-01 … MT-1.6-07 — complete claim/release/selection/fencing/limit path and
  endpoints.
* Parent plan Section 9.3 — the algorithm under test; Section 18 — concurrency test
  requirements (real Postgres, multiple connections).
* NFR-01 (correctness), NFR-12 (idempotency: double submit with same idempotency
  key is listed in the Section 18 concurrency row).
* CI Postgres service from the WP-0.3 test jobs (MT-0.3-02).

## Scope (in)
* Write the 50-claimant race test: 50 concurrent connections (threads/processes with
  separate DB sessions) POST `claim` on one `pending` task; assert exactly one 200,
  49 rejections with `TASK_ALREADY_CLAIMED` (or an empty-selection outcome for the
  next-available variant), and a single final lease with one Transition/Event pair.
* Write the next-available race variant: 50 claimants against a small set of
  `pending` tasks; assert no task is double-claimed and winners are disjoint
  (Section 9.3 "concurrent agents receive different tasks automatically").
* Write the claim-vs-release and release-vs-claim interleavings at the limit
  boundary, asserting invariants from Section 8.3 hold after every run.
* Write the late-owner test: claim, force expiry and sweeper-style reclaim, then the
  original owner's mutating call returns `LEASE_EXPIRED` and changes nothing
  (fencing end-to-end; the sweeper itself arrives in WP-1.7 — drive expiry directly
  here).
* Write the idempotency race: two simultaneous identical claim requests with the
  same idempotency key yield one lease (NFR-12).
* Make the suite deterministic enough for CI (retries only where flakiness is
  inherent; investigate, never mask, failures) and record runtime in the changelog.
* Add a WP changelog note.

## Out of scope
* Claim-vs-sweeper and dead-worker reclaim chaos — MT-1.7-05.
* Checkpoint-vs-expiry race — WP-1.15 (listed in Section 18; reuses this harness).
* Performance targets (NFR-02) — WP-1.15 performance suite.
* 20-agent load scenarios — Section 18 performance layer, WP-6.3.

## Target paths
* `backend/tests/` (concurrency/race test modules; shared race harness)
* WP changelog entry

## Acceptance criteria
- [ ] The 50-concurrent-claim test passes repeatedly: exactly one winner, 49
  canonical rejections, one lease, one history row, one event (NFR-01, FR-LEA-01).
- [ ] The next-available race yields no duplicate assignment across tasks
  (Section 9.3).
- [ ] The late-owner test returns `LEASE_EXPIRED` after reclaim with zero writes
  (WP-1.6 acceptance).
- [ ] The same-idempotency-key race produces exactly one lease (NFR-12).
- [ ] Tests run against real Postgres with multiple connections (Section 18) and are
  wired into the CI test job (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k claim_race -q` against the CI Postgres service (50
claimants, next-available race, idempotency race, late-owner fencing) and repeat
three times to confirm stability; CI must be green on the branch.

## Attachments
* [Section 18 — Testing and Quality Strategy (Concurrency row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.3 — Claim algorithm](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Concurrency tests are the classic flake source — use real barriers (start
  simultaneously), not staggered sleeps; a "passing" race test that never actually
  overlaps connections is worse than none, so assert connection count in the test.
* 50 sessions against one Postgres may hit CI connection limits — size the CI
  service accordingly (MT-0.3-02) rather than lowering the count below NFR-01's 50.
* WP-1.7's sweeper will add a new racer; keep the harness reusable so MT-1.7-05
  extends it instead of duplicating it.
