# MT-1.1-03 — Implement /health/live and /health/ready Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.1-03 |
| Title | Implement /health/live and /health/ready endpoints |
| Parent WP | WP-1.1 — Django project skeleton (Milestone M1) |
| Requirements | NFR-10, NFR-06 |
| Priority | S |
| Dependencies | MT-1.1-01 (project exists), MT-0.2-04 (Compose health checks that consume these) |
| Parent sections | 9.2 (Ops row), 16.1, 17, 19.1 (WP-1.1), 20.4, 20.5 |

## Context
WP-1.1 lists `/health/live` and `/health/ready` as deliverables and makes "container
healthy under Compose" the WP acceptance. Section 9.2 defines both Ops endpoints;
Section 16.1 wires the `backend` service health check to `/health/ready`; Section 17
lists live/ready among observability basics. `live` answers "process is up", `ready`
answers "dependencies (database, cache) are reachable" so restarts and dependency
outages are visible without errors in logs alone (NFR-04/NFR-06 posture).

## Inputs / Prerequisites
* MT-1.1-01 — running ASGI project and settings (database/cache URLs from Section 9.10).
* MT-0.2-01/MT-0.2-04 — the Compose services and health-check definitions these
  endpoints must satisfy (Section 16.1: backend health check = `/health/ready`).
* Parent plan Section 9.2 — Ops endpoints `GET /health/live`, `GET /health/ready`
  (caller: infrastructure, unauthenticated).
* Parent plan Section 17 — health: live and ready endpoints; worker/beat heartbeat
  checks arrive with their own WPs.

## Scope (in)
* Implement `GET /health/live`: returns success whenever the process is serving
  requests; no dependency checks, no auth.
* Implement `GET /health/ready`: performs cheap dependency checks — database
  connectivity and cache reachability as declared in Section 16.1 — returning a
  non-2xx status when a required dependency is unavailable.
* Keep both endpoints outside authenticated surfaces (caller is infrastructure) and
  documented in the OpenAPI contract when it lands (MT-1.1-04 adds the document; the
  routes exist now).
* Tests for the success path and for the not-ready path with an unreachable dependency.
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Worker and beat heartbeat checks (Section 17) — background-job WPs.
* Metrics endpoints — not scoped to any WP micro-task (see MT-1.1-02 risk note).
* Making Compose use these endpoints — already defined by MT-0.2-04; this task only
  provides what the existing health check probes.
* OpenAPI publication of the routes — MT-1.1-04.

## Target paths
* `backend/` — health routes (under `core` per Section 9.1)
* `backend/tests/` — liveness/readiness tests
* WP changelog entry

## Acceptance criteria
- [ ] `GET /health/live` returns success with no dependency checks (Section 9.2 Ops).
- [ ] `GET /health/ready` returns success when database and cache are reachable and a
  non-2xx status when either is unavailable (Section 16.1).
- [ ] Both endpoints are unauthenticated and never require a user or agent token.
- [ ] Tests cover live-always-up and ready-failure paths; lint and type check green
  (Section 20.4 item 2).
- [ ] Any error responses use codes from the Section 9.2 catalog (Section 20.4 item 5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k health` to cover both endpoints; then start the stack with
Compose and confirm the `backend` service health check turns healthy
(`docker compose ps` shows backend healthy per MT-0.2-04).

## Attachments
* [Section 9.2 — REST API surface (Ops endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.1](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 9.2 lists the Ops endpoints inside the `/api/v1`-based table while
  Section 16.1 health-checks `/health/ready` directly — expose the path the Compose
  probe uses (Section 16.1) and record the canonical path choice in the changelog so
  the OpenAPI document and the probe never disagree.
* Readiness must fail fast but not flap: keep checks cheap (ping-level), or a slow
  dependency will restart-loop the container.
