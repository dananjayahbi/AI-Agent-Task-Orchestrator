# MT-5.3-03 — Implement Device Revocation with Immediate Rejection

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.3-03 |
| Title | Implement device revocation with immediate rejection |
| Parent WP | WP-5.3 — Device registration and mobile authentication (Milestone M5) |
| Requirements | FR-SEC-02, FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.3-02 (device-bound tokens issued) |
| Parent sections | 9.2, 12.1, 12.2, 19.1 (WP-5.3), ADR-006, 20.4, 20.5 |

## Context
Section 12.1 threat "Lost phone": mitigation "device-bound token, biometric gate,
remote device revocation." Section 12.2: devices are "independently revocable."
Section 9.2: `DELETE /devices/{id}`. Section 19 (WP-5.3) acceptance: "revoked device
is rejected on the next request and stream reconnect." The web account settings UI
(MT-5.3-04) is the Owner-facing trigger.

## Inputs / Prerequisites
* MT-5.3-02 — issued device tokens and their validation path.
* MT-5.3-01 — the `DELETE /devices/{id}` route registered.
* MT-1.10-05 — SSE stream authorization; stream reconnect must reject revoked
  devices (Section 19 WP-5.3 acceptance explicitly includes the stream).
* Section 9.6 event helper (MT-1.9-02) for the audit event — subject to the pending
  token-event OQ; do not invent a catalog type.

## Scope (in)
* `DELETE /devices/{id}` behavior: Owner-authenticated revocation of one of their
  devices; the device's token stops validating immediately (revocation state checked
  in the token validation path, not cached past the check).
* Immediate rejection on the **next** request of any kind: REST calls and SSE stream
  reconnection both fail with canonical auth errors (Section 19 WP-5.3 acceptance).
* Existing sessions of the revoked device: established stream connections are closed
  on revocation (reject on next use at minimum; close-active preferred — record the
  chosen semantics in the changelog note).
* Revocation is independent per device — revoking device A never affects device B or
  agent tokens (Section 12.2 "independently revocable"; FR-SEC-02).
* Audit trail: revocation writes an event via the established helper (Section 12.5).
* Tests: revoke → next REST request rejected; revoke → SSE reconnect rejected;
  other devices unaffected; revocation idempotent on repeat.

## Out of scope
* The web UI triggering revocation — MT-5.3-04.
* Bulk revocation / "revoke all devices" — not in the plan; raise an OQ if wanted.
* Revoking agent tokens or owner sessions — WP-1.2 (`DELETE /tokens/{id}`, logout).
* Push-token pruning on revocation — WP-5.4 (token pruning is listed there).
* Cloudflare Access revocation — WP-5.2 (edge gate is separate layer).

## Target paths
* `backend/apps/accounts/views.py` (DELETE /devices/{id} behavior)
* `backend/tests/accounts/test_device_revocation.py`
* WP changelog entry

## Acceptance criteria
- [ ] A revoked device is rejected on its next REST request with a canonical auth
  error from the Section 9.2 catalog (Section 19 WP-5.3 acceptance).
- [ ] A revoked device is rejected on SSE stream reconnect
  (`GET /events/stream`) (Section 19 WP-5.3 acceptance).
- [ ] Revoking one device leaves all other devices, agent tokens and sessions
  working (Section 12.2; FR-SEC-02).
- [ ] Only the owning Owner can revoke (Section 9.2 caller; cross-owner attempt
  denied).
- [ ] Revocation writes an audit event without inventing a catalog type (Section
  12.5; pending token-event OQ).
- [ ] Lint, type check and tests green (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
`pytest backend/tests/accounts/test_device_revocation.py -v` — next-request
rejection, SSE-reconnect rejection, isolation between devices, owner-only
authorization, audit-event assertion.

## Attachments
* [Section 12.1 — Threat model (lost phone)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Independent device revocation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-5.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* "Immediate" is only as strong as the slowest cache: if token validation or the SSE
  connection caches revocation state, a stolen token still works until the cache
  expires — review every caching layer on the auth path (API auth classes, stream
  connections) for revocation checks; document any bounded staleness honestly.
* Existing live SSE connections are the hardest case (the acceptance only says
  "stream reconnect") — implement connection-close on revoke if feasible; at minimum
  guarantee reconnect rejection and note the chosen behavior.
