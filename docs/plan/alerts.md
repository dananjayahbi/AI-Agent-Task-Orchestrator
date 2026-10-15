# Alert rules — the six Section 17 alerts (MT-6.4-02)

Owner MT: **MT-6.4-02**. This is the rules catalog the MT's scope asks for:
for each of the plan's Section 17 **Alerts** row entries — none renamed,
added or dropped — the concrete rule (signal source, threshold, severity),
its rationale (plan anchor or flagged default), and the chosen surfacing
channel. Implementation: `backend/apps/core/alerts.py`
(`evaluate_alerts` at read time — see "Global semantics" below); forcing tests:
`backend/tests/test_alerts.py` (`pytest backend/tests/ -k alert -v`).

Signals come from what MT-6.4-01 landed (the nine metrics, heartbeats, the
push counters) plus cheap DB/cache reads — the alert layer computes nothing
the metrics endpoint does not already source. Every threshold is an
`ORCHESTRATOR_ALERT_*` setting (Section 9.10 group, `settings/base.py`),
adjustable by configuration without code change (the MT's risk note:
thresholds start from job cadences and documented rationale; tuning from
production traffic is post-v1).

## Global semantics

* **Evaluation is pull-based.** `evaluate_alerts()` runs when alert state is
  read — today the owner-only `GET /api/v1/ops/overview` (MT-6.4-03) and the
  tests. There is no scheduled emitter and no external paging (email,
  PagerDuty — out of scope per the MT); the recorded decision: the
  plan's alert/event channels are the **ops dashboard** plus a structured
  WARNING log line on each ok→firing transition. The Section 9.9 stalled
  detector keeps owning `system.alert` Event rows; alert evaluation never
  writes Events (a read path must not mutate the audit trail).
* **States:** `ok`, `firing`, or `unknown` (the signal has never been
  reported — `unknown` does not fire; pretending a state we cannot observe
  would violate Section 20.4 item 1).
* **`since`:** first evaluation timestamp that observed the alert firing
  (tracked in cache; resets on a cache restart — documented). Rules whose
  signal carries its own onset (heartbeat age, oldest backlog item, tunnel
  report time) use that instead.
* **No secrets** (Section 12.4): payloads carry metric names, counts, ages
  and thresholds only. Auth-failure sources are hashed before touching a
  cache key; raw IPs, tokens, task ids and attachment content never appear.
* **Forcing discipline** (Section 18): every rule has a test that forces its
  condition through the real signal path (stopped heartbeat, stuck
  attachment rows, failed pushes, dropped tunnel status, auth burst, disk
  pressure via an injected usage function) and asserts the alert fires —
  WP-6.4 acceptance "each listed alert can be triggered in a test".

## The six rules

### 1. Sweeper not running — RISK-12's mitigation

| Field | Value |
| --- | --- |
| Signal | `heartbeats.sweeper.age_seconds` (MT-6.4-01 heartbeat stamp, written by every lease sweep) |
| Threshold | `ALERT_SWEEPER_MAX_HEARTBEAT_SECONDS` = 180 s (3× the Section 9.9 60 s cadence — one-missed-beat margin), **plan anchor** |
| Severity | critical (RISK-12: lease/sweeper bugs reclaiming or never reclaiming work) |
| Firing | heartbeat missing (never swept in this counter store) or older than the threshold |
| Runbook | none yet (Section 17 lists no sweeper-down runbook; WP-6.5 may add one) |

**RISK-12 traceability (MT acceptance):** this alert is the "clear metrics
and alerts" half of RISK-12's mitigation. The fencing/race tests cover the
"reclaims active work" half; this rule covers the "never reclaims dead
work" half — if the sweeper stops, `lease_expirations` flatlines *and this
alert fires within three minutes*, so the risk cannot materialize quietly.

### 2. Backlog of unprocessed attachments

| Field | Value |
| --- | --- |
| Signal | DB at evaluation: count of non-terminal (`uploaded`/`processing`, not deleted) attachment rows and the oldest row's age |
| Threshold | age > `ALERT_ATTACHMENT_BACKLOG_MAX_AGE_SECONDS` = 900 s **or** depth > `ALERT_ATTACHMENT_BACKLOG_MAX_DEPTH` = 25 |
| Anchor | Age: the documented retry envelope (`ATTACHMENT_RETRY_BACKOFF_SECONDS` = 60 s, exponential over `ATTACHMENT_RETRY_MAX_ATTEMPTS` = 3 → minutes) — 15 min is the outer bound past which a row is a backlog, not a retry. Depth 25 is a **configurable default flagged for owner confirmation**. |
| Severity | warning |
| Firing | either bound exceeded |
| Runbook | none |

