# MT-5.10-05 — Run the Real-Device Release Checklist (Push + Biometric)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.10-05 |
| Title | Run the real-device release checklist (push + biometric) |
| Parent WP | WP-5.10 — Mobile release builds and distribution (Milestone M5) |
| Requirements | FR-MOB-06, FR-MOB-04 |
| Priority | M |
| Dependencies | MT-5.10-02 (Android artifact), MT-5.10-03 (iOS TestFlight or recorded blocker), MT-5.10-04 (distribution path), MT-5.9-01 (deep links), MT-5.5-04 (biometric gate), MT-5.4-01 (FCM sender) |
| Parent sections | 14.2 (biometric gate; push deep link), 19 (WP-5.10 fifth slice and acceptance), 18 (Mobile UI row: manual device matrix for push and biometrics), 20.4, 20.5; NFR-03; 21 (RISK-10) |

## Context
Section 19 (WP-5.10) acceptance is explicit: "installable build on a real iOS and
Android device passes the manual push and biometric checklist." Section 18's Mobile
UI row requires a "manual device matrix for push and biometrics" with real-device
checks before release. This task is the checklist itself: the recorded, manual
verification that the signed release builds do on real hardware what the widget
tests can only simulate — push arrives, tap routes, biometric gate guards, revocation
behaves. It is the last gate before the WP (and M5) can claim its acceptance, and
Section 1.4 criterion 4 (push within 10 s, approve from the phone) is checked in its
spirit here.

## Inputs / Prerequisites
* MT-5.10-02 (Android artifact) and MT-5.10-03 (iOS build or blocker) — the builds
  under test; MT-5.10-04 — how testers get them.
* MT-5.4-01 — FCM credentials live; a reachable production stack with tunnel up
  (WP-5.1/WP-5.2) so push and API calls take the real path.
* Real devices: at least one Android and one iOS device with biometric capability
  (or passcode fallback per Section 14.2).
* MT-5.9-01 — the cold/warm deep-link behavior under test; MT-5.5-04 — gate rules
  (cold start and inactivity timeout both require unlock).
* Parent plan Section 14.2 — the behaviors the checklist steps assert.

## Scope (in)
* Author the checklist document (the Section 18 "manual device matrix" artifact)
  covering, per platform:
  * Install the release build via the MT-5.10-04 path; app launches against
    production URL.
  * Device registration + login + biometric enrollment complete (FR-MOB-06).
  * Biometric gate: cold start requires unlock; inactivity timeout requires unlock;
    token released only after success (Section 14.2).
  * Push: a task entering `in_human_review` produces a notification on the device
    within 10 s (FR-MOB-04; NFR-03); foreground arrival shows the in-app banner
    (MT-5.9-02).
  * Tap-to-review: notification tap lands on the correct review sheet after unlock —
    tested on **cold and warm** start (MT-5.9-01; Section 19 WP-5.9 acceptance
    re-verified on release builds).
  * Approve safety on-device: approve-and-merge confirmation shows task id, branch
    and diff stats and binds to the viewed resolution id (Section 14.2; WP-5.8).
  * Negative path: revoked device is rejected on next request (MT-5.3-03) — at least
    one revocation check per device matrix.
* Execute the checklist on both real devices, recording per-step results, device
  models/OS versions, build versions and timestamps.
* File any failure as a defect with a follow-up task; re-run the failed steps after
  the fix (Section 20.4 item 1).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Building or distributing — MT-5.10-02/03/04.
* Widget/integration tests — already green from WP-5.5/5.9 CI.
* Performance benchmarking of push latency on a large scale — WP-6.3 owns the
  measured 10 s budget at system level; here a single real delivery is confirmed.
* Automated device farms — Section 18 specifies a manual device matrix for v1.

## Target paths
* `mobile/docs/` — real-device release checklist (the manual device matrix)
* `mobile/docs/` — recorded results (device/build/OS matrix with pass/fail per step)
* WP changelog entry (checklist outcome; defect links if any)

## Acceptance criteria
- [ ] A checklist document exists covering install, registration, biometric gate
  (cold + timeout), push within 10 s, tap-to-review (cold + warm), approve safety and
  revocation (Section 18 Mobile UI row; Section 14.2).
- [ ] The checklist is executed and recorded on a **real Android device** with build
  version, OS version and per-step results (Section 19 WP-5.10 acceptance).
- [ ] The same is executed on a **real iOS device**, or the OQ-08/RISK-10 blocker is
  recorded and the WP-level acceptance gap is explicitly escalated (do not claim
  acceptance without the iOS leg).
- [ ] Notification tap lands on the correct review sheet after unlock, cold and warm,
  on release builds (Section 19 WP-5.9 acceptance re-confirmed here).
- [ ] Every failure has a linked follow-up; failed steps re-run green after fixes
  (Section 20.4 item 1).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Execute `mobile/docs/` real-device checklist top-to-bottom on the Android release
build and the iOS build (or record the OQ-08 block), then verify the results file
shows a per-step pass for every line including push-within-10 s and cold/warm
tap-to-review; confirm recorded build versions match MT-5.10-02/03's artifacts.

## Attachments
* [Section 19 — WP-5.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing strategy (Mobile UI row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 1.4 — Success criterion 4 (push + phone approve)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Results are only as real as the environment: push must traverse FCM → backend →
  device over the deployed stack; a LAN-only pass does not satisfy "release" —
  record where the backend ran.
* Push-within-10 s on one manual run is a smoke confirmation, not the NFR-03 proof —
  WP-6.3's measured budget remains authoritative; keep the wording distinct so the
  two results are not conflated later.
* Biometric availability varies (fingerprint/face/passcode fallback per Section 14.2)
  — record what each device used, or the matrix overstates coverage (RISK-10-style
  friction usually surfaces exactly here).
