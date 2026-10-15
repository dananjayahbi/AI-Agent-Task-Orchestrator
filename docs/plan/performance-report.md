# Performance report — WP-6.3 (NFR-02 / NFR-03 / NFR-09)

| Field | Value |
|---|---|
| Deliverable | WP-6.3 "results" (Section 19) — MT-6.3-02 capture + MT-6.3-03 verdict |
| Scenarios | MT-6.3-01 (`e2e/perf/`), runbook: `docs/plan/perf-runbook.md` |
| Date | 2026-10-15 |
| Seed | `6301` (documented; deterministic fixture) |
| Run count | 3 runs per scenario (`--run-id 1..3`), same seed, same stack |
| Thresholds | `e2e/perf/thresholds.json` — plan constants (Section 5.2 / 13.4), never edited |

## 1. Environment and method

* **Host**: Windows 11 (build 26120), 16 logical CPUs, Docker Desktop VM;
  Python 3.14.0 for the host-side scenario scripts.
* **Stack** (Section 16.1 production topology, compose project `wp63perf`):
  postgres:16-alpine, redis:7.4-alpine, `migrate` (one-shot, exit 0),
  backend (uvicorn, **prod settings module**, no bind mounts), worker
  (celery), beat, web (stub) — healthchecks green; `GET /health/ready`
  → 200 `{database: ok, cache: ok}`.
* **Measured code**: image `orchestrator-backend:wp63perf` built from
  `git archive HEAD backend` at **d703319 (batch 10)** — committed tree
  only; in-flight working-tree edits from concurrent agents never entered
  the build. API at `http://127.0.0.1:8063/api/v1`.
* **Machine sharing (MT-6.3-02 risk note)**: the host also ran other
  sessions' containers during the runs — `wp112-e2e`
  (postgres/redis/worker), `wp52route` (backend/postgres/redis),
  `wp16-pg`, `wp16-redis` — plus host services on ports 8000/3000
  (observed host CPU ≈68% during diagnostics). Numbers are
  local-host numbers, no cross-machine claims (MT-1.10-06 discipline).
* **Clocks**: host-side `time.perf_counter()` around each full request
  (send → response parsed). Percentiles: MT-1.10-06's linear-interpolation
  method (`e2e/perf/perf_common.percentile`).
* **Hygiene**: between scenario runs, simulation-held leases were released
  through the real owner release endpoint (`e2e/perf/release_held_leases.py`)
  so every run starts with identical concurrency headroom — a fixture-state
  reset, not a product change. Rate limits: production defaults
  (agent 120/min/token; observed 0 rate-limit hits in recorded runs).

## 2. Seed — NFR-09 shape evidence (MT-6.3-01 acceptance)

`python e2e/perf/seed_perf_fixture.py` →
`seed=6301 projects=10 tasks=10000 sessions=20 tokens=20 dependencies=1500`

| state | count | | state | count |
|---|---:|---|---|---:|
| pending | 7,060 | | completed | 1,000 |
| to_be_audited | 900 | | in_human_review | 600 |
| draft | 400 | | in_progress | 40 |

Shape: **10 projects / 10,000 tasks / 20 concurrent sessions** — NFR-09's
envelope exercised as the run shape itself. Attachment volume: see §6.

## 3. Scenario results (3 runs each)

### 3.1 Agent simulation — NFR-02 clocks (20 agents, 150 s, checkpoints every 30 s)

| run | claim p50 | claim p95 | claim p99 | ckpt p50 | ckpt p95 | ckpt p99 | claims n | ckpts n | submits | 409s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1253.41 | **1995.53** | 2051.25 | 551.68 | **1576.27** | 1860.72 | 60 | 140 | 40 | 17 |
| 2 | 1358.37 | **1949.75** | 2417.50 | 604.11 | **1613.84** | 1690.31 | 60 | 140 | 40 | 19 |
| 3 | 1326.39 | **1989.88** | 2305.60 | 720.19 | **1544.38** | 1920.51 | 60 | 140 | 40 | 21 |

p95 spread across runs: claim 45.78 ms (2.3 %), checkpoint 69.46 ms (4.5 %)
— stable signal, not noise. Informational (not NFR-scored): orient p95
4794.70–5813.78 ms (work-list over 7,060 pending tasks), submit p95
1418.27–1893.02 ms. 0 HTTP errors, 0 rate-limit hits every run.
**Verdict: FAIL — claim p95 ≈1978 ms vs 300 ms; checkpoint p95 ≈1578 ms
vs 300 ms (NFR-02).** Misses classified in §5.

### 3.2 SSE fan-out — NFR-03 publish→receipt (11 connections, 120 s load)

| run | upper p50 | upper p95 | upper p99 | deliveries | missing | fan-out |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 431.62 | **1303.28** | 1373.55 | 100 | 0 | 2.0× |
| 2 | 397.83 | **1218.93** | 1560.37 | 100 | 0 | 2.0× |
| 3 | 571.63 | **1186.83** | 1381.63 | 100 | 0 | 2.0× |

