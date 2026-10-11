# MT-5.10-03 — Produce the iOS TestFlight Release Build

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.10-03 |
| Title | Produce the iOS TestFlight release build |
| Parent WP | WP-5.10 — Mobile release builds and distribution (Milestone M5) |
| Requirements | FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.10-01 (iOS signing path + RISK-10 spike record), MT-5.10-02 (Android first, per OQ-08), WP-5.9 complete |
| Parent sections | 14.3 (release build), 19 (WP-5.10 third slice and acceptance), 20.4, 20.5; 21 (RISK-10); 22 (OQ-08) |

## Context
OQ-08 (decided): "iOS via TestFlight when developer account is available." RISK-10
names iOS push and distribution friction (accounts, signing) and prescribes
"Android-first validation" — which MT-5.10-02 completes — with iOS as the
conditional second step. Section 19 (WP-5.10) acceptance needs a real iOS device
passing the checklist, so this task produces the TestFlight build, gated on the
MT-5.10-01 spike having confirmed the prerequisites. If they are missing, this task
records the blockage rather than improvising around it — that is a valid, plan-
conformant outcome (OQ-08's conditional wording).

## Inputs / Prerequisites
* MT-5.10-01 — iOS signing configured and spike record (account, certificates,
  provisioning profile status).
* MT-5.10-02 — Android build proven first (OQ-08 order; the pipeline lessons apply).
* MT-5.5-02 — prod flavor for iOS; WP-5.4-01 — APNs/FCM push prerequisites for iOS
  push (push on iOS needs its own credential path — record status if absent).
* Parent plan OQ-08 (conditional) and RISK-10 (friction risk).
* An available Apple developer account with distribution capability — confirmed by
  the spike, not assumed.

## Scope (in)
* If prerequisites (from MT-5.10-01's spike) are available: archive and sign the iOS
  release build from the prod flavor, upload it to TestFlight, and record the build
  number and testing-group setup — the OQ-08 "iOS via TestFlight" path.
* Install/TestFlight-fetched run on a real iOS device as a smoke preflight (same
  subset as MT-5.10-02: launch, login, device registration, biometric enrollment,
  one push) before handing over to MT-5.10-05's full checklist.
* If prerequisites are **not** available: document the blocker precisely (missing
  account / certificate / profile / push credential) against OQ-08's condition, keep
  Android as the validated path, and update the spike record — do not fabricate a
  passing step.
* Record push-on-iOS status explicitly: FCM/APNs wiring must work for the checklist's
  push step (NFR-03) — flag as follow-up if not yet configured.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Signing configuration and the spike itself — MT-5.10-01.
* Android artifact — MT-5.10-02.
* The distribution-path definition — MT-5.10-04 (this task executes one path).
* The full real-device checklist — MT-5.10-05.
* App Store submission — OQ-08 chose TestFlight for v1, not the public store.

## Target paths
* `mobile/` — any iOS-specific build metadata (non-secret only)
* `mobile/docs/` — TestFlight build/upload steps and the blocker record if gated
* Build artifacts / uploads — never committed (Section 20.4 item 3)
* WP changelog entry (build number or blocker statement, push-on-iOS status)

## Acceptance criteria
- [ ] Either a TestFlight build is produced and smoke-preflighted on a real iOS
  device, or the OQ-08 condition is documented as unmet with the specific blocker —
  Section 19 WP-5.10 third slice handled honestly under OQ-08/RISK-10.
- [ ] The iOS signing/upload steps executed are recorded in
  `mobile/docs/` so the run is reproducible (Section 14.3 documentation rule).
- [ ] Push-on-iOS status (FCM/APNs credential path) is stated with the result
  (NFR-03 checklist dependency).
- [ ] No certificate, profile or credential committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
If unblocked: run the documented archive/upload steps from `mobile/` and confirm the
build appears in TestFlight, then smoke-preflight it on a real iOS device (login,
device registration, biometric enrollment, one push) and record the build number; if
blocked: verify `mobile/docs/` names the exact missing prerequisite and the changelog
carries the blocker (Section 22 OQ-08 condition).

## Attachments
* [Section 22 — OQ-08 (iOS via TestFlight when account available)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-10 (iOS push and distribution friction)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The most likely outcome per RISK-10 is friction — treat "blocked with precise
  record" as a passing outcome for this task, but then MT-5.10-05's iOS leg and the
  Section 19 acceptance ("real iOS **and** Android device") cannot be claimed; the
  WP-level gap must be escalated, not hidden.
* TestFlight distribution requires the app's push environment (APNs) to be
  production-correct — a build that installs but cannot receive push fails the
  checklist later; check push credentials as part of this task's preflight.
* iOS signing tied to one Apple ID/machine is fragile — record which account and
  machine produced the build so the next release (post-v1) is reproducible.
