# MT-1.10-02 — Implement Redis Fan-Out to Connected Stream Subscribers

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-02 |
| Title | Implement Redis fan-out to connected stream subscribers |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | FR-WEB-05, NFR-03 |
| Priority | M |
| Dependencies | MT-1.10-01 (stream endpoint exists), MT-1.9-03 (post-commit publish exists) |
| Parent sections | 9.6, 9.10, 19.1 (WP-1.10), ADR-002, 20.4, 20.5 |

## Context
Section 9.6: after commit the event is published to a Redis channel, and connected
subscribers on `GET /events/stream` receive it live. ADR-002 chose Redis pub/sub
fan-out for one-way feeds. This task connects the two halves built in WP-1.9
(publish) and MT-1.10-01 (stream): a subscription layer that receives channel
messages and dispatches them to matching open SSE connections.

## Inputs / Prerequisites
* MT-1.10-01 — authenticated stream connections to dispatch into.
* MT-1.9-03 — publisher and payload contract (Section 9.6 envelope, ids may arrive
  out of order across concurrent commits — consumers order by `id`).
* Parent plan Section 9.10 — Redis connection settings are environment-driven with
  documented defaults.
* Section 9.6 filters — dispatch must respect each connection's `project`/`task`
  filters before sending.

## Scope (in)
* A subscription/relay layer that listens on the configured Redis channel and, for
  every published envelope, dispatches it to each open stream connection whose
  filters match (`project`, `task`).
* One shared Redis subscription per process (not one per connection), fanned out in
  application code, so connection count does not multiply Redis subscriptions.
* Connection lifecycle handling: register on stream open, unregister on close/cancel;
  a failed or closed connection is dropped without affecting others.
* Ordering discipline: dispatch by monotonic `id`; skip or de-duplicate messages a
  connection has already received (foundation for resume in MT-1.10-03).
* Tests: N open connections with different filters each receive exactly the matching
  events; disconnects do not leak registrations.

## Out of scope
* Replay of missed events on reconnect — MT-1.10-03.
* Authorization beyond filter matching — MT-1.10-05 (assumed present from
  MT-1.10-01/MT-1.10-05; this task only applies the connection's established scope).
* Publisher-side changes — MT-1.9-03 (do not modify the publish path).
* Horizontal-scaling topology (multiple backend workers) — not specified by the plan
  for v1; single-process fan-out is the deliverable.

## Target paths
* `backend/apps/events/fanout.py`
* `backend/apps/events/views.py` (register/unregister hooks)
* `backend/tests/events/test_fanout.py`
* WP changelog entry

## Acceptance criteria
- [ ] A published event reaches every connected stream whose filters match it and no
  stream whose filters exclude it (Section 9.6).
- [ ] The process maintains a single Redis subscription regardless of connection
  count (Section 9.6 fan-out design, ADR-002).
- [ ] Closing a stream unregisters it; a test shows no registration leak after
  repeated open/close cycles.
- [ ] Envelopes dispatched to a connection carry the unmodified Section 9.6 field
  names (Section 20.5).
- [ ] Redis settings come from documented configuration with defaults (Section 9.10;
  Section 20.4 item 3); changelog note added (item 7).

## Test command
`pytest backend/tests/events/test_fanout.py -v` — multi-connection filter matching,
lifecycle cleanup, and payload equality with the published envelope.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-002 — SSE primary, Redis pub/sub fan-out](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Redis pub/sub is fire-and-forget: a dropped message is only recoverable via the
  Event table (resume in MT-1.10-03). Do not add unbounded in-process buffering here;
  note this dependency in the changelog.
* Concurrent commits can publish out of `id` order; the dispatch layer must not
  assume ordering — verified by an out-of-order injection test.
