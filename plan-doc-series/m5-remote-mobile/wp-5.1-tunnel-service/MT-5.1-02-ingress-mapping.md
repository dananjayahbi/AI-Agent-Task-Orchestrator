# MT-5.1-02 — Configure Ingress Mapping to Web and Backend

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.1-02 |
| Title | Configure ingress mapping to web and backend |
| Parent WP | WP-5.1 — `cloudflared` service and tunnel ingress (Milestone M5) |
| Requirements | FR-NET-01, FR-NET-02, ADR-002 |
| Priority | M |
| Dependencies | MT-5.1-01 (service running); MT-0.2-02 (networks/profiles) |
| Parent sections | 15.1, 15.2, 15.4, 16.1, 19 (WP-5.1), 20.4, 20.5 |

## Context
Section 15.1: "Two hostnames, separate concerns: a LAN address for the web UI
(direct to the Compose host) and a tunnel hostname (for example
`orchestrator.<owner-domain>`) for remote access… Next.js and the backend are
reached through ingress rules mapping hostname and path to internal services." The
tunnel hostname is the only public surface; its route groups are governed by
Section 15.2 (mobile feature set exposed; agent-token creation, policy editing and
admin LAN-only; health internal only). This task writes the ingress configuration
that routes the tunnel hostname's traffic to the internal `web` and `backend`
services — the routing layer WP-5.2 then gates with Access policy and allowlists.

## Inputs / Prerequisites
* MT-5.1-01 — cloudflared running with credentials from the environment.
* Parent plan Section 15.1 — ingress rules mapping hostname and path to internal
  services; Section 15.2 — route-group table deciding what may be exposed.
* Section 15.4 — SSE through the tunnel needs no response buffering; heartbeats
  every 15 s (Section 9.6) are designed for this — ingress must not buffer or time
  out event streams; CORS/CSRF trusted origins cover only the two known origins.
* Section 16.1 — internal network; `web` and `backend` are the only reachable
  targets; service names/ports as defined by MT-0.2-01/WP-1.1.
* OQ-11 (domain/hostname ownership) outcome from WP-0.4 — hostname parameterization.

## Scope (in)
* Author the ingress rule set for the tunnel hostname: default route to the internal
  `web` service; path prefix(s) for the API (`/api/…`) routed to the internal
  `backend`; a documented catch-all returning 404 for unmatched paths (no silent
  fallback to admin surfaces).
* Ensure routing targets use internal service names/ports on the Compose network —
  never published host ports (FR-NET-01).
* Keep the LAN hostname path separate (Section 15.1): web UI on LAN reaches the
  stack directly; the ingress file only governs the tunnel hostname.
* Route-group review against Section 15.2 recorded next to the config: which groups
  are reachable through the tunnel at the routing layer (auth/devices, reads,
  review, dashboard, events stream; "could" and service-token groups commented),
  so WP-5.2's allowlist work starts from an explicit list — routing here is
  structure, enforcement is WP-5.2.
* Preserve SSE-friendliness: no buffering directives on the events path; proxy
  timeouts above the 15 s heartbeat (Section 15.4/9.6).
* Tests/verification: rendered config validation; LAN-vs-tunnel behavior checks
  documented; unmatched-path 404 confirmed.
* Add a WP changelog note.

## Out of scope
* Cloudflare Access policy, route allowlist enforcement, edge rate limits — WP-5.2.
* Hostname purchase/DNS cutover and token rotation documentation — MT-5.1-03.
* The 30-minute SSE idle test — MT-5.1-04.
* Backend/web application routes themselves — WP-1.1 / WP-4.1.
* Health endpoint exposure policy (internal only per 15.2) — enforced in WP-5.2
  checklist; commented here.

## Target paths
* `infra/cloudflare/` (tunnel ingress configuration)
* `infra/compose/compose.yaml` (mount/reference of the ingress config if required)
* WP changelog entry

## Acceptance criteria
- [ ] Ingress maps the tunnel hostname to internal `web` (UI) and `backend` (API)
  services exactly as Section 15.1 describes — by internal service name, no new
  published ports (FR-NET-01).
- [ ] Unmatched paths return 404 rather than reaching unintended services.
- [ ] The Section 15.2 route groups are listed next to the config with exposed /
  LAN-only / service-token-only marked, matching the plan's table (Section 20.5
  traceability); enforcement is explicitly left to WP-5.2.
- [ ] The events-stream path is not buffered and tolerates the 15 s heartbeat
  (Section 15.4, ADR-002).
- [ ] `docker compose config` validates with the ingress reference; no
  environment-specific hostname committed — parameterized via the environment
  template (Section 20.4 item 3).
- [ ] CI green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `docker compose -f infra/compose/compose.yaml config` to validate the mounted
ingress config, then bring the stack up and verify from a LAN client: API path
reaches `backend`, UI path reaches `web`, an unmatched path returns 404, and the
route-group checklist next to the config matches Section 15.2 line by line.

## Attachments
* [Section 15.1 — Topology](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.2 — Route policy on the tunnel hostname](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Path-prefix collisions between the Next.js routes and the API base
  (`/api/v1`) must be resolved against the real WP-4.1 routing — if the web app
  needs an API path of its own, raise an OQ rather than adding overlapping rules.
* "Task create/publish — Yes (Could)" (Section 15.2) and OQ-12 (mobile creation
  out of v1 scope) interact: keep the route commented/disabled by default until
  WP-5.2 or a decided OQ enables it; do not decide scope here.
