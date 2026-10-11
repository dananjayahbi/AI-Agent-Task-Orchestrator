# MT-4.2-01 — Implement the project list and switcher

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.2-01 |
| Title | Implement the project list and switcher |
| Parent WP | WP-4.2 — Project switcher, project CRUD, manifest and tokens UI (Milestone M4) |
| Requirements | FR-PRJ-01 (read half: list projects), FR-WEB-01 context (board navigation) |
| Priority | M |
| Dependencies | WP-4.1 (Next.js skeleton, login, generated API client), WP-1.3 (project registry endpoints) |
| Parent sections | 13.1 (Overview route), 13.3, 19 (WP-4.2), 20.4, 20.5 |

## Context
WP-4.2 opens with the surface the Owner sees first: the list of all projects and the
means to move between them. Section 13.1's Overview route ("All projects: status
cards, active agents, tasks needing attention, throughput") and the project-scoped
board below it both depend on a reliable project list and a current-project notion.
The data comes from `GET /projects` and `GET /projects/{pid}` (Section 9.2, Owner
caller) through the typed client generated from OpenAPI in WP-4.1 (NFR-11). This
slice is the read side; create/edit forms arrive in MT-4.2-02.

## Inputs / Prerequisites
* Parent plan Section 13.1 — Overview route and Project board route (information
  architecture).
* Parent plan Section 13.3 — typed generated client, query-library caching, SSE
  patches, canonical error-code mapping (WP-4.1 foundations).
* Parent plan Section 9.2 — `GET /projects` (cursor pagination), Owner auth
  (Section 12.2 session login).
* WP-4.1 — login/protected routes, generated API client, error mapping.
* WP-1.3 — project registry API delivering list and detail.

## Scope (in)
* The project list view per Section 13.1: project id, name, status (active/paused/
  archived per Section 8 states), and the Overview's status-card data fields the
  endpoint returns (active agents, tasks needing attention, throughput where
  available from `GET /projects`).
* A project switcher control (header/nav level) that changes the current project
  context, updates the route to the selected project's board, and persists the
  selection across reloads (documented storage choice — client-side routing state,
  no secrets involved).
* Loading, empty (no projects yet — with a create call-to-action pointing at
  MT-4.2-02), and error states per the Section 20.3 rule to separate states; errors
  mapped from canonical codes to friendly messages (Section 13.3).
* Query caching per Section 13.3 so switching back to a project is instant and a
  refresh invalidates correctly.
* Component tests: renders list, switcher changes route/current project, empty and
  error states, `AUTH_REQUIRED` maps to login redirect behavior from WP-4.1.

## Out of scope
* Creating/editing projects and status transitions — MT-4.2-02.
* Manifest download/copy — MT-4.2-03; token management — MT-4.2-04.
* Kanban columns/cards and realtime patching — WP-4.3.
* Overview dashboard metrics aggregation endpoint beyond what `GET /projects`
  returns — if richer cards need `GET /dashboard/summary`, note it as consumed by
  WP-4.x dashboard work rather than inventing fields here.
* Backend pagination behavior — WP-1.3 (surface cursor paging as the API defines).

## Target paths
* `web/` (project list/switcher components, routes per Section 13.1)
* `web/` tests (component tests)
* WP changelog entry

## Acceptance criteria
- [ ] The project list renders from `GET /projects` via the generated typed client
  with id, name and status for every project (Section 13.1, NFR-11).
- [ ] The switcher changes the current project and route; selection survives reload;
  the board/project views consume the same current-project state.
- [ ] Loading, empty and error states exist and are tested; backend errors map from
  Section 9.2 codes to friendly messages (Section 13.3, Section 20.4 item 5).
- [ ] Cursor pagination from the API is honored if more projects than one page exist
  (Section 9.2).
- [ ] No data fetching bypasses the generated client (Section 13.3, NFR-11);
  lint/type checks and tests green in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the web component tests for the project list/switcher (e.g.
`npm test -- project-list` in `web/`), asserting render, switch, empty/error states
and friendly error mapping.

## Attachments
* [Section 13.1 — Information architecture](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Status semantics (active/paused/archived) must come from Section 8's canonical
  states — do not invent intermediate statuses in the UI.
* Two sources of "current project" (switcher state vs URL) can diverge; the route is
  the source of truth — pin that in the component tests.
