# MT-1.15-01 — Consolidate the Claim Race Test Suite

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-01 |
| Title | Consolidate the claim race test suite |
| Parent WP | WP-1.15 — Core engine hardening (Milestone M1) |
| Requirements | NFR-01 (concurrency semantics), NFR-04 (aligned errors) |
| Priority | M |
| Dependencies | MT-1.6-08 (race harness and runner — do not duplicate), MT-1.2-07 (authorization setup), MT-1.1.01 (state machine), WP-1.7 (sweeper, for later WPs) |
| Parent sections | 9.3 (claim algorithm), 9.2 (error catalog), 18 (testing strategy), 19.1 (WP-1.15 acceptance, first slice), 20.4, 20.5 |

## Context
Section 19's WP-1.15 entry names the first slice "claim races" and accepts the WP when
"the suite runs green in CI, with concurrency tests covering 50 parallel claim attempts
per Section 18." Section 18 fixes the execution context: 50 parallel claim attempts
against **real Postgres** (not mocks — concurrency semantics of the claim algorithm in
Section 9.3 are the thing under test), plus the coverage target for the state machine.
MT-1.6-08 already built the harness — `backend/tests/concurrency/test_claim_race.py`,
the race runner, the deterministic byte range and byte-comparison conditions — and its
doc explicitly says "the WP-1.15 suite adopts it rather than duplicating it." This
micro-task's job is consolidation and completion: adopt the MT-1.6-08 harness into the
WP-1.15 suite, guarantee the 50-attempt/real-Postgres shape runs in CI, and close any
gaps (error-code assertions, listener-channel noise, sequential-claims control).

## Inputs / Prerequisites
* MT-1.6-08 — existing claim race tests and runner (adopt, do not rewrite).
* MT-1.7-05 — sweeper chaos tests (parallel collection; not duplicated here).
* MT-1.2-07 — authorization matrix tests the shared setup must keep working (same
  database, same fixtures).
* MT-1.1-01 — the deterministic state machine these tests assume.
* Parent plan Section 9.3 — claim algorithm and `TASK_ALREADY_CLAIMED` behavior.
* Parent plan Section 18 — 50 parallel claims, real Postgres, CI strategy.

## Scope (in)
* Add the claim-race entry to the WP-1.15 suite manifest/CI job so
  `test_claim_race.py` (and any additional assertions added here) runs as part of the
  hardening suite gate — green-in-CI is the WP acceptance.
* Verify/extend the harness to the exact Section 18 shape: **50** parallel claim
  attempts (parameterized if MT-1.6-08 used fewer), against real Postgres in CI
  (Section 18's containerized-postgres CI path), asserting: exactly one winner; every
  loser receives `TASK_ALREADY_CLAIMED` from the Section 9.2 catalog; persisted state
  after the race is a single `running` claim with one active lease (Section 9.3).
* Assert listener-channel noise is absent during the race (MT-1.6-08's documented
  gap) and add a sequential-claims control test if MT-1.6-08 left it as a gap.
* No behavior changes to the claim path — fixes discovered by the suite are separate
  follow-ups recorded as findings (do not silently alter Section 9.3 semantics here).
* Add the WP changelog note for this slice (Section 20.4 item 7).

## Out of scope
* Sweeper races — MT-1.15-02; idempotency — MT-1.15-03; authorization — MT-1.15-04;
  coverage gates — MT-1.15-05.
* Rewriting MT-1.6-08's harness or MT-1.7-05's chaos tests (adoptment over
  duplication is the entire point — Section 19.6 single-implementation rule).
* Changing the claim algorithm or its error codes — Section 9.3 is the contract.
* Load/stress benchmarks beyond 50 attempts (Section 18 reserves optimization for
  later; NFR-01 thresholds are monitored, not micro-tested).

## Target paths
* `backend/tests/concurrency/test_claim_race.py` (extended assertions if needed)
* WP-1.15 suite entry / CI job wiring (per the repo's existing test selection)
* `backend/tests/concurrency/` shared fixtures (real-Postgres setup already used by
  MT-1.6-08)
* WP-1.15 changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] The claim race suite runs 50 parallel claim attempts against real Postgres and
  passes in CI — Section 18; WP-1.15 acceptance first sentence (NFR-01).
- [ ] Exactly one winner; all 49 losers get `TASK_ALREADY_CLAIMED` from the
  Section 9.2 catalog (Section 9.3; Section 20.4 item 5).
- [ ] Post-race persisted state: one `running` claim, one active lease, no orphaned
  `claimed` rows (Section 9.3; MT-1.1-01 state machine).
- [ ] The suite is part of the WP-1.15 CI gate, green on a clean run — Section 19.1
  acceptance (Section 20.4 items 1–2: test command proof, CI green).
- [ ] MT-1.6-08's harness is adopted, not duplicated; listener-noise and
  sequential-claims gaps closed or explicitly recorded (Section 19.6; Section 18).
- [ ] No secrets or environment-specific paths committed (item 3); changelog note
  added (item 7).

## Test command
`pytest backend/tests/concurrency/test_claim_race.py -v` (CI runs it against the
containerized Postgres per Section 18); then the WP-1.15 suite selection once the
other slices land: `pytest backend/tests/concurrency backend/tests/idsempotency
backend/tests/auth -q`.

## Attachments
* [Section 9.3 — Claim algorithm](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (50 parallel claims)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.15 slices and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* CI flakiness is the main threat to "suite green": if MT-1.6-08's runner relies on
  timing, assert on persisted outcomes (one winner, catalog code) rather than
  scheduling; record any residual flake as a risk instead of retrying silently.
* Real-Postgres-in-CI is mandatory for this slice (Section 18) — a mocked-database
  shortcut would test the mock, not the unique-constraint/lease semantics; do not
  accept `@pytest.mark.skipif(no_postgres)`.
* MT-1.6-08's byte-comparison condition has a known theoretical precision caveat
  (documented in its risk notes) — keep that caveat visible in this suite's comments
  rather than "fixing" the claim algorithm to satisfy the test.
