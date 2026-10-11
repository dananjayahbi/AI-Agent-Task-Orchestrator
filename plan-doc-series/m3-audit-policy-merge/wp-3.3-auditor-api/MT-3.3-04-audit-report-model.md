# MT-3.3-04 — Create the Audit Report model with evidence JSON and confidence

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.3-04 |
| Title | Create the Audit Report model with evidence JSON and confidence |
| Parent WP | WP-3.3 — Auditor claim and verdict API (Milestone M3) |
| Requirements | FR-AUD-01, FR-AUD-02 |
| Priority | M |
| Dependencies | MT-3.2-01 (resolution to audit); MT-3.3-01/MT-3.3-03 (auditor session and lease) |
| Parent sections | 7.2 (Audit Report), 10.5 (evidence shape), 9.2 (audit-reports endpoint), 19 (WP-3.3), 20.4, 20.5 |

## Context
Section 7.2 defines the Audit Report entity: the auditor's structured record —
`evidence` JSON (commands run, exit codes, durations, changed files, diff stats, lint
results), `confidence` (1–5), `auditor_notes`, `proposed_verdict`, plus the two fields
the Policy Engine later fills: `policy_decision` and `policy_rule_results`. Section
10.5 fixes the auditor verdict input shape whose `evidence` object (commands with
label/command/exit_code, `lint_clean`) this model must be able to store. Owners read
reports via `GET /tasks/{id}/audit-reports` (Section 9.2) and the human review panel
(Section 13.2) renders them. This task creates the model and its read surface.

## Inputs / Prerequisites
* Parent plan Section 7.2 — Audit Report field list.
* Parent plan Section 10.5 — auditor verdict input JSON shape (evidence and
  `acceptance_criteria_results` structure) as the persistence contract; pointer, not
  re-derivation.
* MT-3.2-01 — `resolution_id` the report attaches to; MT-3.3-01 — `auditor_session_id`
  of the claiming auditor.
* Section 9.4 — `policy_decision` and `policy_rule_results` are engine outputs
  (nullable until WP-3.4 runs; see MT-3.4-06).

## Scope (in)
* Audit Report model exactly per Section 7.2: `id`, `task_id`, `resolution_id`,
  `auditor_session_id`, `evidence` (JSON), `confidence` (1–5 constrained), 
  `auditor_notes`, `proposed_verdict`, `policy_decision`, `policy_rule_results` (JSON),
  `created_at`.
* Evidence JSON persistence that round-trips the Section 10.5 evidence structure
  (commands array with exit codes, lint flag, changed files, diff stats as supplied)
  without reshaping or dropping fields.
* `GET /tasks/{id}/audit-reports` (Section 9.2, auditor/owner) returning a task's
  reports for the review panel and mobile review sheet.
* `policy_decision` and `policy_rule_results` stored as nullable — populated later by
  the engine (MT-3.4-06), never faked here.
* Unit tests: field parity with Section 7.2, evidence round-trip of the 10.5 shape,
  confidence range enforcement, listing order (newest first or by attempt — pick one,
  document it).
* Add a WP changelog note.

## Out of scope
* Accepting the verdict submission — MT-3.3-05.
* Evaluating rules or writing `policy_decision` / `policy_rule_results` — WP-3.4
  (MT-3.4-06).
* Bridge-side evidence validation and guidance — WP-3.5 (schema validation of the
  `submit_audit_verdict` payload).
* Rendering reports in review panels — WP-4.8 / WP-5.8.

## Target paths
* `backend/apps/audit/` (Audit Report model, serializer, report listing endpoint)
* `backend/` migrations (audit report table)
* `backend/tests/` (model and listing tests)
* WP changelog entry

## Acceptance criteria
- [ ] The model persists exactly the Section 7.2 Audit Report fields, nothing added
  or dropped (Section 20.5 traceability).
- [ ] `evidence` round-trips the Section 10.5 structure (commands with
  label/command/exit_code plus `lint_clean`) without loss (FR-AUD-02 structured
  evidence).
- [ ] `confidence` is constrained to 1–5 (Section 7.2).
- [ ] `policy_decision` and `policy_rule_results` exist but stay null until the engine
  writes them (Section 9.4: engine persists results; invariant 8.3.4).
- [ ] `GET /tasks/{id}/audit-reports` returns the reports for owner/auditor callers
  with catalog-coded auth errors (Section 9.2; Section 20.4 item 5).
- [ ] OpenAPI updated for the listing endpoint with schema diff reviewed
  (Section 20.4 item 4); tests green in CI; changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k audit_report -q` and confirm: Section 7.2 field parity,
full evidence-JSON round-trip of the 10.5 shape, confidence bounds rejection, nullable
policy fields, and listing behavior; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Audit Report entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Auditor verdict input shape](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Audit endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* JSON columns are schemaless — the plan fixes the top-level fields but not deep
  validation; keep deep validation in WP-3.5's schema step so the model does not
  drift from Section 10.5.
* One report per attempt vs. multiple: Section 7.2 links a report to a
  `resolution_id`, implying per-resolution reports; if audit retries (T12) allow
  re-claim of the same resolution, define whether reports accumulate — document the
  chosen reading in tests and raise OQ-xx if the plan stays ambiguous.
