# MT-6.4-01 — Implement Metrics Endpoints for the Section 17 Metric List

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.4-01 |
| Title | Implement metrics endpoints for the Section 17 metric list |
| Parent WP | WP-6.4 — Metrics, alerts and dashboards (Milestone M6) |
| Requirements | NFR-10 |
| Priority | M |
| Dependencies | M1 core engine complete (WP-1.1 health endpoints, WP-1.6/1.7 leases and sweeper, WP-1.10 SSE, WP-1.12 attachments per Section 19 WP-6.4 dependency) |
| Parent sections | 5.2 (NFR-10), 9.3 (claim), 9.9 (background jobs), 9.10 (config), 16.1 (services), 17 (Metrics, Health rows), 19 (WP-6.4), 20.4, 20.5 |

## Context
Section 19 (WP-6.4): goal "Section 17 implemented", deliverables "metrics endpoints,
alert rules, operations view", acceptance "each listed alert can be triggered in a
test", requirements NFR-10 ("Structured logs with correlation ids, health endpoints,
basic metrics"). Section 17 fixes the exact metric list: claims per minute, claim
conflicts, active leases, lease expirations, task cycle time per state, attachment
pipeline duration and failures, SSE connections, push success rate, API latency. This
first slice exposes those metrics so MT-6.4-02's alert rules and MT-6.4-03's
dashboard have something to read — the measurement layer everything else in the WP
consumes.

## Inputs / Prerequisites
* Parent plan Section 17 — the nine-item metric list verbatim (the contract for this
  task; no metric invented, none dropped) plus the Health row (live/ready endpoints,
  worker and beat heartbeat checks) already established by WP-1.1 and Section 9.2.
* Parent plan Sections 9.3/9.9 — claim algorithm (claim conflicts originate in the
  row-lock claim), sweeper/expiry jobs (lease expirations), attachment pipeline,
  push dispatch: the events each metric counts.
* Parent plan Section 16.1 — service topology (backend, worker, beat) that metrics
  must aggregate across; worker/beat heartbeat checks from the Health row.
* Parent plan Section 9.10 — configuration groups; metrics exposure settings belong
  in the environment-driven config, not literals.
* Section 12.2/12.4 — metrics must not leak tokens or attachment text; Section 15.2 —
  Health routes are internal-only, and metrics must not be exposed through the tunnel
  either (see risk notes).
* Existing OpenAPI/contract discipline (NFR-11, Section 20.4 item 4) — if the metrics
  endpoint enters the API document, the schema diff applies.

## Scope (in)
* Implement a metrics endpoint on the backend exposing every Section 17 Metrics-row
  item, sourced from real system state (counters/gauges maintained where the events
  happen — claim path, sweeper, pipeline, SSE gateway, push dispatch, request
  timing — not synthetic or sample data).
* Define each metric's semantics precisely alongside the implementation: unit,
  reset/window behavior (e.g. "claims per minute" is a rate over what window), labels
  (per state for task cycle time), so MT-6.4-02's alerts and MT-6.4-03's dashboard
  read unambiguous numbers (Section 20.4 item 1).
* Cover the worker/beat side of the Health row where it does not already exist:
  worker and beat heartbeat visibility so "sweeper not running" (an MT-6.4-02 alert)
  can be derived (Section 17 Health row; Section 9.9).
* Keep metrics free of secrets and content: names and numbers only — no tokens, no
  attachment text, no task payloads (Section 12.4; MT-6.1-04's scrubbing discipline).
* Expose endpoint via configuration (bind/route per Section 9.10), keeping it off the
  public surface: LAN/internal like the Health routes, not on the tunnel hostname
  (Section 15.2 route table).
* Tests asserting each listed metric moves in response to the action it measures
  (Section 18 Integration row) and a changelog note (Section 20.4 item 7).

## Out of scope
* Alert rules and thresholds over these metrics — MT-6.4-02.
* The operations dashboard view — MT-6.4-03.
* Structured logging with correlation ids — already established by WP-1.x (NFR-10's
  logging half; this task is the metrics half).
* Push-success measurement beyond what the backend can observe — push success rate is
  counted from dispatch/delivery outcomes the backend already records; end-to-end
  device-leg verification is WP-5.4/WP-5.10's domain.
* External monitoring-stack integration (Prometheus/Grafana scraping conventions) —
  the plan asks for metrics endpoints, not a specific consumer; expose a standard
  scrapeable/text or JSON representation and record the format choice (see risk notes).

## Target paths
* `backend/` — metrics endpoint, per-source metric instrumentation, tests
* `docs/plan/` — metric definitions (name, meaning, window, labels) tied to Section 17
* `infra/compose/` — only if exposure config requires a documented setting
* WP changelog entry

## Acceptance criteria
- [ ] The endpoint exposes all nine Section 17 metrics — claims per minute, claim
  conflicts, active leases, lease expirations, task cycle time per state, attachment
  pipeline duration and failures, SSE connections, push success rate, API latency —
  and no invented headline metrics are presented as plan metrics (Section 20.5
  traceability).
- [ ] Each metric has documented semantics (unit, window/reset, labels) in
  `docs/plan/` (Section 20.4 item 1; inputs for MT-6.4-02/03).
- [ ] Tests demonstrate each metric changes when its underlying action occurs (claim
  → claims per minute/claim conflicts; sweeper expiry → lease expirations; upload →
  attachment pipeline duration/failures; SSE connect → SSE connections) — Section 19
  WP-6.4 deliverable "metrics endpoints" made verifiable.
- [ ] Worker and beat heartbeat checks from the Section 17 Health row are observable
  (existing or added), enabling the sweeper alert of MT-6.4-02.
- [ ] No token, secret or attachment text appears in metric names, labels or output
  (Section 12.4); endpoint is internal/LAN-only, off the tunnel route table (Section
  15.2).
- [ ] Tests green in CI (Section 20.4 item 2); public contract updated if the endpoint
  joined the API document, schema diff reviewed (item 4); changelog note added
  (item 7).

## Test command
Exercise the local stack (make claims, force a lease expiry, upload an attachment,
open an SSE connection) and fetch the metrics endpoint to confirm the corresponding
values move; then run `pytest backend/tests/ -k metrics -v` for the metric-behavior
tests, and grep the metrics output for known token/secret patterns (expected: zero
matches).

## Attachments
* [Section 17 — Observability and Operations (Metrics, Health rows)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-10 — Observability](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.4 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan names metrics but not their transport/format — a decision is needed
  (Prometheus text exposition vs JSON). Record it in `docs/plan/` and keep it a thin
  representation choice; do not pull in a monitoring stack the plan never scoped.
* Rates ("claims per minute") and cycle times need windowing choices the plan leaves
  open — pick explicit, documented windows and label gauges with their definition;
  ambiguous metrics make MT-6.4-02's alert thresholds meaningless.
* SSE connections and push success rate cross process boundaries (ASGI server, worker)
  — aggregate honestly across backend and worker (Section 16.1 topology); a metric
  that only sees one process will lie under concurrency.
* Exposing metrics publicly would add an unauthenticated data source to the internet —
  keep it beside the internal Health routes (Section 15.2 "Health — Internal only").
