# MT-0.2-04 — Add Health Checks and Prove Data Survives a Restart

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.2-04 |
| Title | Add health checks and prove data survives a restart |
| Parent WP | WP-0.2 — Compose skeleton and environment template (Milestone M0) |
| Requirements | NFR-06 |
| Priority | M |
| Dependencies | MT-0.2-01, MT-0.2-02, MT-0.2-03 |
| Parent sections | 16.1, 16.3, 19.1 (WP-0.2), 20.4 |

## Context
This task delivers the proof behind WP-0.2's acceptance criterion: one command starts
the stack, health checks go green, and data survives a restart. Section 16.1 assigns a
health check to every service; Section 16.3 makes local named volumes the default
storage. Together they demonstrate the durability baseline that later builds on (NFR-04
backend restarts, backup drills in WP-6.2).

## Inputs / Prerequisites
* MT-0.2-01 (services and volumes), MT-0.2-02 (profiles/network), MT-0.2-03 (env
  template for `docker compose up` configuration).
* Parent plan Section 16.1 — health check column: Postgres readiness probe, Redis ping,
  `migrate` exit code, backend `/health/ready`, worker ping, beat process check, web
  HTTP check, cloudflared tunnel status.
* Placeholder `backend`/`web` images able to serve their health endpoints/answers
  (real `/health/ready` implementation arrives in WP-1.1; the placeholder must answer
  equivalently for the skeleton).
* Docker Compose v2 with `--wait` support.

## Scope (in)
* Add the health check for each of the eight services exactly as specified in the 16.1
  table (migrate uses its exit code).
* Order startup so `docker compose up` blocks until health checks pass (e.g. `--wait`).
* Document the one-command bring-up and the restart procedure in the Compose README.
* Prove durability: write a marker row into Postgres through the running stack, restart
  the stack, and read the row back.
* Add a WP changelog note.

## Out of scope
* Backend `/health/live` and `/health/ready` endpoints — WP-1.1.
* Backup/restore drills and retention — WP-6.2 (Section 16.5).
* Worker/beat real functionality — WP-1.7/WP-1.9 scheduling work.
* Monitoring and alerting on health — WP-6.4.

## Target paths
* `infra/compose/compose.yaml` (health check definitions)
* `infra/compose/README.md` (one-command bring-up, restart, and data-survival check)
* WP changelog entry

## Acceptance criteria
- [ ] All eight services carry the health check specified in Section 16.1.
- [ ] One documented command starts the whole stack and reports all health checks green
  (WP-0.2 acceptance).
- [ ] Health checks go green within the documented startup window (WP-0.2 acceptance).
- [ ] A marker row written to Postgres before a restart is readable after the restart
  (WP-0.2 acceptance; named volume per 16.3).
- [ ] Restart procedure documented in the Compose README.
- [ ] No secrets or environment-specific values committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the documented one-command bring-up (e.g. `docker compose -f infra/compose/compose.yaml --env-file <env> --profile dev up -d --wait`), then `docker compose ps` to confirm every service is `healthy`. Insert a marker row with a one-line `docker compose exec postgres` SQL statement, run `docker compose restart` (or `down` followed by `up` without `-v`), wait for health again, and query the marker row to confirm it persisted.

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.3 — Storage](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `docker compose down` without `-v` preserves volumes, but `down -v` destroys them —
  document the safe tear-down explicitly to avoid false "data loss" or accidental data
  loss during the proof.
* Placeholder health answers must not mask the real endpoints: WP-1.1's `/health/ready`
  must satisfy the same check without changing it (keep the probe path as in 16.1).
