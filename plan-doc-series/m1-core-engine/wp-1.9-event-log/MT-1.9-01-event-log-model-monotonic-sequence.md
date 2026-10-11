# MT-1.9-01 — Create the Event Log Model with Monotonic Sequence Used as SSE Event Id

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.9-01 |
| Title | Create the Event log model with monotonic sequence used as SSE event id |
| Parent WP | WP-1.9 — Event log and audit trail (Milestone M1) |
| Requirements | FR-SEC-03 |
| Priority | M |
| Dependencies | MT-1.5-06 (WP-1.5 complete; transition history model and insert-only pattern exist) |
| Parent sections | 9.6, 12.5, 19.1 (WP-1.9), 20.2, 20.4, 20.5 |

## Context
Section 9.6 states that every state-changing action writes an Event row and that each
SSE message carries the event's monotonically increasing id; Section 12.5 requires the
row to hold actor and correlation id and to be append-only. This task creates the
foundation: an `events` app model whose id doubles as the SSE event id, so replay and
resume (MT-1.10-03) have a single ordering key. Section 19 (WP-1.9) requires the event
model with monotonic ids as a deliverable.

## Inputs / Prerequisites
* Parent plan Section 9.6 — the canonical event envelope: `id`, `type`, `project_id`,
  `task_id`, `occurred_at`, `actor` (`type`, `ref`), `data`.
* Parent plan Section 12.5 — every state change, token event, review decision, merge
  result, login and policy edit writes an Event row with actor and correlation id.
* WP-1.5 complete (MT-1.5-06) — the append-only Task Transition history model is the
  in-repo pattern for insert-only tables.
* Module layout Section 9.1 — the model lives in the `events` module.
* Django project and migrations infrastructure from WP-1.1.

## Scope (in)
* Create the `events` Django app module and the Event model with exactly the envelope
  fields of Section 9.6: `id` (monotonic primary key used as the SSE event id), `type`,
  `project_id`, `task_id`, `occurred_at`, `actor` (`type` and `ref`), `data`.
* Add the correlation id required by Section 12.5 and the indexes needed to read events
  in `id` order for replay and filtered by project/task.
* Database migration for the model.
* Uniqueness/monotonicity guarantee for `id` under concurrent inserts, with a test that
  proves ids strictly increase and never repeat.
* A check that `occurred_at` is recorded at write time inside the transaction.

## Out of scope
* The write-in-transaction helper and call-site wiring — MT-1.9-02.
* Publishing to Redis after commit — MT-1.9-03.
* Insert-only database permissions — MT-1.9-04.
* Catalog coverage tests — MT-1.9-05.
* The SSE endpoint, filters, resume, heartbeat — WP-1.10.
* The Task Transition history model — WP-1.5 (already exists; do not modify).

## Target paths
* `backend/apps/events/models.py`
* `backend/apps/events/migrations/`
* `backend/tests/events/test_event_model.py`
* WP changelog entry

## Acceptance criteria
- [ ] The Event model carries exactly the Section 9.6 envelope fields (`id`, `type`,
  `project_id`, `task_id`, `occurred_at`, `actor`, `data`) plus the correlation id
  required by Section 12.5 — no invented or missing envelope fields (Section 20.5).
- [ ] A concurrency test proves `id` is strictly monotonic and unique, and is the value
  used as the SSE event id in Section 9.6.
- [ ] Migration applies cleanly on a fresh database and on the existing dev database.
- [ ] Reading events ordered by `id` yields a total order usable for replay
  (input to MT-1.10-03).
- [ ] Lint, type check and tests green in CI (Section 20.4 item 2); no secrets or
  environment-specific paths committed (item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`pytest backend/tests/events/test_event_model.py -v` — includes the concurrent-insert
monotonic-id test and envelope-field assertions derived from Section 9.6.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.5 — Audit trail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.9 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Primary-key strategy choice (native sequence vs explicit sequence column) affects
  replay behavior on rollback; the plan requires monotonic ids but does not forbid
  gaps — resume guarantees "no gaps, no duplicates" refer to delivery, not to
  contiguous ids. Document the chosen strategy in the changelog note.
* `actor` is a structured field (`type`, `ref`), not a free-text string — flattening it
  breaks the Section 9.6 envelope contract; review the migration carefully.
