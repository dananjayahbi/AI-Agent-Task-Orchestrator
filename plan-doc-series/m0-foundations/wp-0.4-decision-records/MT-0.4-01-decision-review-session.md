# MT-0.4-01 — Run the Decision Review Session and Record Outcomes for OQ-01..OQ-14

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.4-01 |
| Title | Run the decision review session and record outcomes for OQ-01..OQ-14 |
| Parent WP | WP-0.4 — Decision confirmation and ADR records (Milestone M0) |
| Requirements | All (risk reduction) — gates OQ-01..OQ-14 from Section 22 |
| Priority | M |
| Dependencies | none (WP-0.4 has no upstream WP) |
| Parent sections | 19.1 (WP-0.4), 20.4, 22, Appendix C |

## Context
Section 22 defines fourteen open questions, each with a recommended default, that the
owner must confirm or override in WP-0.4. Five of them (OQ-01, OQ-02, OQ-03, OQ-04,
OQ-06) block M1/M2 work and must be decided outright; the remainder must receive an
assigned decision milestone. This session produces the raw decisions that MT-0.4-02
(ADRs) and MT-0.4-03 (plan table update) then formalize.

## Inputs / Prerequisites
* Parent plan Section 22 — the full OQ-01..OQ-14 table with recommended defaults and
  "needed by" milestones.
* Parent plan Appendix C — review checklist before micro-task expansion (items 1–7).
* Owner availability — these are owner decisions; an unattended session can only
  confirm defaults, which must be stated explicitly as such.
* Session notes location decided under `docs/plan/`.

## Scope (in)
* Schedule and run the decision review covering every row of Section 22.
* For each OQ-01..OQ-14, record: accepted default or override, rationale in one or two
  sentences, decision date, and — for deferred items — the assigned decision milestone.
* Explicitly confirm OQ-01, OQ-02, OQ-03, OQ-04 and OQ-06 as decided (WP-0.4
  acceptance), unblocking M1 and M2.
* Walk the Appendix C checklist and record each item's status.
* Publish the session notes under `docs/plan/` as the input for MT-0.4-02.
* Add a WP changelog note.

## Out of scope
* Writing the ADR files — MT-0.4-02.
* Editing the Section 22 table in the parent plan — MT-0.4-03.
* Implementing any decision (e.g. building SSE-only realtime) — belongs to the M1/M2
  WPs that consume the decisions.
* Re-opening ADR-001..013 substance beyond confirming them — Section 23 already states
  the recommended decisions.

## Target paths
* `docs/plan/m0-decision-review-notes.md` (session outcomes for OQ-01..OQ-14 and the
  Appendix C checklist status)
* WP changelog entry

## Acceptance criteria
- [ ] Every OQ-01 through OQ-14 row has a recorded outcome: decided (with rationale and
  date) or deferred (with assigned decision milestone and date).
- [ ] OQ-01, OQ-02, OQ-03, OQ-04 and OQ-06 are explicitly decided (WP-0.4 acceptance).
- [ ] All remaining OQs carry an assigned decision milestone consistent with their
  "needed by" column.
- [ ] Appendix C checklist items 1–7 each have a recorded status.
- [ ] Notes are published under `docs/plan/` and referenced from the changelog
  (Section 20.4 item 7).
- [ ] No decision contradicts an existing Section 23 ADR without flagging the conflict.

## Test command
Review the published notes against Section 22: confirm all 14 OQ IDs appear with a
non-empty outcome and date, and run the Appendix C checklist as a read-through gate
(e.g. search the notes file for each OQ-xx and C-1..C-7 item).

## Attachments
* [Section 22 — Open Questions and Decisions Needed](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix C — Review Checklist](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Defaults accepted without a live owner review are still "recommended defaults", not
  decisions — the notes must distinguish confirmed decisions from pass-through defaults
  so OQ-14 (dogfooding) and similar owner-preference items are not silently settled.
* A decision that contradicts Section 23's ADR rationale requires an ADR amendment —
  flag it for MT-0.4-02 rather than burying it in the notes.
