# MT-1.6-06 — Enforce Per-Project max_concurrent_tasks at Claim Time

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-06 |
| Title | Enforce per-project max_concurrent_tasks at claim time |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-08, G-26, ADR-013 |
| Priority | S |
| Dependencies | MT-1.6-01 (in-lock re-validation hook) |
| Parent sections | 7.2 (Project Policy), 8.2 (T4 guard), 9.3 (step 4), 19 (WP-1.6), 20.4, 20.5 |

## Context
T4's guard list includes "`max_concurrent_tasks` not exceeded", Section 9.3 step 4
re-validates the concurrency limit inside the lock, and FR-LEA-08 makes it a
requirement: per-project `max_concurrent_tasks` enforced at claim time. The default
is 1 (Section 7.2, G-26) — the primary mitigation for "several agents on one
repository corrupt the shared working tree" (RISK-03). ADR-013 keeps that default
while allowing per-project raises.

## Inputs / Prerequisites
* MT-1.6-01 — the in-lock re-validation step where the limit check belongs (it must
  run inside the transaction, never before the lock).
* Section 7.2 — Project Policy `max_concurrent_tasks` (default 1); Task
  `claimed_role` (`coder` / `auditor`).
* Section 7.4 integrity constraint 1 — at most one active lease per task (partial
  unique rule) complements this limit.
* Section 19 (WP-1.6): concurrency limit listed among slices and deliverables.

## Scope (in)
* Implement the in-transaction concurrency check: count the project's tasks currently
  `in_progress` (coder leases; audit claims counted per `claimed_role` so auditor
  work does not silently consume the coder budget — confirm semantics against
  Section 7.2 wording during the session) and compare with the project's
  `max_concurrent_tasks`.
* Reject a claim that would exceed the limit with `CONCURRENCY_LIMIT_REACHED`
  (Section 9.2 catalog), releasing the row lock cleanly with no side effects.
* Read the limit from Project Policy (default 1 per Section 7.2); never hardcode.
* Tests: at limit → next claim rejected with the catalog code; below limit →
  succeeds; two simultaneous claims at the limit-1 boundary admit exactly one;
  raising the policy value admits more; a paused project still fails earlier at the
  project-active guard (separate error, not this one).
* Add a WP changelog note.

## Out of scope
* Project Policy CRUD and validation of the setting — WP-1.3.
* Worktree mode for higher-concurrency repos — WP-2.10 (OQ-03, ADR-013).
* Per-role concurrency policy variants beyond what Section 7.2 states — needs an OQ
  first.
* Sweep/release interactions with the count — emergent from WP-1.7; re-verified in
  MT-1.7-05.
* Rate limiting on the endpoint — WP-1.2 (Section 9.2 rate limits).

## Target paths
* `backend/apps/leases/` (concurrency check inside the claim transaction)
* `backend/tests/` (concurrency-limit tests)
* WP changelog entry

## Acceptance criteria
- [ ] A claim at the limit fails with `CONCURRENCY_LIMIT_REACHED` and no lease,
  transition or event is written (FR-LEA-08; catalog code, Section 20.4 item 5).
- [ ] The check executes inside the claim transaction after the row lock (Section
  9.3 step 4), so racing claims cannot both pass the count.
- [ ] The limit is read from Project Policy with default 1 (Section 7.2, G-26);
  raising it changes behavior without code changes (ADR-013).
- [ ] Boundary test: `in_progress` count at N-1 → next claim succeeds; at N → rejected.
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k concurrency_limit -q` against real Postgres and confirm
the boundary accept/reject behavior, the racing-claims test admits exactly one, and
the policy override is honored; full suite stays green.

## Attachments
* [Section 7.2 — Project Policy (`max_concurrent_tasks`)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.3 — Claim algorithm step 4](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Counting `in_progress` rows without the lock invites TOCTOU — the count must run
  on the locked path (Section 9.3 step 4); a pre-lock count would be a silent
  correctness bug.
* Whether auditor leases share the coder limit is not stated unambiguously in
  Section 7.2 ("Simultaneous `in_progress` tasks") — tasks in `to_be_audited` are
  not `in_progress`, so default to coder-only counting and raise an OQ if audit
  concurrency needs its own limit.
