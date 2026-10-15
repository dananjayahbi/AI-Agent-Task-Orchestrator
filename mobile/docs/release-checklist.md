# Real-device release checklist — push + biometric (MT-5.10-05)

> The Section 18 Mobile UI row's "manual device matrix for push and
> biometrics" — the recorded, manual verification that the signed release
> builds do on real hardware what widget tests can only simulate. Section
> 19 (WP-5.10) acceptance is "installable build on a real iOS and Android
> device passes the manual push and biometric checklist".

**Execution status: not yet run — see [Blockers](#blockers) below.** This
document is the authored checklist (MT-5.10-05 Scope item 1); every run
appends its filled-in matrix under [Recorded runs](#recorded-runs).

## FCM transport status (recorded — shapes the push steps)

The mobile app currently has **no FCM transport plugin** (no
`firebase_messaging` dependency in `mobile/pubspec.yaml`). Notification
taps enter the app through the documented seam:
`PendingNotificationTapNotifier.report(...)` — the platform callback
(initial message / message-opened) will call it once the plugin lands
(WP-5.9 changelog, MT-5.9-01; the in-app foreground banner is
`ForegroundPushHandler.present`, MT-5.9-02). Widget tests drive both seams
directly. **This checklist is the designated real-device backstop**: the
push steps below (real FCM delivery, OS notification, tap routing on
release builds) can only pass once the FCM client transport is integrated;
until then those steps are *blocked*, not failed.

## Environment required for a valid run

* A deployed stack with the **tunnel up** (WP-5.1/WP-5.2) and the backend
  reachable at the production URL baked into the build
  ([release-build.md](release-build.md)).
* Push enabled with real FCM credentials: worker-side sender per WP-5.4
  (MT-5.4-01) — `ORCHESTRATOR_PUSH_ENABLED` + FCM project config on the
  backend — plus the mobile FCM transport above.
* The release build installed via [distribution.md](distribution.md),
  signer verified ([release-signing.md](release-signing.md)).
* **Record where the backend ran** (LAN host vs VPS via tunnel) with every
  run — a LAN-only pass does not satisfy "release" (MT-5.10-05 risk note).

## The checklist (per platform)

Columns to fill per step: **result** (pass/fail/blocked), notes. Device
metadata goes in the run header.

### A. Install and launch
1. Install the release build via the [distribution.md](distribution.md)
   path (Android: sideload with unknown-sources; iOS: TestFlight when
   unblocked — currently blocked, see Blockers).
2. App launches against the **production URL** (no fail-fast; onboarding
   shows the flavor-derived tunnel host).

### B. Registration, login, biometrics
3. Login succeeds (FR-MOB-06).
4. Device registration succeeds; device appears active server-side.
5. Biometric enrollment completes (FR-MOB-06). Record the method used
   (fingerprint / face / passcode fallback per Section 14.2).

### C. Biometric gate (Section 14.2)
6. Cold start requires unlock — no API token available before success.
7. Inactivity timeout requires unlock (per the configured timeout).
8. Token is released only after biometric success; a cancelled/failed
   biometric leaves the app locked.

### D. Push (FR-MOB-04; NFR-03 smoke)
9. Trigger a task into `in_human_review`; a notification arrives on the
   device **within 10 s**. (Smoke confirmation of a single real delivery —
   *not* the NFR-03 measured proof; WP-6.3 owns the measured budget.)
10. With the app foregrounded, the same event shows the **in-app banner**
    (MT-5.9-02), not a duplicate system notification.

### E. Tap-to-review (MT-5.9-01; Section 19 WP-5.9 acceptance re-verified
    on release builds)
11. **Cold start:** tap the notification → after unlock, the correct
    task's review sheet opens.
12. **Warm start (app backgrounded, unlocked):** tap → same result.
13. **Warm start with inactivity lock:** tap → unlock required first, then
    the review sheet (gate precedence).
14. Stale tap: a task that left review before the tap shows the explained
    fallback, never a broken sheet.

### F. Approve safety on-device (Section 14.2; WP-5.8)
15. Approve-and-merge confirmation shows task id, branch and diff stats,
    and is bound to the viewed resolution id (a newer submission
    invalidates a stale approval).

### G. Negative path (MT-5.3-03)
16. Revoke the device server-side; its next request is rejected
    immediately. At least one revocation check per device in the matrix.

## Failure handling

Every failure is filed as a defect with a follow-up task; failed steps are
re-run after the fix and the re-run recorded (Section 20.4 item 1).

## Blockers (why no run is recorded yet)

1. **No real Android device** is attached to this Windows build host —
   steps 1–16 cannot execute here (the MT requires real hardware; widget
   tests are explicitly out of scope for this gate).
2. **No FCM transport in the app yet** — steps 9–14 are blocked until the
   plugin lands and calls the documented `report` seam (see FCM transport
   status above), even on a real device.
3. **iOS entirely blocked** — no Apple Developer account (MT-5.10-03
   deferred entry; OQ-08/RISK-10). Per the MT acceptance, the WP-level
   Section 19 gap ("real iOS **and** Android device") is **escalated here,
   not hidden**: WP-5.10/M5 acceptance cannot be claimed without the iOS
   leg.

## Run header template

```
Date/time:            ...
Build:                versionName ... / versionCode ... (record both)
APK source:           <sha256 of the artifact>
Device:               <model> — Android <OS version> / iOS <OS version>
Biometric method:     fingerprint / face / passcode fallback
Backend location:     LAN host / VPS via tunnel <hostname> (record which)
FCM:                  configured (project ...) / transport missing → push steps blocked
```

## Recorded runs

_None yet — the first run fills the matrix above top-to-bottom and is
appended here (device/build/OS per step, timestamps)._
