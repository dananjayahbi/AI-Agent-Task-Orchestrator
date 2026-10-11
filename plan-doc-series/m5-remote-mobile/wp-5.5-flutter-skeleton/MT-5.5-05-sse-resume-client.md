# MT-5.5-05 — Implement the SSE client with resume

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-05 |
| Title | Implement the SSE client with resume |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | NFR-04 (reconnect with backoff, no lost state); NFR-11 |
| Priority | M |
| Dependencies | MT-5.5-01 (scaffold), MT-5.5-03 (client/auth wiring), WP-1.10 (backend realtime gateway) |
| Parent sections | 9.6 (event envelope, resume via last event id, 15 s heartbeats), 14.2 (realtime), 19 (WP-5.5), 20.4, 20.5 |

## Context
Section 9.6 defines the realtime contract: clients subscribe to `GET /events/stream`
with optional filters; each SSE message carries a monotonically increasing event id;
reconnecting clients send their last id and receive missed events before switching
to live — "no gaps, no duplicates"; heartbeat comments every 15 s keep connections
alive through proxies. Section 14.2 applies this to mobile: "SSE stream when
foregrounded; on resume, replay from the last event id; fall back to polling if the
stream cannot be maintained." WP-5.5's deliverable "stream client" is this slice —
the reusable subscription the dashboard/board/detail WPs (5.6-5.8) will consume.

## Inputs / Prerequisites
* Parent plan Section 9.6 — event envelope (`id`, `type`, `project_id`, `task_id`,
  `occurred_at`, `actor`, `data`), resume semantics, heartbeats, per-connection
  authorization (Owner sees all; agents never subscribe).
* Parent plan Section 14.2 — foreground-only streaming, resume on app resume,
  polling fallback.
* Parent plan Section 15 (Cloudflare) / RISK-05 — tunnel or proxy buffering can
  break SSE; mitigations are heartbeats, verification in WP-5.1 and polling
  fallback.
* MT-5.5-03 — authenticated request layer the stream uses; WP-1.10 — backend
  gateway to test against.

## Scope (in)
* An SSE client service: connect to `GET /events/stream` with the authenticated
  session, parse the event envelope into typed events, and expose them as a stream
  to feature layers; support the filters the API defines (project, task).
* Resume: persist the last processed event id in memory-and-storage appropriate for
  a session (documented; id is not secret) and send it on reconnect so replay
  covers the gap exactly once (Section 9.6 "no gaps, no duplicates").
* Lifecycle per Section 14.2: stream only while foregrounded; on app pause,
  disconnect cleanly; on resume, reconnect with last-event-id replay; heartbeat
  handling keeps intermediaries from idling the connection out.
* Reconnect with exponential backoff and jitter (NFR-04), bounded; after repeated
  failure, enter the documented polling fallback (Section 14.2) that fetches event
  history (`GET /events`) and emits the same typed events, restoring the stream
  when possible.
* Connection-status observable (connected/reconnecting/polling/disconnected) for UI
  badges in later WPs.
* Unit tests with a fake transport: envelope parsing, resume id sent and replay
  de-duplication, pause/resume cycles, backoff schedule, fallback transitions.

## Out of scope
* Applying events to query caches / board UI — WP-5.6 (MT-5.6-04/05 live updates
  and resume replay at the feature level).
* Backend gateway, authorization and event emission — WP-1.10/Section 9.6.
* Push notifications as an alternative delivery path — WP-5.4.
* Web stream hook — WP-4.3 (same contract, different stack).
* Tunnel verification under buffering — WP-5.1 (RISK-05 mitigation).

## Target paths
* `mobile/` (SSE client service, typed event model, connection-status observable)
* `mobile/` tests (stream client unit tests)
* WP changelog entry

## Acceptance criteria
- [ ] Events from `GET /events/stream` deserialize into the exact Section 9.6
  envelope fields; malformed messages are skipped with a logged warning, never
  crashing the stream.
- [ ] Reconnect sends the last processed event id and replayed events are processed
  exactly once — a test simulates a gap and asserts no missing/duplicate handling
  (Section 9.6).
- [ ] App pause disconnects; app resume reconnects with replay; after bounded
  backoff failures the client enters polling fallback and recovers to streaming
  (Section 14.2, NFR-04, RISK-05).
- [ ] Heartbeats (15 s comments per Section 9.6) are tolerated without resetting
  resume state.
- [ ] Connection status is observable by UI layers; only catalog-relevant errors
  surface (Section 20.4 item 5).
- [ ] Tests, lint and analyze green in CI (Section 20.4 item 2); changelog note
  added (item 7).

## Test command
From `mobile/`, run `flutter analyze` and `flutter test` with the stream tests
selected (e.g. `flutter test test/sse_client_test.dart`); later integration
against WP-1.10 runs in the mocked-backend suite (Section 18 mobile UI row).

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.2 — Mobile-specific behaviors](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Resume correctness is the whole point — an id persisted before the event's effect
  is durably handled creates gaps; define "last processed" precisely in tests
  (processed, not merely received).
* Tunnel buffering (RISK-05) may only surface in production paths; keep the polling
  fallback genuinely usable so the app degrades honestly rather than appearing
  live-but-stale.
