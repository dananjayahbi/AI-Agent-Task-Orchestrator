# MT-5.1-01 — Add the cloudflared Compose Service

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.1-01 |
| Title | Add the cloudflared Compose service |
| Parent WP | WP-5.1 — `cloudflared` service and tunnel ingress (Milestone M5) |
| Requirements | FR-NET-01, FR-NET-02, NFR-06, GOAL-4 |
| Priority | M |
| Dependencies | MT-0.2-01 (service entry), MT-0.2-03 (environment template); WP-1.1 complete (backend) |
| Parent sections | 15.1, 15.4, 16.1, 19 (WP-5.1), 20.4, 20.5 |

## Context
FR-NET-01: remote access only via an outbound Cloudflare Tunnel, no inbound public
ports. Section 15.1 places `cloudflared` as a Compose service on the internal network
connecting outbound only; Section 16.1 already declares the service (official image,
no ports, tunnel-status health check, depends on `backend` and `web`) as a skeleton
from MT-0.2-01 — with WP-5.1's note that only the service entry belonged to M0. This
task makes the service real: pinned official image, tunnel token from the
environment, startup validation, and a health check that reflects actual tunnel
status, all on the internal network with zero published ports (GOAL-4: monitor and
approve from anywhere without opening public ports).

## Inputs / Prerequisites
* MT-0.2-01 — `cloudflared` service skeleton and dependency edges in
  `infra/compose/compose.yaml`; MT-0.2-02 — dev/prod profiles; MT-0.2-03 —
  environment template.
* Parent plan Section 15.1 — outbound-only topology; Section 15.4 — tunnel token is
  a secret in the environment; Section 16.1 — service row (image basis, health
  check, depends-on, no ports).
* Section 16.2 — one documented environment template, real values outside Git,
  startup validation in `prod`.
* Section 9.10 — configuration groups include the Cloudflare tunnel token.
* WP-1.1 — `backend` healthy; MT-0.2-04 — `web` health check (dependency order).

## Scope (in)
* Upgrade the `cloudflared` Compose service to run the official image (pinned tag;
  `latest` only acceptable for `dev` per profile rules) with the tunnel started from
  the environment-provided tunnel token/credentials (Section 15.4 — token is a
  secret; add its variable to the environment template with an empty default and
  document it; real value never committed).
* Health check reporting tunnel status per Section 16.1 (`cloudflared` tunnel status
  probe), with `depends_on` edges to `backend` and `web` preserved.
* Enforce zero published ports and internal-network attachment for `cloudflared`
  (FR-NET-01 — no inbound public ports anywhere in the stack).
* Fail-fast behavior consistent with Section 16.2: `prod` refuses to start the
  service without the tunnel token; `dev` may run the stack with the service
  disabled via profile (documented).
* Document bring-up and token provisioning pointer in the Compose README (details
  of hostname/token handling land in MT-5.1-03).
* Add a WP changelog note.

## Out of scope
* Ingress rules mapping hostname/path to `web` and `backend` — MT-5.1-02.
* Hostname configuration, token rotation runbook, CORS/CSRF origin lists —
  MT-5.1-03.
* SSE stability verification — MT-5.1-04.
* Cloudflare Access policy, route allowlist, edge rate limits — WP-5.2.
* Device/agent token layers — WP-1.2 / WP-5.3 (Section 15.3 layers 2–3).
* LAN hostname for the web UI (Section 15.1) — MT-0.2-02 network bindings.

## Target paths
* `infra/compose/compose.yaml` (cloudflared service made real)
* `infra/compose/` environment template (tunnel token variable, documented default)
* `infra/compose/README.md` (bring-up notes for the tunnel service)
* WP changelog entry

## Acceptance criteria
- [ ] The `cloudflared` service runs the official image with a pinned tag under
  `prod` and reports tunnel status via its health check (Section 16.1).
- [ ] The stack requires no inbound ports: `docker compose config` shows no ports
  published by `cloudflared`, and only `web`/`backend` publish (LAN-bounded,
  FR-NET-01, Section 16.1).
- [ ] The tunnel token comes from the environment template only — no secret or
  environment-specific value committed (Section 20.4 item 3; Section 15.4).
- [ ] `prod` fails fast when the token is missing/weak (Section 16.2); documented
  `dev` behavior for running without the tunnel.
- [ ] `depends_on` edges to `backend` and `web` preserved; `docker compose config`
  validates (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `docker compose -f infra/compose/compose.yaml config` and confirm the
cloudflared service definition (pinned image, health check, deps, zero published
ports, token env reference); start the stack and check `docker compose ps` for the
tunnel health status; restart with the token unset in `prod` and confirm fail-fast.

## Attachments
* [Section 15.1 — Topology](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Cloudflare's official image and config formats change over time — pin the image
  tag and document the upgrade path in the README; if the token-based run mode and
  the config-file mode differ materially for ingress (MT-5.1-02), confirm the chosen
  mode there before writing ingress rules; ambiguity → OQ.
* Tunnel credentials in a local `.env` are a secret-handling surface — ensure the
  secret scan gate (MT-0.3-04) covers the template and that `.env` is git-ignored
  (MT-0.2-03 convention).
