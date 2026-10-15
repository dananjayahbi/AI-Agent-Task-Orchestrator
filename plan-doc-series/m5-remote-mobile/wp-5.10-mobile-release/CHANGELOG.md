# WP-5.10 — Mobile release builds and distribution — Changelog

## Unreleased

**MT-5.10-01 — Configure release signing for Android and iOS (done).**

Android: `mobile/android/app/build.gradle.kts` now resolves release signing
from git-ignored `android/key.properties` (storeFile/storePassword/keyAlias/
keyPassword) — no secret is hardcoded or printed by the build (parent plan
Sections 16.2 / 20.4 item 3). A release keystore was generated on this host
(never committed: `git check-ignore` covers `key.properties`, `*.jks` and the
other certificate/profile patterns in both `.gitignore` files) and the release
build reached the signed-artifact step. iOS (RISK-10 spike): everything not
depending on an account is configured — bundle id
`com.aiagenttaskorchestrator.orchestratorMobile` (+ `.dev`), Automatic signing,
iPhone Developer identity, **no DEVELOPMENT_TEAM** — and the blocker is named
explicitly: no Apple Developer account/team on this Windows host (no
certs/profiles possible, no xcodebuild on Windows); MT-5.10-03 stays conditional
on that account per OQ-08, restated with the spike facts. Documentation per
Section 14.3 lives at `mobile/docs/release-signing.md` (setup, credential
handling, rotation, Section 16.5 backup obligation with the off-repo backup
flagged as an outstanding operator action, doc-location decision recorded
instead of adding an eighth Section 17 runbook).

Evidence: `cd mobile; flutter build apk --release --flavor prod` →
`√ Built build\app\outputs\flutter-apk\app-prod-release.apk (53.4MB)`;
`apksigner verify --print-certs` → signer `CN=Orchestrator Mobile Release,
OU=Mobile, O=AI Agent Task Orchestrator` (SHA-256 `e70e4b3a…037966`, not the
debug identity); `git check-ignore -v` confirms both ignore rules; post-build
`git status --porcelain` shows no keystore/props in tracked changes;
`flutter analyze` → "No issues found"; `flutter test` → **243 passed** (199
existing + 44 new from batch-9 WP-5.8/5.9 work).

**MT-5.10-02 — Produce the Android internal release build (done — build
pipeline; on-device preflight remains the open gate recorded below).**

Dependency verification against the MT's Inputs row (checked this batch
against the repo, not from memory):

* MT-5.10-01 (signing): done (entry above) — release keystore +
  `key.properties` present on this host, git-ignored.
* MT-5.5-02 (prod flavor): done (WP-5.5 changelog) — `android/app/src/prod/`,
  `env/prod.json` (flavor key only).
* WP-5.9 complete: batch-11 WP-5.9 changelog (MT-5.9-01..04 done) — push
  deep-link routing, foreground banner, notification history/toggles and the
  audit-log viewer are in the release candidate. WP-5.8 complete: wp-5.8
  changelog (MT-5.8-01..06 done) — review sheet + approve safety.
* FCM input (MT-5.4-01): **backend half** done (wp-5.4 changelog, committed
  in batch 10 — sender, payload contract, dispatch, preferences). **Mobile
  half absent — recorded, not glossed:** the app has no FCM transport plugin
  (`firebase_messaging` is not in `mobile/pubspec.yaml`; taps enter via the
  `PendingNotificationTapNotifier.report` seam, WP-5.9 changelog), so "the
  build whose push registration works against the production sender" cannot
  exist yet; the MT's preflight leg "one real push received" is blocked on
  that client-transport follow-up and is carried into the MT-5.10-05
  checklist (its FCM-transport section marks the push steps blocked, not
  failed).

What landed this batch — the signed artifact, the version-identity scheme
and the build notes:

