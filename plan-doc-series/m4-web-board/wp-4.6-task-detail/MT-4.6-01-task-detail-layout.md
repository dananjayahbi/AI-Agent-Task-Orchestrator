# MT-4.6-01 — Implement the task detail layout (drawer or page)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.6-01 |
| Title | Implement the task detail layout (drawer or page) |
| Parent WP | WP-4.6 — Task detail: checkpoints, resolutions, attachments (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | WP-4.1 complete (auth, generated API client); WP-4.3 complete (board and stream hook, MT-4.3-04/05); MT-4.6-01 is the WP entry point |
| Parent sections | 13.1 (Task detail route row), 13.2 (components), 13.3 (data handling), 19 (WP-4.6), 20.3, 20.4, 20.5 |

## Context
Section 13.1 reserves a "Task detail (drawer or page)" for "Description, criteria,
scope, attachments, checkpoint feed, resolutions, audit reports, transitions history."
Section 19 WP-4.6 delivers a detail drawer plus feed, resolutions list, transition
history and attachment viewer, with acceptance "feed streams live; attachment pages
navigable." This micro-task lays down the shell and the data wiring that
MT-4.6-02 (feed), MT-4.6-03 (resolutions/history) and MT-4.6-04 (attachment viewer)
fill in — layout, data wiring and states are kept separate per the sizing rules
(Section 20.3).

## Inputs / Prerequisites
* Parent plan Section 13.1 — the seven content blocks the detail view must host.
* Parent plan Section 13.3 — typed API client from OpenAPI (NFR-11), query-library
  caching, SSE event patches, errors mapped from canonical codes.
* Parent plan Section 9.2 — `GET /tasks/{id}` (PATCH/GET `/tasks/{id}` row) and
  related read endpoints for the blocks.
* Parent plan Section 7.2 — Task fields to render (title, description, acceptance
  criteria, target_scope, test_command, priority, state, version, worker, feedback).
* WP-4.3 — board entry point (card → detail) and the stream hook used later by
  MT-4.6-02.

## Scope (in)
* The task detail component hosting the Section 13.1 blocks: description, criteria,
  scope, attachments (placeholder region), checkpoint feed (placeholder region),
  resolutions (placeholder region), audit reports, transitions history (placeholder
  regions filled by MT-4.6-02/03/04).
* Open/close behavior from the board (drawer) or route (page) — one of the two forms
  Section 13.1 allows; record which form was chosen and why in the WP changelog.
* Data wiring through the typed API client and query cache (Section 13.3): fetch task
  by id, loading / empty / error states as separate states (Section 20.3), canonical
  error codes mapped to friendly messages (Section 13.3; Section 20.4 item 5).
* Task `version` surfaced for optimistic-locking flows (Section 8.2 rule 3: the UI
  sends the version it saw).
* Keyboard accessibility and dark/light theme consistency with the board
  (Section 13.4).
* Component tests: render with fixture task, loading and error states, board → detail
  navigation, missing-id route handling.
* A WP changelog note.

## Out of scope
* Live checkpoint feed behavior — MT-4.6-02.
* Resolutions/audit-report/transition-history internals — MT-4.6-03.
* Attachment viewer — MT-4.6-04.
* Diff rendering inside resolutions — WP-4.7.
* Task editing/modal — WP-4.5 (Section 13.2 task modal).
* Drag-and-drop moves — WP-4.4.

## Target paths
* `web/` (task detail component/route and layout regions)
* `web/` tests (layout, states, navigation tests)
* WP changelog entry

## Acceptance criteria
- [ ] A task detail view exists in one of the two Section 13.1 forms and renders all
  seven content blocks (regions may be placeholders owned by MT-4.6-02/03/04).
- [ ] Task data loads through the generated API client with loading, empty and error
  states handled distinctly (Sections 13.3, 20.3).
- [ ] Errors map from canonical codes to friendly messages — no invented codes
  (Sections 13.3, 9.2, 20.4 item 5).
- [ ] The board opens the detail for a task and the detail returns to the board
  without losing cached board state (Section 13.3 cache discipline).
- [ ] Task `version` is available to child views for optimistic-locking actions
  (Section 8.2 rule 3).
- [ ] Keyboard navigation and theme behavior match Section 13.4 targets for dialogs
  and content.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to task detail (for example `npm test -- -t
"task detail"`) and confirm: fixture render with all regions, loading/error states,
board-to-detail navigation, and error-code mapping; then the full web suite stays
green.

## Attachments
* [Section 13.1 — Information architecture (Task detail row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 13.1 says "drawer or page" — the choice is left open by the plan; make it
  once at the start of the WP, record it in the changelog, and keep MT-4.6-02…04
  agnostic to it (Section 20.1 item 5: no hidden decisions — an unrecorded flip-flop
  is the real risk).
* Detail data volume (checkpoints, resolutions) must not be fetched eagerly —
  Sections 13.1/13.3 favor per-block fetch; over-fetching here would hurt the
  Section 13.4 first-load target.
* Cross-links from review queue/panel (WP-4.8) will reuse this view — keep the entry
  contract (task id parameter) stable.
