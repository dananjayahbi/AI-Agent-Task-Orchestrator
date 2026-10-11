# MT-1.7-03 — Implement Retry-Exhaustion Escalation to in_human_review (retry_exhausted)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.7-03 |
| Title | Implement retry-exhaustion escalation to in_human_review (retry_exhausted) |
| Parent WP | WP-1.7 — Lease sweeper and retry policy (Milestone M1) |
| Requirements | FR-LEA-07, G-10 |
| Priority | M |
| Dependencies | MT-1.7-02 (sweep loop); MT-1.5-03 (T9 service transition) |
| Parent sections | 6.5 (Flow B), 8.2 (T9), 8.4, 9.8, 19 (WP-1.7), 20.4, 20.5 |

## Context
Flow B's escalation line: "if retries >= `max_retries`: transition to
`in_human_review` (`retry_exhausted`)". FR-LEA-07 is the requirement; G-10 is the
gap it closes (a task could otherwise bounce `pending` ↔ `in_progress` forever —
default `max_retries` 3, then human review with reason `retry_exhausted`, no new
state). T9 already exists as a service transition from MT-1.5-03; this task wires
the sweep cycle to fire it and proves the end-to-end escalation, including the push
trigger from Section 9.8 (`in_human_review` entry is a notification trigger for all
reasons).

## Inputs / Prerequisites
* MT-1.7-02 — sweeper loop with its post-T5 exhaustion hook.
* MT-1.5-03 — T9: guard `failure_retry_count` >= `max_retries`, side effects
  `review_reason` = `retry_exhausted` and push trigger.
* Section 7.2 — Project Policy `max_retries` (default 3); Task `review_reason`.
* Section 8.4 — `retry_exhausted` in the canonical review-reason enum.
* Section 9.8 — push triggers, dedupe key `(event type, task id, state version)`.
* WP-1.9 — `task.transitioned` event written in the T9 transaction.

## Scope (in)
* Add the escalation check to the sweep cycle: after T5 increments
  `failure_retry_count`, if `failure_retry_count` >= `max_retries` dispatch T9 for
  that task in the same run (per Flow B ordering) so the task lands in
  `in_human_review` with `review_reason` = `retry_exhausted`.
* Emit the Section 9.8 push trigger on T9 (in-transaction event; FCM delivery is
  later) with the canonical dedupe key so worker retries cannot double-notify.
* Project-scoped `max_retries`: read from Project Policy (default 3, Section 7.2) —
  projects can differ.
* Guarantee terminal escalation: once in `in_human_review`, the sweeper never
  touches the task again (T5 guard is `in_progress`-only).
* Tests: exactly at `max_retries` the escalation fires on the sweep following the
  increment; below it the task simply returns to `pending`; a project with custom
  `max_retries` behaves accordingly; `review_reason` is exactly `retry_exhausted`
  from the enum; push trigger emitted once per escalation (dedupe key asserted).
* Add a WP changelog note.

## Out of scope
* Human review decisions (approve/request changes) — WP-3.6.
* FCM delivery, device targeting — WP-5.4 (consumes the trigger).
* Reset semantics for `failure_retry_count` on Owner reassign (T16) — WP-3.x owns
  T16; coordinate there (see Risk notes).
* Retry policies for other job types (attachment pipeline, push) — Section 9.9 rows
  owned by their WPs.
* Auditor retry counters (T12) — WP-3.3.

## Target paths
* `backend/apps/leases/` (escalation branch in the sweep cycle)
* `backend/tests/` (escalation tests)
* WP changelog entry

## Acceptance criteria
- [ ] After the increment that reaches `max_retries`, the task ends the sweep cycle
  in `in_human_review` with `review_reason` = `retry_exhausted` — Section 8.2 T9,
  Section 8.4 enum, FR-LEA-07 (WP-1.7 acceptance).
- [ ] Below `max_retries`, the task returns to `pending` and remains claimable
  (G-10 bounded retries, not immediate escalation).
- [ ] `max_retries` comes from Project Policy (default 3; Section 7.2) — no
  hardcoding (Section 20.5).
- [ ] The push trigger fires once per escalation with the Section 9.8 dedupe key;
  the T9 transition writes its event/history rows in one transaction
  (Section 20.4 item 6).
- [ ] The sweeper never re-processes a task already in `in_human_review`.
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k retry_exhaustion -q` and confirm the escalation
boundary, custom `max_retries`, exact `retry_exhausted` reason, single push trigger
with dedupe key, and sweeper no-touch after escalation; full suite stays green.

## Attachments
* [Section 6.5 Flow B — Sweep escalation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.8 — Notifications](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `failure_retry_count` reset rules are not specified for T16 (request changes /
  reassign) — if a reset is expected there, escalation counts could carry over
  incorrectly; raise an OQ (Section 22 numbering) with WP-3.x before implementing a
  reset.
* Push trigger must be wired to the notifications seam only — actual dispatch,
  dedupe storage and pruning are WP-5.4; duplicating dedupe logic here would
  conflict with Section 9.8's design.
