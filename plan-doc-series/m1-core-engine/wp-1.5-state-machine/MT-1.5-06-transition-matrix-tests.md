# MT-1.5-06 — Write the Exhaustive Transition Matrix Tests (Legal + Illegal Pairs)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-06 |
| Title | Write the exhaustive transition matrix tests (legal + illegal pairs) |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-03, FR-TSK-04, NFR-01 |
| Priority | M |
| Dependencies | MT-1.5-02, MT-1.5-03, MT-1.5-04, MT-1.5-05 (transitions and history model in place) |
| Parent sections | 8.1, 8.2, 8.3, 18, 19 (WP-1.5), 20.4, 20.5 |

## Context
WP-1.5's acceptance is explicit: every legal transition has a passing test; every
illegal pair returns `TASK_STATE_CONFLICT`; direct writes to `state` outside the
service are blocked by a test or lint rule. Section 18 requires table-driven tests
for every transition in Section 8.2 and sets an 85% coverage target on the state
machine. This micro-task is the WP's proof: one exhaustive matrix over the six
canonical states and the transitions WP-1.5 registers, with stubbed rows marked as
such for later WPs.

## Inputs / Prerequisites
* MT-1.5-01 … MT-1.5-05 — framework, owner transitions (T2, T3, T19), system
  transitions (T5, T9), agent stubs (T4, T6, T7, T8), history model.
* Parent plan Section 8.2 — the authoritative legal-pair list; Section 8.1 — the six
  canonical states; Section 8.3 — invariants.
* Section 18 — unit layer (table-driven) and 85% state-machine coverage target.
* A test database with real Postgres per Section 18 (concurrency layer is WP-1.6's
  concern; here transactional correctness suffices).

## Scope (in)
* Build a table-driven test module enumerating all state × trigger combinations for
  the transitions registered by WP-1.5: legal pairs assert target state, actor
  acceptance, guard outcomes, side effects and exactly one Transition row; illegal
  pairs assert `TASK_STATE_CONFLICT` (HTTP 409) with zero side effects.
* Cover stub transitions (T4, T6, T7, T8) asserting the not-wired failure path, so
  the matrix is complete today and flip to behavior tests when WP-1.6/WP-2.6 wire
  them.
* Add invariant checks: no transition to `completed` without `merge_status` =
  `merged` (Section 8.3 item 2, subject to OQ-06), no coder lease outside
  `in_progress` (item 1), state values always canonical (ADR-010).
* Add the direct-write guard test (or lint rule) proving code paths outside the
  state-machine service cannot mutate `state` (Section 9.1 dependency rule).
* Record coverage; WP-1.5 reaches the Section 18 85% target for the state machine.
* Add a WP changelog note.

## Out of scope
* Audit/review/merge transitions T10–T18 — matrices extend in WP-3.x; the table
  format here must make that addition a data change, not a rewrite.
* Claim-vs-sweeper and 50-claimant concurrency races — MT-1.6-08 and MT-1.7-05.
* Event catalog completeness across the whole plan — MT-1.9-05.
* Performance benchmarks (NFR-02) — WP-1.15.

## Target paths
* `backend/tests/` (transition matrix, invariant and direct-write test modules)
* Coverage/lint configuration only if the direct-write rule needs a new check
* WP changelog entry

## Acceptance criteria
- [ ] Every legal pair from Section 8.2 registered by WP-1.5 has a passing test with
  asserted side effects and one history row (WP-1.5 acceptance; FR-TSK-04).
- [ ] Every illegal (state, trigger) combination returns `TASK_STATE_CONFLICT` with
  HTTP 409 and no side effects (Section 8.2 rule; catalog code only).
- [ ] Stub transitions are asserted in their not-wired state and clearly marked for
  later WP updates.
- [ ] A direct write to `state` outside the service fails a test or lint rule
  (Section 9.1, WP-1.5 acceptance).
- [ ] State-machine coverage meets the Section 18 target of 85%.
- [ ] CI green (lint, type check, tests — Section 20.4 item 2); changelog note added
  (item 7).

## Test command
Run `pytest backend/tests -k transition_matrix -q` plus the coverage gate
`pytest backend/tests -k transition_matrix --cov=backend.apps.tasks --cov-fail-under=85`
and confirm the matrix reports zero illegal-pair leaks and zero direct-write paths;
CI must be green on the branch.

## Attachments
* [Section 8.2 — Transition table](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The matrix must be generated from the registry, not hand-copied, or it will drift
  from Section 8.2 as WPs add transitions — verify the test enumerates registered
  pairs programmatically.
* T19 (archive flag) and T10/T11/T12/T13 (same-state or flag-affecting rows) do not
  fit a naive from→to matrix — model them explicitly so "illegal pair" counts stay
  honest; any table ambiguity becomes an OQ, not a silent test skip.
* Direct-write detection via lint may need a custom rule — keep it narrowly scoped to
  the Task `state` column to avoid false positives on legitimate field updates.
