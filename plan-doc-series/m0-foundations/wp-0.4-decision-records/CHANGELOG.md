# WP-0.4 Changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of
WP-0.4 (Decision confirmation and ADR records).

## 2026-10-11 — MT-0.4-01: Decision review session run, outcomes recorded

* Published session notes at `docs/plan/m0-decision-review-notes.md` covering every
  Section 22 row: OQ-01, OQ-02, OQ-03, OQ-04 and OQ-06 recorded as **decided** by
  confirming their recommended defaults (unattended default-confirmation session,
  owner ratification requested; no overrides); OQ-05, OQ-07, OQ-08, OQ-09, OQ-10,
  OQ-11, OQ-12, OQ-13 and OQ-14 recorded as **consciously deferred** with assigned
  decision milestones identical to their "needed by" columns (not settled).
* Appendix C checklist items 1–7 each carry a recorded status (C-1 satisfied via
  MT-0.4-03 write-back; C-2 satisfied; C-6 accepted; C-3/C-4/C-5/C-7 deferred with
  assigned milestones).
* No decision contradicts Section 23, so **zero ADR amendments** were flagged for
  MT-0.4-02.

## 2026-10-11 — MT-0.4-02: ADR-001..ADR-013 records written and accepted

* Wrote thirteen accepted records under `docs/adr/` — one file per Section 23 row,
  `ADR-001-single-monorepo.md` … `ADR-013-optional-per-task-worktrees.md` — each with
  status `accepted`, decision date 2026-10-11 (from the MT-0.4-01 session), and
  decision/rationale/alternatives faithful to Section 23 (no invented alternatives).
* Created/updated the index at `docs/adr/README.md`: ADR-001..ADR-013 all listed as
  accepted, no pending entries, record template (context/decision/consequences)
  fixed there; the MT-0.1-06 skeleton had not landed yet, so the index was created
  directly in its accepted end-state.
* No amendments from MT-0.4-01 to apply — each record's Amendments section says so
  explicitly (Appendix C item 1 consistency).

## 2026-10-11 — MT-0.4-03: Section 22 open-question table updated

* Extended the Section 22 table in `ai_agent_task_orchestrator_architecture_plan.md`
  with **Decision** and **Decision date** columns; all OQ-01..OQ-14 rows filled —
  OQ-01, OQ-02, OQ-03, OQ-04 and OQ-06 show concrete decisions (cross-referenced to
  ADR-002, ADR-005, ADR-013 and ADR-008 respectively), the other nine show a
  conscious deferral with an assigned milestone identical to their "needed by"
  column (deferral date 2026-10-11, not the future decision date).
* Rewrote the Section 22 preamble to state that defaults were confirmed or
  consciously deferred in WP-0.4 (unattended default-confirmation, owner ratification
  requested; no overrides) and that no Section 23 wording changed.
* Reconciled Appendix C item 1 as satisfied; no other parent-plan section was
  modified. Decisions match `docs/plan/m0-decision-review-notes.md` (MT-0.4-01) and
  the accepted records in `docs/adr/` (MT-0.4-02) without contradiction.
