# MT-5.1-03 — Document Hostname Configuration and Tunnel Token Handling

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.1-03 |
| Title | Document hostname configuration and tunnel token handling |
| Parent WP | WP-5.1 — `cloudflared` service and tunnel ingress (Milestone M5) |
| Requirements | FR-NET-01, FR-NET-02, NFR-06, ADR-006, GOAL-4 |
| Priority | S |
| Dependencies | MT-5.1-01 (token variable), MT-5.1-02 (ingress and route list) |
| Parent sections | 15.1, 15.3, 15.4, 16.2, 16.4, 19 (WP-5.1), 20.4, 20.5 |

## Context
WP-5.1's deliverables include "documentation", and Section 15.4 fixes what must be
written down: the tunnel token is a secret in the environment, rotated through the
Cloudflare dashboard; CORS and CSRF trusted-origin lists include only the two known
origins (LAN address and tunnel hostname); the failure mode is explicit — tunnel
down means LAN access and all agents continue, mobile shows "unreachable", and push
still works via FCM from the backend (outbound internet only). OQ-11 sets the
hostname convention (`orchestrator.<owner-domain>`, owner supplies the domain).
Section 16.4 makes "point the tunnel to the new host" a VPS-migration step, so the
document doubles as the runbook input for GOAL-5 (configuration-only moves).

## Inputs / Prerequisites
* MT-5.1-01 — token variable in the environment template and fail-fast behavior;
  MT-5.1-02 — ingress config and Section 15.2 route-group list.
* Parent plan Section 15.4 — operational details verbatim (token rotation, trusted
  origins, failure mode, SSE heartbeat note).
* Section 15.1 — two-hostname topology; Section 15.3 — access-control layers with
  the edge as layer 1 only (identity headers never trusted as authentication alone).
* Section 16.2 — one documented environment template, secrets outside Git;
  Section 16.4 — VPS migration step 4 (point the tunnel to the new host).
* OQ-11 outcome (WP-0.4) — domain ownership and hostname default.

## Scope (in)
* Write the tunnel operations document under `infra/cloudflare/`: hostname
  configuration (LAN address vs tunnel hostname, `orchestrator.<owner-domain>`
  convention per OQ-11, DNS record and tunnel route setup steps at the level the
  plan fixes — dashboard-driven).
* Document tunnel token handling: where the variable lives (environment template,
  empty default; real value outside Git per Section 16.2), how it is provisioned,
  and rotation via the Cloudflare dashboard (Section 15.4), including the
  zero-downtime rotation note (old/new token overlap or immediate cutover — record
  what the dashboard flow guarantees; do not invent beyond it).
* Document the two known origins for CORS/CSRF trusted-origin lists (LAN + tunnel
  hostname) and why the mobile app uses token auth without cookies
  (Section 15.4, ADR-006 layer 3 context).
* Document the failure mode: tunnel down → LAN and agents unaffected, mobile
  "unreachable", FCM push still works (Section 15.4) — tie to the LAN fallback
  expectation in GOAL-4.
* Document the VPS-migration pointer (Section 16.4 step 4) and cross-link the
  future runbook (WP-6.5).
* Add a WP changelog note.

## Out of scope
* Cloudflare Access policy configuration — WP-5.2 (Section 15.3 layer 1 details).
* Actual dashboard clicks performed for the owner — the document records the
  procedure; executing DNS/tunnel setup is an operator action.
* Changing CORS/CSRF settings in backend config — WP-1.1 settings consume these
  lists; this document is their source of truth for values.
* Token rotation automation — Section 15.4 says dashboard; automation would need an
  OQ.
* The SSE verification and heartbeat proof — MT-5.1-04.

## Target paths
* `infra/cloudflare/` (tunnel and hostname operations document)
* `infra/compose/README.md` (pointer to the operations document)
* WP changelog entry

## Acceptance criteria
- [ ] The document covers hostname configuration for both hostnames with the
  OQ-11 convention and cites Section 15.1 (Section 20.5 traceability).
- [ ] Tunnel token handling matches Section 15.4/16.2: environment-only secret,
  rotation via the Cloudflare dashboard, no value committed
  (Section 20.4 item 3).
- [ ] The two trusted origins (LAN, tunnel) and the mobile token-auth/no-cookie rule
  are stated per Section 15.4.
- [ ] The failure-mode section matches Section 15.4 point for point (LAN continues,
  agents continue, mobile unreachable, FCM outbound-only).
- [ ] The VPS step (Section 16.4 item 4) is cross-referenced for GOAL-5.
- [ ] The Compose README links to the document; changelog note added
  (Section 20.4 item 7).

## Test command
Review pass: grep `infra/cloudflare/` for the token variable name, both hostnames,
`rotate`, `CORS`, `unreachable` and the Section 16.4 pointer — every Section 15.4
bullet must be findable; confirm no secret-looking value is committed
(`git grep -iE "(tunnel|cf)_token.*[A-Za-z0-9]{20,}"` returns nothing).

## Attachments
* [Section 15.4 — Operational details](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.3 — Access control layers](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.4 — VPS migration checklist](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Documentation drifts from config fastest — reference the environment variable
  names and ingress file by path rather than re-typing values (plan stays
  authoritative, Section 0).
* OQ-11's outcome may change the hostname default — if WP-0.4 recorded something
  other than `orchestrator.<domain>`, the document must follow the decided value;
  mismatch → OQ, not a silent rewrite.
* The document must not read as if the edge layer authenticates users by itself —
  Section 15.3 layer 2 (Django tokens always required) must be explicit to avoid a
  false sense of security (G-series Zero-Bleed discipline).
