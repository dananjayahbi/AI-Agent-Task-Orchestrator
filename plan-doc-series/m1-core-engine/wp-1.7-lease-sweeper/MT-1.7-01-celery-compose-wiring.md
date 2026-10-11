# MT-1.7-01 — Wire Celery Worker and Beat Services into Compose

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.7-01 |
| Title | Wire Celery worker and beat services into Compose |
| Parent WP | WP-1.7 — Lease sweeper and retry policy (Milestone M1) |
| Requirements | FR-LEA-05, NFR-06, ADR-003 |
| Priority | M |
| Dependencies | WP-1.1 complete (backend image); MT-0.2-01 (service entries), MT-0.2-04 (health checks) |
| Parent sections | 16.1, 9.9, 9.10, 19 (WP-1.7), 20.4, 20.5 |

## Context
WP-1.7's first slice wires the background-jobs runtime the sweeper needs. ADR-003
fixes Celery (worker and beat) on Redis for background jobs; Section 16.1 already
declares `worker` (backend image, worker-ping health check, depends on postgres +
redis) and `beat` (backend image, process check, depends on redis) as service entries
from MT-0.2-01 — this task makes them real: run the actual backend image, configure
the Celery app, register the beat schedule hooks (sweeper and lease-expiring notifier
from the Section 9.9 job table, both every 60 s), and prove the pair starts healthy
under the dev and prod profiles.

## Inputs / Prerequisites
* MT-0.2-01/MT-0.2-04 — `worker` and `beat` service skeletons, health checks and
  profiles in `infra/compose/compose.yaml`.
* WP-1.1 — runnable backend image, settings split by environment (Section 9.10
  configuration groups) — the same image basis for worker and beat (Section 16.1).
* Parent plan Section 9.9 — background-jobs table: lease sweeper every 60 s,
  lease-expiring notifier every 60 s (jobs themselves land in MT-1.7-02/04).
* Section 16.2 — one environment template, real values outside Git, startup
  validation in `prod`.
* ADR-003 — Celery on Redis; Section 16.1 — networking (worker/beat publish no
  ports).

## Scope (in)
* Configure the Celery application in the backend project: broker/result backend on
  Redis from the environment (Section 9.10 groups), settings validated at startup
  (fail fast in `prod`, Section 16.2).
* Activate the `worker` and `beat` Compose services against the real backend image:
  worker-ping health check and `/health/ready`-style liveness as specified in 16.1;
  beat runs the periodic schedule with placeholder registrations for the two 60-second
  jobs from Section 9.9 (names fixed; behavior in MT-1.7-02 and MT-1.7-04).
* Keep `worker`/`beat` publishing no ports on the internal network (Section 16.1;
  only `web` and `backend` publish).
* Document local bring-up/verification in the Compose README (worker/beat logs,
  beat schedule listing).
* Add a WP changelog note.

## Out of scope
* The sweeper job body — MT-1.7-02; retry escalation — MT-1.7-03; expiring warning —
  MT-1.7-04; chaos suite — MT-1.7-05.
* Other Section 9.9 jobs (attachment pipeline WP-1.12, push dispatch WP-5.4,
  retention/backup WP-6.x) — register later, same mechanism.
* VPS/`prod` image pinning and secrets mechanism — MT-0.2-02 / Section 16.2/16.4.
* Application-level job configuration beyond Celery (e.g. alternative brokers) —
  ADR-003 decided; no re-litigating.

## Target paths
* `infra/compose/compose.yaml` (worker/beat wiring: image, command, health checks)
* `backend/` (Celery app configuration and beat schedule skeleton)
* `infra/compose/README.md` (worker/beat verification notes)
* WP changelog entry

## Acceptance criteria
- [ ] `docker compose up` starts `worker` and `beat` healthy alongside `backend`,
  with the Section 16.1 dependency edges (worker → postgres, redis; beat → redis).
- [ ] The Celery app is environment-driven per Section 9.10 and validated at startup
  (NFR-06 identical behavior on Docker Desktop and VPS).
- [ ] Beat's schedule declares the two Section 9.9 60-second jobs by their final
  names (sweeper, lease-expiring notifier), even with stub task bodies.
- [ ] `worker` and `beat` publish no ports and run on the internal network
  (Section 16.1).
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] CI green (`docker compose config` in the pipeline); changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run `docker compose -f infra/compose/compose.yaml config` (renders worker/beat with
correct images, deps and no published ports), then `docker compose up -d` and check
`docker compose ps` shows worker and beat healthy; `docker compose logs beat` shows
the schedule loaded with both 60-second entries.

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.9 — Background jobs](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Worker/beat share the backend image — settings that fail fast in `prod` (weak
  secrets) will stop beat too; that is intended (Section 16.2) but must be
  documented so operators are not surprised.
* Beat's clock and single-instance assumption: Section 9.9 jobs are idempotent and
  skip-locked by design (FR-LEA-05), so running beat twice is tolerated — do not add
  singleton locks the plan does not specify; if scheduling jitter appears, raise an
  OQ.
