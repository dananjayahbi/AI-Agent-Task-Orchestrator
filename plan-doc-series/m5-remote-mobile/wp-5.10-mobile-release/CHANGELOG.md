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

### Deferred

**MT-5.10-03 — Produce the iOS TestFlight release build (deferred).**
Blocker: no Apple Developer account/team on this Windows host — no
certificates or provisioning profiles are possible and `xcodebuild` does
not run on Windows (the RISK-10 spike facts recorded under MT-5.10-01
above); OQ-08's condition ("iOS via TestFlight when developer account is
available") is unmet, so the build stays conditional until an account is
available.
