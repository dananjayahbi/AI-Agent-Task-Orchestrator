# MT-5.5-04 — Implement secure token storage and biometric gate

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-04 |
| Title | Implement secure token storage and biometric gate |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | FR-MOB-06 (biometric unlock and secure token storage); ADR-006 (layered mobile auth) |
| Priority | M |
| Dependencies | MT-5.5-01 (scaffold), MT-5.5-03 (client that uses the token), WP-5.3 (device registration and device-bound token backend) |
| Parent sections | 12.2 (mobile auth), 14.2 (biometric gate), 15.3 (access layers), 19 (WP-5.5), 20.4, 20.5 |

## Context
ADR-006 layers mobile auth: edge policy first, then a Django device-bound token,
then biometric unlock — Section 14.2 spells out the client half: "the app token
lives in platform secure storage and is unlocked only after biometric success; cold
start and a configurable inactivity timeout both require unlock. Fallback to device
passcode as the OS allows." Section 12.2 adds that the device token is
independently revocable. WP-5.5's acceptance includes biometric enrollment working
on both platforms; this slice implements the storage and the gate that every
authenticated screen sits behind.

## Inputs / Prerequisites
* Parent plan Section 14.2 — biometric gate behavior: platform secure storage,
  unlock on cold start and inactivity timeout, passcode fallback as OS allows.
* Parent plan Section 12.2 — mobile: device registration after Owner login,
  device-bound token in secure storage, released only after biometric success,
  independently revocable.
* Parent plan Section 15.3 / ADR-006 — layered access: edge policy, device token,
  biometric unlock (Section 23 rationale).
* WP-5.3 — backend device registration, token issuance and revocation
  (`POST /devices`, `DELETE /devices/{id}`).
* MT-5.5-01/03 — scaffold and generated client to attach the token to.

## Scope (in)
* Secure storage integration: store and read the device-bound token only via the
  platform secure storage mechanisms (Keychain on iOS, Keystore-backed storage on
  Android) — never in SharedPreferences/plaintext files, never logged
  (Section 12.4, Section 20.4 item 3).
* The biometric gate: an app-level lock that requires biometric success before any
  token is released to the HTTP client; enforced on cold start and after a
  documented configurable inactivity timeout (Section 14.2); passcode fallback when
  the OS offers it; clear handling when the device has no biometrics enrolled
  (route to enrollment in MT-5.5-06, with honest messaging — no silent bypass).
* Token injection point: the generated client (MT-5.5-03) reads the token only
  through the unlocked gate; locking the app (background timeout) stops releasing
  it.
* A lock/unlock state exposed to navigation so screens render a locked view when
  gated.
* Widget/unit tests: storage never receives plaintext beyond the secure store
  call, cold start locks, successful unlock releases the token, timeout re-locks,
  no-biometrics path shows enrollment guidance; both-platform behavior verified in
  the manual device matrix where emulators cannot simulate biometrics
  (Section 18 mobile UI row).

## Out of scope
* Device registration and token issuance/revocation API flows — WP-5.3 (backend)
  and MT-5.5-06 (the registration UX that obtains the token).
* Cloudflare edge policy — WP-5.2 (ADR-006 layer 1; external to the app).
* Push token registration — WP-5.4.
* Logout/session end UI — Settings screen in later mobile WPs; only the gate and
  storage primitives here.
* Store-level biometric policy on unsupported devices — documented limitation.

## Target paths
* `mobile/` (secure storage service, biometric gate, lock state)
* `mobile/` tests (unit/widget tests for gate and storage)
* WP changelog entry

## Acceptance criteria
- [ ] The token is persisted only in platform secure storage and read only after
  gate unlock — tests plus code review confirm no plaintext persistence or logging
  (FR-MOB-06, Section 14.2, Section 20.4 item 3).
- [ ] Cold start requires biometric success before any authenticated request can
  carry the token; a configurable inactivity timeout re-locks (Section 14.2).
- [ ] Passcode fallback is offered where the OS allows; devices without biometrics
  get explicit enrollment guidance instead of a bypass (Section 14.2, honest
  states).
- [ ] Lock state blocks the app shell: locked views show no authenticated data
  (Section 14.2).
- [ ] Works on both platforms per WP-5.5 acceptance — widget/unit tests in CI plus
  the recorded manual device check (Section 18 mobile UI row; Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
From `mobile/`, run `flutter analyze` and `flutter test` with the gate/storage
tests selected (e.g. `flutter test test/biometric_gate_test.dart`); record the
manual biometric check on real devices for both platforms in the WP changelog.

## Attachments
* [Section 14.2 — Mobile-specific behaviors](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 23 — ADR-006](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Emulators poorly simulate biometrics — CI can prove the state machine, but
  WP-5.5 acceptance ("both platforms") requires the manual device matrix entry;
  do not claim done on emulator evidence alone.
* Inactivity timeout value is configurable but unspecified in the plan — choose a
  documented default (Section 9.10) and note it as a WP decision.
