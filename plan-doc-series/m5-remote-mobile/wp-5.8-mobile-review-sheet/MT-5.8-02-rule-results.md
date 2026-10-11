# MT-5.8-02 — Implement rule results and evidence display

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-02 |
| Title | Implement rule results and evidence display |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.8-01 (sheet regions); WP-3.4 complete (`policy_rule_results` persistence); WP-3.3 complete (Audit Report evidence) |
| Parent sections | 14.1 (rule results row), 9.4 (persisted rule results), 7.2 (Audit Report), 10.5 (verdict evidence shape), 8.4 (reasons), 19 (WP-5.8), 20.3, 20.4, 20.5 |

## Context
Section 14.1 puts "Reason and rule results" first in the review sheet; Section 9.4's
design note states the rule results are persisted "so the human reviewer sees exactly
why the task was escalated," with every R1–R9 outcome listed and the engine version
stored for traceability. Evidence lives on the Audit Report (Section 7.2):
`evidence` JSON (commands run, exit codes, durations, changed files, diff stats,
lint results), `confidence` (1–5), `auditor_notes`, `proposed_verdict`,
`policy_decision`, `policy_rule_results`. Section 10.5 fixes the evidence command
shape (`label`, `command`, `exit_code`, `summary`) the display must honor.

## Inputs / Prerequisites
* Parent plan Section 9.4 — rules R1–R9 with their fail conditions and review-reason
  mapping; persistence and engine versioning.
* Parent plan Section 7.2 — Audit Report fields.
* Parent plan Section 10.5 — auditor verdict evidence shape (commands with exit
  codes, `lint_clean`, `acceptance_criteria_results`).
* Parent plan Section 8.4 — canonical reasons the sheet ties results to.
* MT-5.8-01 — the sheet's rule-results region.

## Scope (in)
* The rule-results table in the sheet: every R1–R9 row with pass/fail from
  `policy_rule_results`, the failing rule's mapped review reason (Section 9.4
  table), and the persisted engine version shown for traceability — all read
  verbatim from the backend (no client-side rule evaluation; Section 9.4 authority).
* Evidence display beneath it: commands with `label`, `command`, `exit_code`,
  `summary` (Section 10.5), `lint_clean`, `acceptance_criteria_results` per
  criterion, auditor `confidence` (1–5), `auditor_notes`, `proposed_verdict`, and
  the resulting `policy_decision` (Section 7.2).
* Degraded states: no audit report (Section 8.5 coder-evidence path or pre-audit
  T8/T9 escalations) → show reason + execution summary only, no fabricated
  "pass" table; unknown extra JSON keys collapsed rather than guessed
  (Sections 20.3, 20.5).
* Mobile ergonomics: horizontally scrollable rule rows or stacked cards — every
  failing rule visible without truncation (Section 9.4's purpose).
* Widget tests: fixture failing R2/R5 → correct rows/reasons; full-pass table on a
  T13-adjacent fixture; evidence commands with exit codes; missing-report state;
  unknown-key tolerance.
* A WP changelog note.

## Out of scope
* Rule evaluation — WP-3.4 (Section 9.4).
* Diff rendering — MT-5.8-03.
* Action flows — MT-5.8-04…06.
* Web rule table — WP-4.8 (MT-4.8-02).
* Producing audit reports — WP-3.3/3.5.

## Target paths
* `mobile/` (rule results and evidence widgets in the review sheet)
* `mobile/` tests (widget tests with fixture audit data)
* WP changelog entry

## Acceptance criteria
- [ ] All R1–R9 outcomes render from `policy_rule_results` with each failing rule's
  Section 9.4 review reason — no client-side computation (Sections 9.4, 20.5).
- [ ] Evidence renders commands with exit codes plus `lint_clean`, criterion
  results, confidence, auditor notes, proposed verdict and policy decision
  (Sections 7.2, 10.5).
- [ ] The engine version persisted per Section 9.4 is visible (traceability).
- [ ] Missing-report states degrade to reason + summary without errors and without
  fake pass tables (Sections 8.5, 20.3).
- [ ] Reason strings are canonical Section 8.4 values (Sections 8.4, 20.4 item 5,
  20.5).
- [ ] Unknown evidence keys render collapsed — no invented fields (Section 20.5).
- [ ] Widget tests green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to rule results (for example
`flutter test --dart-define=test_filter=rule_results` or the project's equivalent)
and confirm fixture rule tables, reason mapping, evidence exit codes, missing-report
degradation, and unknown-key tolerance; then the full mobile suite stays green.

## Attachments
* [Section 9.4 — Policy Engine (persisted rule results)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog (auditor evidence shape)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Entities (Audit Report)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `evidence` and `policy_rule_results` are JSON blobs whose exact serialization is
  WP-3.4/WP-3.3's contract — build against their OpenAPI-published schema, not the
  prose summary here (Section 20.4 item 4).
* Long evidence commands must wrap/scroll without horizontal page scroll on phones —
  monospace blocks with their own scroll (mirror Section 14.2's diff approach).
* Showing only failing rules would hide the "exactly why" context — Section 9.4
  persists every rule and outcome; display all rows (fails first, passes collapsed).
