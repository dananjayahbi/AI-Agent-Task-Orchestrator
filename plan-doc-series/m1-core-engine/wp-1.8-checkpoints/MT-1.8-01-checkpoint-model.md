# MT-1.8-01 — Create the Task Checkpoint Model with Kind and Token Usage Fields

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.8-01 |
| Title | Create the Task Checkpoint model with kind and token_usage fields |
| Parent WP | WP-1.8 — Checkpoints and token usage (Milestone M1) |
| Requirements | FR-LEA-03, P8, G-11, G-17 |
| Priority | M |
| Dependencies | WP-1.4 complete (task model); WP-1.1 (model/migration conventions) |
| Parent sections | 7.2 (Task Checkpoint), 3 (glossary), 8.6, 19 (WP-1.8), 20.4, 20.5 |

## Context
Section 7.2 fixes the Task Checkpoint entity: `id` (UUID), `task_id`,
`attempt_number`, `session_id`, `timestamp` (server), `message`, `percent` (0-100,
nullable), `token_usage` (JSON), `kind` (`progress` / `liveness` / `system`). The
glossary defines a Checkpoint as "a progress report from an agent" that "also extends
the lease"; G-11 makes the checkpoint stream the v1 live feed, and G-17 makes
checkpoints the (default) only lease-extension path. WP-1.8's first slice is the
model; everything else in the WP hangs off it.

## Inputs / Prerequisites
* Parent plan Section 7.2 — Task Checkpoint field list (copy by reference; do not
  extend).
* Section 7.4 — integrity constraints; P8 — checkpoints are never edited
  (append-only like history).
* Section 8.6 — `last_checkpoint_at` on the Task and the stalled indicator keyed on
  `progress` checkpoints.
* Section 19 (WP-1.8): deliverables "checkpoint model, endpoints, history listing
  with pagination"; acceptance "percent bounds enforced".
* WP-0.5-04 — cursor pagination conventions (for MT-1.8-04, informs indexing here).

## Scope (in)
* Create the Task Checkpoint model with exactly the Section 7.2 fields: UUID PK,
  FK to Task, `attempt_number`, bridge `session_id`, server-side `timestamp`,
  `message`, `percent` bounded 0–100 nullable, `token_usage` JSON, `kind` constrained
  to `progress` / `liveness` / `system` (ADR-010-style canonical values).
* Migration with an index supporting per-task reverse-chronological listing
  (cursor pagination, WP-0.5-04) for MT-1.8-04.
* Append-only discipline at the application layer (P8): no update/delete paths;
  tests assert immutability and field constraints (percent out of range rejected,
  unknown `kind` rejected).
* Provide the task-side touch point the endpoint will use: updating
  `Task.last_checkpoint_at` (Section 7.2) when a checkpoint is stored — defined
  here, invoked by MT-1.8-03.
* Tests: create/read constraints, percent bounds, kind enum, append-only, index
  presence usable by the listing query.
* Add a WP changelog note.

## Out of scope
* Ownership/fencing validation — MT-1.8-02.
* The POST endpoint, lease extension and event emission — MT-1.8-03.
* Listing endpoint and pagination — MT-1.8-04.
* The bridge `log_task_checkpoint` tool and its `next_checkpoint_due` hint —
  WP-2.6.
* Token usage aggregation/reporting UI — WP-4.6 (fields stored here only).
* Retention of checkpoints (OQ-10, 180 days after completion) — WP-6.x.
* DB-role insert-only grants — MT-1.9-04 pattern (app-level only here, same caveat).

## Target paths
* `backend/apps/tasks/` (Task Checkpoint model + migration)
* `backend/tests/` (model and constraint tests)
* WP changelog entry

## Acceptance criteria
- [ ] The model matches Section 7.2 field-for-field, including `kind`
  (`progress`/`liveness`/`system`) and `token_usage` JSON (Section 20.5).
- [ ] `percent` enforces 0–100 bounds and nullability (WP-1.8 acceptance: "percent
  bounds enforced").
- [ ] Rows are append-only at the application layer (P8) with server-side
  `timestamp`.
- [ ] `Task.last_checkpoint_at` update point exists and is covered by a test
  (Section 7.2, Section 8.6 stalled indicator input).
- [ ] Migration applies/reverses cleanly (Section 18 migration check; Section 20.4
  item 2); listing index present for MT-1.8-04.
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k checkpoint_model -q` and confirm field constraints
(percent bounds, kind enum, JSON token_usage), append-only behavior, and the
`last_checkpoint_at` touch point; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Task Checkpoint entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics (stalled indicator)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `token_usage` is a free JSON blob per Section 7.2 — do not invent a schema beyond
  the plan; if the bridge (WP-2.6) needs a fixed shape, raise an OQ first so web and
  mobile render one contract.
* `attempt_number` links a checkpoint to a specific claim attempt — denormalized
  deliberately so pre-reclaim checkpoints stay attributable; ensure it is copied at
  write time (MT-1.8-03), not joined lazily.
