# MT-1.1-05 — Build the Backend Container Image and Wire It into Compose

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.1-05 |
| Title | Build the backend container image and wire it into Compose |
| Parent WP | WP-1.1 — Django project skeleton (Milestone M1) |
| Requirements | NFR-06, NFR-10 |
| Priority | M |
| Dependencies | MT-1.1-01, MT-1.1-02, MT-1.1-03 (project, logging and health exist), MT-0.2-01, MT-0.2-03 (Compose services and env template), MT-0.3-03 (container build job) |
| Parent sections | 16.1, 16.2, 19.1 (WP-1.1), 20.4, 20.5 |

## Context
WP-1.1's acceptance is "container healthy under Compose". WP-0.2 left a placeholder
`backend` service in the Compose stack; this task replaces the placeholder with the
real backend image so `docker compose up` starts the stack and the `/health/ready`
probe goes green (Section 16.1: backend depends on postgres, redis and a one-shot
`migrate` service). Section 16.1 also defines the `worker` and `beat` services from the
same backend image — with no Celery jobs yet in this WP, they stay out of this task's
wiring beyond what already exists from WP-0.2.

## Inputs / Prerequisites
* MT-1.1-01–03 — a bootable ASGI project with settings validation and health endpoints
  (the health check target).
* MT-0.2-01 — existing Compose definition with a placeholder `backend` service,
  networks, profiles (dev/prod).
* MT-0.2-03 — environment template and validation notes; new backend variables must be
  added there, not invented locally.
* Parent plan Section 16.1 — service table: image basis, LAN-published API port, media
  volume, `/health/ready` health check, dependencies (postgres, redis, migrate).
* Parent plan Section 16.2 — one documented environment template; real values outside
  Git; startup validation refuses weak/missing secrets in `prod`.
* MT-0.3-03 — existing container build CI job that must build this image.

## Scope (in)
* Write the backend Dockerfile (ASGI server per Section 6.6) producing an image that
  runs migrations, the ASGI server, and later Celery roles — the single "backend image"
  of Section 16.1.
* Wire the `backend` and one-shot `migrate` services in the existing Compose file to
  this image: ports, media volume, `/health/ready` health check, dependencies per
  Section 16.1; keep dev/prod profiles (MT-0.2-02) intact.
* Add the backend image build to the existing container-build CI job (MT-0.3-03).
* Extend the environment template (MT-0.2-03) with any backend settings introduced by
  MT-1.1-01, keeping names per MT-0.5-01 and defaults documented (Section 9.10).
* Verify data survives restart (WP-0.2 acceptance still holds) and the stack comes up
  with one command (NFR-06: identical stack configured only by environment variables).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Celery worker/beat behavior — their jobs belong to later WPs; only image wiring
  matters here.
* Web, cloudflared and tunnel images — M4/M5 WPs.
* Production secrets management — Section 16.2 mechanism; this task only ensures
  startup validation triggers (already from MT-1.1-01).
* VPS migration — Section 16.4, M6.

## Target paths
* `backend/` — Dockerfile (and .dockerignore if needed)
* `infra/compose/` — backend/migrate service wiring, profile preservation
* `.github/workflows/` — container build job covers the backend image
* `infra/compose/` environment template (variable additions, per MT-0.2-03)
* WP changelog entry

## Acceptance criteria
- [ ] `docker compose up` starts the stack; the `backend` service reaches healthy via
  the `/health/ready` check (WP-1.1 acceptance; Section 16.1).
- [ ] The `migrate` one-shot service runs against the backend image and gates backend
  startup (Section 16.1 dependency order).
- [ ] Ports, volumes, networks and profiles match Section 16.1 and the MT-0.2-02
  decisions; only `web` and `backend` publish ports (LAN by default).
- [ ] The stack is configured only by environment variables (NFR-06); no secrets or
  environment-specific paths in the image or Compose files (Section 20.4 item 3).
- [ ] CI container build builds the backend image green (Section 20.4 item 2).
- [ ] Data survives a restart (WP-0.2 acceptance preserved).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `docker compose up -d` and poll until `docker compose ps` reports `backend` healthy;
run `docker compose restart backend` and confirm health returns to green with data
intact; confirm the CI container-build job passes for the backend image.

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.2 — Configuration and secrets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.1](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Replacing the WP-0.2 placeholder must not regress its acceptance (one command, health
  green, data survives) — run the full WP-0.2 bring-up checks after rewiring.
* Image bloat or dev-only assumptions (debug flags in `prod` profile) break Section
  16.1's dev/prod profile split — verify both profiles after wiring.