### 3. Push failures

| Field | Value |
| --- | --- |
| Signal | `push_success_rate` counters (dispatched/succeeded) behind MT-6.4-01's `record_push_outcome` seam |
| Threshold | success rate < `ALERT_PUSH_MIN_SUCCESS_RATE_PERCENT` = 90 % **with** ≥ `ALERT_PUSH_MIN_DISPATCHES` = 10 dispatches in the window |
| Anchor | NFR-03's 10 s dispatch window is the related contract; the rate floor and sample size are **configurable defaults flagged for owner confirmation** (no plan number exists; a floor on tiny samples would flap) |
| Severity | warning |
| Firing | floor breached past the sample minimum |
| Runbook | none |

Zero dispatches reads `ok` with a `null` rate: WP-5.4's dispatcher has not
landed yet, and an alert that fires on absent data would train the operator
to ignore alerts (the MT's alert-fatigue risk note).

### 4. Tunnel down

| Field | Value |
| --- | --- |
| Signal | last host-side status reported via `record_tunnel_status` — the `report_tunnel_status` management command runs Section 16.1's exact Compose healthcheck (`cloudflared tunnel ready`) and stamps the result; monitoring hosts may force `--up`/`--down` |
| Threshold | reported down, or last report older than `ALERT_TUNNEL_MAX_STALE_SECONDS` = 300 s (3× the 30 s Compose probe cadence — a silent reporter cannot confirm the tunnel) |
| Severity | warning — **Section 15.4's documented failure mode, not a page**: if the tunnel is down, LAN access and all agents continue; mobile shows unreachable and push still works via FCM outbound |
| Firing | last report down, or stale |
| Runbook | **tunnel down** (Section 17 runbooks row; WP-6.5 writes it) |

**Documented limitation (MT risk note):** the tunnel is outbound-only by
design (Section 15.1), so host-side detection can only be as good as the
reporter. Until a first report exists the alert reads `unknown` — not
firing, not claiming the tunnel is up. Edge-side Cloudflare alerting is out
of the stack's scope (MT out-of-scope).

### 5. Repeated auth failures

| Field | Value |
| --- | --- |
| Signal | per-identity/IP failure counts over a fixed window — the owner-login failure path calls `record_auth_failure` (source hashed before it reaches a cache key; payload carries counts only, never who) |
| Threshold | ≥ `ALERT_AUTH_FAILURES_MAX_PER_WINDOW` = 10 failures from one source within `ALERT_AUTH_FAILURE_WINDOW_SECONDS` = 300 s — **configurable defaults flagged for owner confirmation** (Section 15.3 layer 4 requires the anomaly alert; it names no number) |
| Severity | warning |
| Firing | any source crosses the floor inside the window |
| Runbook | none |

Section 15.3 (layer 4: "anomaly alerts on repeated auth failures") is the
anchor. Instrumented surface today: `POST /auth/login`. Token/device
authentication failures ride the API rate limits (MT-1.2-06/MT-5.2-03)
instead; extending the counter to those paths is a recorded follow-up, not
a silent gap.

### 6. Disk usage on media volume

| Field | Value |
| --- | --- |
| Signal | `shutil.disk_usage(MEDIA_ROOT)` measured at evaluation (Section 16.1 media volume, Section 16.3 storage) |
| Threshold | used ≥ `ALERT_DISK_USAGE_MAX_PERCENT` = 90 % — **configurable default flagged for owner confirmation** (plan names no number) |
| Severity | critical (a full media volume stops uploads and the pipeline) |
| Firing | threshold crossed; unreachable media root reads `unknown` (cannot measure, will not pretend) |
| Runbook | none |

**Documented limitation:** the backup destination's second-location disk
(Section 16.5) is not visible from this process; the daily backup job
(WP-6.2) owns that disk's hygiene. Retention cleanup (Section 9.9) is the
relief valve when this fires.

## Threshold review

Per the MT's alert-fatigue note, the owner should revisit after first use:
the push floor/sample, auth window/floor, backlog depth and disk percent
(all flagged above). The two plan-anchored values (sweeper 180 s, tunnel
300 s) track job cadences and change only if the cadences change.
