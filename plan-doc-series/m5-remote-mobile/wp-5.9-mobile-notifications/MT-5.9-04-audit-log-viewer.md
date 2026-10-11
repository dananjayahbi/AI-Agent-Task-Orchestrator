# MT-5.9-04 — Implement the Read-Only Audit Log Viewer

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.9-04 |
| Title | Implement the read-only audit log viewer |
| Parent WP | WP-5.9 — Push deep links, notification center and audit log (Milestone M5) |
| Requirements | FR-MOB-07 |
| Priority | M |
| Dependencies | MT-5.5-03 (generated API client), MT-5.5-01 (navigation shell), MT-1.9-01 … MT-1.9-05 (event log and endpoints exist); MT-5.6-0x (list/filter patterns) |
| Parent sections | 12.5 (audit trail; viewer read-only), 14.1 (Audit log: read-only list with filters), 9.6 (event stream/catalog), 19 (WP-5.9 fourth slice and deliverables), 20.4, 20.5; FR-SEC-03 |

## Context
FR-MOB-07 is a small, sharp requirement: "Read-only audit log viewer." Section 14.1
gives the screen: "Read-only list with filters." Section 12.5 fixes why it is
read-only: every state change, token event, review decision, merge result, login and
policy edit writes an Event row with actor and correlation id, the viewer is
read-only on web and mobile, and the application database role cannot update or
delete audit rows. The mobile viewer is the Owner's on-the-road window into that
trail — it displays, it never mutates (FR-SEC-03 append-only discipline).

## Inputs / Prerequisites
* Backend event/audit listing endpoints from WP-1.9 and the audit viewer endpoints
  the web viewer uses (WP-4.10-01/02 — its filter set is the reference for parity).
* MT-5.5-03 — generated typed client (NFR-11); events consume via API, not by
  tapping the SSE stream directly.
* Parent plan Section 12.5 — read-only guarantee and Event row contents (actor,
  correlation id).
* Parent plan Section 14.1 — screen definition; Section 14.2 — offline read-only
  cache behavior applies to lists.
* Section 0.5/9.x pagination conventions (WP-0.5) for paged list loading.

## Scope (in)
* An Audit log screen: reverse-chronological list of Event rows with the Section
  12.5 essentials visible (what changed, actor, correlation id, time), paged per the
  pagination conventions, with loading, empty and error states (Section 20.3).
* Filters mirroring the web audit log viewer's filter set (project, task, actor,
  date, type — WP-4.10-02) for every filter the API supports; unsupported filters
  are omitted, not faked (the API is the contract — Section 18 Contract row).
* Strictly read-only: no action buttons, no swipe-to-edit, no mutation calls anywhere
  in the feature — navigating from an event to its task detail (if offered) is
  navigation, not mutation.
* Navigation entry per Section 14.1 (Audit log area) beside Notifications (MT-5.9-03).
* Widget/integration tests: list rendering and paging from fixtures, each filter's
  query wiring, and an assertion that the feature issues no mutating requests.
* Changelog note (Section 20.4 item 7).

## Out of scope
* The web audit log viewer and its filters — WP-4.10 (FR-WEB-08).
* Event generation, retention, insert-only permissions — WP-1.9 and Section 12.5
  backend guarantees.
* Export, search-across-archive, or alerting on audit events — not in Section 14.1.
* Real-time streaming of events into the viewer — the viewer lists; live board/stream
  is WP-5.6's channel.
* Notification history (a different screen) — MT-5.9-03.

## Target paths
* `mobile/` — audit log feature folder (screen, filter widgets, paged repository)
* `mobile/` tests — list, paging, filter wiring and no-mutation tests
* WP changelog entry

## Acceptance criteria
- [ ] The screen renders the audit trail as a read-only list with filters, per
  Section 14.1 (FR-MOB-07).
- [ ] Event rows show actor and correlation id per Section 12.5's audit-trail
  content.
- [ ] Filters map 1:1 to API-supported query parameters — no invented filters
  (Section 18 Contract row; Section 20.5).
- [ ] The feature performs zero mutating API calls, asserted by test (Section 12.5
  "the viewer is read-only"; FR-SEC-03).
- [ ] Paging follows the shared pagination conventions (WP-0.5).
- [ ] Tests green in CI (Section 20.4 items 1–2); changelog note added (item 7).

## Test command
From `mobile/`: `flutter analyze` plus the mobile test suite filtered to the audit
log (for example `flutter test --dart-define=test_filter=audit_log` or the
project's equivalent) — asserts list/paging fixtures, each filter's request wiring,
and that no mutating HTTP method is issued by the feature.

## Attachments
* [Section 12.5 — Audit trail](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.1 — Audit log screen](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.9 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Read-only is a security property, not a UI preference — the no-mutation test must
  be structural (assert request methods), so a future "quick action" addition fails
  CI rather than silently violating Section 12.5.
* Filter parity with web (WP-4.10-02) depends on what the backend endpoints expose;
  if a filter exists on web but not in the API contract, omit it here and note the
  gap — do not fork the API from a mobile screen.
* Wide event payloads (diff summaries, notes) must not be dumped raw on a phone —
  show the Section 12.5 essentials and open task detail for depth (Section 13.2-style
  progressive disclosure).
