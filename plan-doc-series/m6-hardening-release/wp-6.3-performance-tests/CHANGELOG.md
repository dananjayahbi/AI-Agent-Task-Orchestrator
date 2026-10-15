# WP-6.3 — Performance and load tests: changelog

Entries follow Section 20.4 item 7 (numbers recorded with the change).
Each entry cites its MT, the exact command, and the measured result —
misses are listed as misses, never papered over.

## Unreleased

**MT-6.3-01 — Write load scenario scripts (20 agents, 10k tasks, SSE fan-out) (done).**
New stdlib suite in `e2e/perf/`: `agent_simulation.py`, `sse_fanout.py`,
`board_load.py`, `push_dispatch_probe.py`, `seed_perf_fixture.py`,
`release_held_leases.py`, shared `perf_common.py`, plan-derived
`thresholds.json` (Section 5.2/13.4 constants, never edited), stack
lifecycle `stack.py` + `compose.perf.yaml` (push env passthrough —
shared `infra/compose/compose.yaml` untouched) — plus run instructions
in `docs/plan/perf-runbook.md` (one command per scenario) and
`.gitignore` entry for `e2e/perf/.run/` (seed tokens/stack secrets,
never staged). Evidence: `python e2e/perf/seed_perf_fixture.py` →
`seed=6301 projects=10 tasks=10000 sessions=20 tokens=20
dependencies=1500` with all six states (pending 7,060 / completed 1,000 /
to_be_audited 900 / in_human_review 600 / draft 400 / in_progress 40);
each scenario emits results JSON with p50/p95/p99 and a threshold
verdict (e.g. `agent_simulation` run: claims_ok=60, checkpoints_ok=140,
submits_ok=40, 0 http errors; SSE fan-out: 11 connections, 100
deliveries, 0 missing). Fan-out clock extends MT-1.10-06's
publish-point method with send/response bounds (NFR-03 judged on the
conservative upper bound); push probe records the backend→sender leg
only and cross-references MT-5.10-05/WP-5.4 for the device leg.
`python e2e/perf/stack.py up` builds `orchestrator-backend:wp63perf`
from `git archive HEAD` (d703319) — measured code is the committed
tree, prod settings, Section 16.1 topology, healthchecks green.

**MT-6.3-02 — Capture performance results against the latency targets (done).**
`docs/plan/performance-report.md` (environment/seed/versions/run
counts/variance/verdicts/miss classification/50 GB design-envelope
note). Each scenario run 3× (`--run-id 1..3`) on the wp63perf stack:
`python e2e/perf/<scenario>.py --run-id N` (+ `release_held_leases.py`
between runs for equal start state). Measured (p95, 3-run range):
claim **1949.75–1995.53 ms** vs 300 → **MISS**; checkpoint
**1544.38–1613.84 ms** vs 300 → **MISS** (spread ≤4.5 % — stable);
SSE publish→receipt upper bound **1186.83–1303.28 ms** vs 2000, 0
missing → **PASS**; push backend→sender **141.51–197.61 ms** vs 10000
(10/10 triggers, zero devices, FCM never contacted) → **PASS (leg
only)**; board API total **2711.43–2887.22 ms** vs derived 3000 →
PASS (derived, not an NFR; browser half = MT-4.11-04); NFR-09 run shape
10 projects / 20 sessions / 10,000 tasks exercised. Miss M-1
classified **serving-layer configuration (worker concurrency)** —
diagnostics: app middleware 2–3 ms/req, raw ASGI 0.5 ms CPU/req, served
≈37 ms CPU/req, 20-way health p50 ≈600–723 ms, raw DB 0.43 ms,
py-spy leaf frames in the uvicorn↔Django ASGI thread-bridge handoff —
not indexes/pooling/queries; machine shared with other sessions'
containers (recorded).

**MT-6.3-03 — Apply tuning changes (bounded fix applied; NFR-02 claim escalated) (done).**
Change (config only, no app/settings/migration): `infra/compose/compose.yaml`
backend service `command:` adds `--workers
${ORCHESTRATOR_BACKEND_WORKERS:-1}` — **default 1 = unchanged behavior for
every non-perf deployment**; `e2e/perf/stack.py` steps the disposable perf
stack's value 4 → 8 (comment cites WP-6.3 + `performance-report.md` §7,
where the full record lives). Commands: stack recreate, then
`python e2e/perf/release_held_leases.py && python e2e/perf/agent_simulation.py
--run-id N` ×3 per variant. Measured (p95, ms):
**1 worker** runs 1–3 claim 1995.53 / 1949.75 / 1989.88, checkpoint
1576.27 / 1613.84 / 1544.38 → **4 workers** runs 4–6 claim 523.81 /
517.79 / 502.03, checkpoint 421.37 / 428.98 / 492.29 → **8 workers** runs
7–9 claim 449.70 / 445.37 / 512.83, checkpoint 227.22 (PASS) / 323.67 /
525.91; parallel health probe p50 723 → 195, p95 1466 → 272 (1 → 4w).
Effect: ≈77 % claim / ≈71 % checkpoint p95 reduction — M-1 classification
confirmed. **Verdict: claim still MISS (≈1.5× budget) → ESCALATED** per
MT-6.3-03's risk note (capacity/hosting decision; remaining in-vocab
levers closed — no DB pool env knob in `settings/base.py`, py-spy excludes
view/DB, plateau inside shared-host noise); checkpoint on the boundary
(1/3 PASS). Thresholds never edited; owner: backend/platform.
Gates (standing): `cd backend; uv run pytest tests/ -q
--ignore=tests/integration` → **1670 passed, 4 skipped, 0 failed** in
2096 s (batch-10 baseline 1597 all green; +73 = concurrent batch-11
working-tree tests visible to git status, none failing);
`uv run --directory backend ruff check .` → All checks passed;
`ruff format --check .` → 389 files already formatted;
`mypy .` → Success: no issues found in 423 source files.
