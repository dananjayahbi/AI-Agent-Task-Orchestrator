# MT-5.7-01 — Implement the task detail screen

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.7-01 |
| Title | Implement the task detail screen |
| Parent WP | WP-5.7 — Task detail and live checkpoint stream (Milestone M5) |
| Requirements | FR-MOB-03 |
| Priority | M |
| Dependencies | WP-5.6 complete (board navigation, MT-5.6-01…05); WP-5.5 complete (skeleton, API client, auth); WP-1.14 complete (attachment retrieval API) |
| Parent sections | 14.1 (Task detail row), 14.3 (generated API client), 13.1 (web counterpart blocks), 19 (WP-5.7), 20.3, 20.4, 20.5 |

## Context
Section 14.1's Task detail row defines the screen: "Summary, criteria, checkpoint
stream, resolutions, attachments (view)." Section 19 WP-5.7 delivers "detail screen,
streaming feed, attachments viewing" (FR-MOB-03), split across this task and
MT-5.7-02/03. Section 14.3 fixes the engineering approach: one predictable state
management pattern, feature-first folders, and a generated API client from the same
OpenAPI schema as the web client — so this screen consumes the same canonical
contracts (Section 9.2) as WP-4.6, with mobile-appropriate layout.

## Inputs / Prerequisites
* Parent plan Section 14.1 — the four content areas of the screen.
* Parent plan Section 14.3 — state management, generated API client, flavor configs.
* Parent plan Section 9.2 — task, resolutions, attachments read endpoints.
* Parent plan Section 7.2 — Task fields rendered (summary/title/description,
  acceptance criteria, state, priority, worker, `latest_feedback`).
* WP-5.6 — board entry point (card → detail) and navigation stack; WP-5.5 — app
  skeleton, theming, API client.

## Scope (in)
* The task detail screen with the Section 14.1 areas: **summary** (title, state,
  priority, description markdown rendered inertly — Principle P10), **criteria**
  (acceptance-criteria list), **checkpoint stream** (static region owned live by
  MT-5.7-02), **resolutions** (attempt list with summaries; diff bodies link into
  review/detail flows, not rendered here beyond summaries), and **attachments**
  (entry points for MT-5.7-03's viewer).
* Navigation: push from the board (project selector/task card) and back; deep-link
  readiness by task id (full push deep-link routing is WP-5.9).
* Data wiring through the generated API client (Section 14.3) with the single
  established state-management pattern; loading, empty, offline (read-only cached
  view per Section 14.2 offline behavior) and error states (Section 20.3; catalog
  error codes only, Section 20.4 item 5).
* Widget tests per Section 14.3: render fixture task, all states, navigation
  round-trip; integration test against the mocked backend (Section 14.3).
* A WP changelog note.

## Out of scope
* Live feed behavior and backgrounding — MT-5.7-02.
* Attachment viewing internals — MT-5.7-03.
* Review sheet and its actions — WP-5.8.
* Board/dashboard — WP-5.6.
* Read-only audit log — WP-5.9 (FR-MOB-07).

## Target paths
* `mobile/` (task detail screen, state, navigation)
* `mobile/` tests (widget and integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] The screen renders all four Section 14.1 areas: summary, criteria, checkpoint
  stream region, resolutions, attachments (regions may be placeholders for
  MT-5.7-02/03).
- [ ] Data loads via the generated API client from the shared OpenAPI schema — no
  hand-written request layer (Section 14.3; NFR-11 discipline).
- [ ] Navigation push/pop from the board works and the screen is addressable by task
  id (Section 14.1; WP-5.9 deep-link contract).
- [ ] Offline behavior matches Section 14.2: view of cached data with a clear offline
  state; no mutating actions offered (Section 20.3 states).
- [ ] Error states map from canonical codes only (Sections 9.2, 20.4 item 5);
  description markdown renders inertly (Principle P10).
- [ ] Widget and integration tests green; changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to task detail (for example
`flutter test --dart-define=test_filter=task_detail` or the project's equivalent)
and confirm fixture rendering of all areas, loading/offline/error states, and
navigation round-trip against the mocked backend (Section 14.3); then the full
mobile suite stays green.

## Attachments
* [Section 14.1 — Navigation and screens (Task detail row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.3 — Engineering approach](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Mobile detail should mirror WP-4.6's content decisions where possible to avoid two
  divergent interpretations of Section 13.1/14.1 — reuse shared field lists, note
  intentional layout differences.
* Descriptions/criteria can be long — paginate/stream sections rather than one giant
  scroll that hurts mid-range devices (RISK-13 analog on mobile).
* Offline caching scope ("last overview and board", Section 14.2) may not include
  task detail in v1 — verify WP-5.6's cache; if detail is uncached, show the offline
  state honestly instead of a stale screen (record the choice).
