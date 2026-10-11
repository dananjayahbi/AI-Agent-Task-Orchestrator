# MT-5.2-03 — Add Edge and API Rate Limits

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.2-03 |
| Title | Add edge and API rate limits |
| Parent WP | WP-5.2 — Edge policies and route allowlist (Milestone M5) |
| Requirements | FR-SEC-05 |
| Priority | M |
| Dependencies | MT-5.2-02 (route allowlist in place) |
| Parent sections | 15.3, 12.1, 12.2, 19.1 (WP-5.2), 9.2, 20.4, 20.5 |

## Context
Section 15.3 layer 4: "Rate limits at both the edge and the API; anomaly alerts on
repeated auth failures." FR-SEC-05: rate limiting on all agent and device endpoints.
Section 12.1: token theft mitigated partly by rate limiting. Section 19 (WP-5.2)
deliverables include rate limits. The API layer already implements throttling in
WP-1.2 (MT-1.2-06, canonical `RATE_LIMITED`); this task adds the **edge** limits and
verifies the API limits work through the tunnel path.

## Inputs / Prerequisites
* MT-5.2-02 — allowlist so limits apply only to allowed routes.
* MT-1.2-06 — API-side rate limiting on agent and device endpoints (reuse; do not
  duplicate).
* Section 9.10 — rate-limit settings are environment-driven with documented
  defaults; `RATE_LIMITED` exists in the Section 9.2 catalog.
* WP-5.1 — tunnel in front of the API for remote traffic.

## Scope (in)
* Edge rate-limit rules on the tunnel hostname covering the exposed route groups —
  with particular attention to auth and device endpoints (Section 15.2 "Auth,
  devices" group) — configured in `infra/cloudflare/` with documented thresholds.
* Verification pass that the API-level throttles from MT-1.2-06 apply to requests
  arriving through the tunnel (client identity/header considerations: edge headers
  must not mask per-client counting — Section 15.3: edge identity is not
  authentication).
* Denial behavior: edge blocks per its configuration; API rejections return the
  canonical `RATE_LIMITED` envelope (Section 9.2, WP-0.5 conventions).
* Consistency checks: every Section 15.2-exposed group has a defined edge limit;
  thresholds documented with defaults in the repo.

## Out of scope
* Implementing Django throttling — WP-1.2 (MT-1.2-06).
* Anomaly **alerts** on repeated auth failures — observability/alerting work
  (Section 17); this task notes the dependency.
* Bot management/WAF products beyond rate limiting — not specified by the plan.
* LAN-path limits — Section 15.1 LAN is trusted development traffic; limits target
  the public hostname (documented).

## Target paths
* `infra/cloudflare/rate-limits.md` (edge rule definitions with documented defaults)
* `backend/tests/` integration check: API `RATE_LIMITED` response on the tunnel path
* WP changelog entry

## Acceptance criteria
- [ ] Edge rate limits are defined for every route group exposed by Section 15.2,
  with documented default thresholds (Section 15.3 layer 4; Section 20.4 item 3).
- [ ] Auth and device endpoints (FR-SEC-05) are covered by both edge and API limits
  — dual layer as Section 15.3 requires.
- [ ] An API-throttled request through the tunnel returns the canonical
  `RATE_LIMITED` envelope, proving WP-1.2 limits still apply behind the edge
  (Section 9.2; catalog code only, Section 20.4 item 5).
- [ ] Edge rules cannot be bypassed by edge-identity spoofing: API limits key off
  Django authentication context, not edge headers (Sections 12.2, 15.3).
- [ ] No secrets committed (item 3); changelog note added (item 7).

## Test command
`pytest backend/tests/test_rate_limits_tunnel.py -v` — asserts `RATE_LIMITED`
envelope for a throttled device/agent request via the configured tunnel-representing
client context; edge rule definitions verified by
`grep -c "limit" infra/cloudflare/rate-limits.md` plus review of the exposed-groups
coverage table.

## Attachments
* [Section 15.3 — Access control layers (rate limits at edge and API)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-SEC-05 — Rate limiting requirement](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.2 deliverables](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Double limiting (edge + API) can over-throttle legitimate mobile traffic on flaky
  networks — document chosen thresholds and how they were reasoned about; thresholds
  are not specified by the plan (record them as configuration choices, not facts).
* If the edge forwards requests without a stable client identifier, API-side
  throttling may collapse all remote clients into one bucket — verify the identity
  context used by MT-1.2-06 during the tunnel-path test; a mismatch needs a fix in
  WP-1.2's throttle keying, flagged here as a cross-WP note.
