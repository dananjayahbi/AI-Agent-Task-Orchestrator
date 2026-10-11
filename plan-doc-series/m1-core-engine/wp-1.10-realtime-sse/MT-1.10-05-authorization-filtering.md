# MT-1.10-05 — Implement Per-Connection and Per-Event Authorization Filtering

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-05 |
| Title | Implement per-connection and per-event authorization filtering |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | FR-WEB-05, FR-SEC-03 |
| Priority | M |
| Dependencies | MT-1.10-03 (resume path in place), MT-1.10-02 (fan-out dispatch) |
| Parent sections | 9.6, 12.2, 12.1, 19.1 (WP-1.10), 20.4, 20.5 |

## Context
Section 9.6: "Authorization is evaluated per connection and per event (Owner sees all;
agents never subscribe)." Section 12.2 authorization matrix: "Read events" is Yes for
Owner and Device, No for every agent role; Section 12.1 lists event/API filtering by
project as the cross-project-leakage mitigation. This task enforces both dimensions
on every delivery, in live, replay and history paths.

## Inputs / Prerequisites
* MT-1.10-01 — caller authentication (Owner session, device token; agents rejected).
* MT-1.10-02 — dispatch point where per-event checks run.
* MT-1.10-03 — replay path must apply the same checks.
* Parent plan Section 12.2 — the authorization matrix ("Read events" row).
* WP-1.2 permission classes and matrix tests (MT-1.2-05, MT-1.2-07) — reuse, do not
  fork a second permission model.

## Scope (in)
* Per-connection authorization: only callers permitted by the Section 12.2 "Read
  events" row may hold a stream open; agent tokens can never subscribe; the
  connection's visible scope (owner-wide; devices only as scoped by their token) is
  fixed at connect time.
* Per-event authorization: before any delivery (live, replayed, or history page),
  the event must fall within the connection's scope (project visibility); events
  outside it are dropped, never partially sent.
* Consistency: the same checks apply to `GET /events` history so the stream cannot be
  used to read what history denies.
* Tests: matrix-driven — each Section 12.2 caller kind allowed/denied as specified;
  cross-project event leakage attempt is dropped.

## Out of scope
* Authenticating the caller — MT-1.10-01.
* The general authorization matrix for REST endpoints — WP-1.2.
* Revocation behavior of device tokens on the stream — WP-5.3 (acceptance: rejected
  on stream reconnect); coordinate but do not implement here.
* Agent capabilities — agents are simply never subscribers (Section 9.6).

## Target paths
* `backend/apps/events/permissions.py`
* `backend/apps/events/views.py`, `backend/apps/events/fanout.py`,
  `backend/apps/events/resume.py` (apply the checks at each delivery point)
* `backend/tests/events/test_event_authorization.py`
* WP changelog entry

## Acceptance criteria
- [ ] A connection is accepted only for callers matching the Section 12.2 "Read
  events" row (Owner: yes; Device: yes; agents: never) — Section 9.6.
- [ ] Every delivery path (live fan-out, resume replay, history pages) drops events
  outside the connection's scope — per-event authorization (Section 9.6).
- [ ] A cross-project event is never sent to a connection scoped to another project
  (Section 12.1 mitigation demonstrated by test).
- [ ] The checks reuse WP-1.2's permission model — no second, divergent authorization
  implementation.
- [ ] Lint, type check and tests green (Section 20.4 item 2); error codes used exist
  in the catalog (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/events/test_event_authorization.py -v` — Section 12.2 matrix
cases for connect-time denial plus per-event drop tests on live, replay and history
paths.

## Attachments
* [Section 9.6 — Per connection and per event authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (cross-project leakage)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Filtering must happen before serialization to the socket, not after partial send —
  a check applied only in the fan-out module would leave replay (MT-1.10-03) and
  history open; review all three delivery points together.
* Owner scope ("Owner sees all") assumes owner-owned devices inherit owner visibility;
  the plan does not spell out multi-user/device scoping — if account settings expose
  shared devices later, raise a new OQ (next free `OQ-15+` id).
