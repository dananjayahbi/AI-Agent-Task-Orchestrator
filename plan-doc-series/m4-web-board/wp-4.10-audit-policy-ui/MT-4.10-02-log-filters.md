# MT-4.10-02 — Implement log filters (project, task, actor, date, type)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.10-02 |
| Title | Implement log filters (project, task, actor, date, type) |
| Parent WP | WP-4.10 — Audit log viewer and policy editor (Milestone M4) |
| Requirements | FR-WEB-08 |
| Priority | S |
| Dependencies | MT-4.10-01 (viewer); WP-1.9 complete (history API filters) |
| Parent sections | 13.1 (Filterable event history), 9.2 (`GET /events` filters), 9.6 (stream filters: project, task), 7.2 (Event Log fields), 19 (WP-4.10 deliverables), 20.3, 20.4, 20.5 |

## Context
Section 19 WP-4.10's deliverable is a "filterable log" and lists filters among its
slices; Section 13.1's route row says "Filterable event history." The five filter
dimensions map directly onto Event Log fields (Section 7.2): project
(`project_id`), task (`task_id`), actor (`actor_type` + `actor_ref`), date
(`created_at`), type (`type` from the Section 9.6 catalog). Section 9.2 documents
`GET /events` with "(history, filters)" and Section 9.6 shows the stream supports
project/task filters — the exact history-query parameters are fixed by WP-1.9's
implementation.

## Inputs / Prerequisites
* Parent plan Section 19 WP-4.10 — the five named filters.
* Parent plan Section 9.2 — `GET /events` history with filters; WP-1.9's parameter
  names are the contract (OpenAPI, Section 20.4 item 4).
* Parent plan Section 7.2 — Event Log fields the filters select on.
* Parent plan Section 9.6 — catalog of event `type` values to offer; stream filter
  precedent for project/task.
* MT-4.10-01 — the viewer the filters drive.

## Scope (in)
* Filter controls above the audit log list: multi-select **project**, text/select
  **task** (id), **actor** (actor_type and/or actor_ref), **date range** on
  `created_at`, and **type** (checkbox/select of Section 9.6 catalog values).
* Query wiring: filters map 1:1 to the history endpoint's documented parameters;
  filter changes re-fetch via the typed client with cursor pagination reset; filters
  are reflected in the URL so views are shareable/refreshable (web convention;
  record in changelog).
* Filter chips/summary with individual clear + clear-all; empty-result state
  distinct from empty-log state (Section 20.3).
* Type options come from the Section 9.6 catalog only — the client does not invent
  types; unknown types arriving from the server are still renderable in results
  (Sections 9.6, 20.4 item 6).
* Component tests: each filter's parameter mapping, combined filters, URL
  round-trip, pagination reset on filter change, empty-results state, catalog-only
  type options.
* A WP changelog note.

## Out of scope
* Server-side filter implementation/query performance — WP-1.9 (only consume it;
  additions are its scope, see Risk notes).
* The viewer rendering — MT-4.10-01.
* Saved/filter presets — not in the plan; do not invent.
* Policy/rules editors — MT-4.10-03/04.

## Target paths
* `web/` (filter controls and query wiring for the audit log)
* `web/` tests (filter tests)
* WP changelog entry

## Acceptance criteria
- [ ] All five Section 19 WP-4.10 filters exist: project, task, actor, date, type —
  each mapped to its Section 7.2 Event Log field.
- [ ] Filtered requests use only the parameters the OpenAPI document actually
  defines for `GET /events` (Sections 9.2, 20.4 item 4) — if a dimension is missing
  server-side, it is raised as a contract change rather than emulated with
  client-side post-filtering of one page.
- [ ] Type options are limited to the Section 9.6 catalog (Sections 20.4 item 6,
  20.5); combined filters compose correctly.
- [ ] Filter state survives refresh via the URL; clearing restores the full list
  (Section 13.1 "Filterable event history").
- [ ] Empty-results state distinct from empty/error states (Section 20.3);
  catalog-only error codes (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to log filters (for example `npm test -- -t filter)
and confirm per-dimension parameter mapping, combinations, URL round-trip, pagination
reset, and empty-results state; then the full web suite stays green.

## Attachments
* [Section 19 — WP-4.10 deliverables and slices](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (`GET /events`)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Event catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan never enumerates `GET /events`' filter parameters (Section 9.2 says only
  "history, filters"; Section 9.6 confirms project/task on the stream) — before
  building, read WP-1.9's OpenAPI output and map what exists. Actor/date/type may
  need a backend addition: raise it as an OpenAPI contract change (Section 20.4
  item 4) — client-side filtering across an unbounded history would silently break
  correctness and pagination.
* Date-range semantics (inclusive boundaries, UTC vs local display) are unspecified —
  use server UTC (Section 0.4) for the query and local rendering for display;
  document the choice.
* Filter performance on one-year retention (Section 12.4) depends on server indexes
  (WP-1.9) — if filtering is slow, that is a backend follow-up, not a client cache
  workaround.
