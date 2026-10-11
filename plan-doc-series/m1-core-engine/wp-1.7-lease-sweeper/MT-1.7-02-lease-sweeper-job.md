# MT-1.7-02 — Implement the Idempotent Lease Sweeper Job (60 s Interval)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.7-02 |
| Title | Implement the idempotent lease sweeper job (60 s interval) |
| Parent WP | WP-1.7 — Lease sweeper and retry policy (Milestone M1) |
| Requirements | FR-LEA-04, FR-LEA-05, G-10, ADR-003 |
| Priority | M |
| Dependencies | MT-1.7-01 (beat/worker wired); MT-1.5-03 (T5); MT-1.6-01 (claim semantics); WP-1.9 (event helper) |
| Parent sections | 6.5 (Flow B), 8.2 (T5), 8.6, 9.9, 19 (WP-1.7), 20.4, 20.5 |

## Context
Flow B's beat step is the contract: "Beat (every 60 s): find `in_progress` rows with
`lease_expires_at` < now → transition to `pending`, `failure_retry_count` + 1, emit
`lease_expired` → if retries >= `max_retries`: transition to `in_human_review`
(`retry_exhausted`)". FR-LEA-05 fixes the interval at 60 s and demands the job be
idempotent and safe under multiple instances; Section 9.9's job table says the
sweeper "uses skip-locked so parallel runs never double-process". This micro-task
implements the reclaim loop (T5) — the retry-exhaustion branch is MT-1.7-03.

## Inputs / Prerequisites
* MT-1.7-01 — beat schedule entry and worker runtime in place.
* MT-1.5-03 — T5 service transition (`in_progress` → `pending`, guard
  `lease_expires_at` < now, side effects: increment, clear worker, emit
  `task.lease_expired`).
* MT-1.6-01 — claim lock discipline to mirror for sweep selection (`FOR UPDATE SKIP
  LOCKED`).
* Parent plan Section 8.6 — "the sweeper applies T5. Late checkpoints from the old
  owner return `LEASE_EXPIRED` and must not resurrect the lease" (enforced by
  MT-1.8-02, asserted here end-to-end).
* WP-1.9 — write-in-transaction event helper for `task.lease_expired`
  (Section 9.6 catalog).

## Scope (in)
* Implement the sweeper Celery task: select `in_progress` tasks whose
  `lease_expires_at` < now using `FOR UPDATE SKIP LOCKED`, dispatch T5 per row
  inside a transaction, commit, and repeat until no candidates remain.
* Idempotency: a second concurrent sweeper run must observe no double-processing —
  the row lock plus T5's state guard (`in_progress` only) make a second sweep of the
  same task a no-op; tests prove exactly one T5 transition per expiry (FR-LEA-05).
* Register the task on the Section 9.9 60-second beat schedule (replace MT-1.7-01's
  stub).
* Structured logging per task swept (correlation id conventions from WP-0.5-03) so
  reclaim activity is traceable.
* Sweep must not resurrect expired leases: after T5, the old owner's generation is
  stale and `lease_expires_at`/worker fields are cleared (invariant 1, Section 8.3).
* Tests: expired rows reclaimed; unexpired rows untouched; empty sweep is a clean
  no-op; two concurrent sweepers over the same expired set produce one transition
  each task; sweeper vs. simultaneous new claim stays consistent.
* Add a WP changelog note.

## Out of scope
* The retry-exhaustion escalation branch (T9) — MT-1.7-03 (the sweep loop leaves a
  hook where Flow B checks `retries >= max_retries`).
* The lease-expiring warning job — MT-1.7-04 (separate 60-second beat entry).
* Chaos suite — MT-1.7-05.
* Checkpoint-vs-expiry races at the endpoint — WP-1.8/WP-1.15 (asserted indirectly
  here).
* Audit leases (T12) — WP-3.3 ("same lease rules" applied there).

## Target paths
* `backend/apps/leases/` (sweeper task)
* `backend/` Celery beat schedule (60 s entry active)
* `backend/tests/` (sweeper tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every `in_progress` task with `lease_expires_at` < now receives exactly one T5:
  returns to `pending`, `failure_retry_count` + 1, worker cleared, `task.lease_expired`
  emitted (FR-LEA-04, Section 8.2 T5, Section 20.4 item 6).
- [ ] Selection uses `SKIP LOCKED`; two concurrent sweeper runs yield one transition
  per expired task (FR-LEA-05, Section 9.9).
- [ ] The beat schedule runs the job every 60 s (Section 9.9) and a sweep of an empty
  set is a clean no-op.
- [ ] After a sweep, the former owner's mutating calls fail with `LEASE_EXPIRED`
  (Section 8.6) — no lease resurrection (Section 8.3 invariant 1).
- [ ] Error codes used are catalog codes (Section 20.4 item 5).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k lease_sweeper -q` against real Postgres and confirm
reclaim side effects, double-sweeper single-transition behavior, empty-sweep no-op
and post-sweep `LEASE_EXPIRED` for the old owner; full suite stays green.

## Attachments
* [Section 6.5 Flow B — Checkpoint and lease extension](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics (Expire)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sweep batches could hold locks long on a large backlog — process in bounded
  batches; the plan does not specify a batch size, so pick a documented default and
  raise an OQ only if behavior under 10,000-task loads (Section 18) demands tuning.
* Ordering with MT-1.7-03: Flow B checks exhaustion inside the same sweep cycle —
  keep the hook so MT-1.7-03 can extend without restructuring the loop; if the hook
  placement is ambiguous, raise an OQ rather than duplicating sweeps.
* The event must be written in the T5 transaction (Section 8.2) — dependent on the
  WP-1.9 helper (declared dependency); do not emit post-commit from the task layer.
