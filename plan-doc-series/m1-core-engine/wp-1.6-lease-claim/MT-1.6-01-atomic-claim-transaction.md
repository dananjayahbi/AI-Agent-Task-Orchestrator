# MT-1.6-01 — Implement the Atomic Claim Transaction with Row Lock and Skip-Locked

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-01 |
| Title | Implement the atomic claim transaction with row lock and skip-locked |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-01, FR-LEA-02, NFR-01, NFR-12, ADR-012, GOAL-2 |
| Priority | M |
| Dependencies | MT-1.5-04 (T4 registered); WP-1.4 complete (task model) |
| Parent sections | 8.2 (T4), 8.6, 9.3, 12.1, 19 (WP-1.6), 20.4, 20.5 |

## Context
Section 9.3 fixes the claim algorithm: resolve the caller's project from the token,
begin a transaction, select the target row with an exclusive lock and skip-locked
behavior, re-validate state/project status/dependencies/concurrency inside the lock,
set lease fields while incrementing lease generation and `attempt_number`, write
Transition (T4) and Event (`task.claimed`) rows, commit, and return task details,
lease and rules block. FR-LEA-01 guarantees exactly one claimant wins (NFR-01: zero
duplicate claims under at least 50 concurrent attempts), and FR-LEA-02 fixes the
claim record: worker id, session id, role, lease start, lease expiry (default 45
minutes from `lease_duration_minutes`).

## Inputs / Prerequisites
* MT-1.5-04 — T4 registered as a stub ready for wiring; MT-1.5-01 dispatcher
  contract.
* Parent plan Section 9.3 — the six-step claim algorithm and the "no row returned"
  follow-up read producing `TASK_ALREADY_CLAIMED` or `TASK_NOT_FOUND`.
* Section 8.6 — lease acquire semantics (`lease_acquired_at` = now,
  `lease_expires_at` = now + `lease_duration_minutes`) and fencing (lease generation
  increments on every claim).
* Section 7.2 — Task lease fields; Project Policy defaults (`lease_duration_minutes`
  45, `max_concurrent_tasks` 1).
* Section 10.6 — the claim response carries the rules block (fetched via the
  project's rules; wiring shape only — full tool delivery is WP-2.4).
* Real Postgres for tests (Section 18 concurrency layer).

## Scope (in)
* Implement the claim service function following Section 9.3 step for step, using
  `SELECT … FOR UPDATE SKIP LOCKED` on the target task row.
* Cheap follow-up read when no row is returned, distinguishing `TASK_ALREADY_CLAIMED`
  (held by another worker) from `TASK_NOT_FOUND` (wrong id/project) — both catalog
  codes (Section 9.2).
* In-lock re-validation: state is `pending`, project `active_status` is `active`,
  dependencies completed, `max_concurrent_tasks` not exceeded (counting is factored
  for MT-1.6-06), token scope matches the task's project (`AUTH_FORBIDDEN_PROJECT`
  otherwise).
* Lease write per FR-LEA-02: `worker_agent_id`, `worker_session_id`, `claimed_role`
  (`coder`), `lease_acquired_at`, `lease_expires_at`, `lease_generation` + 1,
  `attempt_number` + 1.
* Dispatch T4 through the state-machine service and write the `task.claimed` event in
  the same transaction; commit; return task details, lease record (Section 8.6 JSON
  shape) and rules block.
* Idempotency-key handling per Section 9.2/ADR-012 so retried claim calls are safe
  (NFR-12).
* Unit and integration tests of every step, including the two follow-up-read error
  paths.
* Add a WP changelog note.

## Out of scope
* "Next available" selection ordering — MT-1.6-02.
* Extension logic — MT-1.6-03; voluntary release — MT-1.6-04; fencing validation on
  downstream calls — MT-1.6-05; concurrency-limit details — MT-1.6-06 (factor the
  hook only).
* REST endpoints — MT-1.6-07; the 50-claimant race suite — MT-1.6-08.
* Sweep/expiry (T5/T9) — WP-1.7; checkpoint-driven extension — WP-1.8.
* Auditor claim (T11) and audit leases — WP-3.3 (same lease rules, separate scope).

## Target paths
* `backend/apps/leases/` (claim service, lock helpers)
* `backend/apps/tasks/` (T4 wiring into the state-machine service)
* `backend/tests/` (claim transaction tests, concurrency smoke)
* WP changelog entry

## Acceptance criteria
- [ ] Claim implements all six Section 9.3 steps in order, inside one transaction
  with `FOR UPDATE SKIP LOCKED` (FR-LEA-01).
- [ ] The lease record written matches FR-LEA-02 (worker, session, role, start,
  expiry = start + `lease_duration_minutes`) and the Section 8.6 JSON shape.
- [ ] A contended claim returns `TASK_ALREADY_CLAIMED`; an unknown or foreign task
  returns `TASK_NOT_FOUND`; a foreign-project token returns
  `AUTH_FORBIDDEN_PROJECT` — only Section 9.2 codes (Section 20.4 item 5).
- [ ] `lease_generation` and `attempt_number` each increment by exactly one per
  successful claim (Section 8.6, ADR-012).
- [ ] `task.claimed` event and the T4 Transition row commit atomically with the state
  change (Section 8.2, Section 20.4 item 6).
- [ ] A two-connection test proves exactly one of two simultaneous claimants wins.
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k claim_transaction -q` against real Postgres and confirm
the six steps, both error paths, lease record fields and atomic event/history writes;
two-connection contention must yield exactly one winner. Full suite
(`pytest backend/tests -q`) stays green.

## Attachments
* [Section 9.3 — Claim algorithm](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Skip-locked behavior depends on Postgres semantics — tests must run on real
  Postgres, not SQLite (Section 18); CI wiring comes from MT-0.3-02.
* The rules block in the claim response references Section 10.6 content owned by
  later WPs — return it through a narrow interface; if its shape is needed before
  WP-2.x, raise an OQ rather than inventing fields.
* Idempotency-key replay for claims interacts with NFR-12 — reuse the WP-0.5-03
  header conventions; do not design a second mechanism here.
