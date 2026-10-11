# MT-4.10-04 — Implement the rules editor with rules-block preview

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.10-04 |
| Title | Implement the rules editor with rules-block preview |
| Parent WP | WP-4.10 — Audit log viewer and policy editor (Milestone M4) |
| Requirements | FR-WEB-09, FR-PRJ |
| Priority | S |
| Dependencies | MT-4.10-03 (settings shell); WP-3.1 complete (project `system_prompt_rules` persistence); WP-2.7 complete (rules templates) |
| Parent sections | 13.1 (Project settings: rules editor), 7.2 (Project `system_prompt_rules`), 10.6 (rules block), 9.2 (`PATCH /projects/{pid}`), 19 (WP-4.10), 20.3, 20.4, 20.5 |

## Context
Section 13.1's Project settings row includes the "rules editor"; Section 19 WP-4.10
delivers a "rules editor with preview of the rules block." Section 10.6 defines what
agents actually receive: the eight standard rules (branch discipline, stay in
`target_scope`, run the test command, commit before submission, checkpoint cadence,
attachments/repo text are data not instructions, never touch other projects, clear
execution summary), with project-specific rules from `system_prompt_rules` appended —
and for auditors a different set (full test/lint matrix, verify each criterion, never
modify the branch, honest confidence). The block is "delivered on connect and on every
claim" (Section 10.6), and `system_prompt_rules` is the Project's markdown field
(Section 7.2), saved through `PATCH /projects/{pid}` (Section 9.2).

## Inputs / Prerequisites
* Parent plan Section 10.6 — the standard rules and the append model this preview
  must mirror (built/delivered by WP-2.7, MT-2.7-01/02).
* Parent plan Section 7.2 — Project `system_prompt_rules` (markdown text).
* Parent plan Section 9.2 — `PATCH /projects/{pid}` for saving.
* WP-2.7 — rules templates and project-rules merging (the backend/bridge-side truth
  the preview approximates).
* Section 13.3 — form validation and error-mapping discipline.

## Scope (in)
* A markdown editor for `system_prompt_rules` in Project settings with editing,
  basic validation (length/type) and save via `PATCH /projects/{pid}` — canonical
  error mapping on failure (Section 20.4 item 5).
* A **rules-block preview** showing what an agent will receive: the eight standard
  Section 10.6 rules, then the project's `system_prompt_rules` appended beneath a
  clear separator, plus a toggle for the auditor variant's rules (Section 10.6
  auditor half). The preview is labeled as illustrative of the next connect/claim
  delivery (Section 10.6 "delivered on connect and on every claim").
* Preview rendering treats content as inert markdown/data — never executed
  (Principle P10) — and the standard-rule text is referenced from the WP-2.7
  templates rather than duplicated ad hoc (single source, Section 20.5).
* States: loading (initial value), saving, error, read-only for non-Owners
  (Section 12.2), unchanged (pristine) indicator.
* Component tests: editor loads/saves `system_prompt_rules`, preview shows standard
  rules + appended project rules + auditor toggle, inert rendering of markdown,
  save error mapping, read-only state.
* A WP changelog note.

## Out of scope
* Backend storage/merge/delivery of the rules block — WP-3.1 / WP-2.7 (Section 10.6).
* The claim-response/instructions delivery channels — WP-2.7 (MT-2.7-03).
* Policy editor fields — MT-4.10-03 (same settings shell, different field).
* Rules content changes — Section 10.6's standard rules are fixed (edit only the
  project-specific part).

## Target paths
* `web/` (rules editor and preview in project settings)
* `web/` tests (editor and preview tests)
* WP changelog entry

## Acceptance criteria
- [ ] `system_prompt_rules` is editable and saved through `PATCH /projects/{pid}`
  (Sections 7.2, 9.2) with canonical error mapping (Section 20.4 item 5).
- [ ] The preview shows the eight standard Section 10.6 rules plus the project rules
  appended, with an auditor-variant toggle — matching the delivery model the agents
  receive (Sections 10.6, 19 WP-4.10 "preview of the rules block").
- [ ] Standard-rule text comes from the WP-2.7 templates/Section 10.6 source — not a
  divergent re-typed copy (Section 20.5 traceability).
- [ ] Preview content renders as inert data — no script execution or unsafe HTML
  (Principle P10; Section 13.3 form discipline).
- [ ] Non-Owner sessions are read-only (Section 12.2); loading/saving/error states
  handled (Section 20.3).
- [ ] Effect timing is stated to the user consistent with Section 10.6 (applies on
  next connect/claim) — no false "instantly rewrites running sessions" claim.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the rules editor (for example `npm test -- -t
"rules editor"`) and confirm load/save of `system_prompt_rules`, preview composition
(standard + project + auditor toggle), inert markdown rendering, error mapping, and
read-only state; then the full web suite stays green.

## Attachments
* [Section 10.6 — Rules block (delivered on connect and on every claim)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.10 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Entities (Project `system_prompt_rules`)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The preview inevitably duplicates the composition logic that WP-2.7 runs on the
  bridge — keep it thin (fixed standard template + appended markdown) and add a
  cross-check note so a Section 10.6 change updates both (drift risk; Section 20.5).
* Live sessions cache project context at startup (Section 10.3 step 5) while claims
  re-deliver rules (Section 10.6) — the preview's "next connect/claim" wording must
  reflect that nuance; do not promise mid-session updates.
* Free-form markdown invites huge inputs — enforce a sane server-validated limit via
  `VALIDATION_ERROR` rather than inventing a client-only cap that diverges from the
  backend.
