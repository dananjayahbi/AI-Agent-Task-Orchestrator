# MT-1.5-04 — Implement Agent Transition Stubs T4/T6/T7/T8 for Later Wiring

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.5-04 |
| Title | Implement agent transition stubs T4/T6/T7/T8 for later wiring |
| Parent WP | WP-1.5 — State machine service and transition history (Milestone M1) |
| Requirements | FR-TSK-03, FR-TSK-04, FR-MCP-03 |
| Priority | S |
| Dependencies | MT-1.5-01 (registry and guard framework) |
| Parent sections | 8.2 (T4, T6, T7, T8), 8.4, 9.1, 19 (WP-1.5), 20.4, 20.5 |

## Context
WP-1.5's slice list ends with "agent transitions (stubs)". T4 (claim), T6 (voluntary
release), T7 (submit) and T8 (self-flagged/scope-violation submit) are dispatched by
the coder agent, but their real mechanics live in later work packages: T4/T6 in
WP-1.6 (lease and claim service), T7/T8 in WP-2.6 (checkpoint and submission tools)
with WP-1.15 hardening. Registering them now as stubs proves the MT-1.5-01 extension
point, lets the transition matrix tests (MT-1.5-06) enumerate the full table shape,
and makes every subsequent WP fill in behavior instead of restructuring the registry.

## Inputs / Prerequisites
* MT-1.5-01 — registry with its registration extension point.
* Parent plan Section 8.2 rows T4, T6, T7, T8 — exact from/to, actors, guards and
  side effects to be documented on each stub.
* Section 8.4 — canonical review reasons `self_flagged` and `scope_violation` used by
  T8.
* WP-1.4 — Task fields referenced by the guards (`attempt_number`,
  `failure_retry_count`, lease fields).

## Scope (in)
* Register **T4** `pending` → `in_progress` (actor C): guards per table (project
  active; token scope matches; dependencies completed; `max_concurrent_tasks` not
  exceeded; row lock won); side effects per table (set worker, session, lease,
  `attempt_number` + 1; emit `task.claimed`). Stub: structure, guard contracts and
  docstrings present; behavior delegated to WP-1.6, dispatch blocked with a clear
  not-yet-implemented error until wired.
* Register **T6** `in_progress` → `pending` (actors C, O): guard — caller owns lease
  (or Owner override); side effects — clear worker, no failure increment. Stub as
  above; behavior lands in MT-1.6-04.
* Register **T7** `in_progress` → `to_be_audited` (actor C): guards per table (lease
  owner and not expired; resolution valid; `audit_required` true; not self-flagged;
  scope check ok); side effects — store resolution + patch, clear worker. Stub.
* Register **T8** `in_progress` → `in_human_review` (actors C, S): guard —
  `requires_human_attention` true or changed files outside scope; side effects —
  `review_reason` = `self_flagged` or `scope_violation` (canonical enum) plus push
  trigger. Stub.
* Tests asserting each stub is registered with the exact Section 8.2 shape and that
  dispatching it pre-wiring fails safely (no state change, no partial writes).
* Add a WP changelog note.

## Out of scope
* Claim/release/extension mechanics and the row-lock algorithm — WP-1.6 (T4, T6).
* Resolution storage, patch upload, scope evaluation — WP-2.6 / WP-3.2 (T7, T8).
* Transitions T10–T18 (audit, review, merge) — registered by WP-3.x; the same stub
  pattern demonstrated here is their template.
* Bridge-facing tool contracts (`claim_task`, `submit_task_resolution`) — WP-2.4 /
  WP-2.6.

## Target paths
* `backend/apps/tasks/` (stub registrations for T4, T6, T7, T8)
* `backend/tests/` (stub registration tests)
* WP changelog entry

## Acceptance criteria
- [ ] T4, T6, T7, T8 are present in the registry with the exact from/to states,
  actors, guards and side-effect descriptions of Section 8.2 (no paraphrased
  semantics; Section 20.5 traceability).
- [ ] Dispatching any stub before its wiring returns a deterministic not-wired error
  and leaves task state, `version` and history untouched.
- [ ] T8's stub documents `review_reason` values strictly as `self_flagged` /
  `scope_violation` from the Section 8.4 enum.
- [ ] WP-1.6 and WP-2.6 can replace stub behavior through the registration extension
  point without modifying the dispatcher (verified by the test asserting registration
  override).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k agent_transition_stubs -q` and confirm all four stubs
match the Section 8.2 table shape, pre-wiring dispatch fails without side effects,
and an override registration replaces a stub; then the full suite stays green.

## Attachments
* [Section 8.2 — Transition table (T4, T6, T7, T8)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Stubs that raise "not wired" can mask integration gaps if a later WP forgets to
  override — the matrix tests in MT-1.5-06 must mark stubbed transitions explicitly
  so WP-1.15 can re-check wiring status.
* T7's "resolution valid / scope check ok" guards are specified behaviorally in
  Section 8.2 but their parameters come from WP-2.6/WP-3.2 data — keep guard
  signatures stable here; any contract disagreement becomes an OQ before wiring.