* Artifact: `mobile/build/app/outputs/flutter-apk/app-prod-release.apk`
  (APK recorded per internal-distribution needs; no store exists to justify
  an AAB — OQ-08), 53.8 MB, SHA-256
  `3B16775ED144C17842186D2659B1A00B23D676965881E7B4E238E4B20ECE7980`.
* Versioning scheme (recorded, no automation invented): `versionName` =
  pubspec `version` before `+` (`0.0.1`); `versionCode` = the build-number
  part after `+` (absent → `1`; currently `1`). Bump the pubspec before an
  artifact leaves the build machine; every checklist result records the
  `versionCode` it ran (Section 20.5). Build environment recorded in the doc
  per the MT risk note (Windows 11 host, Flutter 3.35.6 / Dart 3.9.2,
  build-tools 36.1.0).
* Build notes: `mobile/docs/release-build.md` — the documented command (the
  bare pipeline form verified below, plus the tunnel-hostname define form
  from `mobile/README.md`; no hostname exists in Git or on this host, so the
  verified build ran the bare form — the app fails fast at first frame
  without the define, by design).
* **Not claimed:** the on-device preflight subset (launch on production URL,
  login, device registration, biometric enrollment, one real push) did not
  run — no real Android device is attached to this Windows host, and the
  push leg is additionally blocked by the missing FCM client transport
  above. No artifact has been handed to any tester, so the "preflight before
  handing out" invariant holds; execution transfers to the MT-5.10-05
  checklist run (blockers 1 and 2 recorded there).

Evidence: `cd mobile; flutter build apk --release --flavor prod` →
`√ Built build\app\outputs\flutter-apk\app-prod-release.apk (53.8MB)`;
`apksigner verify --print-certs` (SDK build-tools 36.1.0) → signer
`CN=Orchestrator Mobile Release, OU=Mobile, O=AI Agent Task Orchestrator`
(SHA-256 `e70e4b3a…037966` — the MT-5.10-01 release cert, not the debug
fallback); `git check-ignore -v` → `key.properties`
(`mobile/android/.gitignore:12`), `**/*.jks` (`:14`), `/build/`
(`mobile/.gitignore:33`); post-build `git status --porcelain` scan → no
keystore/props/apk in tracked changes; `flutter analyze` → "No issues
found!"; `flutter test` → **268 passed** (G1's batch-11 baseline; no mobile
code changed this batch).

**MT-5.10-04 — Define and document the distribution path (done).**

Dependency verification: (1) "MT-5.10-02 (Android artifact produced)" —
satisfied by the entry above (signed artifact + version identity produced
this batch); (2) "MT-5.10-03 (TestFlight **or recorded blocker**)" —
satisfied by the recorded blocker in the deferred MT-5.10-03 entry below
(no Apple Developer account/team on this Windows host; no certificates or
provisioning profiles possible; no `xcodebuild` on Windows — OQ-08/RISK-10
spike facts). No iOS path is claimed to have run.

`mobile/docs/distribution.md` — the v1 path, per platform:

