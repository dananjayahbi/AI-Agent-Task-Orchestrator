# MT-3.5-01 — Define the submit_audit_verdict schema per parent plan 10.5

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.5-01 |
| Title | Define the submit_audit_verdict schema per parent plan 10.5 |
| Parent WP | WP-3.5 — Bridge audit tools (Milestone M3) |
| Requirements | FR-AUD-02 |
| Priority | M |
| Dependencies | WP-2.4 (tool registration conventions), WP-0.5 (error/catalog conventions) |
| Parent sections | 10.5, 11.2, 19 (WP-3.5), 20.4, 20.5 |

## Context
Section 10.5 keeps the five specification tools and adds `submit_audit_verdict` (new)
with the auditor verdict input shape as a necessary contract: `task_id` (string),
`verdict` (enum `pass` / `flag_risk` / `fail`), `confidence` (integer 1–5), `notes`
(string), `evidence` (object with required `commands` array of
{`label`, `command`, `exit_code` required; `summary` optional} plus optional
`lint_clean`), and `acceptance_criteria_results` (array of {`criterion`, `met`});
required at top level: `task_id`, `verdict`, `confidence`, `evidence`. FR-AUD-02
requires the auditor to submit a structured verdict and evidence, with the Policy
Engine deciding the outcome. This task registers the tool with exactly that schema —
a public contract, so schema diffing guards it (Section 20.4 item 4).

## Inputs / Prerequisites
* Parent plan Section 10.5 — the auditor verdict input shape (JSON) and tool design
  rules (no project id; compact, structured output; every error carries a stable code,
  human-readable hint and a "next action" suggestion).
* Parent plan Section 11.2 — auditor workflow this tool completes (step 4).
* Parent plan Section 9.2 — `POST /tasks/{id}/audit-verdict` backend surface and the
  canonical error-code catalog.
* WP-2.4 — established tool registration/schema conventions in the bridge.
* Section 18 contract row — MCP tool schemas are validated in CI.

## Scope (in)
* Register `submit_audit_verdict` in the bridge tool catalog with the input schema
  copied field-for-field from Section 10.5: enums, integer bounds (confidence 1–5),
  required arrays and nested required keys — nothing added, nothing dropped.
* Tool description text that guides auditors (verdict meaning, evidence expectations,
  confidence honesty) while staying consistent with the auditor rules of Section 10.6
  — no behavioral claims beyond the plan.
* Output shape kept compact and structured per the tool design rules, with errors as
  stable catalog code + hint + next action.
* Schema snapshot/contract test so any drift from the Section 10.5 shape fails CI
  (Section 18 contract row; Section 20.4 item 4 schema diff review).
* No `project_id` input (tool design rule; binding comes from the connection —
  Section 10.3).

## Out of scope
* Server-side evidence validation and rejection guidance — MT-3.5-02.
* The auditor claim/list/checkout flow — MT-3.5-03.
* Policy Engine evaluation of the verdict — WP-3.4 (Section 9.4).
* Backend `POST /tasks/{id}/audit-verdict` implementation — WP-3.3.
* Prompt definitions (`orchestrator:audit`) — WP-2.8.

## Target paths
* `bridge/` — tool catalog entry and schema for `submit_audit_verdict`
* `bridge/tests/` — schema snapshot/contract test
* WP changelog entry (public contract — schema diff reviewed)

## Acceptance criteria
- [ ] `submit_audit_verdict` is registered with the exact Section 10.5 shape: verdict
  enum `pass`/`flag_risk`/`fail`, integer confidence 1–5, required `evidence.commands`
  entries with `label`/`command`/`exit_code`, top-level required
  [`task_id`, `verdict`, `confidence`, `evidence`] (FR-AUD-02).
- [ ] No fields added, removed or renamed versus Section 10.5 (Section 20.5
  traceability; Section 0 keeps the plan authoritative).
- [ ] No `project_id` input; output compact and structured; errors carry stable code,
  hint and next action (Section 10.5 tool design rules).
- [ ] A contract test snapshots the schema so drift fails CI (Section 18 contract
  row); schema diff reviewed as a public contract change (Section 20.4 item 4).
- [ ] Only catalog error codes referenced (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k audit_verdict_schema -q` — assert the registered
schema matches the Section 10.5 shape (enums, bounds, required keys, nested
requirements) and rejects an extra-field-free mismatch snapshot; then the full bridge
suite stays green.

## Attachments
* [Section 10.5 — Tool catalog (verdict input shape)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.2 — Auditor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Re-typing the JSON shape invites typos (enum values, required keys) — transcribe
  against Section 10.5 line by line and let the snapshot test pin it.
* Tool descriptions are contract surface too: wording that promises behavior the
  Policy Engine (WP-3.4) actually decides would mislead auditors — describe inputs,
  not outcomes.
* Any "helpful" extra field (e.g. project id "for convenience") violates the design
  rules and the zero-bleed model (Section 12.1) — the schema test must fail on
  additions as well as omissions.
