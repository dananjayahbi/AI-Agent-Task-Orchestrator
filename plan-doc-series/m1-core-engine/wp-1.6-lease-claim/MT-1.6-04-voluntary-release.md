# MT-1.6-04 — Implement Voluntary Release Without Failure Increment

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.6-04 |
| Title | Implement voluntary release without failure increment |
| Parent WP | WP-1.6 — Lease and claim service (Milestone M1) |
| Requirements | FR-LEA-06, FR-TSK-03, ADR-012 |
| Priority | M |
| Dependencies | MT-1.6-01 (claim transaction); MT-1.5-04 (T6 registered) |
| Parent sections | 8.2 (T6), 8.6, 9.2 (`POST /tasks/{id}/release`), 19 (WP-1.6), 20.4, 20.5 |

## Context
T6 moves `in_progress` → `pending` on voluntary release (actors C, O) with the guard
"caller owns lease (or Owner override)" and side effects "clear worker; no failure
increment". FR-LEA-06 is the requirement: voluntary release by the lease owner
returns the task to `pending` without incrementing `failure_retry_count` — the
sweeper's T5 is what increments it. The distinction is what keeps honest releases
from consuming the project's `max_retries` budget (G-10).

## Inputs / Prerequisites
* MT-1.6-01 — lease record fields and ownership data (`worker_agent_id`,
  `worker_session_id`, `lease_generation`).
* MT-1.5-04 — T6 stub awaiting wiring; MT-1.5-01 dispatcher contract.
* Parent plan Section 8.2 row T6 — guard and side effects verbatim.
* Section 9.2 — `POST /tasks/{id}/release` (Agent caller) and the catalog codes
  `LEASE_NOT_OWNED`, `LEASE_EXPIRED`, `TASK_STATE_CONFLICT`.
* Section 9.6 — `task.released` event in the catalog.

## Scope (in)
* Implement the release service function: verify the caller owns the current lease
  (session/worker match and `lease_generation` current) or is the Owner applying the
  documented override; dispatch T6 through the state-machine service.
* Side effects per Section 8.2: clear worker fields and lease timestamps,
  **no** `failure_retry_count` increment, `attempt_number` preserved (compare T16,
  which also preserves it).
* Emit `task.released` and write the T6 Transition row in the same transaction
  (Section 8.2 rule, Section 20.4 item 6).
* Error paths: non-owner agent session → `LEASE_NOT_OWNED`; expired lease →
  `LEASE_EXPIRED` (the sweeper owns reclamation, not the releasing party); task not
  `in_progress` → `TASK_STATE_CONFLICT` — catalog codes only.
* Tests: owner release clears the lease and leaves `failure_retry_count` unchanged;
  foreign session rejected; Owner override path works and is auditable via
  `actor_type` `owner`.
* Add a WP changelog note.

## Out of scope
* The HTTP endpoint and idempotency wiring — MT-1.6-07.
* Sweeper-driven reclamation (T5) and its increment — WP-1.7.
* Audit-lease release (T11/T12 mechanics) — WP-3.3.
* Bridge `release_task` tool behavior — WP-2.4 (consumes this endpoint).
* Owner-override product questions (when UI offers release) — WP-4.9; the service
  only implements the Section 8.2 "(or Owner override)" guard.

## Target paths
* `backend/apps/leases/` (release service)
* `backend/apps/tasks/` (T6 wiring into the state-machine service)
* `backend/tests/` (release tests)
* WP changelog entry

## Acceptance criteria
- [ ] Release dispatches T6 exactly as Section 8.2 defines: `in_progress` → `pending`,
  worker cleared, **no** `failure_retry_count` increment (FR-LEA-06).
- [ ] Only the lease owner (matching session/worker and current
  `lease_generation`) or the Owner override passes the guard; otherwise
  `LEASE_NOT_OWNED` (Section 9.2).
- [ ] Releasing an expired lease returns `LEASE_EXPIRED` and does not apply T6 —
  reclamation belongs to the sweeper's T5 (Section 8.6).
- [ ] `task.released` event and T6 Transition row commit atomically with the state
  change (Section 9.6, Section 20.4 item 6).
- [ ] `attempt_number` is preserved across release (Section 8.2 T16 comparison).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k voluntary_release -q` and confirm: `failure_retry_count`
unchanged after release, worker fields cleared, foreign-session and expired-lease
rejections with the right catalog codes, and event/history rows written; full suite
stays green.

## Attachments
* [Section 8.2 — Transition table (T6)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Owner override could mask a live agent's work if misused — require the same
  optimistic `version` check as other mutations and rely on the Transition row's
  `actor_type`/`actor_ref` for audit (Section 12.5); flag any override UX question
  as an OQ for WP-4.9.
* Release racing the sweeper: both target `in_progress` — the claim/lock discipline
  from MT-1.6-01 must serialize them; add a release-vs-expiry test here and re-verify
  in MT-1.7-05's chaos suite.
