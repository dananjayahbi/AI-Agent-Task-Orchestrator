# MT-4.8-02 — Implement the review panel with reasons, rule table, and evidence

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.8-02 |
| Title | Implement the review panel with reasons, rule table, and evidence |
| Parent WP | WP-4.8 — Human review panel and queue (Milestone M4) |
| Requirements | FR-WEB-06 |
| Priority | M |
| Dependencies | MT-4.8-01 (queue entry); WP-4.7 complete (diff viewer to embed); WP-4.6 complete (task detail, attachments); WP-3.4 complete (persisted rule results) |
| Parent sections | 13.2 (Review panel bullet), 11.5 (human review workflow), 8.4 (reasons), 9.4 (rule results), 7.2 (Audit Report), 19 (WP-4.8), 20.3, 20.4, 20.5 |

## Context
Section 13.2 defines the panel: "escalation reasons with the rule table, summary,
auditor notes, evidence commands with exit codes, diff, attachments, and the three
actions." Section 11.5 restates it: reason(s) for escalation with the rule results,
execution summary, auditor notes, diff, test evidence, attachments. Section 9.4
guarantees the reviewer "sees exactly why the task was escalated" via persisted
`policy_rule_results` on the Audit Report (Section 7.2), and reasons use the
canonical Section 8.4 enum. This task builds the read side; MT-4.8-03 adds the
actions.

## Inputs / Prerequisites
* Parent plan Section 13.2 and 11.5 — the exact panel contents.
* Parent plan Section 8.4 — canonical review reasons (12 values; display verbatim
  with friendly explanations, no new reasons).
* Parent plan Section 9.4 / 7.2 — rule table source (`policy_rule_results`, R1–R9
  pass/fail, engine version), Audit Report `evidence` (commands with exit codes,
  `lint_clean`), `confidence`, `auditor_notes`, `proposed_verdict`.
* Parent plan Section 7.2 — Task Resolution (`execution_summary`,
  `diff_summary`, `risk_justification`) for the summary block.
* WP-4.7 — diff viewer component for embedding; WP-4.6 — attachments viewer/embed.

## Scope (in)
* The review panel component hosting, per Section 13.2: escalation reason(s) from the
  task's canonical `review_reason`; the **rule table** rendering every R1–R9 row with
  pass/fail from `policy_rule_results` (with the rule's review-reason mapping per
  Section 9.4 shown for failing rows); the execution summary; auditor notes and
  confidence; **evidence commands with exit codes** (label, command, exit code, and
  `lint_clean`); the embedded diff (WP-4.7 component); attachments (WP-4.6 component);
  and a docked actions region owned by MT-4.8-03.
* Data composition from existing endpoints: task detail, `GET /tasks/{id}/audit-reports`,
  `GET /tasks/{id}/resolutions` (Section 9.2) — no new endpoints invented.
* Distinct states: no audit report (Section 8.5 path), pre-audit escalation
  (T8/T9 reasons with no rule table), loading, error (catalog codes only,
  Section 20.4 item 5).
* Keyboard-accessible panel/dialog behavior and theming per Section 13.4.
* Component tests: fixture with failing R2/R5 rule results → table shows fail rows
  with correct reasons; evidence rows with exit codes; no-report state; reason
  rendering for all Section 8.4 values.
* A WP changelog note.

## Out of scope
* Approve/request-changes/reassign interactions — MT-4.8-03.
* Merge-status display — MT-4.8-04.
* Producing rule results — WP-3.4 (Section 9.4 engine).
* Diff rendering internals — WP-4.7.
* Queue listing/sorting — MT-4.8-01.

## Target paths
* `web/` (review panel component and composition)
* `web/` tests (panel tests with fixture audit data)
* WP changelog entry

## Acceptance criteria
- [ ] The panel renders all Section 13.2 contents: reasons, rule table, summary,
  auditor notes, evidence commands with exit codes, diff, attachments (and the
  actions region placeholder for MT-4.8-03).
- [ ] The rule table shows every R1–R9 outcome verbatim from `policy_rule_results`
  (Section 9.4) — no client-side rule computation (Sections 9.4 authority note,
  20.5).
- [ ] Reasons render from the canonical Section 8.4 enum only; each displayed reason
  maps to exactly one escalation cause (Sections 8.4, 20.4 item 5).
- [ ] Evidence shows commands with their exit codes and `lint_clean`
  (Section 7.2 Audit Report evidence; Section 10.5 evidence shape).
- [ ] Diff and attachments embed the WP-4.7 / WP-4.6 components rather than
  re-implementing them (Section 13.2).
- [ ] Missing-report and pre-audit states render without errors (Section 8.5;
  Section 20.3); catalog-only error codes (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the review panel (for example `npm test -- -t
"review panel"`) and confirm rule-table rendering from fixture results, evidence exit
codes, all 12 reason values, no-report state, and embedded diff/attachments; then the
full web suite stays green.

## Attachments
* [Section 13.2 — Key components (Review panel)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.5 — Human review workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine (persisted rule results)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Escalations raised without an audit (T8/T9 reasons like `self_flagged`,
  `retry_exhausted`) have no `policy_rule_results` — the panel must degrade to
  reason + summary rather than showing an empty "all pass" table (would mislead per
  Section 9.4's purpose).
* `evidence` is a JSON blob (Section 7.2) — render the Section 10.5-known fields and
  collapse unknown ones; do not invent evidence types.
* The panel embeds two other WPs' components — coordinate their prop contracts at WP
  boundaries; a breaking embed change is a cross-WP dependency issue, not a local
  fix (Section 20.5).
