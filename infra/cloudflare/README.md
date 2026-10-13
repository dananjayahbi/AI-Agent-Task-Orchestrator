# Cloudflare tunnel operations — hostname and token handling

| Field | Value |
|---|---|
| Status | Published |
| Published | 2026-10-12 |
| Owner | WP-5.1 — `cloudflared` service and tunnel ingress (MT-5.1-03) |
| Source of truth | Parent plan Sections 15.1, 15.3, 15.4 and 16.2/16.4 — the plan wins on any conflict (Section 0) |
| Applies to | The `cloudflared` service in `infra/compose/compose.yaml`, the ingress rules in [`ingress.yaml`](./ingress.yaml), and the operator procedures below |

## Purpose

Section 15.4 fixes what must be written down for remote access: the tunnel
token is a secret in the environment, trusted origins are exactly two known
values, and the failure mode when the tunnel drops is explicit. This document
is that record, plus the hostname configuration procedure (Section 15.1,
OQ-11) and the VPS-migration pointer (Section 16.4 step 4) that GOAL-5
requires. Procedures are recorded, not executed: performing DNS/tunnel setup
in the Cloudflare dashboard is an operator action.

## 1. Topology — two hostnames, separate concerns (Section 15.1)

* **LAN address** — the web UI reached directly from the Compose host's LAN
  interface. Its value is the host's bind address `ORCHESTRATOR_BIND_ADDR`
  plus the published ports `ORCHESTRATOR_PORT_WEB` / `ORCHESTRATOR_PORT_BACKEND`
  (environment template; only these two services publish ports, LAN-bounded —
  FR-NET-01). The LAN path never touches Cloudflare.
* **Tunnel hostname** — the only public surface, for remote access. OQ-11
  (owner decision, recorded 2026-10-11, deferred to M5) fixes the convention
  `orchestrator.<owner-domain>`: **the owner supplies the domain**; nothing
  else about the hostname is decided here. Its concrete value is held only in
  `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` (environment template, empty
  default; real value in the git-ignored `.env`) and at the Cloudflare edge —
  never committed (plan 20.4 item 3).

`cloudflared` runs as a Compose service on the internal network and connects
**outbound only**; no ports are published for remote use (Section 15.1,
GOAL-4). Next.js and the backend are reached through the ingress rules in
[`ingress.yaml`](./ingress.yaml), which map hostname and path to the internal
`web` and `backend` services by service name only.

## 2. Hostname configuration (dashboard-driven, Section 15.1)

Operator steps at the level the plan fixes:

1. **Domain and account** — the owner supplies a domain on a Cloudflare
   account (OQ-11 outcome; the plan records this as an owner-owned
   prerequisite).
2. **Set the hostname variable** — put the concrete value
   (`orchestrator.<owner-domain>`) into
   `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` in the git-ignored
   `infra/compose/.env`. The committed template keeps the empty default.
3. **Create the named tunnel** — in the Cloudflare dashboard create the
   tunnel for this stack and copy its token into
   `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` in the same `.env` file (Section
   15.4: the token is a secret in the environment).
4. **Mirror the ingress rules to the edge** — a token-run tunnel is
   *remotely managed*: cloudflared fetches its routes from the edge and
   ignores a local `ingress:` section. Add the public-hostname routes so they
   mirror [`ingress.yaml`](./ingress.yaml) rule for rule: the tunnel hostname
   (default route) to `http://web:3000`, the path prefix `/api` to
   `http://backend:8000`, and no other routes — unmatched names get 404.
   Substitute the hostname value from step 2; the local file deliberately
   carries the OQ-11 placeholder notation, so no environment-specific
   hostname is in Git.
   **The deny half mirrors differently (WP-5.2):** public-hostname *routes*
   can only forward, never deny, so the deny rules of `ingress.yaml`
   (`http_status:403`) are applied at the edge as the Cloudflare Access
   deny applications A2–A10 of [`access-policy.md`](./access-policy.md) §3,
   plus the four method-aware WAF Custom rules W1–W4 of
   [`route-allowlist.md`](./route-allowlist.md) §4. Both are listed as
   operator steps in `access-policy.md` §4 and verified by
   [`route-verification-checklist.md`](./route-verification-checklist.md);
   do not try to express them as routes.
