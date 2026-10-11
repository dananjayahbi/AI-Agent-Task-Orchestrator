# MT-1.8-02 — Implement Lease Ownership and Fencing Validation for Checkpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.8-02 |
| Title | Implement lease ownership and fencing validation for checkpoints |
| Parent WP | WP-1.8 — Checkpoints and token usage (Milestone M1) |
| Requirements | FR-LEA-03, NFR-12, ADR-012, GOAL-2 |
| Priority | M |
| Dependencies | MT-1.8-01 (model); MT-1.6-05 (fencing helper); MT-1.6-03 (extension guard) |
| Parent sections | 6.5 (Flow B), 8.6, 10.5 (`log_task_checkpoint`), 19 (WP-1.8), 20.4, 20.5 |

## Context
Flow B: "Backend: verify lease owner + not expired" before storing a checkpoint and
extending the lease. Section 8.6 is stricter: "Late checkpoints from the old owner
return `LEASE_EXPIRED` and must not resurrect the lease", and fencing means every
mutating call carries the lease generation (ADR-012). WP-1.8's acceptance is
"checkpoint after expiry rejected". The bridge tool contract (Section 10.5) makes
the rejection actionable: `LEASE_EXPIRED` "instructs the agent to stop and re-claim".
This micro-task is that gate — the checkpoint write path never proceeds without a
valid, current, unexpired lease.

## Inputs / Prerequisites
* MT-1.8-01 — Task Checkpoint model to write into.
* MT-1.6-05 — the single fencing-check helper (generation + session + expiry);
  checkpoints must call it, not reimplement it.
* MT-1.6-03 — extension function whose guard refuses expired/stale leases.
* Parent plan Section 8.6 — Expire and Fencing rules verbatim; Section 6.5 Flow B —
  owner + not-expired verification step.
* Section 9.2 — canonical codes `LEASE_EXPIRED`, `LEASE_NOT_OWNED`, plus
  `TASK_NOT_FOUND` for unknown tasks.

## Scope (in)
* Implement the checkpoint validation step applied before any write: resolve task →
  caller must be the current lease owner (session/worker match), lease unexpired,
  and presented `lease_generation` equal to the task's current generation — reusing
  the MT-1.6-05 helper so all agent mutations fence identically (ADR-012).
* Rejection outcomes (catalog codes only): expired lease or stale generation →
  `LEASE_EXPIRED`; session not the owner → `LEASE_NOT_OWNED`; unknown/foreign task →
  `TASK_NOT_FOUND` / `AUTH_FORBIDDEN_PROJECT`. None of these create a row, touch
  `last_checkpoint_at`, extend the lease or emit events (no resurrection, Section
  8.6).
* Validation runs inside the same transaction as the checkpoint insert and the
  extension, re-checked after acquiring the row lock — a sweeper reclaim racing the
  checkpoint must lose cleanly (checkpoint vs expiry race, Section 18).
* `kind` gating per plan semantics: extension applies to a valid checkpoint from the
  owner (Section 8.6: "each valid checkpoint"); `liveness` kind participates only if
  OQ-04's `checkpoint_and_liveness` mode was enabled — default `checkpoint_only`
  treats `progress`/`system` as the extension-carrying kinds (confirm exact
  participation against Section 8.6 during the session; ambiguity → OQ).
* Tests: happy path for current owner; expired → `LEASE_EXPIRED` with zero writes;
  stale generation after reclaim → `LEASE_EXPIRED`; foreign session →
  `LEASE_NOT_OWNED`; racing sweeper reclaims and checkpoint fails; nothing written
  on any rejection path.
* Add a WP changelog note.

## Out of scope
* The endpoint surface, response payload (new expiry) and idempotency — MT-1.8-03.
* The extension math (min/cap) — MT-1.6-03 (called after this gate passes).
* Listing/validation on read — MT-1.8-04.
* Submissions and audit verdicts applying the same gate — WP-2.6 / WP-3.3 (they
  reuse this helper).
* Bridge-side handling of `LEASE_EXPIRED` (stop and re-claim) — WP-2.6.

## Target paths
* `backend/apps/leases/` or `backend/apps/tasks/` (checkpoint validation gate —
  placed with the checkpoint write path)
* `backend/tests/` (ownership/fencing tests incl. race)
* WP changelog entry

## Acceptance criteria
- [ ] A checkpoint from the current owner with the current generation and unexpired
  lease passes the gate (FR-LEA-03 precondition).
- [ ] A checkpoint after expiry is rejected with `LEASE_EXPIRED` and writes nothing —
  no row, no `last_checkpoint_at`, no extension, no event (WP-1.8 acceptance;
  Section 8.6).
- [ ] A stale generation after reclamation is rejected with a canonical lease error
  (ADR-012, Section 9.2 codes only — Section 20.4 item 5).
- [ ] The gate re-validates under the row lock so a concurrent sweep always wins
  (Section 18 checkpoint-vs-expiry race).
- [ ] Validation is the shared MT-1.6-05 helper — one fencing implementation across
  release and checkpoints.
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k checkpoint_ownership -q` against real Postgres and
confirm each acceptance path (owner pass, expired/stale/foreign rejections with zero
writes, sweep-race outcome); full suite stays green.

## Attachments
* [Section 8.6 — Lease semantics (Expire, Fencing)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog (`log_task_checkpoint`)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The gate and the insert must share one transaction; a check-then-insert split is
  the classic TOCTOU the Section 18 race test is designed to catch — review the
  transaction boundaries carefully.
* Which `kind` values extend the lease is not spelled out beyond "valid checkpoint"
  (Section 8.6) — confirm against OQ-04's outcome from WP-0.4; unresolved ambiguity
  becomes an OQ before MT-1.8-03 wires extension.
