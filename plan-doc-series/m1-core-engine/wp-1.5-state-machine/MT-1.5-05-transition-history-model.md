# MT-1.5-05 — Create the Append-Only Task Transition History Model with Insert-Only Permissions

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-05 |
| Title | Create the append-only Task Transition history model with insert-only permissions |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-04, P8 |
| Priority | M |
| Dependencies | MT-1.5-01 (registry writes Transition rows through the dispatcher) |
| Parent sections | 7.2 (Task Transition), 7.4 (item 5), 8.2, 12.5, 19 (WP-1.5), 20.4, 20.5 |

## Context
FR-TSK-04 requires every transition to be recorded immutably (who, when, from, to,
reason), principle P8 states history is append-only, and Section 7.4 item 5 makes
transition rows insert-only — no update or delete permissions at the application role
level. Section 7.2 fixes the fields: `id`, `task_id`, `from_state`, `to_state`,
`actor_type` (`owner` / `agent` / `system`), `actor_ref`, `reason_code`, `note`,
`timestamp`. This task creates that model and the application-level discipline that
keeps history immutable; the database role grants arrive with WP-1.9.

## Inputs / Prerequisites
* MT-1.5-01 — dispatcher already writes one Transition row per successful transition
  in the same transaction (Section 8.2 rule).
* Parent plan Section 7.2 — Task Transition field list (copy by reference; do not
  extend).
* Section 7.4 integrity constraint 5 — insert-only at application role level.
* Section 12.5 — audit trail expectations; Section 8.2 — reason/actor semantics.
* WP-1.1 conventions — model/migration patterns and error envelope usage.

## Scope (in)
* Create the Task Transition model with exactly the Section 7.2 fields, with
  `from_state`/`to_state` constrained to the six canonical state values
  (ADR-010) and `actor_type` constrained to `owner` / `agent` / `system`.
* Create the migration for the history table; indexed for per-task chronological
  reads (task detail transitions history, Section 13.1).
* Enforce append-only at the application layer: no update/delete APIs or manager
  methods; queryset mutations raising a hard error; the only write path is creation
  inside the state-machine transaction.
* Add tests proving update and delete attempts on transition rows fail, and that
  every dispatched transition produced exactly one row with actor, from, to, reason
  and timestamp (FR-TSK-04).
* Add a WP changelog note.

## Out of scope
* Database role grants (REVOKE UPDATE/DELETE) — MT-1.9-04 applies the insert-only
  permissions to transition and event tables together.
* The Event log model — WP-1.9.
* Exposing transitions history through the API/UI — web task detail (WP-4.6) consumes
  a listing that WP-1.15 hardening verifies; no endpoint invented here beyond what
  the tests need in-process.
* Retention of history — OQ-10 / WP-6.x.

## Target paths
* `backend/apps/tasks/` (Task Transition model + migration)
* `backend/tests/` (immutability and completeness tests)
* WP changelog entry

## Acceptance criteria
- [ ] The model matches Section 7.2 field-for-field; no extra or missing columns
  (Section 20.5 traceability).
- [ ] `from_state`/`to_state` accept only the six canonical states; `actor_type`
  accepts only the three canonical actor values (ADR-010).
- [ ] Update and delete of transition rows fail at the application layer (P8,
  Section 7.4 item 5).
- [ ] Every successful transition in tests writes exactly one history row with actor,
  when, from, to and reason populated (FR-TSK-04).
- [ ] Migration applies and reverses cleanly under the CI migration check
  (Section 18 quality gates; Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k transition_history -q` and confirm the immutability
tests fail any update/delete attempt, the completeness test finds one row per
dispatched transition, and field constraints reject non-canonical values; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Task Transition entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.4 — Integrity constraints](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Migrations are called out in Section 20.3 as never to be combined with unrelated
  logic — keep this migration model-only.
* Insert-only enforcement is split (app layer here, DB grants in MT-1.9-04); until
  both land, a raw SQL writer could still mutate history — note this in the changelog
  so the gap closes with WP-1.9.
* `reason_code` values span transition reasons and review reasons; constrain to the
  Section 8.4 enum plus transition trigger codes, and raise an OQ if a new reason
  would be needed rather than inventing one.
