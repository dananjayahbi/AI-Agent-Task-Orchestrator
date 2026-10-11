# MT-5.10-01 — Configure Release Signing for Android and iOS

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.10-01 |
| Title | Configure release signing for Android and iOS |
| Parent WP | WP-5.10 — Mobile release builds and distribution (Milestone M5) |
| Requirements | FR-MOB-06 |
| Priority | M |
| Dependencies | MT-5.5-02 (environment flavors / build configuration), MT-5.5-01 (app scaffold); RISK-10's early spike is this task's prerequisite check |
| Parent sections | 14.3 (release signing documented in the runbook), 16.2 (secrets outside Git), 19 (WP-5.10 first slice), 20.3, 20.4, 20.5; 21 (RISK-10); 22 (OQ-08) |

## Context
Section 19 (WP-5.10) lists "signing" as the first slice; Section 14.3 requires
release signing to be configured and documented. RISK-10 (iOS push and distribution
friction) explicitly calls for an "early spike in WP-5.10 prerequisites" — this
task is that spike: get both platforms' signing stories working (or discover the
blocker) before any build work in MT-5.10-02/03. OQ-08 (decided: Android internal
build first, iOS via TestFlight when a developer account is available) is the
distribution assumption signing must satisfy. Secrets discipline applies: signing
material and credentials never enter Git (Section 16.2; Section 20.4 item 3).

## Inputs / Prerequisites
* MT-5.5-02 — flavor/build configuration for Android and iOS (release flavor exists).
* Parent plan Section 14.3 — signing must be configured and documented.
* Parent plan Section 16.2 / 20.4 item 3 — real values live outside Git; the env
  template pattern from WP-0.2.
* Parent plan OQ-08 (decided) and RISK-10 — Android-first, iOS conditional on a
  developer account; spike outcome feeds MT-5.10-03/04.
* Platform requirements as facts to record: an Android keystore; for iOS, an Apple
  developer account with certificates/profiles (existence to be confirmed — RISK-10).

## Scope (in)
* Android release signing: configure the release build to sign with a keystore whose
  location/credentials are supplied from outside Git (env/config file ignored by
  Git); document the exact setup steps and the credential-handling rule.
* iOS signing: configure the release signing path (certificates and provisioning
  profile) for the app's bundle identifier, with credentials referenced, never
  embedded; if no developer account exists yet, configure everything that does not
  depend on it and record the remaining step as blocked.
* The RISK-10 spike record: what exists (account, certs, profiles), what is missing,
  and the resulting forecast for MT-5.10-03 — written into the docs below so
  MT-5.10-04 can define the distribution path from facts.
* Signing documentation per Section 14.3 (see target paths and risk notes for the
  location question): setup, rotation basics, and the "never commit secrets" rule.
* A verification that a release-flavor build attempt resolves signing without
  printing secrets to logs (Section 12.4 scrubbing spirit).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Actually producing release builds — MT-5.10-02 (Android) and MT-5.10-03 (iOS).
* The distribution path definition — MT-5.10-04.
* The real-device checklist — MT-5.10-05.
* Push credential setup (FCM keys) — WP-5.4 (MT-5.4-01); this is app signing only.
* CI/CD pipeline for releases — not in the plan; manual release builds are the v1
  path unless the plan says otherwise.

## Target paths
* `mobile/` — release signing configuration for Android and iOS (non-secret parts:
  build references, keystore property names, profile names)
* `mobile/docs/` — release signing document (setup steps, credential handling,
  spike record; see risk notes on the Section 14.3 "runbook" wording)
* Git-ignored local files / environment — actual keystores, certificates, passwords
  (must not be committed; Section 20.4 item 3)
* WP changelog entry (spike outcome summary)

## Acceptance criteria
- [ ] Android release flavor resolves signing from outside-Git configuration, and a
  release build attempt reaches the signed-artifact step (Section 19 WP-5.10 first
  slice).
- [ ] iOS signing is configured to the extent the account situation allows, with any
  blocker named explicitly (RISK-10 spike recorded).
- [ ] No keystore, certificate, profile file or credential is committed; the ignored
  paths are covered by Git ignore rules (Section 20.4 item 3; Section 16.2).
- [ ] Signing is documented (Section 14.3) including credential handling and
  rotation notes.
- [ ] OQ-08 assumption restated with the spike's facts (Android-first; iOS
  conditional) so MT-5.10-04 documents a real path (Section 22).
- [ ] Lint/analyze green; changelog note added (Section 20.4 items 2, 7).

## Test command
From `mobile/`: attempt the release-flavor build for Android up to artifact
signing (documented command in the signing doc) and confirm it signs without any
committed secret — then `git status`/secret-scan confirm no signing material is
tracked; re-read the signing document for the Section 14.3 completeness check.

## Attachments
* [Section 14.3 — Engineering approach (release signing)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-10 (iOS push and distribution friction)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 22 — OQ-08 (mobile distribution path)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 14.3 says signing is "documented in the runbook", but Section 17's seven
  runbooks contain no signing entry — documenting under `mobile/docs/` with a
  pointer from the operator guide (MT-6.5-01) is the reading that satisfies both;
  record the choice rather than adding an eighth runbook silently.
* The iOS step may be blocked by account availability (RISK-10) — a blocked spike is
  a valid outcome; record it as such and keep MT-5.10-03 conditional, never fake
  configuration that cannot be verified.
* Keystores are unrecoverable-loss items — the doc must state where the Android
  keystore is backed up (with the Section 16.5 backup discipline) or v1 signing
  becomes a single lost-file away from being un-updatable.
