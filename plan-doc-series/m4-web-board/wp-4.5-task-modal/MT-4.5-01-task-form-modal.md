# MT-4.5-01 — Implement the task form modal with field validation

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-01 |
| Title | Implement the task form modal with field validation |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03 |
| Priority | M |
| Dependencies | WP-4.3 (board entry points), WP-4.1 (typed API client, theming), WP-1.4 (task CRUD endpoint) |
| Parent sections | 13.2, 13.3, 8.2 (T1), 9.2, 19 (WP-4.5), 20.4, 20.5 |

## Context
Section 13.2 defines the task modal: "title, markdown editor with preview,
acceptance criteria list editor, target-scope editor with glob validation, test
command, priority, dependencies picker, attachment dropzone with per-file processing
status." FR-WEB-03 is the task create/edit modal with attachment uploader and
progress. This first slice builds the modal shell and its core field validation —
the container the specialized editors (MT-4.5-02..04) and the uploader
(MT-4.5-05) slot into. Creation follows T1 (`*new*` → `draft`, actor O, guard:
project active), served by `POST /projects/{pid}/tasks` (Section 9.2); edits go
through `PATCH /tasks/{id}`.

## Inputs / Prerequisites
* Parent plan Section 13.2 — modal field list (verbatim).
* Parent plan Section 13.3 — forms validated with shared schemas; errors mapped from
  canonical codes to friendly messages.
* Parent plan Section 8.2 T1 — creation lands in `draft`; Section 9.2 — tasks
  endpoints.
* WP-1.4 — task CRUD backend, required-field rules.
* WP-4.1 — typed client and shared UI primitives (dialogs, theming).

## Scope (in)
* The task modal component: open from the board (create) and from a card/detail
  (edit), with the Section 13.2 field set as the layout scaffold — placeholders
  wired for markdown, criteria, scope, dependencies and dropzone, implemented in
  MT-4.5-02..05.
* Core fields implemented here: title (required), test command, priority — with
  client-side validation from shared schemas (Section 13.3), matching backend
  required-field rules from WP-1.4.
* Create/edit submission through the typed client (`POST /projects/{pid}/tasks` →
  `draft` per T1; `PATCH /tasks/{id}` for edits), with the API's canonical errors
  mapped to friendly messages (Section 13.3); unsaved-change protection on modal
  close.
* Accessibility: modal keyboard navigation, focus trap, announced validation errors
  (Section 13.4).
* Component tests: open/close (create and edit), required-field validation,
  successful create lands a `draft` card, API error mapping, keyboard operation.

## Out of scope
* Markdown editor with preview — MT-4.5-02.
* Acceptance-criteria and target-scope glob editors — MT-4.5-03.
* Dependencies picker — MT-4.5-04.
* Attachment uploader and processing status — MT-4.5-05.
* The publish action — MT-4.5-06.
* Backend validation and task CRUD — WP-1.4.

## Target paths
* `web/` — task form modal (shell, core fields, validation, submit wiring)
* `web/tests/` — modal component tests
* WP changelog entry

## Acceptance criteria
- [ ] The modal exposes the full Section 13.2 field set as a wired scaffold, with
  title, test command and priority implemented and validated here.
- [ ] Create submits via the typed client to `POST /projects/{pid}/tasks` and the new
  task appears as `draft` (T1; FR-WEB-03).
- [ ] Edit loads current values into the same modal and saves via `PATCH /tasks/{id}`.
- [ ] Client validation uses shared schemas; server `VALIDATION_ERROR` (and other
  catalog codes) map to friendly messages with field-level feedback
  (Section 13.3).
- [ ] Modal is keyboard-operable with focus management (Section 13.4); unsaved
  changes prompt before close.
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`npm test -- -t task-form-modal` — assert scaffold completeness, validation messages,
create→`draft` flow, edit round trip, canonical error mapping, and keyboard
operation; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (task modal)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Client and server validation rules drift easily — derive both from the same
  field contract (WP-1.4's required fields) and keep the server as the gate.
* The modal is one component with six sub-slices; resist implementing editors
  "inline" here — sizing rules (Section 20.3) keep UI tasks split by concern.
* Publishing is intentionally not part of create — a saved task must sit in `draft`
  (T1/T2 split), never auto-publish (MT-4.5-06 owns T2).
