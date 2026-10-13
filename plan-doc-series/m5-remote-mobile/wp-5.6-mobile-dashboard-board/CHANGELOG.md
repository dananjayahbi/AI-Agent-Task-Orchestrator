# WP-5.6 — Overview dashboard and mobile Kanban: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-5.6-01** — Home / Overview screen (Section 14.1 verbatim contents):
  project cards with per-state counts, velocity and active-agent counts,
  plus the "needs review" banner driven by the summary's `in_human_review`
  counts (FR-MOB-01). Data flows through a clean data-source seam —
  `DashboardSummarySource` with the Dio implementation
  (`DioDashboardSummarySource`, shared client/interceptors/error mapping)
  and a scripted fake in tests — reading `GET /dashboard/summary`; see the
  gap note below for why the hand-authored tolerant `DashboardSummary`
  model (wire keys documented by Section 14.1, canonical state keys via
  the generated serializers, G-01) replaces the nonexistent generated type.
  Screen states are separate and tested (Section 20.3): loading skeleton,
  empty (no projects), friendly catalog-code error with retry (Section
  20.4 item 5; the raw server message never reaches the UI — Section
  12.4), and offline-stale presentation served from the Section 14.2
  read-only cache (`JsonCache`/`SharedPreferences`, wired in `main()`,
  network-first with honest stale banner — cached data is never shown as
  live; no mutating affordance anywhere). The screen renders only behind
  the WP-5.5 biometric gate — a locked-gate test asserts zero dashboard
  fetches. Card tap wires the MT-5.6-02 handoff: selects the project and
  lands on the Board tab. Velocity/active agents are payload-owned, never
  recomputed client-side (MT-5.6-01 risk note; a backend that omits them
  is a backend gap). Tests: `test/dashboard/` (20).
- **MT-5.6-02** — Project selector on the Board screen over `GET /projects`
  through the generated typed client behind the `ProjectsRepository` seam
  (cursor-paged; NFR-11; id + name + status labels). Selection state
  (`currentProjectProvider`) is the single source of truth: changing it
  refetches the board and re-filters the SSE subscription
  (`SseClient.updateProjectFilter`, Section 9.6) — both consumers watch
  one provider, asserted end-to-end by tests. Dashboard card tap
  preselects the project and the selector shows it (both directions
  tested; the `DropdownButtonFormField` syncs external selection). Empty
  (no projects) and error states are distinct with catalog-mapped copy
  and working retry (Section 20.3/20.4). Recorded decisions: selection is
  session-local (a persisted pick would be restored before the device
  proves connectivity — Section 14.2 honesty); the selector stays visible
  with a single project and auto-selects it when unambiguous; stale
  selections never ghost (they clear to the honest "select a project"
  state). Fast successive selections are guarded by a monotonic load
  token in the board notifier (MT-5.6-02 race risk note) — an older
  project's fetch can never overwrite the newer selection. Tests:
  `test/board/project_selector_test.dart` (6).
- **MT-5.6-03** — The WP-5.5 placeholder BoardScreen is replaced by the
  real screen: a horizontally paged board (PageView) over exactly the six
  canonical G-01 states in Section 8.1 order with a touch chip-row page
  indicator carrying per-state counts, swipe/tap paging (FR-MOB-02),
  per-page pull to refresh (Section 14.1), and separate per-page
  loading/empty/error states with catalog-mapped friendly copy and retry
  (Section 20.3/20.4). `board_states.dart` owns only order + labels +
  grouping (canonical `StateEnum` keys from the API types, no
  hand-copied strings) plus a coverage guard that fails loudly if the
  schema grows a seventh state; merge-pending renders as the Section 8.1
  "Approved, merging" badge on the card — never a seventh page. Touch
  task cards show id, title, priority and worker/progress basics and tap
  through to the WP-5.7 task-detail route (stub handoff, tested).
  **Grouping decision recorded (MT-5.6-03 risk note):** one project-scoped
  cursor-paged list (`GET /projects/{pid}/tasks` via the generated client)
  grouped client-side; per-page fetching would multiply round trips
  without buying correctness — revisited only if payload size forces it.
  `BoardCache` mirrors MT-5.6-01's read-only cache with tasks
  round-tripping through the generated serializers (NFR-11; corrupt
  entries read as absent). The board notifier keeps Section 20.3 states,
  the stale-from-cache banner, and an honest offline presentation. **Gap
  fixed by the verification pass:** the original run left
  `BoardNotifier`'s cache hooks as `UnimplementedError` stubs (every load
  would have crashed) — wired to `BoardCache`; `jsonCacheProvider` was
  never overridden in app wiring — wired in `main()`; three
  `EnumClass` switch-expressions and a non-const throw failed
  `flutter analyze` — all corrected. Tests:
  `test/board/board_screen_test.dart` (15).