*Connection set*: 1 global + 10 per-project (web-shaped filters);
per-connection events 160 (global) / 16 (each project); 0 stream faults;
0 missing deliveries; 100 checkpoint responses timed per run.
*Method (stated precisely)*: publish runs post-commit inside the
checkpoint request, so the publish instant lies in `[t_send, t_resp]`;
the table's **upper** bound (receipt − send) is a conservative superset —
if its p95 < 2 s, true publish→receipt p95 < 2 s. The lower bound
(receipt − response) was **0.0 ms at p50/p95** in all runs (receipts
regularly landed before the HTTP response finished parsing) — consistent
with an in-request publish. `occurred_at` (second precision) was recorded
but never used for timing. **Verdict: PASS — p95 ≤1303.28 ms vs 2000 ms,
zero missing deliveries.**

### 3.3 Board load — API side of the 500-card board (5 pages × 100 cards, 10 iterations)

| run | page p50 | page p95 | total p50 | total p95 | total p99 | cards |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 499.42 | 674.74 | 2578.80 | **2887.22** | 2965.51 | 500 |
| 2 | 490.22 | 650.37 | 2541.93 | **2711.43** | 2714.21 | 500 |
| 3 | 488.31 | 641.00 | 2508.89 | **2796.12** | 2844.02 | 500 |

**Verdict: PASS vs the derived 3000 ms API-share ceiling — a necessary
condition for Section 13.4's 3 s web first-load, NOT an NFR** (labeled
`board_api_total_p95_derived` in the results files). Browser half:
MT-4.11-04 / `docs/plan/web-performance-report.md` (reused by
cross-reference, not duplicated).

### 3.4 Push dispatch — NFR-03 10 s budget, backend→sender leg

| run | p50 | p95 | max | n |
|---|---:|---:|---:|---:|
| 1 | 119.74 | **197.61** | 214.84 | 10 |
| 2 | 122.34 | **141.51** | 145.27 | 10 |
| 3 | 115.89 | **160.34** | 170.21 | 10 |

*Method (labelled per MT-6.3-01/02 risk notes)*: host wall clock at the
escalating resolution POST → `dispatch_push` Celery line in the worker
log (`docker compose logs worker --timestamps`; on-commit enqueue happens
inside the request, so the span is an upper bound of backend→sender
dispatch). Clock used: `completed_ms` (the task's `succeeded in` line;
job execution itself ≈28–38 ms in worker logs, result
`{'accepted': 0, …, 'suppressed': 0}`).
**Not claimed**: device delivery — the stack has **zero registered
devices**, the FCM transport is never built, Google is never contacted.
The device leg stays with **MT-5.10-05 / WP-5.4**.
**Verdict: PASS — p95 ≤197.61 ms vs 10000 ms (backend→sender leg only).**

## 4. Verdicts per NFR

| NFR | Target | Measured | Verdict |
|---|---|---|---|
| NFR-02 claim | p95 < 300 ms | baseline p95 1949.75–1995.53 ms; after serving tuning (1→8 workers, §7) p95 445.37–512.83 ms | **MISS — escalated (§7)** |
| NFR-02 checkpoint | p95 < 300 ms | baseline p95 1544.38–1613.84 ms; after tuning 227.22–525.91 ms (1/3 runs PASS) | **MISS — escalated (§7)** |
| NFR-03 event delivery | p95 < 2 s | upper-bound p95 1186.83–1303.28 ms, 0 missing | **PASS** |
| NFR-03 push dispatch | < 10 s | backend→sender p95 141.51–197.61 ms (0 devices) | **PASS** (leg only; device leg = MT-5.10-05) |
| NFR-09 shape | 10 projects / 20 sessions / 10,000 tasks | run shape (§2) | **PASS** |
| NFR-09 attachments | 50 GB | design-envelope documentation (§6) | **documented, not seeded** |
| Board (derived) | < 3 s API share | total p95 2711.43–2887.22 ms | PASS (derived, narrow margin) |

## 5. Miss list and classification (input to MT-6.3-03)

| # | Miss | Suspected class | Evidence |
|---|---|---|---|
| M-1 | claim/checkpoint p95 ≈1.6–2.0 s (NFR-02) | **config / serving layer (worker concurrency)** — not index, not pooling, not a specific query | see below |

Evidence collected on the same stack (diagnostic probes, same image):

| probe | result |
|---|---|
| app middleware `duration_ms` (structured log, per request) | **2–3 ms** |
| in-process Django test client, health, sequential | **8.5 ms/req** |
| raw ASGI app (no Django) through the same uvicorn | **0.8 ms wall / 0.5 ms CPU per req** |
| Django health via HTTP, sequential | 43–44 ms wall, **≈37 ms CPU** per req |
| Django health via HTTP, 20 concurrent | p50 ≈600–723 ms |
| raw DB `SELECT 1` ×50 | 21.7 ms total (0.43 ms each) |
| py-spy on the live serving process | time concentrated in asyncio self-pipe wakeups (`_read_from_self`), threading `notify`/`__enter__`, executor `submit`, contextvars restore, transport `write` — the **uvicorn↔Django ASGI sync-bridge handoff**, not view/DB code |

