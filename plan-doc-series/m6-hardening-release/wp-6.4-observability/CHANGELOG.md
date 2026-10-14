# WP-6.4 — Metrics, alerts and dashboards: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

**MT-6.4-01 — Implement metrics endpoints for the Section 17 metric list (done).**

The measurement layer M6's alerts (MT-6.4-02) and dashboard (MT-6.4-03)
read: `GET /metrics` on the backend exposes **all nine** Section 17
Metrics-row items — claims per minute, claim conflicts, active leases,
lease expirations, task cycle time per state, attachment pipeline duration
and failures, SSE connections, push success rate, API latency — sourced
from real state, nothing invented as a headline plan metric. Format
decision recorded per the risk note: **JSON, not Prometheus text**
(`docs/plan/metrics.md` — M1 consumer is an internal/LAN scrape, no new
runtime dependency, thin representation a Prometheus exporter can layer on
later). The route is a plain Django view, so it stays out of the OpenAPI
document (no schema-diff gate), gated by `METRICS_ENABLED`
(`ORCHESTRATOR_METRICS_ENABLED`, Section 9.10 group, default on; off →
404) and lives at the root beside Health — off the tunnel allowlist,
internal/LAN-only (Section 15.2). Counters are written where the events
happen — claim path (`leases.claim.claim_task`: successful claims as a
fixed one-minute UTC window; lost races as cumulative conflicts), lease
sweeper (`lease_expirations` plus worker/beat/sweeper heartbeat stamps so
MT-6.4-02's "sweeper not running" alert is derivable), attachment
pipeline (`run_pipeline` times each terminal run; per-outcome counts),
request-timing middleware (overall + per-resolver-route averages, labels
are route patterns — never task ids), SSE hub gauge — while `active_leases`
and `task_cycle_time_per_state` (7-day window over `TaskTransition`)
are DB gauges computed at scrape. `record_push_outcome` is the documented
push-dispatch seam for WP-5.4 (reads 0 dispatched / `null` rate until a
real dispatcher lands — honest, not a lie). Semantics for every metric
(unit, window/reset, labels, known M1 limitations) are tabulated in
`docs/plan/metrics.md` as MT-6.4-02/03's inputs. No secret can appear in
the output: names and numbers only (Section 12.4) — asserted by a payload
grep test. Files: `backend/apps/core/metrics.py` (new),
`backend/tests/test_metrics.py` (new), `docs/plan/metrics.md` (new);
seams in `apps/leases/claim.py`, `apps/leases/sweeper.py`,
`apps/attachments/pipeline.py`, `apps/core/middleware.py`,
`apps/core/settings/base.py`, `config/urls.py`. Test evidence:
`uv run pytest tests/test_metrics.py -q` → **10 passed** (each metric
moves on its real action: claim → claims-per-minute, lost race →
conflicts, sweeper pass → expirations + heartbeats, real upload +
`run_pipeline` → pipeline duration/outcome, hub connect → SSE gauge,
`/metrics` endpoint JSON + 404-when-disabled + no-secrets grep);
`uv run ruff check` / `ruff format --check` / `mypy` clean for these
files. Full backend suite (2026-10-14): `uv run pytest tests/ -q
--ignore=tests/integration` → **1498 passed, 4 skipped, 0 failed**;
`uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy .`
all clean across `backend/`.

### Deferred

**MT-6.4-02 — Define alert rules (deferred).** The six Section 17 alerts
(sweeper, backlog, push, tunnel, auth, disk). Blocker: MT-6.4-01 left only
the measurement layer the rules must read — the nine metrics, the
worker/beat/sweeper heartbeats and
their semantics in `docs/plan/metrics.md` (including the "sweeper not
running" heartbeat input) — and explicitly scoped the rules themselves out
("alert rules and thresholds over these metrics — MT-6.4-02"). The rules
catalog, evaluation/triggering logic and the per-alert forcing tests do not
exist yet: no alert-rules document in `docs/plan/`, no alert suite under
`backend/tests/`, so none of the six Section 17 alerts can be triggered in
a test (Section 19 WP-6.4 acceptance unmet).

**MT-6.4-03 — Build the operations dashboard view (deferred).** Blocker:
depends on MT-6.4-02's six rules and firing state, which are not written
(above); from MT-6.4-01 only `GET /metrics` and `docs/plan/metrics.md`
exist to read, and the web Overview hosts no operations section yet — the
view, its placement decision and its component tests are not started.