5. **DNS** — adding the public hostname in the dashboard creates the DNS
   record (CNAME) for the tunnel hostname; verify it resolves after the
   route exists.
6. **LAN stays separate** — the LAN address from Section 1 reaches the stack
   directly; the ingress file and the edge routes only ever govern the tunnel
   hostname.

Not here: Cloudflare Access policy, route allowlists and edge rate limits —
those are **WP-5.2's** documents in this folder:
[`access-policy.md`](./access-policy.md) (Section 15.3 layer 1),
[`route-allowlist.md`](./route-allowlist.md) (Section 15.2 rules),
[`rate-limits.md`](./rate-limits.md) (layer 4), all defined as code here
with their live application as the operator steps in those files; this
document and `ingress.yaml` record the structure they gate.

## 3. Tunnel token handling (Sections 15.4, 16.2)

* **Where the variable lives** — `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` has
  its row in `infra/compose/.env.example` with an empty default and the
  purpose/validation comment; the real value lives only in the git-ignored
  `infra/compose/.env` (or the host's secret mechanism / Compose secrets on a
  VPS — same canonical name everywhere, NFR-06). No secret or
  environment-specific value is ever committed (plan 20.4 item 3); the
  committed template and this document carry placeholders only.
* **How it is provisioned** — the Cloudflare dashboard issues the token for
  the named tunnel (step 2.3 above); the operator pastes it into `.env`.
  Compose maps it to cloudflared's image-mandated `TUNNEL_TOKEN` inside the
  container (configuration.md rule 7).
* **Fail-fast** — with the token missing or invalid, cloudflared refuses to
  run and exits non-zero at startup, so a `prod` bring-up with
  `--wait` can never report healthy without it (Section 16.2; verified in
  MT-5.1-01). In `dev` the tunnel service is profile-gated off by default —
  the documented way to run without a tunnel is simply not to enable the
  `tunnel` profile (see [`infra/compose/README.md`](../compose/README.md)).
* **Rotation** — rotate the token through the **Cloudflare dashboard**
  (Section 15.4; no automation — automation would be a new open question).
  Rotation replaces the
  token value in `.env` and restarts the `cloudflared` service. The plan does
  not state whether the dashboard flow guarantees an old/new token overlap or
  an immediate cutover; **record the observed guarantee here after the first
  rotation** (zero-downtime overlap vs immediate cutover) rather than
  assuming one (plan 20.1 principle 5 — no invented facts).
* **Backend validation** — `prod` startup validation refuses weak or missing
  required secrets (Section 16.2; settings live in WP-1.1's
  `backend/apps/core/settings/prod.py`). The header comment of
  `infra/compose/.env.example` is the authoritative required-in-prod list.

## 4. Trusted origins and mobile authentication (Section 15.4, ADR-006)

* **Exactly two known origins** belong in the CORS and CSRF trusted-origin
  lists: the **LAN address** (Section 1, e.g. the `ORCHESTRATOR_BIND_ADDR`
  origin with its published port) and the **tunnel hostname**
  (`https://<ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME>`). The backend
  consumes them from `ORCHESTRATOR_CORS_ORIGINS` /
  `ORCHESTRATOR_CSRF_ORIGINS` (environment template); this document is the
  source of truth for *which* values are legitimate — no third origin is ever
  added casually.
* **The mobile app uses token auth, no cookies** (Section 15.4): device-bound
  tokens (ADR-006 layer 3 context) make CSRF origin checks a web-only
  concern; the phone never carries a session cookie.
