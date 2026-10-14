# Release signing — Android and iOS (MT-5.10-01)

> Covers parent plan Section 14.3 (signing configured *and documented*), Section 16.2 /
> 20.4 item 3 (secrets outside Git), Section 16.5 (backup discipline), RISK-10 (early
> spike) and OQ-08 (distribution assumption). Written for WP-5.10 (Milestone M5).

## Status summary

| Platform | State | Evidence |
|---|---|---|
| Android | **Configured and verified** — release build reaches the signed-artifact step with the release keystore | `flutter build apk --release --flavor prod` → `app-prod-release.apk` (53.4 MB); `apksigner verify --print-certs` reports signer `CN=Orchestrator Mobile Release, OU=Mobile, O=AI Agent Task Orchestrator` (SHA-256 `e70e4b3a…037966`) — not the debug identity |
| iOS | **Configured as far as the account situation allows; blocked on a developer account (RISK-10 spike outcome)** | See [iOS spike record](#ios-spike-record-risk-10) below |

## Android

### How signing is wired

`mobile/android/app/build.gradle.kts` loads, from **outside Git**:

* `mobile/android/key.properties` (git-ignored) containing `storeFile`,
  `storePassword`, `keyAlias`, `keyPassword`; <!-- pragma: allowlist secret -->
* the keystore file it points at (`mobile/android/upload-keystore.jks`, git-ignored).

If `key.properties` is absent (fresh clone, lint-only jobs) the release build type
falls back to the **debug** key so the project still compiles. **A fallback-signed
APK must never be distributed** — confirm the signer before shipping:

```powershell
# from mobile/
apksigner verify --print-certs build\app\outputs\flutter-apk\app-prod-release.apk
```

The signer DN must be the release identity, not `CN=Android Debug`.

### One-time setup (new machine)

1. Generate the keystore (JDK `keytool`; any JDK 8+ works):

   ```powershell
   keytool -genkeypair -v -keystore android\upload-keystore.jks `
     -keyalg RSA -keysize 2048 -validity 10000 -alias upload
   ```

   Choose a strong store/key password and store it **only** in a password manager
   (never in chat, tickets, or Git).

2. Create `mobile/android/key.properties` (git-ignored):

   ```properties
   storeFile=../upload-keystore.jks
   storePassword=<from password manager>
   keyAlias=upload
   keyPassword=<from password manager>
   ```

3. Build and verify (see above).

### Credential-handling rule (Section 16.2 / 20.4 item 3)

* Real values live **only** in git-ignored files — `mobile/.gitignore` and
  `mobile/android/.gitignore` cover `key.properties`, `*.jks`, `*.keystore`,
  `*.p12`, `*.pem`, `*.cer`, `*.p8`, `*.mobileprovision`.
* No keystore, certificate, profile file or credential is committed; the build
  never echoes property values (the verified build log contains no passwords —
  Section 12.4 scrubbing spirit). Verified with `git check-ignore -v` and a
  `git status --porcelain` scan after the build.

### Rotation and backup (Section 16.5)

* **Rotate passwords** with `keytool -keychgpasswd`; update `key.properties` in
  the same change (still never committed).
* **Never re-generate the upload keystore casually**: Android keeps the first
  signing cert for the app's identity — losing it means either losing the ability
  to update the installed app or going through the platform's upload-key reset /
  re-listing flow. If the keystore must be rotated, follow the platform's key
  reset process, don't just swap files.
* **Backup obligation (Section 16.5)**: `upload-keystore.jks` **and** the
  `key.properties` values are unrecoverable-loss items and must be copied to the
  operator's encrypted password-manager/off-repo vault. As of this MT the only
  copy on this host is `mobile/android/` itself (git-ignored, machine-local) —
  **the off-repo backup is an outstanding operator action**, tracked here rather
  than claimed done. Treat "keystore present + password recoverable off-site" as
  a release-readiness checklist item for MT-5.10-05.

## iOS spike record (RISK-10)

**What exists (facts from this host):**

* `mobile/ios/Runner.xcodeproj` configured with
  `PRODUCT_BUNDLE_IDENTIFIER = com.aiagenttaskorchestrator.orchestratorMobile`
  (dev flavor: `…orchestratorMobile.dev`; tests: `…RunnerTests`),
  `CODE_SIGN_STYLE = Automatic`, `CODE_SIGN_IDENTITY[sdk=iphoneos*] = "iPhone
  Developer"`.
* **No `DEVELOPMENT_TEAM` is set anywhere in the project** — nothing to embed
  without an account, and per Section 16.2 credentials are referenced, never
  embedded.

**What is missing (the blocker):**

* No Apple Developer account / team membership is available on this (Windows)
  host; certificates, provisioning profiles and TestFlight cannot be created or
  verified without it, and `xcodebuild` cannot run on Windows at all.

**Forecast for MT-5.10-03 (conditional, per OQ-08):**

* With an account + macOS/Xcode: set the team id once, keep `CODE_SIGN_STYLE =
  Automatic` (Xcode then creates/keeps certificates and profiles for the bundle
  id above), archive, upload to TestFlight. Effort once unblocked: low — the
  project-side configuration this MT could do is already done. Until then
  MT-5.10-03 stays blocked and must not be reported as (done).

## OQ-08 restated with spike facts

OQ-08 (decided): **Android internal build first; iOS via TestFlight when a
developer account is available.** The spike confirms this is the only honest
path: Android signing is fully working end-to-end on this host, while iOS is
blocked purely on account/toolchain availability, not on any app-side gap. The
MT-5.10-04 distribution path should therefore document the Android internal-
distribution route as the real v1 path and keep TestFlight as the conditional
step keyed on the account landing.

## Where this document lives (Section 14.3 wording decision)

Section 14.3 says signing is "documented in the runbook", but Section 17 defines
exactly seven runbooks with no signing entry. Rather than silently adding an
eighth, the setup/spike record lives here under `mobile/docs/`; MT-6.5-01
(operator guide) should link to this page from the operator documentation. This
records the choice instead of bending the runbook list.

## Verification commands (Section 19 first slice)

```powershell
# from mobile/ — reaches the signed-artifact step
flutter build apk --release --flavor prod
# signer must be the release identity
apksigner verify --print-certs build\app\outputs\flutter-apk\app-prod-release.apk
# no signing material tracked
git status --porcelain   # key.properties / *.jks must not appear (git-ignored)
```
