# MT-4.6-03 — Implement resolutions and transition history views

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.6-03 |
| Title | Implement resolutions and transition history views |
| Parent WP | WP-4.6 — Task detail: checkpoints, resolutions, attachments (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.6-01 (detail shell); WP-3.2 complete (resolution storage); WP-3.6 complete (`latest_feedback` in task details); WP-3.3 complete (audit reports) |
| Parent sections | 13.1 (detail blocks), 9.2 (resolutions, audit-reports endpoints), 7.2 (Task Resolution, Task Transition, Audit Report), 8.2 (transition rules), 19 (WP-4.6), 20.4, 20.5 |

## Context
Section 13.1's task detail row promises "resolutions, audit reports, transitions
history." Section 19 WP-4.6 delivers "resolutions list, transition history." The data
is already defined: `GET /tasks/{id}/resolutions` and `GET /tasks/{id}/audit-reports`
(Section 9.2); Task Resolution fields — `branch_name`, `commit_sha`,
`execution_summary`, `diff_summary`, `changed_files`,
`requires_human_attention`, `risk_justification`, `attempt_number` (Section 7.2);
Audit Report — `evidence`, `confidence`, `auditor_notes`, `proposed_verdict`,
`policy_decision`, `policy_rule_results` (Section 7.2); and the append-only Task
Transition rows (Section 7.2; Principle P8 — history is never edited).

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /tasks/{id}/resolutions`, `GET /tasks/{id}/audit-reports`.
* Parent plan Section 7.2 — Task Resolution, Audit Report, Task Transition fields.
* Parent plan Section 8.2 — transitions carry `from_state`, `to_state`, `actor_type`,
  `reason_code`, `note`, `timestamp`; illegal transitions return
  `TASK_STATE_CONFLICT` (not shown as history rows unless they occurred).
* WP-3.6 — `latest_feedback` surfaced in task details, shown to the next coder and
  visible here as review context.
* Section 9.7 — patch stats shown at summary level come from the backend's
  authoritative stats (viewer detail is WP-4.7).

## Scope (in)
* A resolutions section in the detail view: one entry per submission attempt
  (`attempt_number` ordered), showing branch, commit sha, execution summary,
  diff stats (files/insertions/deletions), `requires_human_attention` and
  `risk_justification`, and the resolution's audit report when present (verdict,
  confidence, auditor notes, policy decision).
* A transitions history section: reverse-chronological rows from the task's transition
  records with actor, from/to state, reason code and server timestamp — read-only
  (Principle P8).
* `latest_feedback` display when set (Section 19 WP-3.6 deliverable) as the context a
  viewer needs to understand why work was sent back.
* Fetch-on-expand per block to protect first load (Section 13.3 caching; Section 13.4
  target); canonical error-code mapping (Section 20.4 item 5).
* Component tests: multi-attempt fixture, audit-report pairing, transitions ordering,
  feedback display, empty and error states.
* A WP changelog note.

## Out of scope
* Rendering patch bodies / diffs — WP-4.7 (links into the diff viewer only).
* The review actions and their dialogs — WP-4.8.
* Backend resolution/transition writes — WP-3.2 / state machine.
* Mobile presentation of the same data — WP-5.7.

## Target paths
* `web/` (resolutions and transition history sections of task detail)
* `web/` tests (section tests with fixtures)
* WP changelog entry

## Acceptance criteria
- [ ] Resolutions list renders per Section 7.2 fields for each attempt, including the
  paired audit report summary where one exists (Sections 9.2, 7.2).
- [ ] Transition history renders the append-only record with actor, states, reason
  code and server timestamp — read-only (Section 7.2, Principle P8).
- [ ] Canonical transition reason codes are displayed verbatim from Section 8.2 —
  nothing invented (Section 20.5).
- [ ] `latest_feedback` is visible when present (WP-3.6 deliverable).
- [ ] Data loads through the generated API client with loading/empty/error states
  (Sections 13.3, 20.3) and catalog-only error codes (Section 20.4 item 5).
- [ ] Diff stats shown are the backend's authoritative values (Section 9.7), not
  recomputed in the client.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to resolutions/history (for example
`npm test -- -t resolution`) and confirm: multi-attempt rendering, audit-report
pairing, transition ordering with verbatim reason codes, feedback display, and
empty/error states; then the full web suite stays green.

## Attachments
* [Section 7.2 — Entities (Task Resolution, Task Transition, Audit Report)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (resolutions, audit-reports)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Audit reports may not exist (auditor-less or pre-audit flows, Section 8.5) — the
  resolution entry must render without one instead of erroring.
* `evidence` and `policy_rule_results` are JSON blobs (Section 7.2) — display known
  shapes from Section 10.5/9.4 and degrade to a collapsed raw view for unknown keys;
  do not invent fields.
* Cursor pagination on resolutions/audit-reports (Section 9.2) — assume long tasks
  have many attempts; unbounded fetch would violate Section 13.4 (RISK-13).
