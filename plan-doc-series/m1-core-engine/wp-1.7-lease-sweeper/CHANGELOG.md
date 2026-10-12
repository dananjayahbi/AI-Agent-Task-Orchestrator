# WP-1.7 — Lease sweeper and retry policy: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.7-01 (celery/beat compose wiring)** — the `worker`/`beat` services run
  real commands (`celery -A config.celery worker` / `beat`) from the backend
  image; the worker's health check is a worker-ping
  (`inspect ping -d celery@$HOSTNAME | grep -q pong` — a silent exit is
  unhealthy), beat keeps the Section 16.1 process check; no ports published.
  `backend/config/celery.py` is the app (broker/result backend from the
  already-documented `ORCHESTRATOR_CACHE_BROKER_URL` — **no new env names**,
  so configuration.md/.env.example needed no rows) with the two Section 9.9
  60-second beat entries (names fixed: `leases.sweep_expired_leases`,
  `leases.notify_lease_expiring`); settings add `CELERY_BROKER_URL`,
  `CELERY_RESULT_BACKEND`, `CELERY_TIMEZONE`/`CELERY_ENABLE_UTC` (UTC, P7) and
  a startup scheme check. Recorded reading: the broker scheme check accepts
  `redis://` (documented) and `rediss://` (same family over TLS), mirroring
  the DATABASE_URL `postgres`/`postgresql` precedent. Both compose renders
  (prod base, dev overlay) pass `docker compose config`; the Compose README
  documents worker/beat verification (logs, ping, beat schedule listing) and
  notes dev worker/beat run image code (no bind mount — rebuild to refresh).
  The "CI green (`docker compose config` in the pipeline)" acceptance is
  verified locally; no workflow step exists to host it and workflows are
  outside this WP's edit ownership — follow-up recorded in the report.
- **MT-1.7-02 (lease sweeper job)** — `apps/leases/sweeper.py`: expired
  `in_progress` rows selected under `FOR UPDATE SKIP LOCKED` in bounded
  batches (documented default 100, risk-note rule), T5 dispatched per row
  inside the batch transaction via the dispatcher's public API only, loop
  repeating until a round comes back empty (empty sweep = clean no-op); one
  correlation id per run scopes logs and events (WP-0.5-03); structured log
  line per task swept plus a run summary. Exactly-once under double sweepers
  comes from the row lock plus T5's `in_progress`-only guard (FR-LEA-05);
  the `seen` set guarantees termination even for a conflict-skipped row.
  Unit tests: reclaim side effects + event/history pair, unexpired and empty
  no-ops, sequential double sweep, batch remainder, post-sweep
  `LEASE_EXPIRED` for the old owner's extension/release (no resurrection,
  invariant 1).
- **MT-1.7-03 (retry-exhaustion escalation)** — the sweep cycle dispatches
  T9 (`retry_exhausted`) instead of T5 when `failure_retry_count` already
  meets the project policy's `max_retries`, so the task lands in
  `in_human_review` with `review_reason` `retry_exhausted`; the
  increment-causing sweep is the preceding T5 (recorded reading: T9's frozen
  Section 8.2 from-state is `in_progress`, so Flow B's "T5 then T9" cannot be
  one row's same-sweep pair — the MT's own test wording "the sweep following
  the increment" is what the registry allows; G-10's bounded loop holds:
  every expiry either consumes budget or escalates). Push trigger fires once
  per escalation with the Section 9.8 dedupe key (asserted); `max_retries`
  read from Project Policy per project, never hard-coded (Section 20.5); the
  sweeper never re-processes a task in `in_human_review`.
- **MT-1.7-04 (lease-expiring warning)** — `apps/leases/notifier.py` emits
  the catalog `task.lease_expiring` through the WP-1.9 write/publish path at
  80% of the current window (`lease_acquired_at` → `lease_expires_at`), still
  valid leases only (expired → the sweeper's T5 owns expiry; zero/negative
  windows fail closed — policy validation is WP-1.3's). Exactly-once-per-
  window rule (documented, risk-note OQ trigger considered): dedupe key is
  `(task, lease_generation, lease_expires_at)` kept in the append-only Event
  log under the row lock — repeated 60-second runs never duplicate within one
  window; a checkpoint extension (MT-1.6-03) redefines the expiry, i.e. a
  new window, so the warning re-arms at 80% of the new window; a new claim
  (generation bump) is likewise a new window. Payload `data` carries
  `task_id`, `lease_generation`, `lease_expires_at` (envelope unchanged).
- **MT-1.7-05 (sweeper chaos test)** —
  `tests/integration/test_sweeper_chaos_postgres.py` (PG-gated twin of the
  unit suites, `--ds apps.core.settings.dev`, `transaction=True`,
  MT-1.6-08's barrier harness): dead-worker reclaim asserted as *scheduling
  contract* (both beat entries at 60 s) + triggered run; two concurrent
  sweepers over the same expired set → one T5 + one event per task, no
  duplicated increments; exhaustion loop lands `in_human_review` /
  `retry_exhausted` and the sweeper stops touching it (a zombie claim
  refuses with `TASK_STATE_CONFLICT`); claim-vs-sweeper race has one
  coherent outcome (new owner wins after reclaim, or both back off and the
  next beat pass reclaims — the deferred-row case `SKIP LOCKED` allows);
  checkpoint-vs-expiry race: the late extension always answers
  `LEASE_EXPIRED` (catalog code) and never resurrects the lease. Section 8.3
  invariants 1/2 and history↔events one-to-one asserted after every
  scenario; three consecutive runs deterministic (Section 20.4 item 2).
