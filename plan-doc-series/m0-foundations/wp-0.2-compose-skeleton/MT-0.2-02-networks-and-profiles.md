# MT-0.2-02 — Configure the Internal Network and Dev/Prod Profiles

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.2-02 |
| Title | Configure the internal network and dev/prod profiles |
| Parent WP | WP-0.2 — Compose skeleton and environment template (Milestone M0) |
| Requirements | NFR-06 |
| Priority | M |
| Dependencies | MT-0.2-01 |
| Parent sections | 16.1, 16.2, 19.1 (WP-0.2), 20.4 |

## Context
Section 16.1 fixes the networking model — one internal network for all services, with
only `web` and `backend` publishing ports and only to the LAN interface by default —
and two Compose profiles: `dev` (hot reload, helper tools) and `prod` (pinned images,
no debug). This task implements that model so the same stack is portable between Docker
Desktop and a Linux VPS (NFR-06), with differences carried entirely by profile choice
and environment variables (16.2).

## Inputs / Prerequisites
* MT-0.2-01 — services defined in `infra/compose/compose.yaml`.
* Parent plan Section 16.1 — networking and profiles paragraph.
* Parent plan Section 16.2 — configuration via environment; real values outside Git.
* LAN interface/bind address handling coordinated with the env template (MT-0.2-03).

## Scope (in)
* Declare one internal Compose network attached by all services; no other networks.
* Restrict published ports to `web` and `backend`, bound to the LAN interface by default
  (bind address supplied via environment so the same file works on Docker Desktop and a
  VPS — NFR-06).
* Define the `dev` profile: hot-reload wiring for backend and web, plus helper tooling
  if needed (16.1 mentions "mailhog-style tools if needed").
* Define the `prod` profile: pinned image tags, no debug flags, no hot reload.
* Document profile selection (`--profile dev` / `--profile prod`) in the Compose README.
* Add a WP changelog note.

## Out of scope
* The environment template contents — MT-0.2-03 (the bind address variable lives there).
* Health checks and data-survival verification — MT-0.2-04.
* Cloudflare tunnel/Zero Trust configuration — WP-5.1/WP-5.2.
* TLS and public exposure — out of scope for v1 (tunnel handles edge, Section 15).

## Target paths
* `infra/compose/compose.yaml` (network, port bindings, profile annotations)
* `infra/compose/README.md` (profile usage documentation)
* WP changelog entry

## Acceptance criteria
- [ ] Exactly one network is defined and every service joins it.
- [ ] Only `backend` and `web` publish ports; no other service exposes a host port.
- [ ] Default port binding targets the LAN interface, driven by an environment variable.
- [ ] `dev` profile enables hot reload; `prod` profile uses pinned images with debug off.
- [ ] `docker compose --profile dev config` and `docker compose --profile prod config`
  both validate.
- [ ] No host-specific paths or secrets committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Validate both profiles from the repository root: `docker compose -f infra/compose/compose.yaml --profile dev config` and `docker compose -f infra/compose/compose.yaml --profile prod config`. Confirm each render shows the single internal network, port publishing only on `backend` and `web`, and the profile-specific image/debug differences.

## Attachments
* [Section 16.1 — Compose services](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.2 — Configuration and secrets](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The LAN interface address differs per host (RISK-15 host differences); hard-coding a
  bind address would violate NFR-06 — keep it environment-driven and document the
  default in MT-0.2-03.
* Hot-reload mounts must not leak host paths into `prod` images; verify the `prod`
  render contains no bind-mount based dev wiring.
