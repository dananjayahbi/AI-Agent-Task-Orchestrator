# MT-0.3-02 — Add Unit and Integration Test Jobs

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.3-02 |
| Title | Add unit and integration test jobs |
| Parent WP | WP-0.3 — CI pipeline (Milestone M0) |
| Requirements | NFR-07, NFR-11 |
| Priority | M |
| Dependencies | MT-0.3-01 |
| Parent sections | 18, 19.1 (WP-0.3), 20.4 |

## Context
Section 18 requires unit and integration tests as blocking quality gates, with
integration coverage running against real Postgres and Redis (and the Compose stack for
end-to-end scenarios). This task wires the test jobs into the pipeline for the skeleton
stage: the runners, services, and commands exist and pass now, and real suites land
per-package as milestones progress (WP-1.15 race/idempotency suites, WP-2.x
conformance, WP-4.11 UI tests).

## Inputs / Prerequisites
* MT-0.3-01 — workflow exists with lint/type-check jobs to extend.
* MT-0.2-01..04 — the Compose stack that integration jobs can start against.
* Parent plan Section 18 — unit, concurrency, integration, contract test layers;
  "Integration: API with database and Redis".
* Test runners per package as established by WP-0.1 tooling (Python test runner for
  backend/bridge, JS test runner for web, `flutter test` for mobile).

## Scope (in)
* Add a unit-test CI job that runs each package's unit suite (skipping packages whose
  suite is still empty via a documented, explicit allow-empty invocation).
* Add an integration-test CI job that starts the required services (Postgres, Redis —
  via Compose or service containers) and runs the integration suite against them.
* Make both jobs required checks so a failing test blocks merge (WP-0.3 acceptance).
* Report test results visibly in the job log and enforce no-new-failures.
* Add a WP changelog note.

## Out of scope
* Writing the substantive suites: state-machine/lease/policy race suites — WP-1.15;
  MCP conformance — WP-2.11; end-to-end scenarios — later e2e WPs; performance — WP-6.3.
* Coverage thresholds (85% targets in Section 18 apply once the target modules exist).
* Triggering integration tests against the full Compose skeleton on every commit —
  reserved for e2e jobs (Section 18 end-to-end row).

## Target paths
* `.github/workflows/` — test jobs in the CI workflow (or a dedicated test workflow)
* Package test entry points as defined in WP-0.1 command documentation
* WP changelog entry

## Acceptance criteria
- [ ] A unit-test job exists and runs every package's unit suite; green on the skeleton.
- [ ] An integration-test job exists, provisions Postgres and Redis, and runs green.
- [ ] Both jobs are required checks — a PR with a failing test cannot merge
  (WP-0.3 acceptance).
- [ ] Test jobs reuse the WP-0.1 documented commands (single source of truth).
- [ ] No secrets committed; service credentials come from CI-provided environment
  (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Push a branch with a deliberately failing unit test and confirm the unit-test job fails
and the merge gate blocks; confirm the integration-test job starts Postgres and Redis,
runs the suite, and reports green on the clean branch (`gh run list` / workflow status).

## Attachments
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-0.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Skeleton suites are near-empty; avoid inventing placeholder tests that later mask
  real coverage gaps — jobs must simply run whatever the package's suite contains.
* Integration jobs need database credentials; use ephemeral CI-only values, never
  committed ones (Section 20.4 item 3, RISK-14).
