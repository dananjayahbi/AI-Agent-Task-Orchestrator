# WP-5.9 Mobile Notifications — Changelog

One entry per micro-task, in ID order. Owner scope: `mobile/**` + this
changelog only.

## Unreleased

**MT-5.9-04 — Read-only audit log viewer (done).**
`AuditLogScreen` behind the `/audit-log` area route with the Section
14.1 "read-only list with filters": reverse-chronological rows showing
the Section 12.5 essentials the envelope carries — what changed
(canonical Section 9.6 wire string via the generated serializer, never
the Dart enum name), actor (`type · ref`), ids, local-rendered time —
plus navigation from a row to its task detail (navigation, not
mutation). Filters are exactly the two `GET /events` documents
(`project`, `task`), validated client-side against the Section 7.3 id
shapes before any request, with apply/clear, individual-clear chips,
distinct empty-log / empty-filtered-results / loading / error states,
a failed-refresh notice over kept data, and a bounded cursor walk
(page_size 100, max 50 pages) that follows `next_cursor` to the end
(WP-0.5) before presenting the history reversed. Entry point: an
"Open audit log" button on the Notifications tab, beside Notifications
per Section 14.1 (the notifications history itself stays the
MT-5.9-03 placeholder).

Decisions (recorded per the MT risk notes):
- **Correlation id is absent by contract, not by omission:** Section
  9.6 fixes the envelope at exactly seven keys and the backend keeps
  `correlation_id` a database column that is "never an envelope key" —
  so the viewer shows the actor/ids/time/type essentials the API
  carries and does not fake a correlation field. If the plan wants it
  on screen, it is an envelope contract change (Section 18), raised
  here rather than worked around.
- **Actor/date/type filters are omitted, not emulated:** `GET /events`
  supports only `project` and `task` (the web filter set in
  MT-4.10-02 names five dimensions the API does not accept — Section
  18 Contract row; no client-side post-filtering of one page).
- **Ascending endpoint, newest-first screen:** the history endpoint
  declares id-ascending with a forward-only cursor, so the walk follows
  the cursor to the end (bounded) and displays the accumulated rows
  reversed; hitting the bound is an honest "narrow it with a filter"
  error — never a wrong-ended (oldest) list dressed as the newest. A
  descending sort parameter would be the API-side fix if histories
  outgrow the bound (contract change, not invented here).
- **No raw `data` dumps on a phone:** wide payloads stay behind task
  detail (progressive disclosure, Sections 13.2/12.5).
- **Structurally read-only:** `AuditLogRepository` exposes no mutating
  method; the widget test exercises filters/navigation and asserts
  every recorded operation is the one read (`FR-SEC-03`).

Test evidence: `cd mobile; flutter test test\audit_log\` → 8/8 green
(reverse-chronological essentials + wire-type/actor/time rows, cursor
paging with round-trip cursor, 1:1 filter wiring + pagination reset,
invalid filter makes no request, distinct empty states, loading +
catalog error + retry recovery, row → task detail with the
no-mutation assertion, notifications entry point). `flutter analyze` →
no issues.

### Deferred

- **MT-5.9-01 — deep-link routing to the review sheet behind the
  biometric gate.** Concrete blocker: MT-5.4-01/02 (FCM sender and the
  payload contract with ids) are not implemented — WP-5.4 has no
  changelog and no push channel exists in the app, so there is no
  notification tap to route (the MT's own dependency list). The route
  contract it consumes is in place from WP-5.8 (`/review` takes the
  task id) and the app-level gate already wraps the navigator, so the
  remaining work is the FCM payload + tap handling when WP-5.4 lands.
- **MT-5.9-02 — foreground notification banner.** Same WP-5.4
  blocker (nothing to display yet).
- **MT-5.9-03 — notification history with per-type toggles.** Same
  WP-5.4 blocker; the Notifications tab remains the honest
  placeholder (which now carries the MT-5.9-04 entry point).
