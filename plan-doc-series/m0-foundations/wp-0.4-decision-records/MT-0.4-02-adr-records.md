# MT-0.4-02 — Write ADR-001 through ADR-013 as Accepted Decision Records

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.4-02 |
| Title | Write ADR-001 through ADR-013 as accepted decision records in docs/adr |
| Parent WP | WP-0.4 — Decision confirmation and ADR records (Milestone M0) |
| Requirements | All (risk reduction) — records Section 23 ADR-001..ADR-013 |
| Priority | M |
| Dependencies | MT-0.4-01, MT-0.1-06 (ADR skeleton and index) |
| Parent sections | 19.1 (WP-0.4), 20.4, 23, Appendix C |

## Context
Section 23 fixes thirteen architecture decisions with their rationale and alternatives
considered, and WP-0.4's goal is to record ADR-001..ADR-013 as accepted. The
documentation skeleton (MT-0.1-06) already lists them as pending in the ADR index;
this task writes the actual records so every downstream micro-document can cite a
stable ADR file instead of a table row in the plan.

## Inputs / Prerequisites
* MT-0.4-01 — session notes, including any ADR amendments the session flagged.
* MT-0.1-06 — `docs/adr/` directory and index with pending ADR entries.
* Parent plan Section 23 — the ADR table: ID, decision, rationale, alternatives
  considered (the authoritative content).
* An ADR template (context/decision/consequences shape) fixed in `docs/adr/README.md`.

## Scope (in)
* Write one file per decision: ADR-001 (monorepo), ADR-002 (SSE), ADR-003 (Celery on
  Redis), ADR-004 (project-scoped agent tokens), ADR-005 (DRF + OpenAPI), ADR-006
  (layered mobile auth), ADR-007 (backend never accesses repos), ADR-008 (host-side
  Merge Executor), ADR-009 (deterministic Policy Engine), ADR-010 (canonical snake_case
  states), ADR-011 (tool-only contract), ADR-012 (idempotency + lease fencing), ADR-013
  (optional worktrees).
* Carry decision, rationale and alternatives verbatim in substance from Section 23; add
  consequences and any MT-0.4-01 amendments without changing the decision's meaning.
* Mark every record status "accepted" with the decision date from the review session.
* Update `docs/adr/README.md` from pending to accepted for all thirteen.
* Add a WP changelog note.

## Out of scope
* New ADRs beyond ADR-013 — future decisions get new IDs per Section 0.2 (IDs never
  reused).
* Changing any decision's substance — that would go through the owner in MT-0.4-01 and
  an explicit amendment note.
* Citing the ADRs from implementation code/docs — happens naturally in later WPs.
* Updating the Section 22 table — MT-0.4-03.

## Target paths
* `docs/adr/ADR-001-*.md` … `docs/adr/ADR-013-*.md` (thirteen records)
* `docs/adr/README.md` (index updated to accepted)
* WP changelog entry

## Acceptance criteria
- [ ] Thirteen ADR files exist, one per Section 23 row, correctly numbered and named.
- [ ] Each record's status is "accepted" with a decision date.
- [ ] Each record contains decision, rationale, and alternatives considered faithful to
  Section 23 (no invented alternatives).
- [ ] The ADR index lists ADR-001..ADR-013 as accepted, with no "pending" leftovers
  from MT-0.1-06.
- [ ] Any amendment from MT-0.4-01 is explicitly marked as an amendment, not a silent
  rewrite (Appendix C item 1 consistency).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Count and inspect the records from the repository root, e.g.
`Get-ChildItem docs/adr/ADR-*.md` must return exactly 13 files, and a grep for the
status field must show "accepted" in each; verify the index lists all thirteen IDs.

## Attachments
* [Section 23 — Architecture Decision Summary](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Appendix C — Review Checklist](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Drift between Section 23 and the ADR files is the main risk — the plan remains the
  single source of truth (Section 0), so any ADR wording that changes meaning must be
  reconciled rather than left to diverge.
* ADR-010 (canonical state names) and ADR-012 (idempotency/fencing) get cited heavily
  by M1 micro-tasks; their IDs and titles must match the plan exactly for traceability.
