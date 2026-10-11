# MT-4.11-04 — Run the Performance Pass Against the 500-Card Board Target

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.11-04 |
| Title | Run the performance pass against the 500-card board target |
| Parent WP | WP-4.11 — Responsive, accessibility and performance pass (Milestone M4) |
| Requirements | NFR-13 |
| Priority | M |
| Dependencies | MT-4.11-01, MT-4.11-02, MT-4.11-03 (layout, keyboard and a11y fixes in), MT-4.3-06 (column virtualization), MT-4.3-05 (SSE cache patching) |
| Parent sections | 13.2 (Board), 13.4 (500-card responsiveness, first load under 3 s on LAN), 18 (Performance row: board load), 19 (WP-4.11 deliverable: performance report; fourth slice), 20.4, 20.5 |

## Context
Section 13.4 fixes two measurable web targets: "Board with 500 cards stays responsive
(virtualized columns); first load under 3 s on LAN." Section 18's Performance row
lists "board load" among the load scenarios, and Section 19 (WP-4.11) makes a
performance report a WP deliverable. MT-4.3-06 built the virtualization; this closing
slice proves the finished board — after responsive, keyboard and contrast changes —
still hits the targets, and records the numbers. This is the web-side companion to
the WP-6.3 full performance program, not a replacement for it.

## Inputs / Prerequisites
* MT-4.11-01 … MT-4.11-03 — the pass runs against the finished UI, not an
  intermediate state.
* MT-4.3-06 — virtualized columns (the mechanism the 500-card target leans on);
  MT-4.3-05 — SSE event → cache patching (interaction cost under live updates).
* Seeded data: a project whose board totals ~500 cards spread over the six
  canonical states (Section 8.1), plus a local Compose stack (WP-0.2) on LAN.
* Parent plan Section 13.4 — the two targets verbatim; Section 18 — board load as a
  named performance scenario.

## Scope (in)
* A repeatable board-load check: seed ~500 cards in one project, open the board, and
  measure first load on LAN (target: under 3 s, Section 13.4) and interaction
  responsiveness while scrolling/filtering with all columns populated (target:
  responsive — record frame/interaction timings as the evidence).
* Exercise live-update cost: apply a batch of SSE event patches (MT-4.3-05) to the
  500-card board and confirm interaction stays responsive (Section 13.3's patch
  model).
* Verify virtualization is actually engaged at 500 cards (bounded render counts —
  the MT-4.3-06 assertion still holds with the current UI).
* Record results in the web performance report: date, environment, method, measured
  first-load time, interaction observations, pass/fail against the Section 13.4
  targets.
* Fix regressions caused by the WP-4.11 changes themselves (layout/keyboard/a11y
  costs) inside this task when small; raise anything requiring broader redesign as a
  follow-up (Section 20.3 split rule).
* Changelog note (Section 20.4 item 7).

## Out of scope
* The WP-6.3 program (20 simulated agents, 10,000 tasks, SSE fan-out, API latency
  budgets) — that validates NFR-02/03/09 against the backend; this pass is the web
  board's Section 13.4 target only.
* Backend/API performance tuning — WP-6.3 (MT-6.3-03).
* Mobile app performance — WP-5.x.
* Building new virtualization or caching — mechanisms exist (MT-4.3-06, MT-4.3-05);
  this task measures and fixes small regressions only.

## Target paths
* `web/` — any small fixes for regressions found in this pass
* `docs/plan/` — web performance report (WP-4.11 deliverable; same location
  convention as the accessibility audit report)
* `web/` tests — the repeatable board-load check if scripted
* WP changelog entry

## Acceptance criteria
- [ ] First load of the 500-card board measured under 3 s on LAN, with the number
  recorded in the report (Section 13.4 verbatim target; Section 20.4 item 1).
- [ ] Board described as responsive at 500 cards with virtualization engaged —
  bounded render counts demonstrated, not asserted (Section 13.4; MT-4.3-06
  regression check).
- [ ] SSE patch application to the full board keeps interaction responsive
  (Sections 13.3, 13.4).
- [ ] Performance report exists with environment, method and measured values
  (Section 19 WP-4.11 deliverable).
- [ ] Any regression introduced by MT-4.11-01 … 03 is fixed or explicitly listed as
  a follow-up task with owner (no silent misses).
- [ ] Tests/lint green in CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
Run the board-load check against the local Compose stack with the 500-card fixture
(e.g. `npm --prefix web test -- board-load` if scripted) and confirm first load < 3 s
plus bounded render counts; then verify `docs/plan/` performance report contains the
measured values and a pass/fail line per Section 13.4 target.

## Attachments
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (Performance row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.11 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Responsive" is qualitative in the plan — record concrete interaction measurements
  (e.g. input-to-paint timings) so the report is evidence, not opinion; if a numeric
  bar is chosen, document it as this task's interpretation, not as a plan value.
* First load "on LAN" is environment-dependent — record hardware/network assumptions
  alongside the number, or the < 3 s claim is not reproducible (same discipline as
  MT-1.10-06's local-p95 note).
* Seeding 500 cards must not leave junk in a developer's shared database — use a
  disposable project and note the fixture method in the report.