* **Android end-to-end:** artifact (operator builds + verifies the signer)
  → checklist smoke gate → shared out-of-band to **named** testers →
  sideload install with the unknown-sources note (MT-5.10-02's risk note) →
  updates install-over the existing app with the **same signing key**
  (MT-5.10-01 keystore discipline; Section 16.5 upgrade analogue: secure
  storage survives the update; re-login only if tokens rotate). Mechanism
  **decision recorded as this task's decision** per the MT risk note
  (OQ-08 does not pick one): direct file-share sideload, the simplest fit
  for a single Owner; no MDM/internal track; automation is post-v1
  (Section 20.3).
* **iOS:** the precise recorded blocker (cited from MT-5.10-03's deferred
  entry + MT-5.10-01's spike record) with RISK-10's web fallback — the
  responsive web review channel (MT-4.11-01) as the interim review path;
  the branch stays keyed on a developer account landing (OQ-08 conditional
  wording); the Section 19 "real iOS **and** Android device" acceptance gap
  stays explicitly open and escalated.
* **Rollout:** one current internal build during WP-5.10 verification;
  version identity (`versionCode`) referenced from `release-build.md`;
  checklist results attach to a specific build (Section 20.5); the
  same-signing-key upgrade constraint is stated.
* **Secrets:** pointers only to `release-signing.md` (Section 20.4 item 3).
  Cross-links to the signing, build and checklist docs and the MT-6.5-01
  operator-guide link target all resolve.

Evidence (the MT's documentation-review test command): secret-value grep
over the three `mobile/docs/` release docs → only prose uses of "tokens"
(no values, keys or credentials); link-resolution check →
`release-signing.md`, `release-build.md`, `distribution.md`,
`release-checklist.md`, MT-6.5-01 and MT-4.11-01 paths all resolve; every
referenced artifact/version exists (`app-prod-release.apk`, `versionCode`
1) or is explicitly marked blocked (iOS/TestFlight).

### Deferred

**MT-5.10-03 — Produce the iOS TestFlight release build (deferred).**
Blocker: no Apple Developer account/team on this Windows host — no
certificates or provisioning profiles are possible and `xcodebuild` does
not run on Windows (the RISK-10 spike facts recorded under MT-5.10-01
above); OQ-08's condition ("iOS via TestFlight when developer account is
available") is unmet, so the build stays conditional until an account is
available.
_Re-verified this batch (11): blocker unchanged. MT-5.10-04's "TestFlight
or recorded blocker" dependency consumes this record (its entry above);
MT-5.10-05's iOS leg remains blocked on it._

**MT-5.10-05 — Run the real-device release checklist (deferred —
checklist authored; execution blocked).**

What stands (this batch): the checklist document — the Section 18 "manual
device matrix" artifact — exists at `mobile/docs/release-checklist.md`,
covering every MT scope line: install via the MT-5.10-04 path, launch on
the production URL, login + device registration + biometric enrollment
(FR-MOB-06), biometric gate (cold start + inactivity timeout; token
released only after success — Section 14.2), push within 10 s on
`in_human_review` (FR-MOB-04; NFR-03 smoke, worded distinctly from
WP-6.3's measured budget per the MT risk note), foreground banner
(MT-5.9-02), tap-to-review cold + warm plus warm-locked and stale-tap
variants (MT-5.9-01), approve safety on-device (task id, branch, diff
stats, resolution-id binding — Section 14.2/WP-5.8), and the revocation
negative path (MT-5.3-03). A run-header template records device model, OS
version, biometric method, build `versionCode` and backend location per
the risk notes; failures are filed as defects with follow-up and re-run
(Section 20.4 item 1). The FCM transport seam is documented in the
checklist as the MT's backstop: no FCM plugin exists in the app yet — taps
enter via `PendingNotificationTapNotifier.report` (WP-5.9 changelog) — and
the push steps are marked *blocked, not failed* until the plugin calls
that seam.

Blockers (execution cannot run on this host):

1. No real Android device is attached to this Windows host — the MT
   requires real hardware; widget tests are explicitly out of scope for
   this gate.
2. No FCM transport in the mobile app — even on a real device the push
   steps (real delivery, OS notification, cold/warm tap routing on
   release builds) cannot pass until the plugin lands.
3. iOS legs fully blocked on the Apple Developer account (MT-5.10-03
   deferred entry above; OQ-08/RISK-10). Per the MT acceptance the
   WP-level gap is **escalated here, not hidden**: Section 19 WP-5.10
   acceptance ("installable build on a real iOS and Android device passes
   the manual push and biometric checklist") is **not claimed** — WP-5.10
   and M5 stay short of acceptance until both device legs run.

Verification of repo state this batch (no app code changed): `cd mobile;
flutter analyze` → "No issues found!"; `flutter test` → **268 passed**;
`flutter build apk --release --flavor prod` → the signed
`app-prod-release.apk` (MT-5.10-02 entry) — the checklist's build under
test exists; the run itself awaits an operator with a device.
