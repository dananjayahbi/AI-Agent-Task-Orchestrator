# MT-2.4-07 — Write core-tool tests incl. concurrent claim outcomes

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.4-07 |
| Title | Write core-tool tests incl. concurrent claim outcomes |
| Parent WP | WP-2.4 — Tools: availability, details, claim, release, context (Milestone M2) |
| Requirements | FR-MCP-03, FR-LEA-01; NFR-01 (concurrency, via Section 18 test layer) |
| Priority | M |
| Dependencies | MT-2.4-01..06 (all five core tools implemented), WP-1.6 (claim service on real Postgres), WP-2.3 (client) |
| Parent sections | 9.3, 18 (Concurrency and Integration rows), 19 (WP-2.4), 20.4, 20.5 |

## Context
WP-2.4's acceptance criterion is behavioral: two concurrent bridges calling
`claim_task` on one task produce one success and one `TASK_ALREADY_CLAIMED`. Section
18's concurrency layer specifies the fuller picture — 50 parallel claim attempts on
one task, claim vs lease-sweeper races — against real Postgres with multiple
connections (NFR-01), and Section 9.3 defines the skip-locked algorithm being
verified. This final slice of WP-2.4 writes the tool-level test suite: per-tool
behavior tests plus the concurrency acceptance tests, closing the loop between the
bridge handlers and the backend claim service.

## Inputs / Prerequisites
* MT-2.4-01..06 — the five implemented tools.
* Parent plan Section 9.3 — claim algorithm; Section 18 — concurrency/integration
  test requirements.
* WP-1.6 — lease and claim service backed by real Postgres.
* WP-0.3 — CI pipeline that will run the suite.
* Parent plan Section 19 WP-2.4 acceptance — the two-bridge claim scenario.

## Scope (in)
* A tool-level test suite covering each of the five tools' happy paths, validation
  failures, and error-mapping behavior (complementing, not duplicating, the
  per-slice unit tests: this task owns the cross-tool scenarios).
* The WP-2.4 acceptance scenario: two independent bridge instances (separate sessions
  and tokens) call `claim_task` on the same task concurrently; exactly one succeeds,
  the other receives `TASK_ALREADY_CLAIMED` with hint and next action.
* An extended concurrency scenario per Section 18: 50 parallel claim attempts on one
  task yield exactly one winner and 49 structured failures, with no partial lease
  state left behind.
* Role-matrix scenarios: coder claims `pending`, auditor claims `to_be_audited`,
  cross-role attempts rejected (`ROLE_NOT_PERMITTED` / `AUDITOR_SAME_AS_CODER`).
* End-to-end tool chain smoke: orient (`get_project_context`) → list
  (`get_available_tasks`) → details → claim → release, against the integration
  environment.
* CI wiring so the suite runs with the bridge/integration test jobs
  (Section 20.4 item 2).

## Out of scope
* Backend-only races (claim vs lease sweeper) — WP-1.6/Section 18 owned at the
  backend layer; this task covers tool-call concurrency.
* MCP conformance across real agent clients — WP-2.11.
* Policy Engine, submission and audit tools — WP-2.6, M3 WPs.
* Performance benchmarks (20 simulated agents) — Section 18 performance layer.

## Target paths
* `bridge/tests/` (core-tool test suite, concurrency tests)
* CI pipeline config (suite invocation)
* WP changelog entry

## Acceptance criteria
- [ ] Two concurrent `claim_task` calls from separate bridge sessions on one task
  produce exactly one success and one `TASK_ALREADY_CLAIMED` (WP-2.4 acceptance,
  FR-LEA-01).
- [ ] 50 parallel claim attempts yield exactly one winner; failures are structured
  `TASK_ALREADY_CLAIMED`/`CONCURRENCY_LIMIT_REACHED` errors with hint and next
  action (Section 18 concurrency row, Section 9.2 catalog).
- [ ] Role-matrix scenarios pass: coder/auditor positive paths and cross-role
  rejections (Section 12.2).
- [ ] The orient→list→details→claim→release chain passes against the integration
  environment.
- [ ] Suite runs green in CI with lint and type checks (Section 20.4 item 2); uses
  only catalog codes (item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the core-tool suite against the integration environment, e.g.
`uv run pytest bridge/tests/ -k core_tools`; the concurrency tests require the real
Postgres-backed backend per Section 18.

## Attachments
* [Section 9.3 — Claim algorithm](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Concurrency tests against a shared database are flaky by nature — the Section 18
  design (real Postgres, skip-locked) is the mitigation; do not "fix" flakiness by
  weakening assertions to allow two winners.
* If WP-1.6 is incomplete, the two-bridge test cannot be honest; mark it dependent
  rather than mocking the backend's lock (the mock would prove nothing).
