# MT-1.2-04 — Create the Device Token Model for Mobile Registration

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.2-04 |
| Title | Create the device token model for mobile registration |
| Parent WP | WP-1.2 — Accounts, tokens and permissions (Milestone M1) |
| Requirements | FR-SEC-02, FR-SEC-05; ADR-006 |
| Priority | M |
| Dependencies | MT-1.2-02 (API Token model), MT-1.2-01 (owner session authenticates registration) |
| Parent sections | 7.1, 7.2, 9.2 (Devices row), 12.2, 19.1 (WP-1.2), 20.4, 20.5; ADR-006 |

## Context
WP-1.2's slice "device token model" prepares mobile authentication. Section 12.2:
mobile registers a device after Owner login and gets a device-bound token kept in
secure storage, released only after biometric success, independently revocable
(ADR-006 layered mobile auth). Section 7.2 defines the Device entity: `id`, `user_id`,
`platform`, `push_token`, `token_id` (FK to the API Token of kind `device`),
`biometric_bound`, `last_seen_at`, `revoked_at`. Section 9.2 gives `POST /devices`
and `DELETE /devices/{id}` with caller Mobile. This task creates the model plus the
two endpoints; biometric UX and push delivery are M5 concerns.

## Inputs / Prerequisites
* MT-1.2-02 — API Token model; devices use `kind = device` tokens linked by
  `token_id`.
* MT-1.2-01 — owner session; registration happens after Owner login (Section 12.2).
* Parent plan Section 7.2 — Device entity fields, verbatim.
* Parent plan Section 9.2 — Devices endpoints, caller Mobile.
* Parent plan Section 12.2 — device registration after Owner login; device-bound
  token; independent revocation.
* Parent plan Section 12.4 — data protection (tokens in secure storage client-side;
  server stores what the model requires).

## Scope (in)
* Create the Device model with exactly the Section 7.2 fields, in its own migration
  (Section 20.3).
* Implement `POST /devices`: authenticated as Owner (session) plus payload carrying
  `platform` and `push_token`; create the Device row and an associated `kind = device`
  API Token (hashed, with `expires_at` per Section 9.10); return the device-bound
  token plaintext once to the mobile client for secure storage (Section 12.2).
* Implement `DELETE /devices/{id}`: revokes the device (`revoked_at`) **and** its
  linked API Token in one action — losing a phone must independently revoke access
  (Section 12.2, threat "Lost phone").
* Set `biometric_bound` from the registration payload/contract as defined by
  Section 12.2 (server records the flag; enforcing biometrics is client-side, M5).
* Maintain `last_seen_at` on authenticated device use.
* Document endpoints in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Push notification dispatch/FCM — WP-5.x (Section 9.8).
* Biometric unlock UI and secure storage — Flutter app, WP-5.x (FR-MOB-06).
* Edge access policy — WP-3.x (Section 15.3).
* Rate limiting — MT-1.2-06 (device endpoints are explicitly in FR-SEC-05's scope;
  this task ensures the endpoints exist so MT-1.2-06 can throttle them).
* The Device row's relationship to notifications delivery — WP-5.x consumes it.

## Target paths
* `backend/apps/accounts/` — Device model, register/revoke endpoints
* `backend/` — migration for the Device model only
* `backend/tests/` — registration, one-time token, combined revocation tests
* `schemas/` — OpenAPI snapshot updated
* WP changelog entry

## Acceptance criteria
- [ ] Device model fields match Section 7.2 exactly; standalone migration
  (Section 20.3; Section 18 migration check).
- [ ] `POST /devices` creates Device + `kind = device` API Token; plaintext returned
  once, stored hashed only (Section 7.2; FR-SEC-02).
- [ ] `DELETE /devices/{id}` revokes device and token together; the token fails
  immediately afterwards (Section 12.2 lost-phone control; FR-SEC-02).
- [ ] The device token is a distinct kind from owner sessions and agent tokens
  (FR-SEC-02: distinct token kinds, each revocable).
- [ ] `last_used_at` / `last_seen_at` maintained per Section 7.2.
- [ ] OpenAPI snapshot updated (item 4); catalog error codes only (item 5);
  tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests -k device` covering: registration
creates both rows with only hashed secrets, deleting the device makes its token fail
authentication on the next call, and a non-Owner/non-authorized caller is rejected with
a catalog code.

## Attachments
* [Section 7.2 — Entities (Device, API Token)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization (mobile)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-006 — Layered mobile auth](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `push_token` is sensitive (Section 12.4) — ensure it never appears in logs (Section
  17 scrubbing, MT-1.1-02) or list responses beyond the owner's own device view.
* The plan does not spell out the `POST /devices` request/response shape beyond the
  caller — define it minimally from Section 12.2, fix it in the OpenAPI snapshot, and
  flag any ambiguity (e.g. how `biometric_bound` arrives) rather than guessing twice.
