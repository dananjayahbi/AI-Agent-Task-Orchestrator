# MT-4.3-01 — Implement the six board columns mapped to canonical states

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-01 |
| Title | Implement the six board columns mapped to canonical states |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-01, FR-WEB-05 |
| Priority | M |
| Dependencies | WP-4.1 complete (app shell, typed client MT-4.1-03, theme/error mapping MT-4.1-04) |
| Parent sections | 13.1 (project board), 13.2 (Board component), 8.1 (merge-pending badge note), 19 (WP-4.3), 20.3, 20.4, 20.5 |

## Context
Section 13.1 gives the web client a per-project Kanban route ("six columns"), and
Section 13.2's Board component spec starts: "columns map 1:1 to canonical states".
G-01 fixes those six canonical machine values — `draft`, `pending`, `in_progress`,
`to_be_audited`, `in_human_review`, `completed` — with display labels kept separate.
Section 8.1's note forbids a seventh column: merge-pending is a sub-status badge on
`to_be_audited`/`in_human_review` cards, not a state. This micro-task builds the
column structure the card (MT-4.3-02), filters (MT-4.3-03) and live patching
(MT-4.3-05) hang off.

## Inputs / Prerequisites
* Parent plan Section 13.1 — project board route (columns, filters, search, archive
  toggle).
* Parent plan Section 13.2 — Board component: columns map 1:1 to canonical states.
* Parent plan G-01 / Section 8.1 — the exact six canonical values and the
  merge-pending badge rule.
* WP-4.1 — scaffolded Next.js app, generated typed API client (MT-4.1-03), theming
  (MT-4.1-04) and canonical error-code mapping.
* Board data source: the tasks list endpoint from the OpenAPI-generated client.

## Scope (in)
* Board page component rendering exactly six columns in canonical state order
  (`draft` → `pending` → `in_progress` → `to_be_audited` → `in_human_review` →
  `completed`), each column keyed by the canonical value, with a separate human
  display label (G-01: machine values vs. labels).
* Data wiring: fetch the project's tasks through the typed client and group them into
  columns by canonical `state`; loading, empty and error states implemented as
  separate concerns (Section 20.3: layout, data wiring, and states split).
* Merge-pending presentation: cards with `merge_status` `pending`/`merging` stay in
  their state column with an "approved, merging" badge (Section 8.1 note) — no extra
  column.
* State values sourced from the API schema (generated types) — no hand-maintained
  string copies that could drift from G-01.
* Component/unit tests: six columns rendered in order, grouping correctness, badge
  presence, empty/loading/error states.
* Add a WP changelog note.

## Out of scope
* Drag-and-drop and move validation — WP-4.4.
* Card internals (id, priority chip, worker badge, progress) — MT-4.3-02.
* Filters, search, archive toggle — MT-4.3-03.
* SSE stream and cache patching — MT-4.3-04 / MT-4.3-05.
* Virtualization — MT-4.3-06.
* All-projects overview route — Section 13.1 Overview (WP-4.2/other).

## Target paths
* `web/` (board page, column components, grouping logic)
* `web/` tests (column mapping and state-derivation tests)
* WP changelog entry

## Acceptance criteria
- [ ] Exactly six columns render, keyed by the canonical six states in order —
  `draft`, `pending`, `in_progress`, `to_be_audited`, `in_human_review`, `completed`
  (G-01; Section 13.2 "columns map 1:1 to canonical states") (FR-WEB-01).
- [ ] Display labels are presentation-only; grouping uses the canonical values from
  the generated API types (G-01 discipline).
- [ ] Merge-pending tasks stay in `to_be_audited`/`in_human_review` with the
  Section 8.1 badge — no seventh column exists.
- [ ] Loading, empty and error states are separate, testable states with errors mapped
  from canonical codes (MT-4.1-04; Section 20.3 and Section 20.4 item 5).
- [ ] Data fetched via the OpenAPI-generated client only — no bespoke fetch layer
  (NFR-11 discipline from WP-4.1).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the board (for example `npm test -- -t board` or
the project's equivalent) and confirm: six canonical columns in order, tasks grouped
by `state`, merge-pending badge without a seventh column, and loading/empty/error
states; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (Board)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.1 — State diagram note (merge pending badge)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Duplicate hand-written state lists are the classic drift source against G-01 —
  import states from the generated client/types so a schema change fails the build
  instead of silently mis-grouping.
* Column order is not explicitly enumerated in Section 13.2; use the Section 8.1
  diagram order (as above) and note the choice — if design later requires another
  order, it is a presentation change only.
