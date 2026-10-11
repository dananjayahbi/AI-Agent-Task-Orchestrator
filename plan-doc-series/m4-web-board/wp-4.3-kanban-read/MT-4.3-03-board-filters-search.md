# MT-4.3-03 — Implement board filters and search

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-03 |
| Title | Implement board filters and search |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-01, FR-WEB-05 |
| Priority | M |
| Dependencies | MT-4.3-01 (columns), MT-4.3-02 (cards); WP-4.1 complete (typed client) |
| Parent sections | 13.1 (filters, search, archive toggle), 7.2 (archived_at), 8.2 (T19 hidden by default), 13.3 (cache), 19 (WP-4.3), 20.3, 20.4, 20.5 |

## Context
Section 13.1's project board row specifies the board's query surface: "Kanban for one
project (six columns), filters, search, archive toggle". Section 7.2 gives tasks a
soft-archive timestamp (`archived_at`), and T19's note (Section 8.2 side effect)
says archived tasks are hidden from boards by default — so the archive toggle's
default-off behavior is plan-mandated. The plan does not enumerate every filter
dimension; the generated client's endpoint query parameters are the contract for what
can be filtered (Section 13.3: typed client from OpenAPI). This micro-task implements
the filter/search UI bound to server-supported parameters, keeping search and
filtering as separate, testable concerns from layout (Section 20.3).

## Inputs / Prerequisites
* Parent plan Section 13.1 — filters, search, archive toggle requirement.
* Parent plan Section 8.2 T19 / Section 7.2 — archived tasks hidden by default.
* WP-4.1 generated client — the authoritative list of query parameters the tasks
  endpoint supports (Section 13.3; NFR-11).
* MT-4.3-01/MT-4.3-02 — board and card render the filtered result set.

## Scope (in)
* Filter controls bound to server-supported query parameters of the tasks list
  endpoint as exposed by the generated client — implement exactly what the contract
  offers (for example priority or assignment filters if present); parameters not in
  the OpenAPI contract are out of scope rather than invented client-side.
* Search input wired to the endpoint's search/filter capability if present in the
  contract; otherwise client-side filtering over the loaded board set with the
  limitation documented — flag the gap as OQ-xx if server search is required but
  absent from Section 13.1's backing API.
* Archive toggle: default OFF shows only non-archived tasks (Section 8.2 T19
  "hidden from boards by default"); toggling ON includes archived tasks.
* Filter/search/toggle state composes (combined predicates), clears, and drives
  fetch/refetch through the query cache (Section 13.3) without breaking the SSE
  patching seam (MT-4.3-05).
* Empty-result state distinct from loading/error (Section 20.3).
* Tests: default hides archived, toggle reveals, each supported filter applied and
  combined, search behavior per chosen wiring, empty state.
* Add a WP changelog note.

## Out of scope
* Server-side endpoint changes to add new filter parameters — would be a backend
  contract change (Section 9.2) beyond this WP; raise as OQ-xx if needed.
* Review-queue cross-project view — Section 13.1 separate route.
* Drag-and-drop filtering interactions — WP-4.4.
* Persisting filter state in the URL — not specified in the plan; only add if the
  team decides it, note as optional.

## Target paths
* `web/` (board filter/search components, query parameter wiring)
* `web/` tests (filter/search/archive behavior)
* WP changelog entry

## Acceptance criteria
- [ ] The board exposes filters, search and an archive toggle per Section 13.1
  (FR-WEB-01).
- [ ] Archived tasks are hidden by default and revealed only when the archive toggle
  is on (Section 8.2 T19; Section 7.2 `archived_at`).
- [ ] Only query parameters present in the OpenAPI-generated client are used — no
  invented server parameters (Section 13.3; NFR-11; Section 20.5 traceability).
- [ ] Filters, search and archive toggle compose and produce an empty state distinct
  from loading and error states (Section 20.3).
- [ ] Errors during refetch map from canonical codes (MT-4.1-04;
  Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to board filters (for example `npm test -- -t
filters`) and confirm: archive default-off hiding archived tasks, toggle reveal,
each contract-supported filter alone and combined, search behavior, and empty state;
then the full web suite stays green.

## Attachments
* [Section 13.1 — Information architecture (project board)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T19 archive note)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan names but does not enumerate "filters" — scope drift risk is real. Bind
  strictly to the generated client's parameters; if the endpoint exposes none usable,
  that is an OQ-xx for the backend contract, not a reason to fake client-only
  semantics silently.
* Filtering server-side vs. filtering the cached set interacts with SSE patching
  (MT-4.3-05): a live transition must respect the active filter (a task that moves
  out of the filter should disappear, one that enters should appear or refetch) —
  decide this behavior explicitly in tests.
