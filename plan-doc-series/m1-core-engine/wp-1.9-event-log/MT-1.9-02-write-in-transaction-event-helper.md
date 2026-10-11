# MT-1.9-02 — Implement the Write-in-Transaction Event Helper

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.9-02 |
| Title | Implement the write-in-transaction event helper |
| Parent WP | WP-1.9 — Event log and audit trail (Milestone M1) |
| Requirements | FR-SEC-03 |
| Priority | M |
| Dependencies | MT-1.9-01 (Event model exists) |
| Parent sections | 9.6, 12.5, 19.1 (WP-1.9), 9.3, 20.4, 20.5 |

## Context
Section 9.6 requires that every state-changing action writes an Event row **in the same
transaction** as the state change, so the event and the change commit or roll back
together. Section 19 (WP-1.9) acceptance states that every transition and token action
produces exactly one event. The helper is the single API through which all modules
write events, making that guarantee enforceable and testable.

## Inputs / Prerequisites
* MT-1.9-01 — the Event model with monotonic id and envelope fields.
* Parent plan Section 9.6 — event types and envelope.
* Parent plan Section 9.3 — the claim flow writes Transition and Event rows inside the
  claim transaction; the helper must fit this pattern (no publish, no side effects
  inside the transaction).
* Existing state-changing services: state machine service (WP-1.5), token issuance
  (WP-1.2), claim/release service (WP-1.6), sweeper (WP-1.7).

## Scope (in)
* A helper in the `events` module that appends an Event row to the caller's open
  transaction, filling the Section 9.6 envelope fields and the correlation id.
* Wire the helper into the state-transition service so every legal transition emits
  exactly one `task.*` event per Section 9.6, and into token actions (issuance,
  revocation, login) required by Section 12.5.
* Guarantees: exactly one event per action (no duplicates), zero events when the
  transaction rolls back, no network or Redis calls inside the transaction.
* Unit/integration tests proving the exactly-once and rollback behaviors for
  transitions and token actions (Section 19 WP-1.9 acceptance).

## Out of scope
* Post-commit Redis publishing — MT-1.9-03 (the helper must not publish; it only
  registers or writes rows).
* Emission sites belonging to later WPs (attachments WP-1.12, agent sessions WP-2.x,
  review/merge WP-3.x) — those WPs adopt the same helper when they land.
* Catalog completeness tests — MT-1.9-05.
* The SSE gateway — WP-1.10.

## Target paths
* `backend/apps/events/services.py` (write helper)
* `backend/apps/tasks/`, `backend/apps/leases/`, `backend/apps/accounts/` (call-site
  wiring: transition service, claim/release, token actions)
* `backend/tests/events/test_event_writes.py`
* WP changelog entry

## Acceptance criteria
- [ ] Every state transition produced by the state machine service writes exactly one
  Event row in the same transaction (Section 19 WP-1.9 acceptance).
- [ ] Every token action required by Section 12.5 (issuance, revocation, login) writes
  exactly one Event row in the same transaction.
- [ ] A forced rollback test proves no Event row survives the rolled-back transaction.
- [ ] The helper performs no Redis/network calls while the transaction is open
  (publish belongs to MT-1.9-03).
- [ ] Event payloads match the Section 9.6 envelope exactly (Section 20.4 item 6,
  Section 20.5).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/events/test_event_writes.py backend/tests/tasks/ -v` — proves
exactly-one-event per transition/token action and rollback behavior.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.3 — Claim algorithm (Transition and Event rows in one transaction)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.9 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The Section 9.6 catalog has no dedicated token type (`token.*` is absent), yet
  Section 12.5 and the WP-1.9 acceptance require token actions to emit an event.
  Do not invent a new type: raise a new OQ (next free `OQ-15+` id in Section 22)
  asking whether an existing type covers token events or the catalog must be extended
  first (Section 20.4 item 5 discipline: codes/types are added to the catalog first).
* Wiring call sites across three apps risks merge conflicts with concurrent WP work —
  keep each wiring change minimal and covered by the tests named above.
