# MT-1.2-06 — Add Rate Limiting on Agent and Device Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-06 |
| Title | Add rate limiting on agent and device endpoints |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-05, NFR-07 |
| Priority | S |
| Dependencies | MT-1.2-03 (agent endpoints), MT-1.2-04 (device endpoints), MT-1.2-05 (auth context for keyed throttling), MT-0.5-02 (`RATE_LIMITED` catalog code) |
| Parent sections | 9.1 (`core` owns rate limiting), 9.10, 12.1, 12.3, 19.1 (WP-1.2), 20.4, 20.5 |

## Context
FR-SEC-05 (priority S) requires rate limiting on all agent and device endpoints; the
Section 12.1 threat model lists token theft with "rate limited" among mitigations, and
Section 12.3's access-control layers include "rate limits at both the edge and the
API" (the edge half is WP-3.x). Section 9.1 assigns rate limiting to the `core`
module; Section 9.10 lists rate limits among the environment-driven configuration
groups. Exceeding a limit returns `RATE_LIMITED`, which already exists in the Section
9.2 error catalog.

## Inputs / Prerequisites
* MT-1.2-03/04 — the agent and device endpoints to throttle (issuance, revocation,
  device register/revoke; work/claim/checkpoint endpoints join as WP-1.4/1.6 land —
  apply the rule by endpoint class, not by a frozen list).
* MT-1.2-05 — authenticated caller identity (token id/kind) so throttling can be keyed
  per token rather than per IP where the caller is authenticated.
* Parent plan Section 9.1 — `core` module responsibility: rate limiting.
* Parent plan Section 9.10 — rate limits are configuration with documented defaults.
* Parent plan Section 9.2 — `RATE_LIMITED` is a canonical error code; envelope
  (MT-0.5-02) wraps it.

## Scope (in)
* Implement API-side throttling in the `core` module applied to every agent-facing and
  device-facing endpoint (Section 9.2 caller columns: Agent, Auditor, Bridge, Mobile),
  keyed on the authenticated token where available and on client address otherwise.
* Make limits and windows configuration-driven via Section 9.10 settings, with
  documented defaults — thresholds are not fixed in the plan, so choose conservative
  defaults, document them, and flag them in the changelog for owner confirmation
  (Section 20.1 item 5).
* Return the standard error envelope with code `RATE_LIMITED` (Section 9.2) and an
  appropriate HTTP status per the catalog's mapping in the OpenAPI document.
* Tests: under-limit requests pass; over-limit requests return `RATE_LIMITED`; owner
  session endpoints are not throttled by this rule (FR-SEC-05 scope is agent and
  device endpoints only — do not silently widen it).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Edge rate limits (Cloudflare) — WP-3.x (Section 15.3; WP-3.1's "rate limits"
  deliverable).
* Anomaly alerts on repeated auth failures — Section 17 alerts (M6 operational WPs).
* Throttling web/owner endpoints — not required by FR-SEC-05; note as out of scope
  rather than adding scope.
* Redis/Celery infrastructure — reuse whatever the settings/cache config already
  provides (Section 9.10 cache URLs); do not stand up new services.

## Target paths
* `backend/apps/core/` — throttling classes/policies and settings wiring
* `backend/` — endpoint classes hooked to throttling
* `backend/tests/` — throttle behavior tests
* `schemas/` — OpenAPI snapshot updated if `RATE_LIMITED` responses are annotated
* WP changelog entry

## Acceptance criteria
- [ ] Every Section 9.2 endpoint whose caller is Agent/Auditor/Bridge/Mobile is
  throttled; a test enumerates those endpoints and asserts throttling applies
  (FR-SEC-05: *all* agent and device endpoints).
- [ ] Exceeding the limit returns the standard envelope with catalog code
  `RATE_LIMITED` (Section 9.2; Section 20.4 item 5).
- [ ] Limits/windows are configurable via Section 9.10 settings with documented
  defaults; no magic numbers in code paths (Section 9.10).
- [ ] Owner-session endpoints are not affected (FR-SEC-05 scope respected).
- [ ] Tests, lint, type check green (item 2); OpenAPI reflects the 429 response where
  applicable (item 4).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k "ratelimit or throttle"` covering: burst over the
configured limit yields `RATE_LIMITED` in the canonical envelope, reset after window
allows requests again, and an endpoint-coverage test asserting the throttle hook exists
on all agent/device routes.

## Attachments
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.3 — Access control layers](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.2](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Numeric limits are unspecified in the plan — defaults chosen here directly affect
  NFR-02-adjacent behavior (legit agents under load). Keep defaults permissive enough
  for the Section 18 performance scenario (20 agents, checkpoints every 30 s) and
  record the calculation in the changelog.
* Throttling keyed by IP breaks behind the tunnel/proxy if the client address is not
  forwarded correctly — verify keying with authenticated tokens preferred (Section
  12.3's layered intent).
