# MT-4.2-02 — Implement project create/edit forms with status transitions

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.2-02 |
| Title | Implement project create/edit forms with status transitions |
| Parent WP | WP-4.2 — Project switcher, project CRUD, manifest and tokens UI (Milestone M4) |
| Requirements | FR-PRJ-01 (create, read, update, pause, archive; auto-assigned `PID` ids), FR-WEB-09 (project policy and rules editor) |
| Priority | M |
| Dependencies | MT-4.2-01 (list/switcher), WP-4.1 (forms tooling, generated client, error mapping), WP-1.3 (project/policy/rules endpoints) |
| Parent sections | 13.1 (Project settings), 13.3, 19 (WP-4.2), 20.4, 20.5 |

## Context
FR-PRJ-01 covers create, read, update, pause and archive with auto-assigned `PID`
ids, and FR-WEB-09 adds the project policy and rules editor — Section 13.1 places
these in the Project settings route ("Policy editor, rules editor, manifest download,
agent token management"). The endpoints are `POST /projects`, `GET/PATCH
/projects/{pid}`, and `POST /tasks/{id}/transition`-style transitions at project
level via PATCH/status semantics as WP-1.3 exposes them (Section 9.2 lists project
CRUD and policy endpoints; Owner caller). This slice builds the forms: create, edit,
and the status transitions, plus the policy/rules editors that feed
`system_prompt_rules` consumed by the bridge (WP-2.7).

## Inputs / Prerequisites
* Parent plan Section 9.2 — `POST /projects`, `GET/PATCH /projects/{pid}`,
  `GET/PATCH /projects/{pid}/policy`; Owner-only authorization (Section 12.2).
* Parent plan FR-PRJ-01, FR-WEB-09 — functional scope.
* Parent plan Section 13.1 — Project settings route; Section 13.3 — shared validated
  forms, canonical error mapping, generated client.
* WP-4.1 — form/validation foundation and typed client; WP-1.3 — backend registry,
  policy and rules storage.
* WP-2.7 consumer note: `system_prompt_rules` edited here are injected by the bridge
  (Section 10.6).

## Scope (in)
* Create-project form: name and required fields per the API; on success the response
  supplies the auto-assigned `PID` (FR-PRJ-01), shown to the Owner, with navigation
  to the new project (flow continues in MT-4.2-03 for manifest download).
* Edit form for an existing project (`PATCH /projects/{pid}`): name and mutable
  fields, with optimistic-safe save (server truth wins on `VERSION_CONFLICT`, per
  Section 13.2's rollback discipline) and canonical error mapping.
* Status transitions UI: pause/resume and archive actions for projects exactly as
  the backend exposes them; destructive/archive actions require confirmation
  dialogs; unavailable transitions are not offered (server re-validates anyway).
* Policy and rules editors (FR-WEB-09) in Project settings: policy fields edited via
  `GET/PATCH /projects/{pid}/policy`, rules via the project rules field
  (`system_prompt_rules`), both validated with shared schemas and saved with
  success/error feedback.
* Loading/saving/error/permission-denied states; component tests for create, edit,
  transitions (including conflict rollback) and both editors.

## Out of scope
* Project list/switcher — MT-4.2-01.
* Manifest download/copy — MT-4.2-03.
* Agent token management UI — MT-4.2-04.
* Backend validation and state machine for project statuses — WP-1.3.
* Task-level transitions (drag-and-drop) — WP-4.4/Section 13.2.
* Auto-assigning `PID` client-side — the backend assigns it (FR-PRJ-01).

## Target paths
* `web/` (project forms, settings editors, routes)
* `web/` tests (component tests)
* WP changelog entry

## Acceptance criteria
- [ ] Create flow succeeds against `POST /projects`, displays the backend-assigned
  `PID`, and the new project appears in the MT-4.2-01 list after invalidation
  (FR-PRJ-01).
- [ ] Edit flow saves via `PATCH /projects/{pid}`; a simulated `VERSION_CONFLICT`
  rolls back with a friendly message (Section 13.2/13.3 error mapping,
  Section 9.2 catalog).
- [ ] Pause/archive actions exist with confirmation and only offer transitions the
  server permits; server rejection surfaces as a structured friendly error.
- [ ] Policy editor and rules editor (FR-WEB-09) load current values and save via
  their endpoints; rules text is preserved verbatim on round-trip (Section 10.6
  consumer expectation).
- [ ] All forms use shared validation schemas and the generated client only
  (Section 13.3, NFR-11); tests pass in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the project form component tests in `web/` (e.g.
`npm test -- project-forms`), asserting create/PID display, edit conflict rollback,
transition confirmation gating, and policy/rules editor round-trips.

## Attachments
* [Section 13.1 — Information architecture](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-PRJ-01 / FR-WEB-09 — Requirements](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Policy fields have sensitive defaults (thresholds, `auto_complete_enabled`);
  editors must show current server values, never client-invented defaults — a
  wrong default could silently weaken review requirements.
* Rules editor round-trip must not reformat owner text (whitespace/markdown), or the
  bridge will inject altered policy (WP-2.7 merge expectation).
