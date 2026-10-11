# MT-0.2-01 — Define the Compose Services with Correct Dependencies

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.2-01 |
| Title | Define the Compose services per parent plan Section 16.1 with correct dependencies |
| Parent WP | WP-0.2 — Compose skeleton and environment template (Milestone M0) |
| Requirements | NFR-06 |
| Priority | M |
| Dependencies | MT-0.1-01 (WP-0.1 complete) |
| Parent sections | 16.1, 19.1 (WP-0.2), 19.2, 20.4 |

## Context
WP-0.2 turns the deployment description in Section 16.1 into a runnable Compose stack.
The goal requires `postgres`, `redis`, placeholder `backend` and `web` to start healthy
under Compose, with the full service topology (`migrate`, `worker`, `beat`,
`cloudflared`) and the exact dependency edges from the 16.1 table. NFR-06 demands the
same stack run identically on Docker Desktop and a Linux VPS, configured only by
environment variables.

## Inputs / Prerequisites
* Parent plan Section 16.1 — service table: image basis, ports, volumes, health check,
  depends-on for all eight services.
* MT-0.1-01 — `infra/compose/` directory exists.
* Docker with Compose v2 available on the host.
* Placeholder images for `backend` and `web` sufficient to satisfy depends-on ordering
  (real images arrive with WP-1.1 / WP-4.1; cloudflared/postgres/redis are official
  images per 16.1).

## Scope (in)
* Author the Compose file in `infra/compose/` defining all eight services from 16.1:
  `postgres`, `redis`, `migrate` (one-shot), `backend`, `worker`, `beat`, `web`,
  `cloudflared`.
* Wire the exact dependency edges: `migrate` → `postgres`; `backend` → `postgres`,
  `redis`, `migrate`; `worker` → `postgres`, `redis`; `beat` → `redis`; `web` →
  `backend`; `cloudflared` → `backend`, `web`.
* Mount the volumes from 16.1: Postgres data volume, Redis optional persistence,
  backend media volume.
* Use placeholder definitions for `backend` and `web` consistent with the M0 goal
  (healthy starters, not full applications).
* Document bring-up and tear-down in the Compose README (WP-0.2 deliverable; final
  command set proven by MT-0.2-04).
* Add a WP changelog note.

## Out of scope
* Network topology and dev/prod profiles — MT-0.2-02.
* The environment template and variable documentation — MT-0.2-03.
* Health check probes and the data-survival proof — MT-0.2-04.
* Real backend/web/worker code and migrations — WP-1.1 onwards.
* Cloudflare tunnel configuration values — WP-5.1 (only the service entry belongs here).

## Target paths
* `infra/compose/compose.yaml` (service definitions and depends-on edges)
* `infra/compose/README.md` (bring-up and tear-down notes)
* Placeholder image references for `backend` and `web` (Dockerfiles or stub images)
* WP changelog entry

## Acceptance criteria
- [ ] All eight services from Section 16.1 are defined in the Compose file.
- [ ] Every depends-on edge matches the 16.1 table exactly.
- [ ] Postgres data, Redis persistence, and backend media volumes are declared as in 16.1.
- [ ] Only `web` and `backend` publish ports (binding behavior set up in MT-0.2-02).
- [ ] `docker compose config` validates the file with no errors.
- [ ] No secrets or environment-specific values committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `docker compose -f infra/compose/compose.yaml config` and confirm it renders all
eight services with the 16.1 dependency edges and volumes; then start the stack with
`docker compose -f infra/compose/compose.yaml up -d` to confirm dependency ordering
runs `migrate` before `backend` (final health verification is MT-0.2-04).

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16 — Infrastructure and Deployment](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Placeholder `backend`/`web` images must still answer the health checks expected by
  MT-0.2-04 — coordinate the stubs so they can be replaced by WP-1.1/WP-4.1 images
  without changing service names (OQ not required; image identity is internal).
* Official-image tags must be pinned later for `prod` profile (16.1) — left to
  MT-0.2-02's profile split.
