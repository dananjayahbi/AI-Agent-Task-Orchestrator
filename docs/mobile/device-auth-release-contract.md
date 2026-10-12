# Device-token release contract (mobile client)

> Parent plan Sections 12.2, 14.2, 15.3 and ADR-006 remain the single source of
> truth; this document is the client-facing contract those sections fix for the
> Flutter app (WP-5.3 / MT-5.3-02). Open questions belong in the plan's Section 22
> (next free id: **OQ-15**), not in this file.

## Issuance

* `POST /api/v1/devices` (after Owner login, Section 12.2) registers the device
  and returns the device-bound token material **exactly once**, in the 201 body's
  `token` field.
* The server keeps only the SHA-256 hash (Section 7.2). It cannot show the
  plaintext again — a lost token must be revoked (`DELETE /devices/{id}`) and the
  device re-registered.
* The token expires per the Section 9.10 device lifetime (`expires_at` in the
  registration response and in `GET /devices`).

## Storage and release (Sections 12.2, 14.2; FR-MOB-06)

* Store the token in **platform secure storage only** — iOS Keychain / Android
  Keystore (or the flutter_secure_storage equivalent). Never in plain preferences,
  never in logs, never in analytics.
* The app must **release the token to outbound requests only after biometric
  success**. Cold start always requires unlock; a configurable inactivity timeout
  re-locks the token; OS-passcode fallback is the documented escape hatch
  (Section 14.2).
* Re-locking is local to the device (Section 15.3 layer 3) — it gates *use* of
  the stored value, it does not re-issue anything.

## Trust boundary — stated honestly (ADR-006; Section 15.3)

* The **server cannot verify that a biometric occurred.** Layer 3 is "local to
  the device": the server issues a token and trusts the app to guard it. Issuance
  is never biometric proof; do not read the `biometric_bound` registration flag
  as server-side verification — the server only records what the client reports.
* **Edge identity is never sufficient.** A request must carry the Django device
  bearer token (`Authorization: Bearer <token>`). Cloudflare Access identity
  headers (Section 15.3 layer 2) grant nothing by themselves, and the edge layer
  (WP-5.2) is a separate gate, not a substitute.
* Authentication re-reads the Device and token rows **on every request** (no
  cache): expiry and revocation take effect on the very next call.

## Rejection and recovery

* Invalid, expired or revoked device credentials are rejected with the Section
  9.2 catalog code `AUTH_REQUIRED` (401). Handle it by discarding the stored
  token and returning to the unlock/onboarding flow (Section 14.1) — never by
  silently falling back to an edge-only identity.
* Revocation is per device (Section 12.2): revoking one device never affects
  another device, agent tokens, or the Owner's sessions.

## Server-side coverage

`backend/tests/test_device_token_binding.py` pins the backend half of this
contract: one token per device, hash-at-rest, expiry enforced, structural
binding to its Device row, edge-header insufficiency, and the Section 12.2
"Device" authorization-matrix row.
