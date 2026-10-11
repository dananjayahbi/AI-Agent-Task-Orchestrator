# MT-5.5-06 — Implement onboarding screens (URL, login, device registration)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-06 |
| Title | Implement onboarding screens (URL, login, device registration) |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | FR-MOB-06 context; ADR-006 (layered mobile auth); NFR-11 |
| Priority | M |
| Dependencies | MT-5.5-01..05 (scaffold, flavors, client, secure storage/gate, SSE), WP-5.3 (device registration backend), MT-5.5-02 (flavor defaults) |
| Parent sections | 12.2 (mobile auth flow), 14.1 (Onboarding screens), 15.1 (tunnel hostname), 19 (WP-5.5), 20.4, 20.5 |

## Context
Section 14.1's Onboarding area lists four screens: server URL entry (tunnel
hostname), login, device registration, biometric enrollment. Section 12.2 defines
the flow behind them: "device registration after Owner login; device-bound token
kept in secure storage and released only after biometric success." So the onboarding
sequence is — point the app at the server (flavor default pre-filled, user
override available), authenticate the Owner (username/password session per
Section 12.2), register this device (`POST /devices`, receiving the device-bound
token into MT-5.5-04's secure storage), then enroll biometrics to gate it. WP-5.5's
acceptance requires login, device registration and biometric enrollment to work on
both platforms; this slice is the user-facing flow that completes it.

## Inputs / Prerequisites
* Parent plan Section 14.1 — the four onboarding screens.
* Parent plan Section 12.2 — auth layers: owner login session for registration,
  device-bound token, independent revocation; edge policy still applies
  (ADR-006, Section 15.3).
* Parent plan Section 9.2 — endpoints: `POST /auth/login`, `POST /devices`,
  `DELETE /devices/{id}` (revocation lives in Settings later; flow here registers).
* WP-5.3 — backend device registration, device-bound tokens, revocation.
* MT-5.5-02 (flavor default URL), MT-5.5-03 (typed client), MT-5.5-04 (secure
  storage and gate that receives the token).

## Scope (in)
* The onboarding flow with the four Section 14.1 screens, navigated in order and
  resumable (a returning user mid-flow is not reset):
  1. Server URL entry — pre-filled from flavor config (MT-5.5-02), editable for
     the tunnel hostname (Section 15.1), validated with a reachability check
     against the backend health endpoint before proceeding.
  2. Login — Owner credentials via `POST /auth/login` through the generated client;
     failures map Section 9.2 codes to friendly, non-leaky messages (no credential
     echo, Section 12.4).
  3. Device registration — `POST /devices`; the returned device-bound token is
     handed directly to MT-5.5-04's secure storage, never rendered or logged.
  4. Biometric enrollment — guide the user through enabling the biometric gate
     (ties to MT-5.5-04's lock), with honest skip/deferral handling consistent
     with Section 14.2 (app remains locked until unlocked; no silent bypass).
* Completion hands off to the app shell (Home/Overview) with the gate armed.
* Widget tests per screen (validation, error mapping, navigation order) plus
  integration tests against the mocked backend for the full flow
  (Section 18 mobile UI row).

## Out of scope
* Backend auth/device flows — WP-5.3.
* Secure storage/gate internals — MT-5.5-04 (this task feeds it the token).
* Edge access policy configuration — WP-5.2 (ADR-006 layer 1; app cannot enforce
  it).
* Logout and device revocation UI — Settings (later mobile WPs).
* Push notification permission/registration — WP-5.4.
* Refreshing/re-auth on token revocation mid-session — post-onboarding session
  handling; note as follow-up if WP-5.3 defines a revocation signal.

## Target paths
* `mobile/` (onboarding feature folder: four screens + flow controller)
* `mobile/` tests (widget and mocked-backend integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] All four Section 14.1 onboarding screens exist and run in sequence with
  resumable state; URL entry pre-fills from flavor config and accepts the tunnel
  hostname (Section 14.1, 15.1, MT-5.5-02).
- [ ] Login succeeds against `POST /auth/login` via the generated client; failure
  codes map to friendly messages without leaking credentials (Section 9.2,
  Section 12.4).
- [ ] Device registration calls `POST /devices`; the device-bound token goes
  straight into secure storage through the gate service — it never appears in
  logs, widgets, or app state outside the storage call (Section 12.2,
  Section 20.4 item 3).
- [ ] Biometric enrollment completes the flow and arms the MT-5.5-04 gate; skip
  handling is honest — the app does not claim enrollment that did not happen.
- [ ] Full flow passes mocked-backend integration tests; login, registration and
  enrollment verified on both platforms per WP-5.5 acceptance (Section 18 mobile
  UI row, manual device matrix noted in changelog).
- [ ] Lint/analyze/tests green in CI (Section 20.4 item 2); changelog note added
  (item 7).

## Test command
From `mobile/`, run `flutter analyze` and `flutter test` with the onboarding tests
selected (e.g. `flutter test test/onboarding/`), including the mocked-backend
integration flow; record the manual both-platform verification in the changelog.

## Attachments
* [Section 14.1 — Navigation and screens](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Storing or echoing the device token anywhere outside secure storage would break
  ADR-006's model at the exact point attackers probe — review the handoff path
  from `POST /devices` to storage line by line.
* The plan does not specify a health endpoint name for the URL reachability probe;
  use the documented ops endpoint from Section 9.2 (`/health/live` or
  `/health/ready` as exposed) and raise an OQ-xx if ambiguous, rather than
  inventing one.
