# MT-1.6-05 — Implement Lease Fencing Generation on Every Claim

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-05 |
| Title | Implement lease fencing generation on every claim |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-01, FR-LEA-02, NFR-12, ADR-012, GOAL-2 |
| Priority | M |
| Dependencies | MT-1.6-01 (claim writes the generation); MT-1.6-04 (release consumes it) |
| Parent sections | 8.6, 12.1, 19 (WP-1.6), 20.4, 20.5 |

## Context
Section 8.6: "Fencing: every claim increments an internal lease generation; mutating
calls carry the generation so a slow former owner can never overwrite state after
the task is reclaimed." ADR-012 pairs idempotency keys with lease fencing on all
agent mutations. This is the backend's defense against the classic split-brain: an
agent stalls, the sweeper reclaims (T5), another agent claims (generation + 1), then
the first agent wakes up and tries to write — the stale generation must be rejected.

## Inputs / Prerequisites
* MT-1.6-01 — claim already increments `lease_generation`; the lease record
  (Section 8.6 JSON) exposes `lease_generation` to the caller.
* Parent plan Section 8.6 — fencing rule verbatim; Section 12.1 — threat
  "duplicate/competing work" answered by row-lock claim plus fencing generation.
* Section 9.6 / Section 9.2 — mutating agent endpoints that must carry the
  generation; canonical lease errors `LEASE_EXPIRED`, `LEASE_NOT_OWNED`.
* ADR-012 — fencing on all agent mutations; NFR-12 — safe retries.
* WP-0.5-03 — header conventions (idempotency key) as the model for how the
  generation is transported; the exact carrier for the generation must follow the
  plan (see Risk notes if unspecified).

## Scope (in)
* Persist `lease_generation` on the Task as a monotonic integer that increments on
  every successful claim (T4) and on audit claims when WP-3.3 adopts the same rules;
  initialize at first claim.
* Provide a single fencing-check helper: given the caller's claimed generation and
  the task's current generation/lease state, accept only a matching generation with
  an unexpired lease; otherwise reject with `LEASE_EXPIRED` (stale generation or
  expired lease) or `LEASE_NOT_OWNED` (session mismatch) — catalog codes only.
* Apply the helper inside the mutating agent paths that exist in this WP (release,
  and the claim path's own re-validation) and expose it for WP-1.8 checkpoints and
  WP-2.6 submissions to call — one implementation, no per-endpoint variants.
* Tests: generation increments by exactly one per claim; a request carrying a
  previous generation after reclaim is rejected and changes nothing; concurrent
  claim → reclaim → claim produces strictly increasing generations; rejection leaves
  `version`, history and events untouched.
* Add a WP changelog note.

## Out of scope
* Checkpoint validation wiring — MT-1.8-02 (first major consumer).
* Submission/audit-verdict fencing — WP-2.6 / WP-3.3 (callers of this helper).
* Choosing an alternative transport (body field vs header) — see Risk notes; the
  endpoint surface itself is MT-1.6-07.
* Idempotency-key storage mechanics — WP-0.5 conventions + core module; only the
  fencing half of ADR-012 lands here.
* Redis/database fencing primitives beyond the row-generation design — the plan
  specifies generation-on-claim (Section 8.6); anything else needs an OQ.

## Target paths
* `backend/apps/leases/` (generation increment at claim, fencing-check helper)
* `backend/apps/tasks/` (Task field/migration for `lease_generation` if not already
  present)
* `backend/tests/` (fencing tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every claim increments `lease_generation` by exactly one; the value is returned
  in the lease record (Section 8.6 JSON includes `lease_generation`).
- [ ] A mutating request with a stale generation after reclamation is rejected with a
  canonical lease error and performs no writes (Section 8.6, ADR-012).
- [ ] The check is implemented once and reused (no divergent per-endpoint fencing),
  with WP-1.8 able to adopt it without changes to this helper's contract.
- [ ] Claim → expire → reclaim → claim yields strictly increasing generations in
  tests (GOAL-2 no-duplicate-work evidence).
- [ ] Migration for the generation field applies cleanly (Section 18 migration check).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k lease_fencing -q` and confirm increments, stale
generation rejection with `LEASE_EXPIRED`/`LEASE_NOT_OWNED`, no-write-on-reject, and
strictly increasing generations across reclaim cycles; full suite stays green.

## Attachments
* [Section 8.6 — Lease semantics (fencing)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (duplicate/competing work)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan states mutating calls "carry the generation" but does not fix the carrier
  (body field vs header). Pick the transport consistent with WP-0.5-03 conventions;
  if none applies cleanly, raise an OQ (Section 22 numbering) before locking the
  API — the choice becomes part of the OpenAPI contract (Section 20.4 item 4).
* Generation alone does not stop a stale writer that omits the field — endpoints
  must require it for agent mutations; making it optional would silently defeat
  ADR-012, so enforce presence and test the missing-field path.
