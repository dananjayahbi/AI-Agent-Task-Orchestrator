# MT-1.5-02 — Implement Owner Transitions T2 (Publish), T3 (Unpublish), T19 (Archive)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-02 |
| Title | Implement owner transitions T2 (publish), T3 (unpublish), T19 (archive) |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-03, FR-TSK-04, ADR-010 |
| Priority | M |
| Dependencies | MT-1.5-01 (registry and guard framework) |
| Parent sections | 8.2 (T2, T3, T19), 9.2, 19 (WP-1.5), 20.4, 20.5 |

## Context
Section 8.2 gives the owner (web/mobile) three transitions surfaced by the
`POST /tasks/{id}/transition` endpoint (publish, unpublish, archive): T2 moves `draft`
→ `pending`, T3 moves `pending` → `draft`, and T19 archives any non-`completed` task by
setting `archived_at` — an archived flag, not a seventh state. These are the first real
transitions registered on the MT-1.5-01 framework and the first guards with side effects
that visibility rules depend on.

## Inputs / Prerequisites
* MT-1.5-01 — registry, dispatcher, guard and transaction machinery in place.
* Parent plan Section 8.2 rows T2, T3, T19 — exact guards and side effects.
* WP-1.4 — Task fields (`acceptance_criteria`, `target_scope`, `test_command`,
  dependencies relation, `archived_at`) used by guards; attachments exist from WP-1.11
  later, so the T2 attachment guard degrades gracefully until then.
* Section 9.2 — `POST /tasks/{id}/transition` is Owner-caller; illegal transitions
  return `TASK_STATE_CONFLICT`.

## Scope (in)
* Register and implement **T2** `draft` → `pending` (actor O): guards — required
  fields valid, attachments `ready` (or override), dependencies exist; side effect —
  task becomes visible to agents.
* Register and implement **T3** `pending` → `draft` (actor O): guard — no active
  lease; side effect — hidden from agents.
* Register and implement **T19** any non-`completed` → archived flag (actor O): no
  guards; side effect — sets `archived_at`; hidden from boards by default (soft
  archive already modeled by WP-1.4).
* Actor checks: only the Owner role may dispatch these transitions; agent/system
  callers receive the framework's actor rejection.
* Unit tests covering each legal transition and its guard failures, asserting the
  Transition row records actor, from/to, reason and timestamp (FR-TSK-04).
* Add a WP changelog note.

## Out of scope
* The `POST /tasks/{id}/transition` HTTP wiring — WP-1.4 endpoints call the service;
  endpoint verification belongs to WP-1.15 hardening (only the service behavior is
  asserted here).
* Agent transitions T4/T6/T7/T8 — MT-1.5-04; system transitions T5/T9 — MT-1.5-03.
* Audit and review transitions T10–T18 — WP-3.x.
* Attachment readiness enforcement end-to-end — WP-1.11/WP-1.12 (guard accepts the
  "attachments ready or override" rule; no attachments exist yet).
* Archival visibility filters in list endpoints — WP-1.4 scope, re-verified in
  WP-1.15.

## Target paths
* `backend/apps/tasks/` (registrations and guards for T2, T3, T19)
* `backend/tests/` (owner transition tests)
* WP changelog entry

## Acceptance criteria
- [ ] T2, T3, T19 appear in the registry with the exact from/to states and actors of
  Section 8.2 (T19 treated as `archived_at` flag on any non-`completed` state).
- [ ] Each guard failure returns the canonical error (e.g. `TASK_STATE_CONFLICT` for
  wrong state; dependency guard surfaces `DEPENDENCY_UNMET`) — catalog codes only
  (Section 20.4 item 5).
- [ ] T3 refuses while an active lease exists; T19 refuses on `completed`.
- [ ] Every successful dispatch writes its Transition row with actor and reason
  (FR-TSK-04).
- [ ] Tests green in CI (Section 20.4 item 2); acceptance demonstrated by the named
  test command (Section 20.4 item 1).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k owner_transitions -q` and confirm: T2/T3/T19 happy paths
pass, each guard violation returns the expected catalog code, and Transition rows were
written; then the full suite (`pytest backend/tests -q`) stays green.

## Attachments
* [Section 8.2 — Transition table (T2, T3, T19)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Transition endpoint and error catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* T2's "attachments `ready` (or override)" guard references attachments that do not
  exist until WP-1.11 — implement the guard so it passes vacuously when the task has
  no attachments; do not invent an override flag beyond the plan (raise an OQ if an
  explicit override field is needed).
* "Dependencies exist" wording in T2 means dependency tasks exist and are completed
  (T4 guard says "dependencies completed") — confirm interpretation against Section
  8.2 during the session; ambiguity becomes an OQ, not a silent choice.
