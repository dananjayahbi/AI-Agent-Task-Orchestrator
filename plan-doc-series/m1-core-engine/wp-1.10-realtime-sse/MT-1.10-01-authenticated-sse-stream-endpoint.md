# MT-1.10-01 — Implement the Authenticated SSE Stream Endpoint with Filters

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-01 |
| Title | Implement the authenticated SSE stream endpoint with filters |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | FR-WEB-05, NFR-03 |
| Priority | M |
| Dependencies | MT-1.9-05 (WP-1.9 complete; event log and publish flow in place) |
| Parent sections | 9.6, 9.2, 12.2, 19.1 (WP-1.10), ADR-002, 20.4, 20.5 |

## Context
Section 9.6: clients subscribe to `GET /events/stream` with optional filters
(project, task); each SSE message carries the event's monotonically increasing id.
Section 9.2 lists `GET /events/stream` (SSE, resume via last event id) and
`GET /events` (history, filters) as Owner-facing endpoints. ADR-002 fixes SSE as the
primary realtime channel for v1. This task creates the authenticated stream endpoint
that later tasks add fan-out, resume, heartbeat and authorization filtering to.

## Inputs / Prerequisites
* MT-1.9-05 — WP-1.9 complete: Event rows exist, committed events publish to Redis.
* Parent plan Section 9.6 — endpoint, filters (`project`, `task`), envelope fields.
* Parent plan Section 9.2 — endpoint paths and their caller (Owner).
* Parent plan Section 12.2 — authentication: Owner session (cookies + CSRF) and device
  tokens are valid callers; agents never subscribe.
* WP-1.1 — ASGI server configured for long-lived streaming responses.

## Scope (in)
* `GET /events/stream` implemented as an authenticated SSE response with
  `Content-Type: text/event-stream` and the correct no-buffering headers for the
  ASGI server.
* Query filters `project` and `task` per Section 9.6, validated against the canonical
  error envelope on bad input (Section 9.2).
* `GET /events` history endpoint with the same filters, cursor-paginated per the
  WP-0.5 pagination conventions, returning stored Event rows in `id` order.
* Authentication for both endpoints: Owner session or device token; agent tokens are
  rejected.
* OpenAPI/documented surface updated for the history endpoint; schema diff reviewed
  (Section 20.4 item 4).

## Out of scope
* Redis fan-out into live connections — MT-1.10-02.
* Resume via last event id — MT-1.10-03 (this task may stub the id handoff only).
* Heartbeat comments — MT-1.10-04.
* Per-event authorization filtering beyond caller authentication — MT-1.10-05.
* Load testing — MT-1.10-06.
* WebSocket — rejected by ADR-002/OQ-01 for v1.

## Target paths
* `backend/apps/events/views.py` (stream and history endpoints)
* `backend/apps/events/urls.py`
* `backend/tests/events/test_stream_endpoint.py`
* WP changelog entry

## Acceptance criteria
- [ ] `GET /events/stream` requires authentication; an unauthenticated or agent-token
  request is rejected with a canonical error code from Section 9.2.
- [ ] Filters `project` and `task` narrow the stream/history exactly as Section 9.6
  specifies; the history endpoint returns rows in `id` order (Section 20.5).
- [ ] Each SSE message carries the event's monotonically increasing id from the
  Event model (Section 9.6).
- [ ] The response survives the ASGI server's streaming path without buffering the
  whole body (verified by an early-flush test).
- [ ] OpenAPI contract updated with schema diff reviewed (Section 20.4 item 4);
  error codes used exist in the catalog (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/events/test_stream_endpoint.py -v` — auth rejection cases,
filter behavior, history ordering, and early-flush streaming assertion.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (events endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-002 — SSE as the primary realtime channel](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Long-lived streaming interacts with ASGI worker timeout and proxy buffering — the
  15 s heartbeat (MT-1.10-04) and tunnel verification (WP-5.1/MT-5.1-04) exist for
  this; do not tune buffers ad hoc here.
* Section 9.2 does not state whether the stream and history endpoints accept the same
  filter parameter names — use the Section 9.6 names (`project`, `task`) and record
  the choice in the changelog note.
