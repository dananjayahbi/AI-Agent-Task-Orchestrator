# Android internal release build (MT-5.10-02)

> How the signed internal release artifact is produced, how a tester identifies
> which build they have, and what has (and has not) been verified on this host.
> Signing setup and credential rules live in [release-signing.md](release-signing.md);
> distribution and rollout in [distribution.md](distribution.md); the full
> real-device gate in [release-checklist.md](release-checklist.md).

## Status

| Item | State | Evidence |
|---|---|---|
| Signed prod-flavor APK | **Produced on this host** | `flutter build apk --release --flavor prod` → `mobile/build/app/outputs/flutter-apk/app-prod-release.apk` — signer verified as the release identity via `apksigner verify --print-certs` (see [release-signing.md](release-signing.md); not the debug key) |
| iOS release build | Blocked | MT-5.10-03 deferred — no Apple Developer account on this Windows host (no `xcodebuild` on Windows) |
| On-device preflight subset | **Not executed — open gate** | No real Android device is attached to this Windows host, and the mobile app has no FCM transport plugin yet (see [release-checklist.md](release-checklist.md) § FCM transport status). The smoke subset runs as part of the MT-5.10-05 checklist before any artifact is handed to a tester. |

## Build command (from `mobile/`)

```powershell
flutter build apk --release --flavor prod
```

This is the verified pipeline command (signing via the git-ignored
`android/key.properties` + keystore — [release-signing.md](release-signing.md)).

The **production URL is a build-time operator input**, never committed
(Section 20.4 item 3). For the distribution build, add exactly one of:

```powershell
flutter build apk --release --flavor prod --dart-define-from-file=env/prod.json `
  --dart-define=ORCHESTRATOR_API_BASE_URL=https://<tunnel-hostname>/api/v1
# or, to derive the URL instead:
#   --dart-define=ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME=<tunnel-hostname>
```

`env/prod.json` deliberately carries only the flavor key; the tunnel hostname
is supplied per build (Section 15.1 two-hostname topology). Without either
define the app fails fast at first frame naming the missing define — the APK
above was built with the bare pipeline command because no tunnel hostname
exists in Git or on this host; the operator adds it when building the
artifact that goes to testers.

## Artifact

* Path: `mobile/build/app/outputs/flutter-apk/app-prod-release.apk`
  (APK per internal distribution needs — recorded per the MT Scope; an AAB
  is only needed for store upload, which OQ-08 excludes for v1).
* First internal artifact (this host, 2026-10-15): 53.8 MB,
  SHA-256 `3B16775ED144C17842186D2659B1A00B23D676965881E7B4E238E4B20ECE7980`
  — this is a pipeline-verification build, not a distributed one (no
  tunnel-hostname define, preflight gate below).
* Build artifacts are produced locally and **never committed**
  (Section 20.4 item 3; `build/` is git-ignored).
* Before handing the artifact out, confirm the signer is the release
  identity, never the debug fallback — command in
  [release-signing.md](release-signing.md).

## Version-identity scheme (recorded, no automation)

Version identity is derived from `mobile/pubspec.yaml`'s `version` field
(consumed by Gradle as `flutter.versionName` / `flutter.versionCode`):

| Field | Source | Current value |
|---|---|---|
| `versionName` | `version:` before `+` | `0.0.1` |
| `versionCode` | build-number part after `+` (absent → `1`) | `1` |

Release procedure (manual v1, Section 20.3 — automation is post-v1): bump
`pubspec.yaml` `version` (e.g. `0.0.2+2`) before an artifact leaves the
build machine. A tester identifies their build via Android's app-info
screen (shows versionName/versionCode) and the APK file name; **checklist
results must record the versionCode they ran** (Section 20.5 traceability).

## Build-environment record (reproducibility, MT-5.10-02 risk note)

Recorded with the first internal artifact so future releases (and the iOS
leg once unblocked) can reproduce it:

* Host OS: Microsoft Windows 11 (build host, x64)
* Flutter 3.35.6 (stable), Dart 3.9.2
* Android SDK build-tools 36.1.0 (`apksigner` from
  `%LOCALAPPDATA%\Android\Sdk\build-tools\36.1.0`)
* Signing: outside-Git release keystore per [release-signing.md](release-signing.md)

## Preflight gate

The MT-5.10-02 preflight subset (launch against production URL, login,
device registration, biometric enrollment, one real push) is the smoke
subset of the [release-checklist.md](release-checklist.md). It has **not**
run on this host — see the Status table above and the blockers recorded in
the WP-5.10 changelog. No artifact has been handed to any tester, so the
"preflight before handing out" invariant holds; the checklist run is the
gate before distribution starts.