- **MT-5.6-04** — Foreground live updates reuse `core/realtime/SseClient`
  (MT-5.5-05) verbatim — no forked stream client: the board notifier
  consumes its typed `events` and `status` ("extend, don't fork"), and
  the client gained `updateProjectFilter` (a filter switch reconnects
  with `Last-Event-ID` so the switch itself loses nothing and is not
  counted as a stream failure). `board_event_patcher.dart` implements the
  documented patch-vs-refetch split: catalog-only (Section 9.6 closed
  set), project-scoped, `task_version` staleness guard (Section 7.2 — an
  older event can never regress the cache), pure in-place patches for
  documented payloads and targeted `GET /tasks/{id}` refetches for the
  rest (never a board-list refetch on live traffic). Tests prove:
  foreground events move cards between pages with zero user refresh and
  zero refetches; stale versions and unknown/non-catalog types are
  ignored without breaking the stream; the subscription follows the
  MT-5.6-02 selection (reconnect carries the new filter plus
  `Last-Event-ID`); backgrounding suspends the stream and resuming
  restarts it (`SseLifecycleBinder`, Section 14.2 foreground-only rule);
  forced stream failure enters the documented polling fallback — full
  board refetch, history polling carries the project filter, and the
  status is honest (never "connected" while polling). The AppBar liveness
  chip reports the transport's real status (`boardLivenessLabel`):
  polling shows "Periodic updates", never "Live" (RISK-05 mitigation).
  The dashboard (MT-5.6-01 scope hand-off) debounced-refreshes from
  catalog events and on entering the polling fallback — summary counts
  follow server truth, never client-assembled numbers. Tests:
  `test/board/board_live_updates_test.dart` (10) + the liveness and
  dashboard-refresh widget tests (3).
- **MT-5.6-05** — Resume replay from the last event id (Section 14.2 /
  Section 9.6 "no gaps, no duplicates") over the same shared client: the
  highest processed id persists through `LastEventIdStore` (wired in
  `main()`), reconnects attach `Last-Event-ID`, and replayed events flow
  through the same catalog-typed, version-guarded patching as live ones.
  The board notifier adds a second, event-id idempotency layer
  (`_lastAppliedEventId` + the `appliedEventIds` test hook) so a
  replay/live overlap applies exactly once. Tests assert the exact
  applied range for a known missed set (`[1,2,3,4]` including a
  duplicated replay id), strictly monotonic application under
  out-of-order delivery, first-launch live-only with **no fabricated
  id**, the stored id surviving a simulated process restart (fresh
  client attaches it), replay rejection → full board refetch → recovery
  to live (the UI never presents a stale board as current — RISK-05
  discipline), and a task created while suspended appearing after replay
  via a targeted single-task refetch that lands on its canonical page.
  Tests: `test/board/board_resume_replay_test.dart` (6).

### Dashboard endpoint gap — `GET /dashboard/summary` is unowned

Section 9.2 lists `GET /dashboard/summary` (Owner) and Section 14.1 builds
the Home / Overview on it, but **no backend work package has implemented
it and `schemas/openapi.yaml` has no `/dashboard/summary` path** — so no
generated typed model exists (NFR-11). Per this WP's brief, MT-5.6-01 was
delivered behind the clean `DashboardSummarySource` seam with a **mocked
implementation for tests** and a Dio implementation calling
`/api/v1/dashboard/summary`; the hand-authored `DashboardSummary` model
(documented contract note in `dashboard_summary.dart`, parsing tolerant
like the WP-5.5 `DioEventHistorySource` precedent) is the single
reconciliation point once the backend lands. **Recommendation:** author a
backend micro-task to implement `GET /dashboard/summary` (MT-1.6-09
precedent for an unowned-endpoint follow-up) returning per-project cards
`{project_id, name, state_counts (six canonical G-01 keys), velocity,
active_agents}` per Section 14.1, then add the schema path, regenerate
the typed client, and swap `DioDashboardSummarySource` for the generated
call — the seam makes that a one-file change. Also raise the OQ to pin
the server's velocity definition (the payload is authoritative; the
mobile client must never compute it — MT-5.6-01 risk note). No backend
code was written from this WP (scope rule).

### Deferrals

- Live updates while **backgrounded** (push catch-up, deep links) —
  WP-5.4 / WP-5.9 (MT-5.6-04 out of scope; foreground is in-app only).
- Dashboard card live **patching from stream payloads** (as opposed to
  the debounced summary refresh used here) — pending the real
  `/dashboard/summary` contract above; the seam/localization point is in
  place.
- Task detail content behind the board's route handoff — WP-5.7;
  review actions and the review sheet — WP-5.8; web overview route —
  Section 13.1 (M4).
- Drag/move actions on the mobile board — not in Section 14.1's Board
  row.

### Verification (2026-10-13)

`flutter analyze` clean; `dart format --output none --set-exit-if-changed .`
exit 0 (in `mobile/`); `flutter test` **165/165 green** — WP-5.6 suites:
`test/dashboard/` 20 and `test/board/` 37 (selector 6, board screen 15,
live updates 10, resume replay 6), plus `navigation_shell_test` updated to
assert the real Home/Board screens (placeholders remain only where a later
WP owns them) alongside the untouched WP-5.5 suites.
`dart run tool/openapi_client.dart check` exits 0 — the drift it first
reported was **backend-owned** (the parallel attachments/policy work added
`/api/v1/attachments/*` and policy presets to `schemas/openapi.yaml`); the
client was regenerated once against that schema via the sanctioned tool and
no WP-5.6 model is affected. If `schemas/openapi.yaml` moves again before
the gate, re-run `regen` from the owning backend WP rather than editing
generated files.
