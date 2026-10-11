# MT-6.6-03 — Reconnect Tunnel, Manifests, and Agent Tokens

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.6-03 |
| Title | Reconnect tunnel, manifests, and agent tokens |
| Parent WP | WP-6.6 — VPS migration rehearsal and v1 release (Milestone M6) |
| Requirements | NFR-06, FR-NET-01, FR-NET-02, FR-SEC-01 |
| Priority | M |
| Dependencies | MT-6.6-02 (stack up with restored data), WP-5.1/5.2 (tunnel and edge policies), WP-2.2 (manifest binding), MT-6.5-01/02 (documented reconnect steps) |
| Parent sections | 1.4 (success criterion 5), 5.2 (NFR-06), 10.3 (manifest discovery), 12.2 (agent tokens), 15.1–15.4 (tunnel), 16.4 (VPS checklist, steps 4–5), 19 (WP-6.6), 20.4, 20.5; 21 (RISK-05, RISK-14); Appendix A |

## Context
Section 16.4 steps 4 and 5: "Point the tunnel to the new host (or move the
connector); update `orchestrator_api` in manifests (or rely on tunnel hostname)" and
"Reissue agent tokens if the secret key changed; update bridge configs." This slice
reconnects the outside world to the migrated stack: remote access via the outbound
Cloudflare tunnel (FR-NET-01 — still no inbound ports), project manifests resolving
to the right API, and agent tokens valid under the VPS's secret key. Success criterion
5's "configuration changes only" bar applies here too — the tunnel, manifest and
token changes are environment/config artifacts, never code edits.

## Inputs / Prerequisites
* MT-6.6-02 — restored stack running and ready on the VPS.
* Parent plan Section 16.4 steps 4–5 — verbatim procedure this task executes.
* Parent plan Section 15.1/15.4 — tunnel topology (outbound-only `cloudflared` as a
  Compose service, ingress rules) and operations: tunnel token is a secret in the
  environment, rotated through the Cloudflare dashboard.
* Parent plan Section 15.2/15.3 — route policy on the tunnel hostname and the layered
  access control (edge policy first, Django tokens always required) that must hold
  identically on the VPS.
* Parent plan Section 10.3 — manifest upward discovery, `orchestrator_api` field,
  mismatch aborts: what must be updated and what a wrong value breaks.
* Parent plan Section 12.2 — project-scoped, revocable, hashed agent tokens; secret
  key change invalidates them (Section 16.4 step 5's condition).
* MT-6.5-01/02 — the documented reconnect/agent-config steps; the rehearsal runs
  from the docs.

## Scope (in)
* Point the tunnel at the new host: move/reconfigure the connector per Section 16.4
  step 4, with the tunnel token supplied through the environment (Section 15.4) —
  verify ingress reaches backend and web, and that the Section 15.2 route policy is
  intact (agent work endpoints still service-token-gated; health still internal;
  no new exposure).
* Update `orchestrator_api` in the project manifests per Section 10.3 — or confirm
  the tunnel-hostname path makes the change unnecessary (the checklist offers both;
  record which was used and why). Validate with a manifest-driven connect so
  mismatch aborts would have fired if wrong.
* Assess whether the VPS secret key differs from the laptop's: if it does, reissue
  agent tokens (Section 16.4 step 5) and update bridge configs (user-level config,
  never in-repo — Section 12.2; RISK-14); if it doesn't, record that tokens carried
  over and verify one still authenticates. Device/owner sessions re-login as needed.
* Verify the access layers end to end from a remote client: edge policy gate, then
  Django token (Section 15.3 layering), CORS/CSRF trusted-origin lists updated for
  the new hostname (Section 15.4), SSE stays alive through the tunnel (15 s
  heartbeat, RISK-05).
* Append to the rehearsal log: tunnel/manifest/token steps, which checklist branches
  were taken, verification results, deviations and fixes (Section 19 WP-6.6
  deliverables).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Provisioning and restore — MT-6.6-01/02.
* Running the smoke suite — MT-6.6-04 (this slice proves connectivity and auth;
  scenarios follow).
* Changing route policy or edge rules beyond restoring the existing Section 15.2/15.3
  configuration — security posture is not this rehearsal's to redesign.
* Rotating the Cloudflare tunnel token preventively — only if the migration requires
  it (Section 15.4 rotation is a dashboard operation; record if performed).
* Updating code, manifests schema, or bridge source — config values only
  (Section 1.4 criterion 5).

## Target paths
* Host environment (outside Git) — tunnel token, hostname and connection settings
  (Section 16.4 steps 4–5)
* Project manifest `orchestrator_api` values — configuration change per Section 10.3
  (as recorded in the rehearsal log; manifests live with the projects, not this repo)
* Bridge user-level config (outside the repo) — updated agent tokens if reissued
* `docs/plan/` — rehearsal log (appended: reconnect steps and evidence)
* WP changelog entry

## Acceptance criteria
- [ ] The tunnel routes to the VPS host with the Section 15.2 route policy and 15.3
  layering intact — remote web/API/SSE reachable, privileged routes still blocked,
  no inbound ports opened (Section 16.4 step 4; FR-NET-01/02).
- [ ] Manifests resolve correctly to the VPS (`orchestrator_api` updated or
  tunnel-hostname branch recorded), confirmed by a successful manifest-driven
  connect with mismatch detection still active (Section 16.4 step 4; Section 10.3).
- [ ] Agent token state is correct and recorded: reissued-and-updated if the secret
  key changed, or verified-valid if not — with at least one real authenticated
  agent call succeeding (Section 16.4 step 5; Section 12.2).
- [ ] CORS/CSRF trusted origins include only the known origins for the new hostname
  (Section 15.4); no secret values written to the repo or log (Section 20.4 item 3).
- [ ] SSE verified alive through the tunnel (heartbeat, no buffering) — RISK-05,
  Section 15.4.
- [ ] No tracked-file edits for any of the above (Section 1.4 criterion 5);
  rehearsal log appended with steps, branches and fixes (Section 19 WP-6.6);
  changelog note added (item 7).

## Test command
From a remote network (not the VPS LAN), open the tunnel hostname: owner login
succeeds through the edge gate; a bridge connect with a project manifest completes
orient against the VPS; an agent token (reissued or carried over, as recorded)
authenticates one claim/checkpoint call; SSE stays connected past several 15 s
heartbeats; confirm `git status` shows no tracked-file changes and the rehearsal log
contains the reconnect evidence.

## Attachments
* [Section 16.4 — VPS migration checklist (steps 4–5)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15 — Remote Connectivity (Cloudflare)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Secret-key divergence is the silent killer: if the VPS generated a new key and
  tokens were *not* reissued, everything looks fine until the first agent call
  401s — decide the branch explicitly, verify with a real call, and record the
  decision (Section 20.4 item 1).
* Moving the connector can strand the old host's tunnel or leave split routing —
  confirm which host the public hostname actually resolves to before declaring the
  step done (RISK-05).
* Reissued tokens are credentials: they land in the user-level bridge config only,
  never the repo, never the log; the rehearsal log records *that* reissue happened,
  not the values (Section 12.2; RISK-14; Section 20.4 item 3).
* Trusting the edge alone would violate ADR-006 — retest that Django tokens are
  still required end to end; an edge-only pass means the layering silently broke
  during the move (Section 15.3).
