# MT-1.15-03 — Consolidate the Idempotency Test Suite

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-03 |
| Title | Consolidate the idempotency test suite |
| Parent WP | WP-1.15 — Core engine hardening (Milestone M1) |
| Requirements | NFR-12 (idempotency), NFR-04 (aligned errors) |
| Priority | M |
| Dependencies | MT-1.1-01 (state machine), MT-1.6-08 (claim idempotency harness), MT-1.6-01/MT-1.6-03/MT-1.6-05 (checkpoint/submit actions), MT-1.6-07 (decisions), MT-1.15-01 (suite wiring pattern) |
| Parent sections | 9.3, 9.4 (decision idempotency), 19.1 (WP-1.15 third slice), 19.4 (NFR-12), 18, 20.4, 20.5 |

## Context
NFR-12 is the requirement: "All agent claim, checkpoint, submit, and decision
operations are idempotent (NFR-12)." WP-1.15's third slice is "idempotency," and the
WP acceptance is the suite green in CI. The plan's idempotency semantics live in
Section 9.3 (claim — at-most-once effect under retry), Section 9.4's decision flow
(duplicate decision requests return the stored decision rather than re-executing;
MT-1.6-07 already asserts a duplicate decision's HTTP 409 and terminal persistence),
and the checkpoint/submit paths of Section 9.1/9.4 (retrying a transition already
applied must not double-apply or corrupt the state machine). MT-1.6-08's harness and
MT-1.6-07's duplicate-decision assertions are partial proofs already in the tree; the
WP-1.15 suite consolidates them into one idempotency gate covering all four operation
classes NFR-12 names.

## Inputs / Prerequisites
* MT-1.6-08 — claim race/idempotency harness (adopt its double-claim primitives).
* MT-1.6-01 … MT-1.6-07 — checkpoint, submit, resume and decision endpoints whose
  retry semantics are the subjects; MT-1.6-07 already contains duplicate-decision
  assertions to reuse rather than rewrite.
* MT-1.1-01 / MT-1.1-02 — state machine and transition table these tests validate
  against.
* Parent plan Section 9.3 — claim at-most-once; Section 9.4 — decision idempotency
  and `TASK_STATE_CONFLICT`; Section 9.2 — catalog codes for conflict results.
* Parent plan Section 18 — real-Postgres concurrency/consistency testing.

## Scope (in)
* One idempotency suite covering the four NFR-12 operation classes, each tested as a
  duplicate request (same logical operation replayed concurrently **and**
  sequentially):
  * **claim** — second claim loses with `TASK_ALREADY_CLAIMED`, one lease exists
    (Section 9.3).
  * **checkpoint** — replayed save does not double-append or regress state; file
    bytes and task state unchanged after the duplicate.
  * **submit** — replayed submit yields one transition to `completed`/the Section 9.1
    target state; the duplicate receives a catalog conflict code, not a second
    completion side effect.
  * **decision** — duplicate decision returns the stored decision / `TASK_STATE_CONFLICT`
    per Section 9.4 and MT-1.6-07; no duplicate event emission (Section 9.6 catalog —
    exactly one event per logical decision).
* Extract the duplicate-request helper MT-1.6-08 identified as shared, so all four
  classes drive identical concurrency scaffolding (Section 19.6).
* Assert no duplicate domain events and no orphaned rows after each replay
  (persisted-state checks per Section 18).
* Wire into the WP-1.15 CI gate; changelog note (Section 20.4 item 7).

## Out of scope
* Claim races (50-way) and sweeper races — MT-1.15-01 / MT-1.15-02 (this suite's
  claim case is duplicate-replay, not the 50-attempt race).
* Authorization — MT-1.15-04; coverage gates — MT-1.15-05.
* Implementing or changing idempotency-key mechanisms — NFR-12 fixes discovered by
  the suite are follow-ups, recorded as findings; this task consolidates proof.
* Attachment upload idempotency (dedup-by-checksum is WP-1.12 stage 1, already
  covered by its own tests).

## Target paths
* `backend/tests/idsempotency/` (or the repo's existing home for these tests — place
  beside `backend/tests/concurrency/` per Appendix A layout; keep one suite entry)
* Shared duplicate-request helper under the tests package (extracted from
  MT-1.6-08/MT-1.6-07 assertions)
* WP-1.15 suite entry / CI job wiring
* WP-1.15 changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] All four NFR-12 operations — claim, checkpoint, submit, decision — are proven
  idempotent by duplicate sequential and concurrent replay, green in CI — NFR-12;
  WP-1.15 third slice (Section 19.1).
- [ ] Each replay's conflict result is a Section 9.2 catalog code
  (`TASK_ALREADY_CLAIMED` / `TASK_STATE_CONFLICT` as the flow dictates)
  (Section 20.4 item 5).
- [ ] Exactly one domain event per logical operation after replay (Section 9.6
  catalog); no orphaned rows or double state transitions (Section 18 persisted-state
  assertions).
- [ ] Existing MT-1.6-07 duplicate-decision assertions are adopted, not duplicated
  (Section 19.6).
- [ ] Suite runs on real Postgres in CI as part of the WP-1.15 gate; no secrets or
  environment-specific paths (Section 20.4 item 3).
- [ ] Changelog note added (item 7).

## Test command
`pytest backend/tests/idsempotency -v` (containerized Postgres per Section 18);
combined with the other slices: `pytest backend/tests/concurrency
backend/tests/idsempotency backend/tests/auth -q` green.

## Attachments
* [NFR-12 — Idempotency](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Decision idempotency](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.15 third slice](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* NFR-12 says the operations "are idempotent" — the plan does not specify an
  `Idempotency-Key` header mechanism; do not invent one. Prove idempotency through
  state-machine and persistence invariants; if a genuine double-apply is found, raise
  the mechanism question as a new OQ (`OQ-15+`).
* Submit-replay semantics depend on whether Section 9.1's transition table treats a
  repeat submit as `TASK_STATE_CONFLICT` or a no-op 2xx — decide per the table, not
  per convenience, and record the chosen reading in the changelog so WP-2.6 and
  WP-4.x clients handle retries consistently.
* Checkpoint replay involves file storage as well as DB state — assert both (bytes
  unchanged, one row) or the suite could pass while a storage-side duplication bug
  persists.
