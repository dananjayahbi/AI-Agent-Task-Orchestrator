# MT-4.5-04 — Implement the dependencies picker

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-04 |
| Title | Implement the dependencies picker |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03 |
| Priority | M |
| Dependencies | MT-4.5-01 (modal scaffold), WP-4.3 (board/task list data), WP-1.4 (task CRUD, dependencies) |
| Parent sections | 13.2, 8.2 (T2, T4), 9.2, 19 (WP-4.5), 20.4, 20.5 |

## Context
Section 13.2's modal includes a "dependencies picker". Dependencies matter twice in
the state machine: T2 (publish) guards "dependencies exist", and T4 (claim) guards
"dependencies completed" — a `pending` task with unmet dependencies is unclaimable
(`DEPENDENCY_UNMET`, Section 9.2/10.5). The picker is how the Owner curates that
graph (decomposers set `depends_on` via `create_draft_task` — WP-3.8 — but the Owner
edits here). Project scoping is absolute: only this project's tasks are pickable
(zero-bleed, Section 12.1).

## Inputs / Prerequisites
* Parent plan Section 13.2 — dependencies picker requirement.
* Parent plan Section 8.2 — T2/T4 dependency guards.
* Parent plan Section 9.2 — tasks endpoints and `DEPENDENCY_UNMET` catalog code.
* WP-1.4 — how `depends_on` is stored/validated server-side.
* WP-4.3 — task listing/query infrastructure to populate choices.
* MT-4.5-01 — modal scaffold and shared validation (Section 13.3).

## Scope (in)
* A dependencies picker in the task modal: search/select tasks of the bound project
  to add as dependencies; chips/list of current dependencies with removal; excluded
  self-selection and duplicates.
* Data source: the typed client's project task list (Section 9.2
  `GET /projects/{pid}/tasks`), paginated/searchable for large projects — the picker
  must not load 10k tasks eagerly (Section 13.4 performance posture).
* Feedback on unmet dependencies: display each dependency's state so the operator
  understands why publish/claim may be blocked; map `DEPENDENCY_UNMET` and
  `VALIDATION_ERROR` server responses to friendly messages (Section 13.3).
* Round trip: dependencies persist through save/reload; removal on edit clears them
  server-side.
* Component tests: add/remove/search, self and duplicate rejection, cross-project
  tasks absent from choices, save→reload fidelity, `DEPENDENCY_UNMET` friendly
  mapping when surfaced.

## Out of scope
* Creating dependencies as part of `create_draft_task` (decomposer flow) — WP-3.8.
* Enforcing dependency completion at claim — WP-1.6 (T4 guard).
* Dependency-graph visualization (DAG views) — not specified in the plan; out of
  scope.
* Backend storage/validation of `depends_on` — WP-1.4.

## Target paths
* `web/` — dependencies picker component and modal integration
* `web/tests/` — picker component tests
* WP changelog entry

## Acceptance criteria
- [ ] The modal exposes a dependencies picker listing only the bound project's tasks
  (Section 13.2; zero-bleed posture Section 12.1).
- [ ] Dependencies add, remove and persist through save/reload; self-selection and
  duplicates are impossible.
- [ ] Each dependency's current state is visible, so T2/T4 blocking conditions are
  understandable before publish/claim (Section 8.2).
- [ ] `DEPENDENCY_UNMET` and other catalog responses map to friendly messages
  (Sections 9.2, 13.3).
- [ ] Choices load search-backed/paginated — no eager full-project fetch
  (Section 13.4).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`npm test -- -t dependencies-picker` — assert project-scoped choices, add/remove
round trip, self/duplicate rejection, state badges, error mapping and lazy search
loading; then the full web suite stays green.

## Attachments
* [Section 8.2 — Transition table (T2, T4 guards)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Key components (task modal)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Cycles (A depends on B depends on A) are the classic dependency bug — the plan
  does not state whether the server rejects them; implement the picker's obvious
  guards (no self) and raise cycle handling as an open question if WP-1.4 does not
  define it, rather than silently allowing a deadlock.
* Picking across projects must be impossible, not just filtered — enforce in the
  query, not only in UI filtering (Section 12.1).
* Stale dependency states in the picker come from cached lists — refresh or use the
  SSE patches (WP-4.3) so badges do not mislead at publish time.
