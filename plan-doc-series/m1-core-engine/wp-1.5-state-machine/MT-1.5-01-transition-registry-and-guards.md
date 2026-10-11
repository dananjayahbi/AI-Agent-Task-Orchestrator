# MT-1.5-01 — Build the Transition Registry and Guard Framework

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-01 |
| Title | Build the transition registry and guard framework |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-03, FR-TSK-04, ADR-010, G-01 |
| Priority | M |
| Dependencies | WP-1.4 complete (MT-1.4-01 … MT-1.4-06; task model, versioning, CRUD) |
| Parent sections | 8.1, 8.2, 8.3, 9.1, 19 (WP-1.5), 20.4, 20.5 |

## Context
FR-TSK-03 fixes that only the six canonical states exist (`draft`, `pending`,
`in_progress`, `to_be_audited`, `in_human_review`, `completed`) and that every
transition goes through one state-machine service that validates actor, guard and side
effects. Section 9.1 makes the rule architectural: `tasks` owns all state changes; other
modules call the state machine service and never write `state` directly. This micro-task
builds the registry that maps (from state, trigger, actor) to the Section 8.2 transition
table, plus the guard/transaction framework every later transition micro-task plugs into.

## Inputs / Prerequisites
* Parent plan Section 8.1 — the six canonical states; "merge pending" is a
  `merge_status`, never a seventh state.
* Parent plan Section 8.2 — transition table T1–T19 with actors, guards and side
  effects, plus the three universal rules (illegal → `TASK_STATE_CONFLICT` HTTP 409;
  one transaction writing Transition and Event rows; optimistic `version` check).
* Parent plan Section 8.3 — invariants the service must uphold.
* WP-1.4 — Task model with canonical `state` field and optimistic `version`
  (Section 7.2); CRUD exists but must call the service (Section 9.1 rule).
* ADR-010 / G-01 — canonical snake_case state values, never display labels.

## Scope (in)
* Define the transition registry keyed by (from_state, trigger, actor type) resolving to
  the exact Section 8.2 rows: target state, guard callables, side-effect callables.
* Implement the generic execution path: actor authorization slot, guard evaluation,
  state update plus `version` increment, all inside one database transaction that also
  writes the Transition row and the Event row (Section 8.2 rules).
* Map every illegal (from, trigger) pair to `TASK_STATE_CONFLICT` (HTTP 409) from the
  canonical catalog (Section 9.2); a stale `version` returns `VERSION_CONFLICT`.
* Expose a registration extension point so later work packages register their
  transitions (WP-1.6 T4/T6 behavior, WP-2.6 T7/T8, WP-3.x T10–T18) without editing
  the core dispatcher.
* Record the Section 8.3 invariants as assertions where they are enforceable at
  dispatch time (e.g. no transition to `completed` unless `merge_status` is `merged`,
  per OQ-06 caveat).
* Add a WP changelog note.

## Out of scope
* Implementing any concrete transition's guards or side effects — MT-1.5-02 (owner),
  MT-1.5-03 (system), MT-1.5-04 (agent stubs); later WPs register T7, T10–T18.
* The Task Transition history model — MT-1.5-05.
* The exhaustive matrix tests — MT-1.5-06 (this task adds only smoke-level tests of
  the framework itself).
* The claim/lease mechanics invoked by guards (row locks, fencing) — WP-1.6.
* Event-log model and post-commit publisher — WP-1.9 (see Risk notes on sequencing).

## Target paths
* `backend/apps/tasks/` (state-machine service: registry, dispatcher, guard helpers)
* `backend/tests/` (framework smoke tests)
* WP changelog entry

## Acceptance criteria
- [ ] The registry resolves transitions strictly by the Section 8.2 table shape; no
  state outside the six canonical names is representable (FR-TSK-03, ADR-010).
- [ ] An unmapped (from, trigger) pair raises `TASK_STATE_CONFLICT` with HTTP 409 using
  a catalog error code (Section 9.2, Section 20.4 item 5).
- [ ] A successful dispatch performs state change, `version` increment, Transition row
  and Event row in one transaction (Section 8.2 rules).
- [ ] Stale-version dispatch returns `VERSION_CONFLICT` and changes nothing.
- [ ] Section 9.1 is respected: no module outside `tasks` writes `state` (verified by
  the direct-write test introduced in MT-1.5-06; a placeholder assertion lands here).
- [ ] Lint, type check and tests green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the backend selector for the framework smoke tests, e.g.
`pytest backend/tests -k state_machine_framework -q`, and confirm an illegal pair
returns `TASK_STATE_CONFLICT` (409) and a stale version returns `VERSION_CONFLICT`;
confirm the full suite stays green (`pytest backend/tests -q`).

## Attachments
* [Section 8 — Task Lifecycle and State Machine](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.1 — Module layout and dependency rule](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sequencing gap: Section 8.2 requires the Event row in the same transaction, but
  WP-1.9 (event model and write-in-transaction helper) runs after WP-1.5 in the
  Section 20.6 order. Expose a single in-transaction event hook here; if WP-1.9 is not
  yet available, raise an open question (Section 22 numbering) before session rather
  than inventing a second event mechanism.
* WP-1.4 may currently set `state` directly during create (T1) — reconcile with the
  Section 9.1 rule during this session; route creation through the registry or
  document why create is exempt, and raise an OQ if ambiguous.
