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

**MT-5.10-02 — Produce the Android internal release build (deferred).**
Freeze-clause verification (batch-10 planner's reading, checked before any
implementation): the reading that "WP-5.9 complete (feature set frozen for the
release candidate)" is a *feature-freeze* clause — not a hard dependency — is
**not supported** by the documents. Evidence: (1) the MT's Dependencies row and
Inputs both state "WP-5.9 / WP-5.9 and WP-5.8 complete" as requirements and the
parenthetical only gives the rationale (freeze), while this series writes
conditional dependencies explicitly when intended — MT-5.10-04's own dependency
reads "MT-5.10-03 (TestFlight **or recorded blocker**)", a clause MT-5.10-02
lacks; (2) the Context demands a build "with the WP-5.9 features (push deep
links, notification center, audit log) … included" — deep links (MT-5.9-01) and
the notification center (MT-5.9-03) are exactly the deferred MTs; (3) the
preflight acceptance requires "one real push received (… MT-5.4-01)", and the
risk note only covers an implemented-but-undeployed FCM sender, not an
unimplemented one; (4) parent plan Section 19 (WP-5.10) says "Depends on:
WP-5.9"; (5) parent plan Section 16 (checked as instructed) is
infrastructure/deployment/upgrade discipline and contains no feature-freeze
provision.

Blocker (real): WP-5.4 (FCM sender MT-5.4-01, payload contract, backend push
chain) is unimplemented — `wp-5.4-push-notifications/` has no changelog — so
WP-5.9 cannot complete (its MT-5.9-01/02/03 are deferred on exactly that chain,
per the WP-5.9 changelog), the release candidate cannot contain the push/
notification features the MT's Context and Inputs require, and the preflight
subset ("one real push received") cannot be executed against any environment.
The backend push chain is outside the mobile batch's scope, so the MT stops
here rather than shipping a build whose feature set silently misses the
documented requirements. What already stands and is unaffected: MT-5.10-01's
signing pipeline (`flutter build apk --release --flavor prod` → signed
`app-prod-release.apk`, verified in batch 9) — the build *command* works; what
is missing is the feature-complete feature set, the preflight run and the
version-identity scheme this MT would have recorded.

Verification of repo state this batch (no code changed): `cd mobile;
flutter analyze` → "No issues found!"; `flutter test` → **243 passed** (the
batch-9 baseline).

**MT-5.10-03 — Produce the iOS TestFlight release build (deferred).**
Blocker: no Apple Developer account/team on this Windows host — no
certificates or provisioning profiles are possible and `xcodebuild` does
not run on Windows (the RISK-10 spike facts recorded under MT-5.10-01
above); OQ-08's condition ("iOS via TestFlight when developer account is
available") is unmet, so the build stays conditional until an account is
available.

**MT-5.10-04 — Define and document the distribution path (deferred).**
Blocker: first dependency "MT-5.10-02 (Android artifact produced)" is unmet —
MT-5.10-02 is deferred above on the WP-5.4/WP-5.9 chain, so there is no
preflighted internal artifact and no version-identity scheme for the document's
update/rollout rules to reference, and this MT's own risk note forbids the
exact failure mode writing it now would create ("an idealized path that never
ran"). The second dependency is satisfied as written — MT-5.10-03's "TestFlight
or recorded blocker" clause is met by the blocker record above — but that half
alone cannot carry the MT. Unblock order: WP-5.4 backend push chain → WP-5.9
completion → MT-5.10-02 (artifact + preflight + versioning) → this document;
the iOS branch stays keyed on the developer-account condition already recorded.
