# MT-1.10-03 — Implement Lossless Resume via Last Event Id (No Gaps, No Duplicates)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.10-03 |
| Title | Implement lossless resume via last event id (no gaps, no duplicates) |
| Parent WP | WP-1.10 — Realtime gateway (SSE) (Milestone M1) |
| Requirements | FR-WEB-05, NFR-03 |
| Priority | M |
| Dependencies | MT-1.10-02 (fan-out in place), MT-1.10-01 (history endpoint) |
| Parent sections | 9.6, 9.2, 19.1 (WP-1.10), ADR-002, 20.4, 20.5 |

## Context
Section 9.6: "reconnecting clients send the last id and receive missed events, then
switch to live (no gaps, no duplicates)." Section 9.2: `GET /events/stream` supports
resume via last event id. Section 19 (WP-1.10) acceptance: "killing and reconnecting a
client with the last id yields no gaps or duplicates." The mobile client replays from
the last event id on resume (Section 14.2); the web stream hook handles last-event-id
resume (Section 13.3).

## Inputs / Prerequisites
* MT-1.10-02 — live fan-out with id-based skip/dedup discipline.
* MT-1.10-01 — `GET /events` history endpoint for reading missed rows.
* MT-1.9-01 — monotonic `id` as the total order for replay.
* Parent plan Section 9.6 — resume semantics ("missed events, then switch to live").
* SSE standard: reconnecting clients send their last received id as `Last-Event-ID`.

## Scope (in)
* On reconnect with a last id: read all Event rows with `id` greater than the client's
  last id (filtered by the connection's `project`/`task` filters), send them in `id`
  order, then switch the connection to live delivery.
* Gap-free handover: events published while replaying are buffered/deferred so they
  are delivered exactly once after replay — never skipped (gap) and never re-sent
  (duplicate).
* No-last-id behavior: a fresh connection starts live without replay (documented in
  the changelog note; the plan does not mandate initial backfill).
* Boundary tests: client killed mid-stream, reconnect with last id → missing events
  arrive in order exactly once; reconnect with the newest id → no replay at all.

## Out of scope
* The heartbeat — MT-1.10-04.
* Authorization filtering of replayed events — MT-1.10-05 (reuse the connection's
  filters here).
* Client-side resume implementations (web hook, mobile replay) — WP-4.x / WP-5.x;
  this task is the server side of the contract.
* Compaction/retention of the event history (OQ-10, M6) — replay assumes history is
  retained.

## Target paths
* `backend/apps/events/resume.py`
* `backend/apps/events/views.py` (resume handover in the stream)
* `backend/tests/events/test_resume.py`
* WP changelog entry

## Acceptance criteria
- [ ] Killing a client and reconnecting with its last id delivers every missed event
  exactly once, in `id` order, then live events — no gaps, no duplicates (Section 19
  WP-1.10 acceptance; Section 9.6).
- [ ] Resume respects the connection's `project`/`task` filters for both replay and
  the live handover.
- [ ] A race test (reconnect while events are being published concurrently) proves
  the handover loses nothing and duplicates nothing.
- [ ] Replaying and live phases both emit the Section 9.6 envelope unchanged
  (Section 20.5).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/events/test_resume.py -v` — includes the kill/reconnect no-gaps
no-duplicates test and the concurrent-publish race test required by Section 19
WP-1.10 acceptance.

## Attachments
* [Section 9.6 — Realtime gateway and event model (resume semantics)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (resume via last event id)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The handover from replay to live is the classic double-delivery/loss window; the
  race test above is the deliverable's proof — do not merge without it.
* A client whose last id predates event retention (OQ-10 default: events 1 year) will
  need a defined behavior (full replay vs. restart-live); the plan does not specify
  it — raise a new OQ (next free `OQ-15+` id) if retention becomes relevant before
  M6.
