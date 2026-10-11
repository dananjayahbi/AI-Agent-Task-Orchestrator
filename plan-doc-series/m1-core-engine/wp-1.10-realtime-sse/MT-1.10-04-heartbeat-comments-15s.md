# MT-1.10-04 — Add 15-Second Heartbeat Comments for Proxy Keep-Alive

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-04 |
| Title | Add 15-second heartbeat comments for proxy keep-alive |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | FR-WEB-05, NFR-03 |
| Priority | S |
| Dependencies | MT-1.10-02 (fan-out connected to live streams) |
| Parent sections | 9.6, 15.4, 19.1 (WP-1.10), 20.4, 20.5 |

## Context
Section 9.6: "Heartbeat comments every 15 s keep Cloudflare and mobile connections
alive." Section 15.4: SSE through the tunnel needs verified idle timeouts and no
response buffering; the 15 s heartbeat is designed for this (verified in WP-5.1).
Section 19 (WP-5.1) acceptance requires SSE to stay connected at least 30 minutes
idle with heartbeats. This task implements the server side.

## Inputs / Prerequisites
* MT-1.10-01/MT-1.10-02 — live stream connections to keep alive.
* Parent plan Section 9.6 — exact interval (15 s) and form (SSE comments, i.e. lines
  starting with `:`).
* Parent plan Section 15.4 — the Cloudflare/mobile keep-alive rationale.

## Scope (in)
* Per-connection heartbeat emitting an SSE comment line every 15 seconds (default
  configurable per Section 9.10) while the stream is open.
* Heartbeats do not carry event ids, do not advance the resume position, and do not
  appear in the Event table.
* Timer cleanup on connection close (no task/timer leaks).
* Test: an idle connection receives a comment at least every 15 s; ids/resume state
  are unaffected; timers are cleaned up on disconnect.

## Out of scope
* Tunnel-side idle timeout verification — MT-5.1-04 (WP-5.1).
* Mobile client keep-alive behavior — WP-5.x Flutter app (Section 14.2).
* Load test of sustained connections — MT-1.10-06.
* Server-side ping on Redis — not specified; do not add.

## Target paths
* `backend/apps/events/views.py` (heartbeat in the stream loop)
* `backend/tests/events/test_heartbeat.py`
* WP changelog entry

## Acceptance criteria
- [ ] An idle authenticated stream receives an SSE comment exactly at the Section 9.6
  cadence — every 15 seconds (documented default, configurable per Section 9.10).
- [ ] Heartbeats are comment lines: they carry no event id and never change the
  client's resume position (Section 9.6).
- [ ] Closing the connection cancels the heartbeat timer (leak test passes).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/events/test_heartbeat.py -v` — asserts comment cadence on an
idle stream, no-id semantics, and timer cleanup on disconnect.

## Attachments
* [Section 9.6 — Realtime gateway and event model (heartbeat)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.4 — Operational details (SSE through the tunnel)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.1 acceptance (30 min idle)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Interval must not be raised above the proxies' idle timeouts (Cloudflare ~100 s
  class limits) — the plan fixes 15 s for this reason; make it configurable only
  downward-reviewable, and note the tunnel verification belongs to WP-5.1.
* Tests asserting wall-clock timing can flake in CI — use a short configurable
  interval in tests while keeping the 15 s default.
