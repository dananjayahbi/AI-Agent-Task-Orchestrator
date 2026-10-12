# WP-1.10 Realtime gateway (SSE): changelog

Short note per completed micro-task (Section 20.4, item 7).

## Unreleased

- **MT-1.10-01** — Authenticated SSE stream endpoint with filters + the
  history endpoint (Sections 9.6, 9.2, 12.2; FR-WEB-05, NFR-03). New
  `backend/apps/events/` surface: `GET /events/stream` streams Section
  9.6 envelopes as SSE (`id:` = the monotonic event id, `data:` = the
  envelope JSON) with `Content-Type: text/event-stream`,
  `Cache-Control: no-cache` and `X-Accel-Buffering: no`; `GET /events`
  serves the same rows as history. **Decisions recorded:**
  * *Filter names* (risk note): both endpoints take the Section 9.6
    names `project`/`task`, validated against the Section 7.3 id
    patterns — malformed input answers the canonical
    `VALIDATION_ERROR` envelope before any stream opens.
  * *History order*: `id` **ascending** (chronological) — the Event
    model's monotonic id is the replay total order (MT-1.9-01), so
    history pages read forward through the same order the stream uses;
    pagination is the canonical `cursor`/`page_size` contract
    (pagination.md; default 25, clamped to 100).
  * *Response mechanics*: the stream body is an **async** generator —
    Django's ASGI handler consumes async iterators incrementally,
    while a sync iterator would be materialized through
    `sync_to_async(list)` (whole-body buffering, exactly the failure
    the no-buffering headers prevent). The early-flush test asserts
    the structural half (async iterator; status line + headers arrive
    with the body untouched); the over-the-wire first-byte proof lands
    with MT-1.10-04's heartbeat reads.
  * *Authentication* (do-not-invent rule): the stream uses exactly the
    transports the plan defines for every endpoint — the Owner's
    session cookie (a same-origin `EventSource`/fetch stream carries
    it — MT-4.3-04's wording) or `Authorization: Bearer` (device
    token; the Section 15.4 token transport also covers an owner
    session token for fetch-based clients). No query-parameter token
    scheme exists in the plan, so none was added; agents are rejected
    with `ROLE_NOT_PERMITTED`, anonymous with `AUTH_REQUIRED`.
  * OpenAPI annotations (`extend_schema`) ship with the views; the
    `schemas/openapi.yaml` regeneration is the designated agent's
    **gate follow-up** (endpoint additions listed below).
