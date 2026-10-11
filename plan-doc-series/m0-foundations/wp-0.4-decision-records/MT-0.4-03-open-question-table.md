# MT-0.4-03 — Update the Parent Plan Open-Question Table with Decisions and Dates

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.4-03 |
| Title | Update the parent plan open-question table with decisions and dates |
| Parent WP | WP-0.4 — Decision confirmation and ADR records (Milestone M0) |
| Requirements | All (risk reduction) — closes or schedules Section 22 OQ-01..OQ-14 |
| Priority | M |
| Dependencies | MT-0.4-01, MT-0.4-02 |
| Parent sections | 19.1 (WP-0.4 acceptance), 20.4, 20.5, 22, Appendix C |

## Context
The parent plan is the single source of truth (Section 0), so the outcomes of the
WP-0.4 decision session must be written back into the Section 22 open-question table
itself — WP-0.4's deliverable is "updated open-question table with decisions and
dates". This makes the plan self-contained for every later micro-task author, who
re-reads Section 22 rather than hunting for session notes.

## Inputs / Prerequisites
* MT-0.4-01 — session notes with each OQ's outcome, rationale, date, and assigned
  milestone for deferred items.
* MT-0.4-02 — accepted ADR records to cross-reference in decisions.
* Parent plan Section 22 — the current table (ID, question, recommended default,
  needed-by) to be extended.

## Scope (in)
* Extend the Section 22 table with two columns: **Decision** (decided value, or
  "deferred to {milestone}") and **Decision date**.
* Fill every row OQ-01..OQ-14 — no blank outcome cells (WP-0.4 acceptance).
* Cross-reference the ADR that embodies each decided outcome where one exists
  (e.g. OQ-01/OQ-02 → ADR-002/ADR-005 as applicable; OQ-03 → ADR-013; OQ-06 → ADR-008
  merge-strategy context).
* Update the section preamble to state that defaults were confirmed or overridden in
  WP-0.4, and reconcile Appendix C item 1 ("all Section 22 questions marked as decided
  or consciously deferred").
* Note any decision that also changed Section 23 wording (coordinate with MT-0.4-02).
* Add a WP changelog note.

## Out of scope
* Re-opening or re-deciding any OQ — decisions come only from MT-0.4-01.
* Editing other parent-plan sections (requirements, WPs) — only Section 22 (and the
  Appendix C checklist status line) changes, unless a decision requires an ADR
  amendment flagged in MT-0.4-02.
* Updating `roadmap.md`/`overview.md` — those track documents, not OQ states.

## Target paths
* `ai_agent_task_orchestrator_architecture_plan.md` — Section 22 table (decision and
  date columns) and Appendix C checklist status
* WP changelog entry

## Acceptance criteria
- [ ] The Section 22 table has decision and date values for all OQ-01..OQ-14 rows.
- [ ] OQ-01, OQ-02, OQ-03, OQ-04 and OQ-06 show concrete decisions (WP-0.4 acceptance).
- [ ] All other rows show a conscious deferral with an assigned milestone.
- [ ] Decisions match MT-0.4-01 notes and MT-0.4-02 ADRs without contradiction.
- [ ] No other parent-plan section was modified (traceability discipline, Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Re-read Section 22 of the parent plan and verify each of the 14 rows carries a decision
value and a date (e.g. search the file for `OQ-14` and inspect the row and its
neighbors); confirm Appendix C item 1 now reads as satisfied.

## Attachments
* [Section 22 — Open Questions and Decisions Needed](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix C — Review Checklist](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The parent plan is cited by every micro-document; an inconsistent table edit creates
  widespread confusion — make the edit surgical and re-read the surrounding sections
  after changing it.
* Deferred OQs still need their milestone honored: the "Decision date" for a deferral
  is the date the deferral was recorded, not the future decision — keep the columns
  unambiguous to avoid Appendix C item 1 misreads.
