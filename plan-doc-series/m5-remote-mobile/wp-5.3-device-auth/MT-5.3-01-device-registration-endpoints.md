# MT-5.3-01 — Implement Device Registration Endpoints

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.3-01 |
| Title | Implement device registration endpoints |
| Parent WP | WP-5.3 — Device registration and mobile authentication (Milestone M5) |
| Requirements | FR-SEC-02, FR-MOB-06 |
| Priority | M |
| Dependencies | MT-1.2-07 (WP-1.2 complete; device token model and auth classes exist) |
| Parent sections | 9.2, 12.2, 14.1, 15.3, 19.1 (WP-5.3), ADR-006, 20.4, 20.5 |

## Context
Section 12.2: "Mobile: device registration after Owner login; device-bound token kept
in secure storage and released only after biometric success; independently
revocable." Section 9.2 exposes `POST /devices` and `DELETE /devices/{id}` (caller:
Mobile). Section 14.1 onboarding: server URL entry, login, device registration,
biometric enrollment. Section 19 (WP-5.3): deliverables are device endpoints, token
binding, revoke from web UI, tests; depends on WP-1.2 (device token model created in
MT-1.2-04). ADR-006: layered model — edge policy, device-bound token, biometric.

## Inputs / Prerequisites
* MT-1.2-04 — the device token model (hashed storage, expiry) from WP-1.2.
* MT-1.2-05/MT-1.2-07 — permission classes and matrix tests (registration runs under
  an authenticated Owner session).
* Parent plan Section 9.2 — endpoint paths and caller.
* Section 15.2 — "Auth, devices" is exposed through the tunnel (this flow works
  remotely); the Access gate (MT-5.2-01) sits in front.
* Section 14.1 — the mobile onboarding sequence this serves.

## Scope (in)
* `POST /devices`: registers a device for the authenticated Owner (Owner login
  precedes registration — Section 12.2), storing device metadata (per Section 14.1
  device info surfaced later in settings) and issuing the device credential record;
  returns the device-bound token material per the MT-5.3-02 contract.
* `DELETE /devices/{id}` present per Section 9.2 (the revocation action itself is
  implemented in MT-5.3-03; register the route here so the API surface matches
  9.2 — behavior completed by MT-5.3-03).
* Registration events written via the MT-1.9-02 helper (Section 12.5: token/device
  events are audit-relevant — subject to the token-event OQ raised in MT-1.9-02;
  do not invent a catalog type).
* Idempotency and canonical errors per Section 9.2/WP-0.5; OpenAPI updated with
  schema diff reviewed (Section 20.4 item 4).

## Out of scope
* Device-bound token issuance mechanics and biometric release contract — MT-5.3-02.
* Revocation semantics (immediate rejection) — MT-5.3-03.
* The web device list/revoke UI — MT-5.3-04.
* Flutter onboarding screens — WP-5.x mobile app (Section 14.1).
* The Cloudflare Access gate in front — WP-5.2.
* `GET /devices` listing — not present in Section 9.2; see risk notes (OQ needed
  before MT-5.3-04).

## Target paths
* `backend/apps/accounts/views.py` (device registration routes)
* `backend/apps/accounts/urls.py`
* `backend/tests/accounts/test_device_registration.py`
* WP changelog entry

## Acceptance criteria
- [ ] `POST /devices` registers a device only for an authenticated Owner session
  (Section 12.2: "device registration after Owner login"); unauthenticated calls
  return a canonical error (Section 9.2).
- [ ] The endpoint matches the Section 9.2 surface exactly — no invented routes
  (Section 20.5).
- [ ] Registration is reachable through the tunnel (auth/devices group allowed,
  Section 15.2) — cross-check with MT-5.2-04's checklist.
- [ ] Registration writes an audit-relevant event via the established helper without
  inventing a catalog type (Section 12.5; Section 20.4 item 6 — token-event OQ
  pending).
- [ ] OpenAPI updated with schema diff reviewed (item 4); error codes from the
  catalog (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/accounts/test_device_registration.py -v` — Owner-session
requirement, device record creation, canonical error cases, audit-event assertion.

## Attachments
* [Section 9.2 — REST API surface (Devices endpoints)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization (mobile)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-006 — Layered mobile auth](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 9.2 lists no `GET /devices`, yet Section 13.1 account settings require
  "devices (list and revoke)" for MT-5.3-04 — the list endpoint must be added by
  amending Section 9.2 first (new OQ, next free `OQ-15+` id in Section 22). Do not
  add the route silently in this task.
* Registration must bind the new device to the Owner who registered it (no
  cross-account binding) — the plan says "after Owner login"; assert owner
  association in tests.
