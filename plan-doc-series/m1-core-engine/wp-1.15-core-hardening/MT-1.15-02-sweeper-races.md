# MT-1.15-02 — Consolidate the Sweeper Race Test Suite

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-02 |
| Title | Consolidate the sweeper race test suite |
| Parent WP | WP-1.15 — Core engine hardening (Milestone M1) |
| Requirements | NFR-01 (concurrency semantics), NFR-04 (aligned errors) |
| Priority | M |
| Dependencies | MT-1.7-05 (chaos harness — do not duplicate), MT-1.7-01 … MT-1.7-03 (sweeper behavior), MT-1.15-01 (suite wiring pattern) |
| Parent sections | 9.3 (leases), 9.7 (sweeper), 9.2 (error catalog), 18 (testing strategy), 19.1 (WP-1.15 second slice), 20.4, 20.5 |

## Context
WP-1.15's second slice is "sweeper races": the expiry/ownership interactions where an
expired lease, a running sweeper, and the owner's own renewal or submission collide.
Section 9.3's lease semantics (expiry, `LEASE_EXPIRED`, `LEASE_NOT_OWNED`) and
Section 9.7's sweeper (reclaim after expiry, worker loops from WP-1.7) are the
behaviors under test; Section 18 requires concurrency proof on real Postgres in CI.
MT-1.7-05 already delivered the harness — `backend/tests/concurrency/test_sweeper_chaos.py`,
`SweeperChaosRunner`, `LeaseScenario`, four scenarios, the unique-constraint-as-
arbiter check, lease-renewal and submission races — and its doc says "The WP-1.15
suite adopts it rather than duplicating it," listing its follow-ups. This micro-task
consolidates that harness into the WP-1.15 CI gate, closes the documented follow-ups
(the `LS-SHORT` scenario gap, shared race-runner scaffolding with MT-1.6-08), and
asserts the catalog error codes.

## Inputs / Prerequisites
* MT-1.7-05 — sweeper chaos runner, `LeaseScenario`, four scenarios, follow-up list
  (adopt; do not duplicate).
* MT-1.7-01 … MT-1.7-03 — sweeper worker, expiry, renewal implementations the tests
  observe.
* MT-1.15-01 — claim-race suite and its CI wiring pattern (share scaffolding where
  MT-1.7-05 flagged it).
* Parent plan Section 9.3 — lease states and `LEASE_*` codes; Section 9.7 — sweeper
  responsibilities; Section 18 — real-Postgres concurrency testing.

## Scope (in)
* Add the sweeper-race entry to the WP-1.15 suite/CI job so the chaos tests run as
  part of the hardening gate (green-in-CI is the WP acceptance).
* Close MT-1.7-05's flagged follow-up: the `LS-SHORT` scenario (lease shorter than
  scan interval, extending the sweeper flag) — verify current sweep-interval
  configurability supports it without a behavior change; if it does not, record the
  limitation rather than altering Section 9.7 semantics in this test task.
* Extract/reuse the common race-runner scaffolding MT-1.7-05 identified as shared
  with MT-1.6-08's runner — one harness module, two suites, no duplicated orchestration
  (Section 19.6 single-implementation rule).
* Assert outcomes with catalog codes only: expired-lease paths surface
  `LEASE_EXPIRED` / `LEASE_NOT_OWNED` as Section 9.3 defines; sweeper double-reclaim
  prevented by the unique-constraint arbiter (no second `running` claim, no exception
  escaping the worker).
* Confirm the no-listener-noise check and sequential-baseline checks from MT-1.6-08's
  gap list apply to sweeper scenarios where relevant.
* Add the WP changelog note for this slice (Section 20.4 item 7).

## Out of scope
* Claim races — MT-1.15-01 (separate suite, shared scaffolding only).
* Idempotency / authorization / coverage gates — MT-1.15-03 … MT-1.15-05.
* Changing sweeper scan intervals, backoff or reclaim logic — Section 9.7 behavior
  changes are follow-ups with their own WPs, not test consolidation.
* The sweeper's own unit tests (MT-1.7-01 … MT-1.7-03 keep ownership of those).

## Target paths
* `backend/tests/concurrency/test_sweeper_chaos.py` (extended assertions / `LS-SHORT`)
* Shared race-runner scaffolding under `backend/tests/concurrency/` (one module used
  by both chaos suites)
* WP-1.15 suite entry / CI job wiring
* WP-1.15 changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Sweeper race scenarios run in CI as part of the WP-1.15 suite, green — Section
  19.1 second slice; Section 18 real-Postgres concurrency requirement (NFR-01).
- [ ] Scenarios assert single-reclaim (unique-constraint arbiter), lease-renewal and
  submission-vs-expiry outcomes with catalog codes `LEASE_EXPIRED` /
  `LEASE_NOT_OWNED` (Section 9.3; Section 20.4 item 5).
- [ ] MT-1.7-05's harness is adopted, not duplicated; shared runner scaffolding with
  the claim suite extracted as flagged (Section 19.6).
- [ ] `LS-SHORT` follow-up closed or explicitly recorded as a limitation in the
  changelog with its rationale (no silent drops).
- [ ] Tests run against real Postgres in CI (Section 18); no secrets or
  environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (item 7).

## Test command
`pytest backend/tests/concurrency/test_sweeper_chaos.py -v` (containerized Postgres
per Section 18); combined gate after MT-1.15-01: `pytest
backend/tests/concurrency -q` green.

## Attachments
* [Section 9.3 — Lease semantics](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.7 — Sweeper](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.15 second slice](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Chaos suites are the most flake-prone in the repo; assert terminal persisted
  invariants (one `running` claim, correct lease owner/expiry), not intermediate
  timing, and keep MT-1.7-05's recorded 30-second threshold visible in test names so
  a threshold change does not silently invalidate expectations.
* Reconciling two suites onto one shared runner can break one suite's assumptions —
  run both chaos files in the same CI job during the refactor and treat any diff in
  MT-1.6-08's outcomes as a regression of that suite, not of the claim code.
* If `LS-SHORT` needs a sweep-interval configuration that does not exist yet, that is
  a plan-level gap: raise a new OQ (`OQ-15+`) rather than hardcoding intervals inside
  the sweeper for the test's benefit.