* **The edge is not authentication** — Section 15.3 layer 1 (Cloudflare
  Access) is only the outer gate; Django device/agent tokens are always
  required and edge identity headers are never trusted as authentication on
  their own. Anything reading this document as "the tunnel authenticates
  users" is wrong (G-series Zero-Bleed discipline).

## 5. Failure mode (Section 15.4, point for point)

If the tunnel is down:

1. **LAN access continues** — the web UI and API are still served on the
   Compose host's LAN address (Section 15.1).
2. **All agents continue** — agents and the bridge reach the backend without
   the tunnel.
3. **The mobile app shows "unreachable"** — remote access is the tunnel's
   job and nothing else (GOAL-4 keeps LAN as the fallback).
4. **Push still works via FCM from the backend** — outbound internet only;
   no inbound path is involved.

Operational follow-up lives in
[`docs/runbooks/tunnel-down.md`](../../docs/runbooks/tunnel-down.md) — a stub
whose content is written in **WP-6.5** (Section 17 runbooks); the "tunnel
down" alert itself is WP-6.4.

## 6. VPS migration pointer (Section 16.4, GOAL-5)

Section 16.4 step 4 is "Point the tunnel to the new host (or move the
connector)" — moving the stack to a VPS is configuration-only: copy the
environment file (with the same `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` and
hostname values), start the stack, repoint the edge routes to the new
connector, done — nothing in the stack depends on the laptop's file system
(P2 holds). The full checklist is Section 16.4; the prose runbook is written
in **WP-6.5** and will link back to this document.

## 7. Related files and sections

* [`ingress.yaml`](./ingress.yaml) — canonical ingress rules: the WP-5.1
  routing structure plus the WP-5.2 Section 15.2 deny block (default deny,
  403 at the tunnel; LAN untouched).
* [`access-policy.md`](./access-policy.md) — MT-5.2-01: the Cloudflare
  Access policy for the tunnel hostname (gate `A1`, deny applications
  A2–A10, principals P1/P2), application steps and the named V1–V5
  verification hooks.
* [`route-allowlist.md`](./route-allowlist.md) — MT-5.2-02: every Section
  15.2 row and Section 9.2 path with its explicit decision, the method
  rules W1–W4, the conditional-row flip procedure, and the canonical
  machine-readable rule table.
* [`rate-limits.md`](./rate-limits.md) — MT-5.2-03: edge rules E1–E4 with
  documented threshold choices and their alignment with the API's
  `ORCHESTRATOR_RATE_LIMIT_*` budgets.
* [`route-verification-checklist.md`](./route-verification-checklist.md) —
  MT-5.2-04: the blocked-vs-allowed matrix, layer hooks, results template
  and the recorded local run; runner at
  [`e2e/route_verify.py`](../../e2e/route_verify.py) (results:
  [`e2e/route_verification_results.json`](../../e2e/route_verification_results.json)).
* [`sse-verification.md`](./sse-verification.md) — MT-5.1-04 SSE stability
  verification: the 30-min idle/heartbeat/no-buffering/lossless-resume test
  through the tunnel path — recorded LAN control run, operator procedure for
  the through-tunnel run (OQ-11), and the split acceptance table.
* [`infra/compose/compose.yaml`](../compose/compose.yaml) — the `cloudflared`
  service (profiles `[prod, tunnel]`, pinned official image, token from the
  environment, ingress mounted read-only, zero published ports).
* [`infra/compose/.env.example`](../compose/.env.example) —
  `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` and
  `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` rows (empty defaults, purpose and
  validation notes).
* [`docs/plan/conventions/configuration.md`](../../docs/plan/conventions/configuration.md)
  — naming, grouping and metadata rows for both variables.
* Parent plan: Section 15 (15.1 topology, 15.2 route policy, 15.3 access
  layers, 15.4 operational details), 16.1 (service row), 16.2 (secrets),
  16.4 (VPS migration).
