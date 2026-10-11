# MT-5.6-04 — Implement live updates while foregrounded

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.6-04 |
| Title | Implement live updates while foregrounded |
| Parent WP | WP-5.6 — Overview dashboard and mobile Kanban (Milestone M5) |
| Requirements | FR-MOB-02, FR-MOB-01 |
| Priority | M |
| Dependencies | MT-5.6-03 (board data to patch); MT-5.6-01 (dashboard); WP-5.5 complete (MT-5.5-05 SSE client with resume); WP-1.10 complete |
| Parent sections | 14.2 (Realtime: SSE when foregrounded, polling fallback), 9.6 (stream and envelope), 19 (WP-5.6), 20.3, 20.4, 20.5 |

## Context
Section 14.2 fixes mobile realtime behavior: "SSE stream when foregrounded; on
resume, replay from the last event id; fall back to polling if the stream cannot be
maintained." Section 14.1's Board row promises "live updates". Section 19 WP-5.6
acceptance: "state changes appear live." The stream itself (endpoint, resume,
heartbeat) is WP-1.10 and the Flutter SSE client with resume is MT-5.5-05; this
micro-task connects the app's foreground lifecycle to the stream and patches the
dashboard/board state from events — resume replay is the separate slice MT-5.6-05.

## Inputs / Prerequisites
* MT-5.5-05 — SSE client with resume (transport layer).
* MT-5.6-01 / MT-5.6-03 — dashboard and board state to receive patches.
* MT-5.6-02 — current project; Section 9.6 stream filters (project-scoped
  subscription).
* Parent plan Section 9.6 — event envelope (`id`, `type`, `project_id`, `task_id`,
  `data.task_version`) and closed event catalog.
* Parent plan Section 14.2 — foreground/background lifecycle rules.

## Scope (in)
* Lifecycle wiring: open/subscribe the SSE stream when the app is foregrounded;
  pause/close on background (no battery-draining connection while suspended).
* Project filter: the subscription follows the MT-5.6-02 current project
  (Section 9.6 filters).
* Foreground event application: patch board page state and dashboard from catalog
  events (`task.transitioned` moves cards between the six pages; `task.updated`,
  `task.claimed`, `task.released`, `task.checkpoint`, `task.created`,
  `task.lease_*`, `merge.*`, `review.*` update cards/badges/banners where the board
  or dashboard displays the field) — same stale-version guard discipline as the web
  (ignore patches with older `task_version`).
* Polling fallback: if the stream cannot be maintained, fall back to periodic
  refetch of board/dashboard data per Section 14.2, with the fallback visibly honest
  (no fake "live" indication).
* Visible connection/liveness indication consistent with the web's "visible
  connection status" idea (Section 13.3) adapted to mobile presentation.
* Tests: foreground → events patch pages; background → stream stops; stale-version
  ignored; forced stream failure → polling fallback engages and recovers; unknown
  catalog types ignored.
* Add a WP changelog note.

## Out of scope
* Replay-from-last-event-id on resume — MT-5.6-05 (explicitly the next slice).
* Push notifications while backgrounded — WP-5.4 / WP-5.9 (foreground live updates
  are the in-app path; push is the background path).
* Web stream hook/cache — MT-4.3-04 / MT-4.3-05 (reference behavior only).
* Server stream implementation — WP-1.10.
* Mutating actions driven by events (approve etc.) — WP-5.8 review sheet.

## Target paths
* `mobile/` (stream lifecycle service, event → state patching, polling fallback)
* `mobile/` tests (lifecycle, patching, fallback tests)
* WP changelog entry

## Acceptance criteria
- [ ] While foregrounded, state changes made by agents appear live on the board
  without user refresh — Section 19 WP-5.6 acceptance "state changes appear live"
  (FR-MOB-02 real-time Kanban) — demonstrated by a test applying an event to idle UI
  state.
- [ ] The stream connects only while foregrounded: backgrounding suspends the
  subscription (Section 14.2 "SSE stream when foregrounded").
- [ ] The subscription carries the current project's filter (Section 9.6) and follows
  MT-5.6-02 selection changes.
- [ ] Patching honors `task_version` staleness guards and processes only Section 9.6
  catalog event types (Section 20.4 item 6).
- [ ] When the stream cannot be maintained, the app falls back to polling and shows
  honest liveness state (Section 14.2 fallback; RISK-05 mitigation).
- [ ] Errors surfaced during stream/polling map from canonical codes where applicable
  (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile test suite filtered to realtime (for example
`flutter test --dart-define=test_filter=realtime` or the project's equivalent) and
confirm: foreground subscription with project filter, event patching of board pages,
background suspension, stale-version ignore, and polling fallback on forced stream
failure; then the full mobile suite stays green.

## Attachments
* [Section 14.2 — Realtime behavior (foreground SSE, polling fallback)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Event envelope and catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Tunnel buffering breaking mobile SSE is a known risk (RISK-05) — the polling
  fallback is the plan's mitigation; make sure fallback detection is based on actual
  stream health (heartbeat loss), not a timer alone, and verify under the WP-5.1
  tunnel during integration.
* Foreground/background transitions on mobile are OS-dependent — define exactly which
  lifecycle events count as foreground/background and test on both platforms;
  over-eager reconnects drain battery, lazy ones break the 2 s-class expectation.
