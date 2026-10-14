# Metrics endpoint — format and semantics (Section 17; NFR-10; WP-6.4)

Owner MT: **MT-6.4-01**. This records the format decision and the semantics of
every metric the `/metrics` endpoint exposes, per the MT's "JSON vs Prometheus
text: make a choice, record it in docs/plan/" instruction.

## Format choice: JSON

`GET /metrics` returns a single JSON document (`Content-Type: application/json`),
not Prometheus text exposition.

Why JSON for M1:

- **The M1 consumer is an internal/LAN scrape and human debugging.** Section 17
  frames NFR-10 as "the metrics are there when you need them", not "a metrics
  stack is a hard dependency". JSON is directly readable with `curl` and trivially
  parseable from a health script or a CI step.
- **No new runtime dependency.** Prometheus text format implies either
  hand-rolling the encoder or adding `prometheus_client`. The scaffold adds
  neither; counters live in Django's cache API (Redis in prod, LocMem in the
  unit layer — `apps.core.settings.test`).
- **The route stays out of the OpenAPI document.** It is a plain Django view, not
  a DRF `APIView`, so drf-spectacular does not document it and no schema-diff
  gate applies (there is currently no schema-diff guard configured in the repo;
  this is belt-and-suspenders).

A Prometheus-compatible exporter can be layered on later by reading the same
`collect()` document; the nine metric *names and semantics* below are the stable
contract, the encoding is not.

## Endpoint posture

- Path: `GET /metrics` (root, like the Health endpoints — not under `/api/v1`,
  therefore not on the tunnel allowlist: internal/LAN-only by default).
- Gated by `METRICS_ENABLED` (`ORCHESTRATOR_METRICS_ENABLED`, default `True`;
  Section 9.10 group). When off, the route answers 404.
- Every label is a metric name, a URL-resolver route pattern, a state name, or an
  HTTP method/status. **Never** a token, task id, session id, or attachment
  content (Section 17 no-secrets rule).

## The nine metrics

| Metric | Type | Source | Semantics |
| --- | --- | --- | --- |
| `claims_per_minute` | gauge (rate) | cache counter | Successful claims (`leases.claim.claim_task`) recorded in the current fixed one-minute window (UTC minute bucket, 120 s TTL). Resets each minute — a fixed window, not a sliding one. |
| `claim_conflicts` | counter | cache counter | Cumulative lost claim races: `TASK_ALREADY_CLAIMED` + `CONCURRENCY_LIMIT_REACHED`. Permission/validation refusals are not conflicts. |
| `active_leases` | gauge | DB at scrape | Tasks in `in_progress` or `to_be_audited` whose `lease_expires_at` is in the future. |
| `lease_expirations` | counter | cache counter | Cumulative leases the sweeper touched (`reclaimed + escalated + audit_released`) across all runs. |
| `task_cycle_time_per_state` | gauge (map) | DB at scrape | Average seconds spent in each *departed* state, from `TaskTransition` history over the last 7 days. Each transition closes the dwell in its `from_state` that opened at the prior transition of the same task; a task's first transition has no opener and is skipped. |
| `attachment_pipeline` | counter + avg | cache counters | `count_by_outcome` for `ready/skipped/failed/gone`; `duration_ms_avg` over all terminal runs. Transient failures that retry are not counted until they land terminal. |
| `sse_connections` | gauge | hub at scrape | `events.fanout.hub.connection_count` in the process serving the scrape. Process-local: under multiple ASGI workers this reflects one worker only (documented limitation). |
| `push_success_rate` | ratio | cache counters | `succeeded / dispatched` for backend-observed push dispatch outcomes. Stays `null` (0 dispatched) until WP-5.4's dispatcher calls `record_push_outcome`; the device leg is WP-5.4/WP-5.10's domain. |
| `api_latency` | counter + avg + per-route map | cache counters | Overall `count`/`duration_ms_avg`, plus a `by_route` map keyed `"METHOD route status"` (route = resolver pattern). |

Plus a non-metric `heartbeats` block: `worker`, `beat`, `sweeper` each with
`last_seen` (ISO) and `age_seconds`. The lease sweeper stamps all three when it
runs — a firing sweep proves the beat scheduled it *and* a worker executed it
(MT-6.4-02's "sweeper not running" alert reads these).

## Known limitations (M1)

- The per-route `api_latency` breakdown is a read-modify-write on one cache key;
  fine for single-process/unit usage, a hot multi-worker deployment would want a
  sharded counter. The overall `api:count`/`api:duration_ms_sum` stay atomic.
- `sse_connections` is process-local (see above).
- `task_cycle_time_per_state` recomputes over a 7-day window at each scrape; fine
  at M1 scale, would want a materialised view if the transition table grows large.
