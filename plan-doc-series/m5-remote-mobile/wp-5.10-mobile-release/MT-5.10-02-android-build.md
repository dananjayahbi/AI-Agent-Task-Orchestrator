# MT-5.10-02 — Produce the Android Internal Release Build

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.10-02 |
| Title | Produce the Android internal release build |
| Parent WP | WP-5.10 — Mobile release builds and distribution (Milestone M5) |
| Requirements | FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.10-01 (Android signing configured), MT-5.5-02 (prod flavor), WP-5.9 complete (feature set frozen for the release candidate) |
| Parent sections | 14.3 (release build), 19 (WP-5.10 second slice and acceptance), 20.4, 20.5; 22 (OQ-08: Android internal build first); 21 (RISK-10) |

## Context
OQ-08 (decided) sets the order: "Android internal build first; iOS via TestFlight
when developer account is available." This task produces that first installable
artifact — a signed internal release build of the app with the WP-5.9 features
(push deep links, notification center, audit log) and the WP-5.3/WP-5.8 flows
(biometric unlock, review sheet) included. Section 19 (WP-5.10) acceptance starts
from an "installable build on a real iOS and Android device" — Android is the
platform this slice delivers first, de-risking RISK-10 by validating the pipeline
where it is cheapest.

## Inputs / Prerequisites
* MT-5.10-01 — release signing working for Android (keystore outside Git).
* MT-5.5-02 — prod flavor pointing at the tunnel hostname / production endpoints
  (Section 15.1 two-hostname topology).
* WP-5.9 and WP-5.8 complete — the release candidate contains the notification,
  audit and review features.
* FCM configuration from WP-5.4 (MT-5.4-01) — the build must be the one whose push
  registration works against the production sender.
* Parent plan Section 14.3 — engineering approach; OQ-08 — why Android is first.

## Scope (in)
* Build the signed Android internal release artifact (the plan's "Android internal
  release build" — APK/AAB per internal distribution needs; record which) from the
  prod flavor, using MT-5.10-01's outside-Git signing.
* Versioning/labeling of the artifact so a tester can tell which build they have
  (version code/name derived from the project's versioning — record the scheme in
  the changelog; do not invent a release automation system).
* Preflight verification before handing it out: app launches against the production
  URL, login and device registration succeed, biometric enrollment completes
  (FR-MOB-06), one real push arrives (WP-5.4 path) — i.e., the smoke subset of the
  MT-5.10-05 checklist, so a broken artifact never reaches the full checklist.
* Hand the artifact + install instructions to the distribution path (MT-5.10-04) —
  internal sharing, no store upload (OQ-08).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Signing configuration — MT-5.10-01.
* iOS/TestFlight build — MT-5.10-03.
* Defining the distribution process — MT-5.10-04 (this task only produces and
  preflights the artifact).
* The full real-device checklist — MT-5.10-05 (preflight is a subset gate, the
  checklist is the acceptance run).
* Play Store publication — OQ-08 chose internal distribution for v1.

## Target paths
* `mobile/` — any build configuration needed for the internal release (version
  metadata; non-secret only)
* `mobile/docs/` — build command and artifact notes (where the build command lives)
* Build artifacts — produced locally, never committed (Section 20.4 item 3)
* WP changelog entry (version produced, preflight result)

## Acceptance criteria
- [ ] A signed Android release artifact is produced from the prod flavor with
  MT-5.10-01's external signing (Section 19 WP-5.10 second slice; OQ-08).
- [ ] The artifact passes the preflight subset: launch on production URL, login,
  device registration, biometric enrollment, one real push received (FR-MOB-06;
  NFR-03 push path).
- [ ] The artifact's version identity is recorded so checklist results map to a
  specific build (Section 20.5).
- [ ] No artifact or credential committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the documented release build command from `mobile/` (recorded in the build
notes) and confirm a signed artifact is produced; then execute the preflight subset
manually on one Android device — login, register, enroll biometric, trigger an
escalation and confirm the push arrives — and record the result in the changelog.

## Attachments
* [Section 22 — OQ-08 (Android internal build first)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [NFR-03 — Push dispatch within 10 s](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Preflight push depends on the production FCM sender and a reachable backend
  (tunnel up) — if the stack is not deployed yet, preflight against the reachable
  environment and note which one; do not claim production-readiness from a LAN-only
  run.
* Internal artifacts distribute out-of-band (sideload) — installation must allow
  unknown-sources on the test device; the install instructions (for MT-5.10-04) must
  include this or testers stall (RISK-10 friction avoided early).
* Building on a developer machine pins the environment — record OS/tooling versions
  with the artifact so MT-5.10-03 and future releases reproduce it.
