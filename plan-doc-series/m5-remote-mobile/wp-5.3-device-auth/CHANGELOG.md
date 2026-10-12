# WP-5.3 — Device registration and mobile authentication: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

### MT-5.3-01 — device registration endpoints (verified + hardened)

- Surface verification landed in `backend/tests/test_device_registration_surface.py`
  (flat path — deviation from the MT's `tests/accounts/` wording; WP-1.2 landed flat
  and the suite stays one layout): owner-session guard, Section 9.2 surface exactness
  (documented verbs only; `MethodNotAllowed`/`NotFound` map to the catalog's
  `VALIDATION_ERROR`), catalog-code assertions, throttle wiring on both routes.
- `POST /devices` now honors the Section 9.2 rule that all mutating endpoints accept
  `Idempotency-Key` (ADR-012): same key + same body replays the original 201
  **byte-identically** (the outcome is stored through DRF's own JSON encoder — the
  shared store's `default=str` fallback would have rewritten `expires_at`); different
  body under the same key executes normally (headers.md leaves mismatch open — no
  invented error); no key = always execute. Header declared in OpenAPI.
- Deferred (not invented): the audit event — the MT-1.9-02 helper and a Section 9.6
  device/token catalog type do not exist yet (pending token-event OQ). Tunnel
  reachability is WP-5.2 infra; cross-checked against MT-5.2-02's allowlist
  (Section 15.2 exposes the auth/devices group) — nothing backend-side to run.

### MT-5.3-02 — device-bound token issuance + release contract

- `backend/tests/test_device_token_binding.py`: one hashed token per device
  (distinct rows/hashes), hash-at-rest, expiry enforced on the next request,
  binding enforced (revoked sibling and orphaned-device credentials both fail
  closed with `AUTH_REQUIRED`), edge identity headers alone grant nothing
  (Section 15.3 layer 2), and the Section 12.2 "Device" matrix row asserted at
  permission-class level (complementary to the shared matrix file, which stays
  owned elsewhere — see the wave-gate follow-ups in the WP report).
- Release contract for the mobile client: `docs/mobile/device-auth-release-contract.md`
  — secure storage, biometric-gated release, cold start + inactivity re-lock,
  OS-passcode fallback, exact-once issuance, and an honest trust boundary (the
  server cannot verify a biometric; issuance is not biometric proof).

### MT-5.3-03 — revocation with immediate rejection

- `backend/tests/test_device_revocation.py`: revoked device rejected on its very
  next REST request (`AUTH_REQUIRED`, both rows stamped); revocation independent
  (other device, agent token, Owner session all survive); only the owning Owner
  can revoke (foreign/unknown/anonymous denials from the catalog); idempotent
  repeat returns the original `revoked_at`.
- **Chosen live-SSE-connection semantics:** reject-on-next-use. The auth path
  re-reads the Device + token rows per request (no cache), so any reconnect after
  revocation fails; actively closing established streams is deferred until
  `GET /events/stream` exists (WP-1.10 not landed — the events app had no stream
  route when this WP ran). The reconnect test is conditional and skips with that
  reason, activating when the route lands.
- Audit event deferred as in MT-5.3-01 (same missing helper/catalog type).

### MT-5.3-04 — GET /devices backend surface + web follow-up note

- `GET /devices` added on the existing Section 9.2 collection path
  (`DeviceRegisterView` renamed `DeviceCollectionView` — one path, one view; URL
  name `device-collection`): Owner-scoped cursor page (`results` + `next_cursor`,
  `-pk` newest-first, `cursor`/`page_size`), metadata only — never `push_token`
  (Section 12.4), never token material; revoked devices stay listed with
  `revoked_at` for settings history. Tests: `backend/tests/test_device_list.py`.
- **OQ-15 raised for the plan amendment** (per MT-5.3-01's risk note, flagged not
  silent): Section 9.2 does not list `GET /devices` — add it (new Section 22 id
  OQ-15: "add GET /devices to Section 9.2?") at the wave gate.
- Throttling splits by method: registration keeps `DeviceEndpointThrottle`
  (FR-SEC-05); the Owner list read is exempt (Owner rows are never throttled).
- **Web follow-up note (not built here):** the account-settings device section in
  `web/` consumes this endpoint through the generated OpenAPI client only —
  list + per-row revoke with explicit confirmation, canonical error-code → message
  mapping, and distinct loading/empty/error states (Section 13.3; Section 20.3
  splitting rule). UX edge to handle there: revoking the *active* device (or the
  only one) mid-use — disable/strong-confirm the control; decision recorded in
  that web WP's changelog.

### Verification

- Targeted pytest: 4 new suites (30 passed, 1 conditional skip) + WP-1.2
  device/token suites, rate limiting, contract, authorization matrix
  (114 passed) — green.
- ruff/format/mypy clean for this WP's files; `manage.py check` clean;
  `makemigrations --check`: no changes. One final OpenAPI regen (byte-stable)
  at the WP end.
