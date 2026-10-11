# MT-1.1-01 — Create the Django ASGI Project with Settings Split by Environment

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.1-01 |
| Title | Create the Django ASGI project with settings split by environment |
| Parent WP | WP-1.1 — Django project skeleton (Milestone M1) |
| Requirements | NFR-10, NFR-06; ADR-005, OQ-02 |
| Priority | M |
| Dependencies | MT-0.1-02 (Python tooling), MT-0.2-01, MT-0.2-03 (Compose and env template), MT-0.5-01 (env naming conventions) |
| Parent sections | 6.6, 9.1, 9.10, 16.2, 19.1 (WP-1.1), 20.4, 20.5 |

## Context
WP-1.1's first slice is the project itself: an ASGI Django service whose settings are
split by environment, following the Section 9.1 module layout and the Section 9.10
environment-driven configuration groups. ADR-005 (accepted in WP-0.4) fixes DRF with
OpenAPI generation as the API layer, so the project is created DRF-ready even though
endpoints arrive in later micro-tasks. Everything downstream in M1 (accounts, projects,
tasks) lands inside this skeleton.

## Inputs / Prerequisites
* Parent plan Section 9.1 — the nine Django app modules (`accounts`, `projects`,
  `tasks`, `leases`, `attachments`, `audit`, `merge`, `events`, `notifications`,
  `agents`, `core`) and the dependency rule that `tasks` owns state changes.
* Parent plan Section 9.10 — configuration groups, documented defaults, startup
  validation that fails fast on missing required values.
* Parent plan Section 16.2 — startup validation refuses to boot with weak or missing
  secrets in `prod`; one documented environment template (MT-0.2-03).
* Parent plan Section 6.6 — Django 5.x on Python 3.12+, ASGI via Uvicorn/Daphne.
* ADR-005 / OQ-02 — DRF with schema generation confirmed as the API layer.
* MT-0.5-01 — environment variable naming and grouping conventions the settings must
  follow.
* MT-0.1-02 — documented Python formatter/linter/type-checker commands for `backend/`.

## Scope (in)
* Create the Django project under `backend/` per the Appendix A repository layout,
  runnable as ASGI (Uvicorn/Daphne).
* Register the app packages from the Section 9.1 module layout as thin stubs so later
  WPs only fill them in; `core` holds settings-level wiring (error envelope,
  pagination, idempotency, rate limiting, health — added by their own micro-tasks).
* Split settings by environment (dev/prod behavior) driven by environment variables per
  Section 9.10, using the MT-0.5-01 naming conventions, with documented defaults and
  fail-fast startup validation per Sections 9.10 and 16.2.
* Add a smoke test proving the project boots and settings resolve for each environment.
* Add a short note to the WP changelog (Section 20.4 item 7).

## Out of scope
* Structured logging and correlation-id propagation — MT-1.1-02.
* Health endpoints — MT-1.1-03.
* OpenAPI generation and CI validation — MT-1.1-04.
* Dockerfile and Compose wiring — MT-1.1-05.
* Any models, migrations or endpoints — WP-1.2 onwards.
* Celery worker/beat configuration — background-job WPs (ADR-003).

## Target paths
* `backend/` — Django project package, `apps/core/`, app stubs per Section 9.1
* `backend/tests/` — settings/boot smoke tests
* `infra/compose/` environment template (additions for backend settings, per MT-0.2-03)
* WP changelog entry

## Acceptance criteria
- [ ] The backend boots as ASGI under the documented run command (Section 6.6).
- [ ] Settings are split by environment, read from environment variables per Section
  9.10 with the MT-0.5-01 naming conventions, and carry documented defaults.
- [ ] Startup validation fails fast on missing/weak required values in `prod`
  (Section 16.2); dev configuration starts without secrets committed to the repo.
- [ ] The app layout matches Section 9.1, including the `core` module.
- [ ] Smoke tests pass; lint and type check green (Section 20.4 item 2).
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests` for the boot/settings smoke tests, `python manage.py check`
for project validation, and the documented backend lint/type-check commands from
MT-0.1-02.

## Attachments
* [Section 9.1 — Module layout (Django apps)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.1](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The exact settings-file split (one module per environment vs. env overrides on a base
  module) is not fixed by the plan — pick one, document it in `CONTRIBUTING.md`, and
  record it in the changelog; do not introduce a second mechanism.
* Settings structure choices affect every later WP; if anything in Section 9.10 cannot
  be expressed cleanly, raise it rather than reshaping config groups (they are shared
  with bridge and clients via MT-0.5-01).
