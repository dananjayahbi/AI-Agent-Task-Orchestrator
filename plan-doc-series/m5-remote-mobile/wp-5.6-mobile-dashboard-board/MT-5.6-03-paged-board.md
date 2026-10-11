# MT-5.6-03 — Implement the horizontally paged six-state board

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.6-03 |
| Title | Implement the horizontally paged six-state board |
| Parent WP | WP-5.6 — Overview dashboard and mobile Kanban (Milestone M5) |
| Requirements | FR-MOB-02, FR-MOB-01 |
| Priority | M |
| Dependencies | MT-5.6-02 (current project); WP-5.5 complete (typed client) |
| Parent sections | 14.1 (Board: horizontally paged state columns, pull to refresh), 8.1 (canonical states, badge note), 19 (WP-5.6), 20.3, 20.4, 20.5 |

## Context
FR-MOB-02: "Touch-optimized real-time Kanban across six stages." Section 14.1's Board
row specifies the mobile presentation: "Project selector, horizontally paged state
columns, pull to refresh, live updates." The six stages are the canonical states
(G-01: `draft`, `pending`, `in_progress`, `to_be_audited`, `in_human_review`,
`completed`), and Section 8.1's note applies: merge-pending is a badge on cards, not a
seventh page. This micro-task is the board's layout/data slice — paging across state
columns with pull-to-refresh — before live updates (MT-5.6-04) and resume
(MT-5.6-05) land.

## Inputs / Prerequisites
* Parent plan Section 14.1 — Board screen structure.
* Parent plan G-01 / Section 8.1 — six canonical values; merge-pending badge rule;
  display labels separate from machine values.
* MT-5.6-02 — the current project whose tasks the board loads.
* WP-5.5 typed client (MT-5.5-03) — task list endpoint contract.
* Web board (MT-4.3-01) as behavioral reference for grouping and badge semantics —
  different implementation (Flutter), same canonical rules.

## Scope (in)
* A horizontally paged board: one page per canonical state in Section 8.1 order
  (`draft` → `pending` → `in_progress` → `to_be_audited` → `in_human_review` →
  `completed`), touch-swipe paging with page indicator, keyed by canonical values.
* Per-page task lists loaded through the generated client for the selected project;
  grouping by canonical `state` from API types (no hand-copied state strings — G-01).
* Task cards on mobile sized for touch: id, title, priority, worker/progress basics
  consistent with Section 14.1's overview-level detail (full detail is the Task
  detail screen, WP-5.7) — keep the card minimal and per the design system.
* Pull to refresh on the board re-fetches the current page's data (Section 14.1);
  loading, empty and error states per page (Section 20.3).
* Merge-pending badge per Section 8.1 — no seventh page.
* Navigate a tapped card toward the task detail (WP-5.7) — route stub/handoff only.
* Widget/unit tests: six pages in canonical order, grouping, pull-to-refresh refetch,
  badge on merge-pending, per-page states.
* Add a WP changelog note.

## Out of scope
* Live updates while foregrounded — MT-5.6-04.
* Resume replay after suspension — MT-5.6-05.
* Drag/move actions on mobile — not in Section 14.1's Board row; review actions are
  the review sheet (WP-5.8).
* Task detail content — WP-5.7.
* Offline board cache beyond Section 14.2's read-only last-board rule — apply the
  same caching pattern as MT-5.6-01, no new semantics.

## Target paths
* `mobile/` (paged board screen, state pages, card widgets, pull-to-refresh)
* `mobile/` tests (paging, grouping, refresh tests)
* WP changelog entry

## Acceptance criteria
- [ ] The board pages horizontally through exactly the six canonical states in
  Section 8.1 order, keyed by canonical values from API types (G-01; FR-MOB-02
  "six stages").
- [ ] Pull to refresh re-fetches the current project's board data (Section 14.1).
- [ ] Merge-pending tasks render with the Section 8.1 badge on their state page — no
  seventh page exists.
- [ ] Each page has separate loading, empty and error states (Section 20.3), with
  errors mapped from canonical codes (Section 20.4 item 5).
- [ ] Touch interaction is primary (swipe paging, tappable cards) per FR-MOB-02's
  touch-optimized requirement.
- [ ] Data flows through the generated typed client for the MT-5.6-02 selection —
  no bespoke fetch layer (NFR-11).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile test suite filtered to the board (for example
`flutter test --dart-define=test_filter=board` or the project's equivalent) and
confirm: six pages in canonical order, correct grouping, pull-to-refresh refetch,
merge-pending badge, and per-page states; then the full mobile suite stays green.

## Attachments
* [Section 14.1 — Board screen (paged state columns, pull to refresh)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.1 — State diagram and merge-pending badge note](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Loading all six pages' tasks in one request vs. per-page requests is not specified;
  prefer whatever the tasks endpoint contract already supports (project-scoped list)
  and group client-side — add per-page fetching only if payload size forces it, and
  record the choice.
* Page order and labels must stay identical to the web board's canonical order
  (MT-4.3-01) — shared confusion here causes support bugs; derive both from the same
  canonical list discipline even across stacks.
