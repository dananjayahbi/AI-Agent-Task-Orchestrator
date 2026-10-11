# MT-5.2-01 — Define the Cloudflare Access Policy for the Tunnel Hostname

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.2-01 |
| Title | Define the Cloudflare Access policy for the tunnel hostname |
| Parent WP | WP-5.2 — Edge policies and route allowlist (Milestone M5) |
| Requirements | FR-NET-01, FR-SEC-05 |
| Priority | M |
| Dependencies | MT-5.1-04 (WP-5.1 complete; tunnel serving the hostname) |
| Parent sections | 15.3, 15.1, 12.2, 19.1 (WP-5.2), ADR-006, 20.4, 20.5 |

## Context
Section 15.3 (ADR-006) layer 1: "Cloudflare Access policy on the hostname (identity
or service token) as the edge gate," with layer 2 stating Django device/agent tokens
are always required — edge identity headers are never trusted as authentication on
their own. Section 19 (WP-5.2) deliverables: policy definitions. The tunnel hostname
(e.g. `orchestrator.<domain>`, OQ-11) is the only public surface (FR-NET-01, no
inbound ports).

## Inputs / Prerequisites
* WP-5.1 complete (MT-5.1-03) — tunnel hostname configured and documented.
* Parent plan Section 15.3 — the four access-control layers; this task is layer 1.
* Parent plan Section 12.2 — "Cloudflare: edge access policy is the first gate for
  the tunnel hostname; the Django token is always still required."
* Section 15.2 route groups — the policy must coexist with the per-route rules that
  MT-5.2-02 enforces.
* Cloudflare account/domain availability per OQ-11 (Owner-supplied).

## Scope (in)
* A written and reproducible Cloudflare Access policy definition for the tunnel
  hostname: who may pass the edge gate (Owner identity; service tokens for the
  remote-agent/Merge-Executor scenarios of Section 15.2), applied to the hostname.
* Policy stored as configuration/documentation in the repo (`infra/cloudflare/`) so
  it survives dashboard drift; dashboard application steps documented (the actual
  Cloudflare-side apply is an operational step, verified by MT-5.2-04).
* Explicit statement of the layering rule: the Access policy is the **first** gate
  only; Django token authentication remains mandatory (Section 12.2/15.3) — the
  policy must not be configured as "bypass origin auth."
* Verification hooks: named checks that MT-5.2-04 executes (unauthenticated request
  from the public hostname is challenged/denied at the edge).

## Out of scope
* Route-level allow/deny per endpoint — MT-5.2-02 (Section 15.2 table).
* Rate limits — MT-5.2-03.
* The Django authentication itself — WP-1.2 / WP-5.3.
* LAN access path — Section 15.1: the LAN address bypasses the edge by design.
* Tunnel/ingress configuration — WP-5.1.

## Target paths
* `infra/cloudflare/access-policy.md` (policy definition + application steps)
* `infra/cloudflare/` supporting configuration notes
* WP changelog entry

## Acceptance criteria
- [ ] The policy defines the edge gate for the tunnel hostname with the allowed
  principals (Owner identity; service tokens where Section 15.2 requires them)
  — Section 15.3 layer 1 (Section 20.5: no principals invented beyond the plan).
- [ ] The documentation states that Django device/agent tokens remain always
  required — edge identity is not authentication (Section 12.2, ADR-006).
- [ ] Policy is versioned in `infra/cloudflare/` with reproducible application steps
  (Section 19 WP-5.2 deliverable: policy definitions).
- [ ] Named verification checks are listed for MT-5.2-04's checklist.
- [ ] No secrets committed (Section 20.4 item 3 — tunnel/service token IDs are
  references, not values); changelog note added (item 7).

## Test command
Documentary task: verify by review plus `grep -i "always required\|first gate" infra/cloudflare/access-policy.md`
confirming the layering statement, and confirm every Section 15.3 layer 1 principal
appears in the policy file; execution checks run in MT-5.2-04.

## Attachments
* [Section 15.3 — Access control layers (ADR-006)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.1 — Topology](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-006 — Layered mobile auth](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Cloudflare dashboard configuration is external state — the repo file is the source
  of truth and MT-5.2-04's checklist is the drift detector; schedule the checklist
  run after any dashboard change.
* Over-broad Access policies (e.g. "authenticate everyone in the domain") weaken the
  model silently — the policy must name the exact principals; flag anything broader
  in review as a security finding (FR-SEC-05 context).
