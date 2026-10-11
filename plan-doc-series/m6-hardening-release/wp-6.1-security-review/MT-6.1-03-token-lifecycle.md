# MT-6.1-03 — Audit Token Lifecycle (Scoping, Expiry, Revocation, Hashing)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.1-03 |
| Title | Audit token lifecycle (scoping, expiry, revocation, hashing) |
| Parent WP | WP-6.1 — Security review (Milestone M6) |
| Requirements | NFR-07, FR-SEC-01, FR-SEC-02 |
| Priority | M |
| Dependencies | MT-1.2-02, MT-1.2-03, MT-1.2-04 (token models/issuance), MT-5.3-02, MT-5.3-03 (device-bound tokens, revocation), MT-2.12-02 (bridge token storage), MT-6.1-01 (findings log) |
| Parent sections | 12.1 (token theft threat), 12.2 (token kinds for agents/mobile/owner), 15.3 (edge + Django tokens), 18 (Security row: token scoping), 19 (WP-6.1 acceptance), 20.4, 20.5; ADR-004, ADR-006 |

## Context
Section 12.1's "Token theft" threat prescribes the properties to verify:
project-scoped, revocable, hashed at rest, expiring, rate limited. Section 12.2
defines the three token kinds — Owner session (CSRF-protected cookies), long-lived
but revocable project-scoped agent bearer tokens, device-bound mobile tokens
released only after biometric success — with independent revocation for devices.
Section 19 (WP-6.1) acceptance names **token scoping tests in CI** explicitly, and
RISK-14 (token leakage) makes hashing/scrubbing part of the same story. This slice
audits the full lifecycle across those kinds and turns each property into a
CI-enforced assertion.

## Inputs / Prerequisites
* MT-1.2-02/03/04 — agent token issuance, device token model, hashing storage as
  built; MT-1.2-05/06 — permission classes and rate limiting.
* MT-5.3-02/03 — device-bound token release on biometric success and revocation
  with immediate rejection; MT-2.12-02 — bridge user-level token storage.
* Parent plan Section 12.1/12.2 — the property list and token-kind table to audit.
* Parent plan Section 15.3 — layering: edge identity headers are never trusted as
  authentication on their own (the Django token is always required).
* MT-6.1-01 — findings log, severity scale and mapping to update.
* Fixture identities for all six Section 12.2 actors.

## Scope (in)
* Lifecycle tests per token kind, asserted end to end:
  * **Scoping:** an agent token can only touch its own project — cross-project
    reads/claims rejected at the backend (FR-SEC-01; Section 12.1 cross-project
    leakage), even with a crafted project parameter (the bridge has no project
    parameter; the backend is the second barrier — FR-MCP-06/ADR-004).
  * **Expiry:** expired agent/device tokens are rejected with a canonical error;
    owner session expiry behaves per Section 12.2 (Section 9.2 codes).
  * **Revocation:** revoked device rejected on next request **and** stream
    reconnect (Section 19 WP-5.3 acceptance re-verified); revoked agent token
    rejected immediately; each revocation writes an audit Event (Section 12.5).
  * **Hashing:** tokens stored hashed at rest — assert the database contains no
    plaintext token value for any kind (Section 12.1 token theft).
  * **Kind separation:** owner session, agent and device credentials are not
    interchangeable — each rejected where another kind is required (FR-SEC-02).
  * **Biometric release:** the device token is accessible to app logic only after
    unlock success (Section 12.2, ADR-006) — as far as a backend-plus-app test can
    assert; record the client-side limits honestly.
  * **Rate limiting:** repeated auth/token endpoint failures trip `RATE_LIMITED`
    (FR-SEC-05; Section 12.1 "rate limited") — coordinate with MT-6.1-01's check;
    assert once here in the lifecycle context if not already covered.
* Edge-layer review by pointer: confirm Section 15.3 layering is documented and
  MT-5.2-01/04 cover it; assert that an edge identity header alone never
  authenticates a request (header spoof rejected without a Django token).
* Append results to the threat-to-test mapping and findings log; fix or file
  high/critical gaps.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Re-implementing token models — WP-1.2/WP-5.3 deliver them; this audits them.
* The other review slices — MT-6.1-01/02/04/05 (shared log only).
* Bridge-side storage hardening beyond asserting redaction — MT-2.1-03 owns
  redaction; reference its tests.
* Key rotation runbooks — MT-6.5-03 (Section 17 "rotate tokens" runbook) links the
  verified behavior from here.

## Target paths
* `backend/tests/` — token lifecycle security suite (scoping, expiry, revocation,
  hashing, kind separation, rate limit)
* `docs/plan/security-threat-test-mapping.md` (token theft / cross-project rows
  updated)
* `docs/plan/security-findings-log.md` (findings appended)
* WP changelog entry

## Acceptance criteria
- [ ] Token scoping tests run in CI covering cross-project rejection for agent
  tokens — Section 19 WP-6.1 acceptance "token scoping and traversal tests in CI"
  (FR-SEC-01; ADR-004).
- [ ] Expiry and revocation asserted for agent and device tokens, including the
  device's stream-reconnect rejection (Section 19 WP-5.3 acceptance re-verified;
  FR-SEC-02).
- [ ] Hash-at-rest verified: no plaintext token values in the database for any token
  kind (Section 12.1).
- [ ] Kind separation and edge-header non-trust verified per Section 12.2/15.3.
- [ ] `RATE_LIMITED` observed on repeated auth failures (FR-SEC-05).
- [ ] Mapping and findings log updated; zero open critical/high from this slice;
  tests green in CI (Sections 19, 20.4); changelog note added (item 7).

## Test command
`pytest backend/tests/ -k token_lifecycle -v` — scoping, expiry, revocation,
hashing, kind-separation and rate-limit assertions all pass; then check
`docs/plan/security-findings-log.md` has no open critical/high entries from this
slice and the mapping's token-theft row cites these tests.

## Attachments
* [Section 12.1 — Threat model (token theft)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Biometric release" is enforced in the mobile app's secure storage, not the
  backend — the testable claim is bounded; overclaiming it as a backend guarantee
  would misstate the threat model (ADR-006's honest layering).
* Hashing assertions must not defeat legitimate lookup designs — if tokens are
  looked up by a derived index, verify the stored form is non-reversible rather
  than asserting a specific schema, so the test tracks the property, not the
  implementation.
* Long-lived agent tokens are by design (Section 12.2) — expiry tests cover the
  configured lifetime, not a hypothetical short one; record the configured values so
  the audit result is tied to real settings.
