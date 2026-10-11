# MT-4.10-01 — Implement the audit log viewer

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.10-01 |
| Title | Implement the audit log viewer |
| Parent WP | WP-4.10 — Audit log viewer and policy editor (Milestone M4) |
| Requirements | FR-WEB-08 |
| Priority | S |
| Dependencies | WP-1.9 complete (event log and audit trail); WP-4.2 complete (project settings shell); WP-4.1 complete (auth, API client) |
| Parent sections | 13.1 (Audit log route), 9.2 (`GET /events` history), 7.2 (Event Log), 12.5 (audit trail), 19 (WP-4.10), 20.3, 20.4, 20.5 |

## Context
Section 13.1 reserves the Audit log route for "Filterable event history." Section 12.5
sets the integrity rules: every state change, token event, review decision, merge
result, login and policy edit writes an Event row with actor and correlation id; the
viewer (web, mobile) is read-only; the application database role cannot update or
delete audit rows. The Event Log entity (Section 7.2) carries a monotonic `id` (also
the SSE event id), `type`, `project_id`, `task_id`, `actor_type`, `actor_ref`,
`payload`, `created_at`, append-only (Principle P8). Retrieval is
`GET /events` (history, filters) from Section 9.2; retention default one year
(Section 12.4; OQ-10: events 1 year).

## Inputs / Prerequisites
* Parent plan Section 13.1 — the route and its promise of filters (filters built in
  MT-4.10-02).
* Parent plan Section 9.2 — `GET /events` history endpoint with filters.
* Parent plan Section 7.2 — Event Log fields to render.
* Parent plan Section 12.5 — read-only rule; actor + correlation id on every entry.
* WP-1.9 — event log implementation and history API.

## Scope (in)
* The Audit log route rendering event history entries from `GET /events`: event type,
  timestamp (server, UTC ISO-8601 per Section 0.4), actor (`actor_type` +
  `actor_ref`), project/task linkage, correlation id, and a collapsible view of the
  event `payload` for detail.
* Strictly read-only UI: no edit/delete affordances anywhere (Section 12.5);
  pagination via the Section 9.2 cursor convention for large histories.
* Entry presentation: friendly labels for Section 9.6 catalog event types displayed
  alongside the canonical type string (ADR-010: canonical values separate from
  display labels); unknown/forward types render raw without crashing.
* States: loading, empty, error (catalog codes only, Section 20.4 item 5), and
  stream-down does not affect a history view (it is a REST fetch, not SSE).
* Component tests: fixture history render with fields, payload expansion,
  pagination cursor behavior, read-only assertion (no mutating controls), unknown
  type rendering.
* A WP changelog note.

## Out of scope
* Filter controls — MT-4.10-02.
* Policy/rules editing — MT-4.10-03/04.
* Server-side event writing/retention — WP-1.9 / Section 12.4.
* Live tail of new events — not required by Section 13.1 (history view); the SSE
  stream serves the board (WP-4.3).
* Mobile audit log — WP-5.9 (FR-MOB-07 read-only list).

## Target paths
* `web/` (audit log route/page and entry components)
* `web/` tests (viewer tests with fixture events)
* WP changelog entry

## Acceptance criteria
- [ ] The Audit log route lists event history from `GET /events` with type,
  timestamp, actor, project/task links, correlation id and payload detail
  (Sections 13.1, 9.2, 7.2, 12.5).
- [ ] The view is strictly read-only — no mutation controls (Section 12.5;
  Principle P8).
- [ ] Canonical event type strings are shown with display labels — labels never
  replace the canonical values (ADR-010; Section 20.5).
- [ ] Cursor pagination handles histories beyond one page without unbounded fetch
  (Section 9.2; RISK-13 discipline).
- [ ] Loading, empty and error states handled (Section 20.3); catalog-only error
  codes (Section 20.4 item 5).
- [ ] No event types outside the Section 9.6 catalog are fabricated by the client —
  unknown server types render as raw text (Sections 9.6, 20.4 item 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the audit log (for example `npm test -- -t
"audit log"`) and confirm fixture rendering with all fields, payload expansion,
cursor pagination, read-only guarantees, and unknown-type fallback; then the full web
suite stays green.

## Attachments
* [Section 12.5 — Audit trail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Entities (Event Log)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Payload sizes vary widely (Section 7.2 `payload` JSON) — collapse by default and
  lazy-load detail; rendering every payload inline risks the Section 13.4
  responsiveness target (RISK-13).
* Correlation ids and actor refs may include sensitive context — Section 12.4 says
  logs scrub tokens; the viewer must not add client-side enrichment that could
  expose secrets (P10-adjacent caution).
* Section 9.2's filter surface for `GET /events` is described only as "(history,
  filters)" — confirm actual parameter support when wiring MT-4.10-02 (see its risk
  notes) before promising filter chips in the viewer header.
