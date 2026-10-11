# MT-5.7-02 — Implement the live checkpoint feed surviving backgrounding

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.7-02 |
| Title | Implement the live checkpoint feed surviving backgrounding |
| Parent WP | WP-5.7 — Task detail and live checkpoint stream (Milestone M5) |
| Requirements | FR-MOB-03 |
| Priority | M |
| Dependencies | MT-5.7-01 (detail screen region); MT-5.6-04 (foreground live updates); MT-5.6-05 (resume replay from last event id) |
| Parent sections | 14.1 (checkpoint stream), 14.2 (Realtime: foreground SSE, resume replay, polling fallback), 9.6 (stream, `task.checkpoint`), 9.2 (checkpoints history), 19 (WP-5.7 acceptance), 20.4, 20.5 |

## Context
Section 14.1 lists the "checkpoint stream" on task detail; Section 14.2 fixes mobile
realtime: "SSE stream when foregrounded; on resume, replay from the last event id;
fall back to polling if the stream cannot be maintained." Section 19 WP-5.7
acceptance: "feed updates in real time and survives backgrounding." The feed content
mirrors the web component (Section 13.2: reverse-chronological with percent, message,
token usage) over `GET /tasks/{id}/checkpoints` (history) plus live `task.checkpoint`
events (Section 9.6), riding the WP-5.6 stream client (MT-5.6-04 foreground updates,
MT-5.6-05 resume replay).

## Inputs / Prerequisites
* Parent plan Section 14.2 — Realtime contract (foreground SSE, last-event-id
  resume, polling fallback).
* Parent plan Section 9.6 — stream semantics, `task.checkpoint` event, 15 s
  heartbeats, no-gaps/no-duplicates.
* Parent plan Section 9.2 — `GET /tasks/{id}/checkpoints` initial history.
* Parent plan Section 7.2 — Task Checkpoint fields (`message`, `percent`,
  `token_usage`, `kind`, server `timestamp`).
* WP-5.6 — MT-5.6-04 (foreground live updates) and MT-5.6-05 (resume replay) as the
  transport layer.

## Scope (in)
* The checkpoint stream UI in MT-5.7-01's region: reverse-chronological rows with
  percent, message, token usage and kind, fed by initial history fetch then live
  `task.checkpoint` events.
* Backgrounding lifecycle (Section 14.2): while foregrounded, apply SSE events
  live; when the app is backgrounded, the stream may drop; on resume, replay from
  the last received event id via MT-5.6-05 — missed checkpoints append without
  duplicates or gaps (Section 9.6 contract).
* Polling fallback: if the stream cannot be maintained (Section 14.2), fall back to
  polling `GET /tasks/{id}/checkpoints` on a sensible interval with a visible
  degraded-liveness indicator; recover to SSE when possible.
* Ordering/dedup by event id and server timestamp (Section 0.4 server clock; P7);
  reconnect handling reuses the WP-5.6 stream client rather than a second
  connection.
* Widget/unit tests: live append while foregrounded, simulated background/resume
  with replay of missed events (exactly once per checkpoint), polling fallback path,
  dedupe on overlap between replay and history fetch.
* A WP changelog note.

## Out of scope
* The web feed — WP-4.6 (MT-4.6-02).
* Stream client implementation — MT-5.6-04/05 (consume it).
* Server checkpoint ingestion/lease extension — WP-1.8.
* Push notification of checkpoints — not in Section 9.8 triggers; do not invent.
* Stalled indicators — WP-4.9 (web) / not assigned for mobile v1.

## Target paths
* `mobile/` (checkpoint stream widget and lifecycle wiring)
* `mobile/` tests (feed and backgrounding tests)
* WP changelog entry

## Acceptance criteria
- [ ] The feed shows checkpoints live while foregrounded: percent, message and token
  usage per Section 13.2's component spec applied to mobile (Sections 7.2, 14.1).
- [ ] Backgrounding survival works per Section 14.2: on resume, missed events replay
  from the last event id and append exactly once — "no gaps, no duplicates"
  (Section 9.6; Section 19 WP-5.7 acceptance).
- [ ] Polling fallback engages when the stream cannot be maintained and is visibly
  indicated (Section 14.2).
- [ ] Ordering uses server timestamps/event ids — no client-authoritative ordering
  (Section 0.4, Principle P7).
- [ ] Initial history and live/replayed events dedupe correctly (Section 9.6).
- [ ] Only catalog event types processed; unknown types ignored safely
  (Sections 9.6, 20.4 item 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to the feed (for example
`flutter test --dart-define=test_filter=checkpoint` or the project's equivalent) and
confirm foreground live append, background/resume replay with exactly-once
checkpoint ids, polling fallback, and history/event dedupe; then the full mobile
suite stays green.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (Realtime)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Replayed checkpoints plus a fresh history fetch can double-render — define one
  reconciliation order (fetch history first, then apply replay) and test the overlap
  case; this is the classic failure mode of Section 14.2's resume rule.
* Polling interval vs battery/data is unspecified — choose conservatively, surface
  the degraded state (Section 14.2 requires the fallback, not a specific cadence);
  record the interval in the changelog.
* OS may suspend timers in background — correctness must not depend on timer ticks
  while backgrounded; replay-on-resume is the source of truth (Section 14.2).
