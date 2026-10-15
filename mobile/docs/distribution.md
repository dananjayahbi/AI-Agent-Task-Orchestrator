# Mobile distribution path (MT-5.10-04)

> The written, repeatable v1 path for who gets which build, how they install
> it, and how updates roll out — parent plan OQ-08 (decided): "Android
> internal build first; iOS via TestFlight when developer account is
> available"; no public stores for v1. MT-5.10-05's checklist and the
> operator guide (MT-6.5-01) point testers at this page.

## Cross-references

| Document | Covers |
|---|---|
| [release-signing.md](release-signing.md) | Signing setup, credential handling, keystore rotation/backup (MT-5.10-01) |
| [release-build.md](release-build.md) | Producing the signed APK + version-identity scheme (MT-5.10-02) |
| [release-checklist.md](release-checklist.md) | The real-device gate before/with each distribution (MT-5.10-05) |
| MT-6.5-01 (`plan-doc-series/m6-hardening-release/wp-6.5-documentation/MT-6.5-01-operator-setup-guide.md`) | Operator guide — this page is its mobile-distribution link target |

No signing or store credentials appear in this document — pointers only
(Section 20.4 item 3); real values live only in the git-ignored files named
in [release-signing.md](release-signing.md).

## Android — internal distribution (the v1 path)

**Audience:** the single Owner plus explicitly invited testers (the product
is single-owner per plan; every recipient is named, never a public link).

**Mechanism (decision recorded per the MT risk note — OQ-08 does not pick
one):** direct out-of-band file share of the APK (sideload). For a single
Owner this is the simplest mechanism that fits; no MDM or internal track
exists or is needed for v1. Release automation is post-v1 (Section 20.3).

End-to-end path:

1. **Artifact:** the operator builds per [release-build.md](release-build.md)
   (`flutter build apk --release --flavor prod` + the tunnel-hostname
   define) and verifies the signer is the release identity, never the
   debug fallback ([release-signing.md](release-signing.md)).
2. **Preflight gate:** the [release-checklist.md](release-checklist.md)
   smoke subset passes (or its failures are filed) before the APK is shared
   — a broken artifact never reaches a tester.
3. **Sharing:** the APK goes to named testers over a trusted channel
   (the Owner's own file share). Artifacts are never committed to Git
   (Section 20.4 item 3).
4. **Install:** on the test device, allow installation from the share's
   source ("unknown sources" — Android blocks sideloads by default; the
   installer prompts for it). The dev flavor installs side by side and is
   not affected.
5. **Update:** a newer build is delivered by installing its APK
   **over the existing app** — same application id, and it **must be signed
   with the same release keystore** or Android rejects it as an upgrade
   (MT-5.10-01 keystore discipline: never re-generate the upload keystore
   casually; see its rotation/backup section). App data — secure-storage
   tokens, notification history, preference state — survives the update;
   re-login is needed only if the backend tokens rotate (Section 16.5
   upgrade discipline, mobile analogue).

## iOS — blocked, web fallback in the interim

Per OQ-08's conditional wording, the iOS path is TestFlight **when a
developer account is available**. That condition is **unmet**: the MT-5.10-03
deferred entry (WP-5.10 changelog) records the blocker — no Apple
Developer account/team on this Windows host, so no certificates or
provisioning profiles are possible and `xcodebuild` does not run on Windows
(RISK-10 spike facts, [release-signing.md](release-signing.md) iOS section).
The project-side signing configuration is already done; effort once an
account lands is low (set the team id, archive, upload) — the steps live in
MT-5.10-03's doc once it executes.

**Interim review path (RISK-10's "web fallback for reviews"):** while the
iOS leg is blocked, reviews run on the responsive web board
(MT-4.11-01) — the same review sheet flows exist there, so iOS review
work is not stalled on the account. No iOS build is distributed in v1.

## Update rollout rules

* During WP-5.10 verification, testers run the single current internal
  build; there is no parallel-version support for v1.
* **Version identity** is the pubspec-derived scheme recorded in
  [release-build.md](release-build.md): every checklist run and every
  reported result records the `versionCode` it ran — results are never
  attributed to "the app" in general (Section 20.5).
* A new build replaces the installed one install-over-install
  (same-signing-key constraint above); testers confirm the version after
  updating before recording further results.

## iOS branch after v1 (explicit current state)

The iOS branch stays exactly as the recorded blocker states: keyed on an
Apple Developer account becoming available (OQ-08). When it lands:
MT-5.10-03 executes (archive → TestFlight → build number recorded here),
then the same [release-checklist.md](release-checklist.md) runs on a real
iOS device. Until then the Section 19 WP-5.10 acceptance gap ("real iOS
**and** Android device") stays open and escalated in the WP-5.10 changelog —
this document does not claim an iOS path ran.
