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

**MT-5.9-01 — Deep-link routing to the review sheet behind the biometric
gate (done).** Section 14.2's "tapping a notification deep-links to the
task's review sheet *after unlock*", in cold and warm start (the Section
19 WP-5.9 acceptance verbatim):

* **Payload contract** (`features/notifications/push_payload.dart`):
  exactly the MT-5.4-02 five-field allowlist (event type, `project_id`,
  `task_id`, `task_version`, title), parsed from the all-string FCM data
  map with the Section 7.3 id shapes validated client-side; anything
  partial or malformed **fails closed** (no navigation, never a guess),
  and only those five names are read — extras can never ride routing.
  The MT-5.4-03 tuple rides along as `dedupeKey`.
* **Gate precedence is structural, not checked:** the pending tap
  (`pendingNotificationTapProvider`) is consumed by a binder mounted
  *inside `LockGate`'s unlocked branch* — while locked the binder does
  not exist, a recorded tap simply waits, and nothing routes before
  biometric success (ADR-006). Cold start: the binder mounts after the
  first unlock and consumes the launch tap; warm start: the listener
  routes immediately when unlocked, or waits out an inactivity lock.
* **Resolution after unlock** (`notification_tap_screen.dart`): fetch
  the task from the payload id behind the standard loading state, then
  — `in_human_review` → the review sheet route (id-addressed, WP-5.8's
  contract); no longer in review **or** `TASK_NOT_FOUND` → the
  **stale fallback**; a transport/server failure → an honest error state
  with retry and a way home. *Fallback choice recorded (the MT's risk
  note):* the tap route itself presents the clear explained state with
  "Go to home" (lands on the shell root) — the plan's "e.g. home with a
  message" is satisfied without a SnackBar that can attach to the
  outgoing scaffold during `pushReplacement` and vanish; no new screen.
* Routing uses only payload ids (fetches the rest post-unlock); the
  payload title never reaches the sheet.
* Platform note (recorded): the app has no FCM transport plugin yet —
  `PendingNotificationTapNotifier.report` is the seam the platform
  callback (initial message / message-opened) will call; tests drive it
  directly. MT-5.10-05 remains the real-device backstop.
* `AppRoutes.navigatorKey` (app-level) addresses routes from widgets
  that sit above the navigator by construction.

Test evidence: `cd mobile; flutter test test\notifications\deep_link_test.dart`
→ 9/9 green (allowlist/dedupe-key/fail-closed parse unit cases; cold
start with explicit gate-before-content ordering and the parked loading
state; warm start straight-through; malformed no-op; stale fallback →
home; TASK_NOT_FOUND same path; unreachable → error + retry recovery).
`flutter analyze` → no issues.

**MT-5.9-02 — Foreground notification banner (done).** Section 14.2's
"Foreground messages display an in-app banner" (FR-MOB-04):

* `ForegroundPushHandler.present` is the foreground message seam (what
  the platform FCM callback will call): parse → **gate check** (locked
  = nothing presented, nothing recorded — the minimal payload is the
  only protection and this app shows nothing at all until unlock,
  recorded) → **dedupe** on the MT-5.4-03 `(event type, task id, state
  version)` key (a key already presented never renders again; the set
  is session-scoped and a tapped system notification also consumes its
  key, so banner and system notification never double-fire) → record
  the receipt → banner active.
* The banner renders as an overlay strip above the navigator from a
  host mounted inside the unlocked branch — payload content only (the
  short title plus the canonical wire event type, nothing fetched or
  enriched, Section 12.4/MT-5.4-02) — and does not block board
  interaction.
* **Banner tap = notification tap:** it arms the same MT-5.9-01
  pending-tap seam, so routing, unlock precedence and destinations are
  reused, not re-implemented.
* **Dismissal rule (recorded; the plan specifies none):** tap to act,
  or auto-dismiss after **6 seconds** for an untouched banner —
  dismissal never navigates and the alert stays in history. No
  explicit dismiss button (least intrusive rule that still guarantees
  the banner cannot wedge).
* Every presented banner and every tapped system notification records
  a local receipt (`NotificationReceipt`, origin-tagged, deduped on
  the MT-5.4-03 key) for MT-5.9-03's history.

Test evidence: `cd mobile; flutter test test\notifications\foreground_banner_test.dart`
→ 6/6 green (payload-only rendering with an exact text-set assertion;
tap → review sheet via the shared routing; duplicate never renders
twice; locked → nothing presented/recorded/keyed; auto-dismiss after the
recorded delay with the receipt retained; system-tap receipt recorded
and the same event blocked from re-presenting). `flutter analyze` →
no issues.

**MT-5.9-03 — Notification history with per-type toggles (done).**
Section 14.1's Notifications screen, exactly its two parts plus
MT-5.9-04's entry point (kept):

* **History** renders the locally recorded receipts (MT-5.9-02) —
  *storage interpretation recorded per the MT's risk note:* the plan
  never places the history server-side and Section 9.2 has no inbox,
  so it is the local, reverse-chronological receipt list (per-event
  type, task reference, local time; banner vs system-tap origin icon),
  capped at 200 rows, persisted in SharedPreferences (plain local
  cache, never secrets — the app-wiring pattern `main()` overrides).
  Loading/empty/error states per Section 20.3; a *corrupted* local
  cache is discarded and overwritten rather than becoming an error
  dead-end (it is a cache, Section 14.2); offline the list still reads
  (local).
* **Toggles** bind the MT-5.4-05 backend through the generated client
  (NFR-11; OpenAPI + `tool/openapi_client.dart` regen): opening loads
  the set, the toggle list *is* the GET response (no invented types,
  Section 20.5; wire keys stay visible next to display copy), a change
  reflects immediately (optimistic, one save at a time, switches lock
  in flight) and persists via `PUT`; a failed save **restores the
  prior value** and surfaces catalog-friendly copy (raw server text
  never shown); a transport failure renders the Section 14.2 offline
  state — clear copy, nothing queued, no automatic retry — on both
  load (with retry) and save.
* Layout decision (recorded): one scroll surface with a shrink-wrapped
  history list — small phones never clip a toggle or retry affordance
  (the first cut overflowed at 600 px height in tests).
* Harness updates caused by the screen's on-mount loads:
  `navigation_shell_test` gained the two fakes and retires the
  Notifications "placeholder" flag (the fragment assertion stays — the
  caption still carries "per-event-type toggles"); `audit_log_test`'s
  entry-point case gained the same two overrides. Shared fakes live in
  `test/notifications/notifications_test_support.dart`.

Test evidence: `cd mobile; flutter test test\notifications\notifications_history_test.dart`
→ 9/9 green (newest-first receipt rendering with type/task/time;
loading; empty; unreadable store → error → retry recovery; toggle set
mirrors the backend 1:1 with OQ-13 defaults; optimistic persist with
in-flight lock; failed save restores + friendly error with raw text
asserted absent + dismiss; offline save refusal with exactly one
attempted request ever; offline load state with retry; audit entry
present). Whole folder `flutter test test\notifications` → 24/24;
full suite → **268 passed** (243 baseline + 25 new);
`flutter analyze` → no issues; `dart format` clean.

### Deferred

_(none — MT-5.9-01/02/03 landed in batch 11; the three deferral notes
above were their pre-declaration and are retired with the entries.)_
