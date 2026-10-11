# MT-4.3-04 — Implement the SSE stream hook with reconnect and status

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-04 |
| Title | Implement the SSE stream hook with reconnect and status |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-05, FR-WEB-01 |
| Priority | M |
| Dependencies | WP-1.10 complete (MT-1.10-01 stream endpoint, MT-1.10-03 resume, MT-1.10-04 heartbeat); WP-4.1 complete |
| Parent sections | 13.3 (stream hook), 9.6 (stream, resume, heartbeat), 19 (WP-4.3), 20.4, 20.5 |

## Context
Section 13.3 states: "The stream hook handles reconnect, last-event-id resume, and
visible connection status." Section 9.6 defines the wire behavior the hook must ride:
clients subscribe to `GET /events/stream` with optional filters (project, task), every
SSE message carries a monotonically increasing event id, reconnecting clients send the
last id and receive missed events before switching to live (no gaps, no duplicates),
and heartbeat comments every 15 s keep proxies alive. Server-side resume lands in
MT-1.10-03. This micro-task is the client half: a reusable hook the board (and later
screens) subscribe to.

## Inputs / Prerequisites
* Parent plan Section 9.6 — stream endpoint, filters, id-carrying messages, resume
  semantics, 15 s heartbeats.
* Parent plan Section 13.3 — hook responsibilities (reconnect, last-event-id resume,
  visible connection status).
* WP-1.10 — implemented stream (MT-1.10-01) with resume (MT-1.10-03) and heartbeat
  (MT-1.10-04) to test against.
* WP-4.1 auth (MT-4.1-02) — the Owner session the EventSource/fetch stream carries;
  Section 9.6 authorization is evaluated per connection.

## Scope (in)
* A reusable client hook subscribing to `GET /events/stream` with the current
  project's filter (Section 9.6 filters), authenticated per the app's session.
* Last-event-id bookkeeping: remember the highest received event id; on reconnect,
  send it so the server replays missed events then switches to live (Section 9.6
  no-gaps/no-duplicates contract; MT-1.10-03 server side).
* Automatic reconnect with backoff on connection loss; tolerance of heartbeat
  comments (15 s) without treating them as data or dropping the connection.
* Exposed connection status (`connecting` / `open` / `reconnecting` / `closed`) for
  UI display per Section 13.3 "visible connection status".
* Delivery of parsed events to subscribers (data layer only — no cache mutation
  here; MT-4.3-05 applies patches).
* Tests with a mocked stream: connect, receive events, heartbeat handling, dropped
  connection → reconnect with the last id, status transitions, cleanup on unmount.
* Add a WP changelog note.

## Out of scope
* Applying events to the query cache — MT-4.3-05.
* Server endpoint/resume implementation — WP-1.10.
* Polling fallback — Section 13.3 does not require one for web (mobile 14.2 does);
  add only if verification shows a need, otherwise out of scope.
* Agents never subscribe (Section 9.6) — this hook is Owner-session only by design.
* Global connection indicator placement/styling — component work with the board;
  hook only exposes the status.

## Target paths
* `web/` (SSE stream hook module)
* `web/` tests (stream hook tests with mocked EventSource/fetch stream)
* WP changelog entry

## Acceptance criteria
- [ ] The hook connects to `GET /events/stream` with the project filter and
  authenticated session (Section 9.6; Section 13.3).
- [ ] Reconnect sends the last received event id, and the hook accepts replayed
  events without duplicating or skipping — server contract from MT-1.10-03 honored
  (Section 9.6 "no gaps, no duplicates").
- [ ] Heartbeat comments (every 15 s) are tolerated and do not reset event state
  (Section 9.6; Section 20.4 item 6 context).
- [ ] Connection status is exposed and transitions correctly
  (connecting → open → reconnecting → open), satisfying Section 13.3's "visible
  connection status" requirement for the UI.
- [ ] Events are surfaced as typed payloads to subscribers with no cache mutation in
  the hook (separation for MT-4.3-05; Section 13.3 cache discipline).
- [ ] Only Section 9.6 catalog event types are accepted/forwarded; unknown types are
  ignored safely (Section 20.4 item 6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the stream hook (for example `npm test -- -t
stream`) and confirm: connect with filter, replay-after-reconnect id behavior,
heartbeat tolerance, status transitions, and catalog-type filtering; then the full
web suite stays green.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.3 — Data and state handling (stream hook)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Browser `EventSource` cannot set a custom last-event-id header on reconnect in all
  environments — the plan mandates resume behavior (Section 9.6) but not the
  transport mechanism; use whatever MT-1.10-03's contract supports (query parameter vs
  header) and record the choice; do not drop resume because of a transport default.
* Proxy buffering of SSE is a known risk (RISK-05, heartbeats are the mitigation) —
  verify with the WP-1.10 endpoint under the deployment proxy during integration; a
  hook-side test cannot prove proxy behavior.
