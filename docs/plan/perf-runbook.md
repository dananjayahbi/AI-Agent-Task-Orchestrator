# WP-6.3 performance suite — runbook (MT-6.3-01)

Scenario scripts live in `e2e/perf/` (stdlib-only Python; host commands
below). Every scenario writes one machine-readable JSON file into
`e2e/perf/results/` with p50/p95/p99 percentiles **and** a pass/fail line
against `e2e/perf/thresholds.json` — the plan-derived NFR constants
(Section 5.2; never edited to make a run pass, MT-6.3-03).

## 0. Stack (once per measurement session)

```text
python e2e/perf/stack.py up
```

* builds `orchestrator-backend:wp63perf` from `git archive HEAD backend`
  — the committed tree only, so working-tree edits from concurrent agents
  never enter the measured image;
* starts the Section 16.1 production topology under compose project
  `wp63perf` (postgres, redis, migrate, backend, worker, beat, web —
  base render, **prod settings module**, migrations applied by the
  one-shot `migrate` service) on free host ports
  `127.0.0.1:8063` (API) and `127.0.0.1:3063` (web);
* generates strong Section 16.2-valid secrets into
  `e2e/perf/.run/stack-secrets.json` (gitignored — the shared
  `infra/compose/.env` ships placeholders prod settings refuse);
* enables push wiring with wellformed fixture FCM credentials
  (zero registered devices => the FCM transport is never built — see
  `e2e/perf/compose.perf.yaml`).

## 1. Seed (once; serves every run)

```text
python e2e/perf/seed_perf_fixture.py
```

Expected summary line: `seed=6301 projects=10 tasks=10000 sessions=20
tokens=20 ...` plus `tasks_by_state` covering all six canonical states —
that is MT-6.3-01's "seed report shows 10 projects / 10,000 tasks / 20
sessions" evidence. The manifest (owner + per-agent tokens) is written to
`e2e/perf/.run/manifest.json` — gitignored, live run credentials.

One seed serves all runs (MT-6.3-01 risk note: generate once, don't
reseed per run — seed cost stays out of every measurement). Reseed only
after `stack.py down -v`.

## 2. Scenarios — one documented command each

Run each scenario three times with `--run-id 1..3` (the run count the
report records):

```text
python e2e/perf/agent_simulation.py --run-id 1     # NFR-02 claim/checkpoint clocks
python e2e/perf/sse_fanout.py --run-id 1           # NFR-03 publish->receipt fan-out
python e2e/perf/board_load.py --run-id 1           # 500-card board API path
python e2e/perf/push_dispatch_probe.py --run-id 1  # NFR-03 10 s push half (backend->sender leg)
```

* **agent_simulation** — 20 agents, 150 s, checkpoints every 30 s
  (Section 18 wording), API-level Section 11.1 coder flow (not MCP
  bridges — MT-6.3-01 risk note), against the seeded 10,000 tasks.
* **sse_fanout** — 11 owner SSE connections (1 global + 10 per-project,
  web-shaped filters) receiving the agent simulation's events; 120 s
  load + 10 s trailing grace; NFR-03 judged on the conservative
  publish->receipt upper bound (method in the results file).
* **board_load** — 10 iterations x 5 cursor pages x 100 cards = 500-card
  pages; browser half owned by MT-4.11-04
  (`docs/plan/web-performance-report.md`).
* **push_dispatch_probe** — 10 escalation triggers; clocks host wall time
  against the worker's `dispatch_push` log lines; zero devices, so the
  device leg stays with MT-5.10-05 / WP-5.4 (labeled, never claimed).

Exit codes: `0` = scenario executed (a FAIL verdict is *data* — recorded
in the results file and report, not hidden); `2` = scenario could not
run (stack down, seed missing, port conflict).

## 3. Teardown / cleanup

```text
python e2e/perf/stack.py down -v
```

`-v` wipes the stack volumes (database, events, media) and removes the
exported build context; without `-v` the seeded database stays for more
runs. `e2e/perf/.run/` (secrets + manifest) is gitignored — delete it
when the session is done.

## Measurement notes

* Client clocks: `time.perf_counter()` around each full request
  (send -> response parse). Percentiles use MT-1.10-06's
  linear-interpolation method for comparability with WP-1.10.
* Rate limiting: agent endpoints throttle at 120/min per token
  (`apps/core/settings/base.py` default); the simulation issues ~6
  calls/min/agent — no override, production defaults measured.
* Host: shared with other local sessions' containers — recorded in every
  results file (`environment.host`, `environment.cpus`) and stated in
  `docs/plan/performance-report.md` (MT-6.3-02 risk note).
