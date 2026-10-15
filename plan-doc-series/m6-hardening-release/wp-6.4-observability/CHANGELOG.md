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

**MT-6.4-02 — Define alert rules (done).**

The six Section 17 Alerts-row rules exist as a distinct module
(`backend/apps/core/alerts.py`) with a rules catalog in
`docs/plan/alerts.md`: sweeper not running (heartbeat missing or older
than 3× the 60 s cadence — RISK-12), backlog of unprocessed attachments
(oldest non-terminal upload past the retry envelope or depth over a
configurable default), push failures (success-rate floor over a minimum
dispatch volume — honest "ok, no data" below the floor, per MT-6.4-01's
null-until-dispatcher contract), tunnel down, repeated auth failures
(fixed-window count per hashed source — Section 12.4), and disk usage on
the media volume. Each rule's threshold is a settings value with its
plan anchor in a comment, and the catalog lists every default flagged
for owner confirmation. Evaluation is **pull-based** (`evaluate_alerts()`
on scrape — no scheduler, no queue), states are `ok`/`firing`/`unknown`
(the tunnel rule never fires before its first honest report: host-side
`cloudflared tunnel ready` probes via the new
`manage.py report_tunnel_status` command; edge-side Cloudflare alerting
stays out of scope per the MT), ok→firing transitions log a WARNING with
numbers-only payloads, and the read path writes no events and never
touches task state. Tunnel dependency reading verified: MT-5.1-04's
through-tunnel run half is permanently operator-pending (OQ-11), but
this rule needs only the landed metrics plus the host-side reporter —
not the run. Surfacing decision recorded in the catalog: ops dashboard
(MT-6.4-03) + WARNING log; no external paging at M1. Files:
`backend/apps/core/alerts.py` (new),
`backend/apps/core/management/commands/report_tunnel_status.py` (new),
`docs/plan/alerts.md` (new), `backend/tests/test_alerts.py` (new, 16
tests — one forcing test per alert through real seams: aged heartbeat
stamp, backdated attachment rows, real `record_push_outcome` mixes, tunnel
report up/down/stale/unknown, a login burst through the real endpoint,
injected disk usage — plus catalog contract, no-secrets payload,
log-on-transition, settings override and METRICS_ENABLED independence).
Seams: `apps/core/metrics.py` gained `heartbeat_age_seconds()` /
`push_counts()` readers; `apps/core/settings/base.py` gained the
`ALERT_*` threshold group; `apps/accounts/views/auth.py` records failed
logins. Test evidence: `uv run pytest tests/test_alerts.py -q` →
**16 passed**.

**MT-6.4-03 — Build the operations dashboard view (done).**

The operations view exists as its own Section 13 surface (the MT's
web-app option): route `web/app/(app)/ops`, component
`web/components/ops/ops-overview.tsx`, data via a new owner-scoped
`GET /api/v1/ops/overview` (`backend/apps/core/ops.py`). The endpoint
*embeds* MT-6.4-01's `collect()` and MT-6.4-02's `evaluate_alerts()`
plus the Health row (live + ready-check pings) — the view never computes
its own numbers; the snapshot and `/metrics` cannot disagree. It renders
all nine metrics with their plan names/units (`docs/plan/metrics.md`),
all six alert states with severity/firing/since, worker/beat/sweeper
heartbeats, and health — owner-only per Section 12.2 (agents and devices
get `ROLE_NOT_PERMITTED`, anonymous `AUTH_REQUIRED` — the Dashboard-row
guard), read-only (acknowledgement/threshold tuning/runbooks out of
scope per Section 17), loading/empty/error states with catalog copy, and
a displayed "as of" freshness line so a frozen view is recognizable (the
MT's risk note). Update-mode decision recorded: **polling at 30 s**
(not SSE) — the scrape is pull-based by design, the events stream is
project-scoped while this view is cross-project
(`web/lib/queries/ops.ts` records the rationale). The web client calls
the endpoint only through the regenerated generated SDK (NFR-11 import
boundary). New endpoint is a documented plan gap in
`tests/auth/test_section_9_2_authorization.py` GAPS with a PROOF pointer
(Section 17 Dashboards row folds under the Section 9.2 Dashboard row; the
gap entry retires when the plan prints it). Files:
`backend/apps/core/ops.py` (new), `backend/tests/test_ops_overview.py`
(new, 6 tests: owner-only matrix, snapshot shape, collector-embed proof
via a spy, forced-firing sweep surfacing, read-path purity, no-pagination);
`web/components/ops/ops-overview.tsx`, `web/lib/queries/ops.ts`,
`web/app/(app)/ops/page.tsx`, `web/tests/ops/ops-overview.test.tsx`
(new, 6 tests: nine metrics with plan names/units, six resting alerts +
health/heartbeats, forced-firing fixture with severity tones, freshness
line, loading state, error-state catalog copy); one-line additions in
`backend/config/urls.py`, `web/lib/queries/keys.ts` and
`web/components/layout/app-nav.tsx` (nav link). Test evidence:
`uv run pytest tests/test_ops_overview.py tests/auth/test_section_9_2_authorization.py -q`
→ **12 passed**; `npx vitest run tests/ops/` → **6 passed**;
schemas/openapi.yaml + web generated client regenerated in lockstep.
