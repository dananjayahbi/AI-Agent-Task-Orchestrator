# MT-4.10-03 — Implement the policy editor form with preset selection

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.10-03 |
| Title | Implement the policy editor form with preset selection |
| Parent WP | WP-4.10 — Audit log viewer and policy editor (Milestone M4) |
| Requirements | FR-WEB-09, FR-PRJ |
| Priority | S |
| Dependencies | WP-3.1 complete (policy model, validation, preset library); WP-4.2 complete (project settings shell); WP-4.1 complete (generated API client) |
| Parent sections | 13.1 (Project settings: policy editor), 7.2 (Project Policy fields), 9.2 (`GET/PATCH /projects/{pid}/policy`), 9.4 (rules the fields drive), 19 (WP-3.1, WP-4.10), 20.3, 20.4, 20.5 |

## Context
Section 13.1's Project settings row includes the "Policy editor." Section 19 WP-4.10
delivers a "policy form with presets" and accepts that "policy edits take effect on
the next claim and are logged." The form's field set is exactly Section 7.2's Project
Policy table: `lease_duration_minutes` (45), `lease_max_total_minutes` (240),
`lease_extension_mode` (`checkpoint_only` / `checkpoint_and_liveness`),
`max_retries` (3), `max_concurrent_tasks` (1, G-26), `autonomous_diff_threshold_lines`
(250), `auditor_min_confidence` (1–5, default 4), `critical_path_globs`,
`migration_path_globs`, `sensitive_config_globs`, `auto_complete_enabled` (true),
`merge_strategy` (`squash` default; see OQ-06 for `manual`), `branch_prefix`
(`feat/{PID}-`, G-09), `audit_required_default` (true), `stalled_after_minutes` (20).
Presets come from WP-3.1's preset library (at least Django, Next.js, Flutter —
Section 19 WP-3.1).

## Inputs / Prerequisites
* Parent plan Section 7.2 — the full field table with types/defaults (the form's
  source of truth; Section 20.5).
* Parent plan Section 9.2 — `GET/PATCH /projects/{pid}/policy` endpoints.
* Parent plan Section 9.4 — which fields feed which rules (R2–R7, R9) — display help
  text by reference, do not re-derive rule logic.
* WP-3.1 — server-side validation (invalid globs rejected) and the preset library
  ("presets selectable at project creation" acceptance implies the library is
  reusable here).
* Section 19 WP-4.10 acceptance — edits take effect on next claim and are logged
  (Section 12.5 policy-edit events).

## Scope (in)
* A policy editor form in Project settings rendering every Section 7.2 Project Policy
  field with appropriate input types (numeric, enum select, glob text areas, boolean)
  and documented defaults shown as placeholders/help.
* Preset selection for the three glob fields: choose a WP-3.1 preset (Django,
  Next.js, Flutter) to populate `critical_path_globs` / `migration_path_globs` /
  `sensitive_config_globs`, with explicit user confirmation before overwriting
  existing values; presets may be combined with manual edits afterwards.
* Validation client-side mirroring WP-3.1's rules (glob syntax, ranges such as
  `auditor_min_confidence` 1–5, positive durations) with server `VALIDATION_ERROR`
  responses mapped to field errors (Section 9.2 catalog; Section 13.3 form
  discipline; Section 20.4 item 5).
* Save via `PATCH /projects/{pid}/policy` with optimistic concurrency handling
  (`version`/`VERSION_CONFLICT` refresh per Section 13.3); success feedback noting
  the effect timing (next claim — Section 19 WP-4.10 acceptance).
* Loading (initial values), saving, error and read-only (non-Owner) states
  (Section 20.3; Section 12.2: only Owner manages policy).
* Component tests: all fields render with fixture policy, preset application with
  overwrite confirmation, validation failures, save payload shape, conflict path,
  non-Owner read-only.
* A WP changelog note.

## Out of scope
* Server-side policy model, validation, preset library — WP-3.1.
* The rules editor (`system_prompt_rules`) — MT-4.10-04 (different field, different
  endpoint row).
* Manifest download/token management UI — MT-4.2-03/04.
* Policy engine evaluation — WP-3.4 (Section 9.4).
* Creating presets — WP-3.1 owns the library.

## Target paths
* `web/` (policy editor form in project settings)
* `web/` tests (form tests with fixture policy)
* WP changelog entry

## Acceptance criteria
- [ ] Every Section 7.2 Project Policy field appears in the form with its correct
  type and default shown — none added, dropped or renamed (Sections 7.2, 20.5).
- [ ] Preset selection populates the three glob fields from WP-3.1's library with
  overwrite confirmation (Section 19 WP-4.10 deliverable "policy form with
  presets").
- [ ] Saves go through `PATCH /projects/{pid}/policy` with validation errors mapped
  from canonical codes to fields (Sections 9.2, 13.3, 20.4 item 5).
- [ ] After a successful save the UI states edits take effect on the next claim —
  matching Section 19 WP-4.10 acceptance — and the audit trail entry is expected
  from the backend (Section 12.5), asserted in the API-level test if in scope of the
  same suite.
- [ ] Non-Owner sessions see a read-only form (Section 12.2 authorization matrix).
- [ ] Loading/saving/error/conflict states handled (Sections 20.3, 13.3).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the policy editor (for example `npm test -- -t
policy`) and confirm field completeness against Section 7.2, preset application with
confirmation, validation mapping, save payload, conflict and read-only paths; then
the full web suite stays green.

## Attachments
* [Section 7.2 — Entities (Project Policy)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.1 and WP-4.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine (field-to-rule mapping)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `merge_strategy` options: Section 7.2 lists three values while OQ-06 adds `manual`
  (decided per Section 19.1) — the select must offer exactly the values the backend
  accepts; verify against WP-3.1's implementation and flag the plan-doc mismatch
  (Section 20.5) rather than guessing.
* Help text can drift from Section 9.4 rule behavior — keep it pointer-style ("feeds
  R3", etc.) instead of prose that re-explains the engine.
* Preset overwrite is destructive to hand-tuned globs — confirmation is mandatory;
  also ensure unsaved edits are not lost on preset click (record UX decision).
