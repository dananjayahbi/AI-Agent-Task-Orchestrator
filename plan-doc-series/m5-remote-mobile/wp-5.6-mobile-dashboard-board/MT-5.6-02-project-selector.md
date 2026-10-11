# MT-5.6-02 — Implement the project selector

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.6-02 |
| Title | Implement the project selector |
| Parent WP | WP-5.6 — Overview dashboard and mobile Kanban (Milestone M5) |
| Requirements | FR-MOB-01, FR-MOB-02 |
| Priority | M |
| Dependencies | MT-5.6-01 (dashboard entry point); WP-5.5 complete (typed client) |
| Parent sections | 14.1 (Board: project selector), 9.2 (projects list), 13.1 (web parity), 19 (WP-5.6), 20.3, 20.4, 20.5 |

## Context
Section 14.1's Board row begins with "Project selector" — the mobile board operates
within one selected project, mirroring the web board's per-project route
(Section 13.1). The selector chooses which project's tasks the board shows and which
project's events the realtime stream filters by (Section 9.6 filters). Section 19
WP-5.6 lists "project selector" as its own slice. This micro-task builds the selector
control and its selection state.

## Inputs / Prerequisites
* Parent plan Section 14.1 — Board screen: project selector, columns, refresh, live
  updates.
* Parent plan Section 9.2 — `GET /projects` (Owner) for the selector's list.
* Parent plan Section 9.6 — stream filters take a project id.
* MT-5.6-01 — dashboard as the entry surface that can preselect a project;
  WP-5.5 typed client (MT-5.5-03).

## Scope (in)
* A project selector on the Board screen listing the owner's projects from
  `GET /projects` via the generated client (id + name; status visible where the
  payload provides it).
* Selection state: which project the board displays; tapping a dashboard project card
  (MT-5.6-01) preselects that project.
* Selection changes drive: board data fetch for the new project, and the realtime
  stream subscription filter (Section 9.6 project filter) — one source of truth for
  "current project".
* Sensible single-project behavior (only one project → selector still visible or
  collapsed consistently — pick one, document it) and empty state (no projects →
  guidance, Section 20.3).
* Restore the last selected project on app restart within the session scope the plan
  supports (persisted selection is optional; if persisted, treat as UX decision —
  see Risk notes).
* Widget/unit tests: list rendering, selection changes refetch board and re-filter
  stream, preselect from dashboard, empty state.
* Add a WP changelog note.

## Out of scope
* The board columns/paging itself — MT-5.6-03.
* Live updates and resume — MT-5.6-04 / MT-5.6-05.
* Project CRUD/switching management UI (create/edit) — mobile v1 is read-oriented
  here; web owns project management (Section 13.1 settings routes).
* Paused/archived project policy effects on agent work (FR-PRJ-04) — backend
  behavior; the selector merely shows what `GET /projects` returns.

## Target paths
* `mobile/` (project selector widget, current-project state holder)
* `mobile/` tests (selector tests)
* WP changelog entry

## Acceptance criteria
- [ ] The Board screen has a project selector listing the owner's projects from
  `GET /projects` via the generated client (Section 14.1 "Project selector";
  Section 9.2; NFR-11).
- [ ] Changing selection refetches the board for the new project and updates the SSE
  subscription's project filter to match (Section 9.6 filters) — selector state is
  the single source of truth.
- [ ] Tapping a dashboard project card (MT-5.6-01) lands on the Board with that
  project preselected.
- [ ] Empty (no projects) and error states are distinct and mapped from canonical
  codes (Section 20.3; Section 20.4 item 5).
- [ ] The selector works within the WP-5.5 authenticated/gated session (Section 14.2).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile test suite filtered to the project selector (for example
`flutter test --dart-define=test_filter=project_selector` or the project's
equivalent) and confirm: list rendering, selection → board refetch + stream
re-filter, dashboard preselect, and empty/error states; then the full mobile suite
stays green.

## Attachments
* [Section 14.1 — Board screen (project selector)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Stream filters](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.6 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Persisting the selection across restarts is not specified — safe to keep
  session-local first; if persisted, remember the offline rule (Section 14.2): a
  restored selection must show cached/live state honestly rather than implying
  connectivity.
* Race: fast successive selections must not let an older project's fetch overwrite
  the newer selection's data — guard with selection-scoped requests; a bug here
  silently shows another project's board.
