# MT-5.3-02 — Implement Device-Bound Token Issuance and Release After Biometric Success

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.3-02 |
| Title | Implement device-bound token issuance and release after biometric success |
| Parent WP | WP-5.3 — Device registration and mobile authentication (Milestone M5) |
| Requirements | FR-SEC-02, FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.3-01 (device registration endpoints) |
| Parent sections | 12.2, 14.2, 15.3, 9.2, 19.1 (WP-5.3), ADR-006, 20.4, 20.5 |

## Context
Section 12.2: the device-bound token is "kept in secure storage and released only
after biometric success; independently revocable." Section 14.2: the app token lives
in platform secure storage and is unlocked only after biometric success — cold start
and a configurable inactivity timeout both require unlock, with OS-passcode fallback.
Section 15.3 layer 3: biometric unlock is local to the device. ADR-006: edge policy +
device-bound token + biometric, no single point of failure. FR-MOB-06: biometric
unlock and secure token storage. Section 19 (WP-5.3): token binding is a deliverable.

## Inputs / Prerequisites
* MT-5.3-01 — registered device record to bind against.
* MT-1.2-04 — device token model (hashed at rest, expiry fields); MT-1.2-05 auth
  classes accepting device tokens (Section 12.2 authorization matrix "Device" row).
* Parent plan Section 14.2 — the client-side release contract this server side must
  support.
* Section 15.3 — Django device tokens always required regardless of edge identity.

## Scope (in)
* Backend issuance: on successful registration/login completion, issue a token bound
  to the specific device record (per-device identifier in the token's validation
  context), stored hashed (Section 12.2 token-theft mitigation), independently
  revocable (MT-5.3-03).
* The release contract documented for the mobile client: the token value is handed
  to the app exactly once at issuance and the app must hold it in platform secure
  storage, exposing it to requests only after biometric success (Sections 12.2,
  14.2) — server-side, this means tokens authenticate device requests (matrix row)
  and nothing weaker (no edge-header trust, Section 15.3).
* Token lifecycle: expiry fields enforced, hashing at rest, canonical rejection
  (`AUTH_REQUIRED`/`AUTH_FORBIDDEN` family from the Section 9.2 catalog) for invalid
  or expired device tokens.
* Tests: token is bound (valid for its device, rejected when presented as another
  device's), hashed at rest (plaintext never stored), expiry enforced, device
  requests authorized per the Section 12.2 matrix "Device" row.

## Out of scope
* Flutter secure-storage and biometric UI implementation — WP-5.x mobile app
  (Section 14.2); this task fixes the server contract those screens build against.
* Revocation — MT-5.3-03.
* Device list/revoke UI — MT-5.3-04.
* Edge Access gate and rate limits — WP-5.2.
* Owner password/TOTP strength — OQ-09 (owner auth, WP-1.2).

## Target paths
* `backend/apps/accounts/` (device token issuance and validation)
* `backend/tests/accounts/test_device_token_binding.py`
* Contract notes for the mobile client (device-auth section of the API docs)
* WP changelog entry

## Acceptance criteria
- [ ] A device token is issued per registered device, stored hashed, with expiry
  enforced (Section 12.2; Section 19 WP-5.3 deliverable: token binding).
- [ ] Binding is enforced: a token issued for device A is rejected for device B
  (device-bound, ADR-006/FR-SEC-02).
- [ ] The release contract (secure storage + biometric-gated use, cold start and
  inactivity re-lock per Section 14.2) is documented for the client and reflected in
  the token validation expectations (FR-MOB-06).
- [ ] Device requests authenticate via the Django token only — edge identity is never
  sufficient (Section 15.3 layer 2; Section 12.2).
- [ ] OpenAPI/schema diff reviewed (Section 20.4 item 4); error codes from the
  catalog (item 5); changelog note added (item 7).

## Test command
`pytest backend/tests/accounts/test_device_token_binding.py -v` — binding,
hash-at-rest, expiry, and Section 12.2 "Device" matrix-row authorization cases.

## Attachments
* [Section 12.2 — Authentication and authorization (mobile)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.2 — Mobile-specific behaviors (biometric gate)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-006 — Layered mobile auth](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The server cannot verify a biometric happened — it can only issue a token the app
  guards locally. The plan accepts this (layer 3 is "local to the device",
  Section 15.3); document the trust boundary honestly so review does not mistake
  issuance for biometric proof.
* How the device proves which device it is at issuance (registration step vs. a
  separate credential) is not spelled out beyond "device registration after Owner
  login" (Section 12.2) — if a stronger device attestation is expected, raise a new
  OQ (`OQ-15+`) rather than inventing an attestation scheme.
