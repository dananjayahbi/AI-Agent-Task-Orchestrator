# MT-1.5-03 — Implement System Transitions T5 (Lease Expired), T9 (Retry Exhausted)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-03 |
| Title | Implement system transitions T5 (lease expired), T9 (retry exhausted) |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-03, FR-TSK-04, FR-LEA-04, FR-LEA-07, G-10 |
| Priority | M |
| Dependencies | MT-1.5-01 (registry and guard framework) |
| Parent sections | 8.2 (T5, T9), 8.4, 8.6, 19 (WP-1.5), 20.4, 20.5 |

## Context
The system actor (S) owns the two recovery transitions that keep agents from wedging
tasks. T5 moves `in_progress` → `pending` when the lease has expired, incrementing
`failure_retry_count`, clearing the worker and emitting `task.lease_expired`. T9 moves
`in_progress` → `in_human_review` when retries are exhausted
(`failure_retry_count` >= `max_retries`, default 3, G-10), setting
`review_reason` = `retry_exhausted` from the canonical enum (Section 8.4) and
triggering a push. The lease sweeper (WP-1.7) will be the caller; this task implements
and tests the service side so the sweeper only orchestrates timing.

## Inputs / Prerequisites
* MT-1.5-01 — registry, dispatcher, guard and transaction machinery.
* Parent plan Section 8.2 rows T5 and T9 — exact guards and side effects.
* Section 7.2 — Task fields `failure_retry_count`, `worker_agent_id`,
  `worker_session_id`, `review_reason`; Project Policy `max_retries` (default 3).
* Section 8.4 — canonical review-reason enum containing `retry_exhausted`.
* Section 9.6 — `task.lease_expired` event type in the catalog.

## Scope (in)
* Register and implement **T5** `in_progress` → `pending` (actor S): guard —
  `lease_expires_at` < now; side effects — `failure_retry_count` + 1, clear worker
  fields (`worker_agent_id`, `worker_session_id`, `claimed_role`, lease timestamps),
  emit `task.lease_expired` in-transaction (FR-LEA-04).
* Register and implement **T9** `in_progress` → `in_human_review` (actor S): guard —
  `failure_retry_count` >= `max_retries`; side effects — `review_reason` =
  `retry_exhausted`, trigger the Section 9.8 push-notification path for
  `in_human_review` entry (FR-LEA-07).
* Both transitions run through the single service with Transition rows recording
  actor_type `system` and an actor_ref identifying the sweeper (FR-TSK-04).
* Unit tests covering the guards, side effects and the exact boundary
  (`failure_retry_count` == `max_retries` - 1 still allows T5; at `max_retries` the
  escalation path applies).
* Add a WP changelog note.

## Out of scope
* Finding expired leases and scheduling — the sweeper job itself is WP-1.7
  (MT-1.7-02 invokes T5; MT-1.7-03 wires the T9 escalation trigger into the sweep
  cycle).
* Fencing and late-checkpoint rejection — MT-1.6-05 / MT-1.8-02.
* Actual FCM push delivery — notifications module and WP-5.4; only the in-process
  trigger per Section 9.8 lands here.
* Audit/merge recovery transitions T12/T18 — WP-3.x.

## Target paths
* `backend/apps/tasks/` (registrations and guards for T5, T9)
* `backend/tests/` (system transition tests)
* WP changelog entry

## Acceptance criteria
- [ ] T5 matches Section 8.2 exactly: guard `lease_expires_at` < now; increments
  `failure_retry_count`; clears worker; emits `task.lease_expired` (FR-LEA-04).
- [ ] T9 matches Section 8.2 exactly: guard `failure_retry_count` >= `max_retries`;
  sets `review_reason` = `retry_exhausted` (canonical enum, Section 8.4); triggers
  the push path (FR-LEA-07, G-10).
- [ ] A task in any state other than `in_progress` cannot receive T5 or T9 —
  `TASK_STATE_CONFLICT` (catalog code, Section 20.4 item 5).
- [ ] `task.lease_expired` is a Section 9.6 catalog event (Section 20.4 item 6).
- [ ] Transition rows carry actor_type `system` with a sweeper `actor_ref`.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k system_transitions -q` and confirm: expired-lease T5
side effects and event, T9 boundary at `max_retries`, `retry_exhausted` reason, and
non-`in_progress` rejections; then the full suite (`pytest backend/tests -q`) stays
green.

## Attachments
* [Section 8.2 — Transition table (T5, T9)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics in detail](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Event emission depends on the WP-1.9 in-transaction hook (same sequencing caveat as
  MT-1.5-01) — assert the emission point exists; do not queue events post-commit here.
* Push trigger must reuse the Section 9.8 dedupe design `(event type, task id, state
  version)` when notifications land; keep the trigger seam narrow so WP-5.4 plugs in
  without changing T9.
* The exact escalation ordering (T5 first, then T9 on the same sweep, per Flow B) is
  a WP-1.7 concern; tests here must not bake in a sweeper loop — flag any ambiguity
  as an OQ.