Conclusion: the per-request cost lives between ASGI entry and the Django
sync view (thread-bridge handoff + single-process serving), multiplied
into queueing at 20-way concurrency; the application and the database are
an order of magnitude below the budget. Classification: **serving-layer
configuration (worker concurrency)**. The work-list query (orient p95 ≈5 s
over 7,060 pending rows) is a *secondary*, informational observation —
orient is outside NFR-02's named clocks, recorded for the tuning list.
Environment factor recorded per the risk note: shared host (§1).

## 6. NFR-09's 50 GB attachment half — design-envelope verification

Not seeded (the plan's honest path; a partial number would be invented
evidence). Verification by documented envelope behavior:

* **Size caps before any byte is stored** — `apps/attachments/validation.py`
  (MT-1.11-02): 25 MB per file, 10 files per task, 100 MB per task total —
  plan defaults, env-overridable via the Section 9.10 `ATTACHMENT_` group.
  With 10,000 tasks the caps bound what any single task can ever add; the
  50 GB line is the fleet-level envelope the storage layer must absorb
  without architectural change (NFR-09).
* **Storage abstraction** (Section 16.3): `STORAGE_BACKEND` local/S3
  switch — bytes live behind the abstraction, so volume scales with the
  backend choice, not the application.
* **Lazy + streamed access** (FR-ATT-03, Section 9.2/9.5): list endpoints
  return descriptors only; content is a separate streaming endpoint;
  pages cap at `MAX_PAGE_SIZE` 100 (`docs/plan/conventions/pagination.md`,
  RISK-13). RISK-13's mitigations (size caps, lazy loading, pagination,
  streaming — parent plan row RISK-13) are all landed and unit-tested;
  **no large-volume runtime was executed**, and none is claimed.

## 7. MT-6.3-03 — tuning record

**Change applied (bounded, documented).** Backend serving-process count for
the perf stack: `infra/compose/compose.yaml`'s backend service gained a
`command:` block with `--workers ${ORCHESTRATOR_BACKEND_WORKERS:-1}` —
default **1 = unchanged image behavior** for every non-perf deployment
(comment cites WP-6.3 and this file). `e2e/perf/stack.py` sets the perf
value in the disposable stack's env (4, then 8). **No application code,
settings, or migration changed** (migration gate: the backend suite —
including the `tests/ -k "lease or claim or events"` subset MT-6.3-03
prescribes — runs green; see the WP changelog's gate evidence below).

**Measured series** (`e2e/perf/agent_simulation.py` ×3 per variant, same
seed fixture and clock method; every number from
`e2e/perf/results/*.json`):

| variant | runs | claim p95 (3 runs, ms) | checkpoint p95 (3 runs, ms) | vs 300 ms budget |
|---|---|---|---|---|
| baseline image CMD (1 worker) | 1–3 | 1995.53 / 1949.75 / 1989.88 | 1576.27 / 1613.84 / 1544.38 | MISS (≈6.6×) |
| `--workers 4` | 4–6 | 523.81 / 517.79 / 502.03 | 421.37 / 428.98 / 492.29 | MISS (≈1.7×) |
| `--workers 8` | 7–9 | 449.70 / 445.37 / 512.83 | 227.22 / 323.67 / 525.91 | claim MISS (≈1.5×); checkpoint 1/3 PASS |

Parallel health probe (20 concurrent, same host): p50 723 → 195 ms, p95
1466 → 272 ms (1 → 4 workers). **Effect:** ≈77 % lower claim p95
(3-run mean of p95s: 1978 → ≈469 ms) and ≈71 % lower checkpoint — the
M-1 classification (serving layer, §5) is confirmed by the response, but
**NFR-02 claim (300 ms) is still not met on this host**; checkpoint sits
on the boundary.

**Stop rule (why tuning ends here).** The series plateaus inside host
noise (run9: 512.83/525.91 on a shared machine, §1 risk); the remaining
in-vocabulary levers were checked and are closed: no DB pool /
`CONN_MAX_AGE` env knob exists in `apps/core/settings/base.py`, py-spy
excluded view/DB hotspots (§5), and more workers oversubscribe the shared
host. Further capacity is an ops decision, not a config default.

**Final verdict (MT-6.3-03): bounded tuning applied and measured —
NFR-02 claim remains MISS → ESCALATED** per MT-6.3-03's own risk note
(capacity/hosting decision for a production deployment; accepting the
remaining false-positive exposure needs stakeholder sign-off).
Thresholds were never edited. Owner: backend/platform.
Refs: miss M-1 (§5), series above, WP changelog entry MT-6.3-03.

## 8. Reproducing

Every number above comes from `e2e/perf/results/*.json` (machine-readable,
one file per run, with percentiles and threshold verdicts). Commands:
`docs/plan/perf-runbook.md` — stack up → seed → each scenario ×3 →
`stack.py down -v`.