- **MT-1.10-02** — Redis fan-out to connected subscribers (Sections
  9.6, 9.10; ADR-002). `events/fanout.py`: one process-wide `Hub` —
  a **single** Redis subscription (one subscriber task on the first
  stream's event loop; asserted through a factory-counting fake) fanned
  out to N `StreamConnection`s in application code. Each connection
  holds its connect-time filters and an in-flight queue; `claim()`
  de-duplicates by monotonic id at **send** time (the MT-1.10-03
  foundation); the ordered-set window is bounded (4096 ids). Ordering
  discipline per MT-1.9-03's risk note: dispatch never sorts by
  arrival — out-of-order ids are delivered exactly once each, in
  arrival order (injection test). A failed connection is dropped from
  dispatch without disturbing the others; subscriber outages are
  logged and retried (5 s) — Redis pub/sub stays fire-and-forget, with
  the Event table (DB resume) as the recovery story, and no
  unbounded buffering added. The connection registers in the view
  (before response start) so nothing published in the first step can
  slip past; unregistering runs in the generator's cleanup — repeated
  open/close leaks nothing. Test seam mirrors `publisher._client`:
  `fanout._async_redis` (returns `None` ⇒ subscriber disabled, the
  Section 18 unit-layer default via the events suite's autouse
  fixture).
- **MT-1.10-03** — Lossless resume via Last-Event-Id (Sections 9.6,
  9.2; Section 19 WP-1.10 acceptance). `events/resume.py` reads the
  client's last id from the SSE-standard `Last-Event-ID` header **and**
  the `last_event_id` query parameter (MT-4.3-04's risk note resolved:
  browsers cannot set arbitrary headers on `EventSource`, so both
  spellings are accepted; the choice is recorded here); blank = fresh
  connection, non-integer = canonical `VALIDATION_ERROR` before any
  stream opens. Fresh connections start **live without backfill** (the
  plan does not mandate initial backfill — documented reading; `GET
  /events` covers browsing). The gap-free handover: the connection
  registers **before** the replay query runs, so a concurrently
  published event is either in the replay set or in the live queue, and
  the shared `claim()` gate delivers each id exactly once whichever
  copy arrives second — the race test injects overlapping publishes
  during the handover and asserts exactly-once, in id order, then
  live. Replay assumes retained history (OQ-10): a last id predating
  retention replays from the oldest retained row; no retention-specific
  behavior was invented (MT risk note's OQ guidance tracked, nothing
  free to raise as of this writing).
- **MT-1.10-04** — 15-second heartbeat comments (Sections 9.6, 15.4;
  RISK-05). While the queue is silent for
  `ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS` (default **15** — the plan's
  value; configuration.md row added, flagged for owner confirmation),
  the stream yields `: heartbeat` — an SSE **comment**: no event id, no
  data, no Event-table row, no movement of any resume position
  (tests pin all four). The wait is intrinsic to the connection's
  generator, so a disconnect cancels it — no timer/task survives close
  (task-set leak test). Tests override the interval to 50 ms (the MT's
  flakiness risk note) while the committed default stays 15 s.
  Tunnel-side idle-timeout verification remains WP-5.1's.
- **MT-1.10-05** — Per-connection and per-event authorization
  (Sections 9.6, 12.1, 12.2; FR-SEC-03). Connect time reuses WP-1.2's
  `CanReadEvents` (the Section 12.2 "Read events" row — no second
  permission model); `events/permissions.py` adds `StreamScope`, read
  from the authenticated token at connect time (never from client
  input — ADR-004), and one `allows()` predicate applied at **every**
  delivery point: live fan-out (`StreamConnection.accepts`), replay
  (`missed_envelopes` re-checks after SQL narrowing), history
  (queryset narrowed identically) — the risk note's "replay/history
  left open" failure mode is answered structurally. Scope reading:
  only agent tokens are project-bound (Section 7.2) and agents can
  never pass the row, so today's scope is owner-wide for Owner and
  Device; a directly-built **scoped device token row** pins the
  narrowing seam (replay, live and history all confine to the token's
  project with no client filters). Cross-project leakage (Section
  12.1) is demonstrated dropped on every path, never partially sent.
  Authorization-matrix updates (sole-editor file): the *Read events*
  row now runs on the **real** `/api/v1/events` **and**
  `/api/v1/events/stream` routes (probe retired), the revoked-device
  case asserts against the real history route, and the two
  `/api/v1/events*` entries left `DEFERRED_ENDPOINTS` — the drift
  guard stays honest. Device-token revocation on a *live* stream stays
  WP-5.3's acceptance (reconnect-reject); not implemented here.
- **MT-1.10-06** — SSE delivery/load test, p95 under 2 s locally
  (Section 19 WP-1.10 acceptance; NFR-03).
  `backend/tests/perf/test_sse_delivery_load.py` opens nine concurrent
  connections with mixed `project`/`task` filters, publishes thirty
  committed events over ~0.6 s and times every delivery from its
  **publish point** (the MT risk note's clock: publish, not commit) to
  client receipt; one victim connection drops mid-run, resumes with its
  last id, and catches up within the same budget. Deterministic counts,
  thresholds documented in the file (Section 20.4 item 1); percentiles
  are printed as a JSON line so the run carries the numbers, not just
  the verdict. **Measured result** (local dev machine, real Redis via
  `wp16-redis`, mode `redis`): p50 2.4 ms, **p95 75.9 ms**, p99
  289.0 ms, max 335.8 ms, victim catch-up 3.9 ms — budget 2000 ms.
  Transport modes: the test prefers the real pipeline
  (`publisher.publish_event` → channel → subscriber → fan-out →
  receipt); with no reachable Redis it falls back to the in-process
  transport seam (`hub.broadcast`) and says so in the printed report —
  re-running against the full Compose topology (backend + Redis +
  database) is the recorded **gate follow-up**, per the MT's local
  environment wording.

## Gate follow-ups (for the wave gate)

* **OpenAPI regeneration** (designated agent): `schemas/openapi.yaml`
  must gain `GET /api/v1/events/stream` (200 `text/event-stream` +
  the three canonical error responses; `project`/`task` query params)
  and `GET /api/v1/events` (the `EventListEnvelope` → `EventEnvelope`
  components — exactly the Section 9.6 seven keys — plus
  `cursor`/`page_size`), with the schema diff reviewed (Section 20.4
  item 4). Views carry complete `extend_schema` annotations for this.
* **Compose re-run of the delivery load test** (MT-1.10-06 mode note)
  once the wave gate has the stack up; the unit layer already asserts
  the budget in both modes.

## Configuration rows added

* `ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS` (group `EVENTS_`, default
  `15`) — configuration.md row + `infra/compose/.env.example` entry,
  both flagged for owner confirmation per the conventions document.
