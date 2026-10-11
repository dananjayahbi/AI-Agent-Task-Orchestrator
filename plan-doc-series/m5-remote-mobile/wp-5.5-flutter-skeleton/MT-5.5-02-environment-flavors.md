# MT-5.5-02 — Configure environment flavors (dev/prod endpoints)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-02 |
| Title | Configure environment flavors (dev/prod endpoints) |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | NFR-11; NFR-06 (environment discipline, via Section 16.2) |
| Priority | M |
| Dependencies | MT-5.5-01 (app scaffold), WP-4.1 context (web LAN UI), WP-5.1 (tunnel hostname for remote prod) |
| Parent sections | 14.3, 15.1 (two hostnames), 16.2, 19 (WP-5.5), 20.4, 20.5 |

## Context
Section 14.3 requires "flavor configs for dev and prod endpoints," and Section 15.1
fixes the two-hostname reality: a LAN address for direct access and a tunnel
hostname for remote access. The mobile app therefore needs a first-class way to run
against a development backend (local Compose host / LAN) and a production backend
(tunnel hostname) without code edits — endpoints are configuration, not constants,
and no environment-specific value may be hard-coded into source (Section 20.4 item 3,
Section 16.2 configuration discipline).

## Inputs / Prerequisites
* Parent plan Section 14.3 — flavor configs for dev and prod endpoints.
* Parent plan Section 15.1 — LAN address vs tunnel hostname; Section 16.2 —
  configuration and secrets discipline (values from environment/build args, not
  committed secrets).
* Parent plan Section 9.10-style rule — every setting documented with a default.
* MT-5.5-01 — scaffold where flavors attach; MT-5.5-03/06 — consumers of the
  resolved base URL (generated client, onboarding URL entry).
* WP-5.1 — the production tunnel endpoint this flavor will point at.

## Scope (in)
* Flavor definitions for `dev` and `prod` (distinct app ids/names so both can be
  installed side by side on a device), each resolving a backend base URL from
  build-time configuration — dev defaults to the documented LAN development address
  pattern, prod to the tunnel hostname supplied at build time, neither committed as
  an environment-specific literal in source (Section 20.4 item 3).
* A single resolved-configuration object the app consumes (base URL plus any
  environment-derived flags), with documented defaults and startup validation that
  fails fast with a clear message on a missing prod URL (Section 9.10/16.2
  discipline).
* Platform wiring for both flavors: Android product flavors and iOS schemes/configs
  so `flutter run` can target either, with debug/release variants intact.
* Documentation in `mobile/` on how to build each flavor and where the URL comes
  from (build arg/env), plus tests: config resolution returns the right URL per
  flavor, missing prod URL fails with the clear error.

## Out of scope
* The generated API client and how it consumes the URL — MT-5.5-03.
* Server URL entry by the user during onboarding (tunnel hostname typing) —
  MT-5.5-06; flavors provide defaults, onboarding may override per Section 14.1
  (record the precedence rule: onboarding-set URL overrides flavor default — note it
  explicitly as this WP's decision since the plan lists both).
* Cloudflare tunnel provisioning — WP-5.1/WP-5.2.
* Secrets of any kind — none belong in a mobile flavor (Section 12.4).
* Release signing and store flavors — WP-5.10.

## Target paths
* `mobile/` (flavor/build configuration for Android and iOS; resolved-config module)
* `mobile/` docs or README (flavor build instructions)
* `mobile/` tests (config resolution tests)
* WP changelog entry

## Acceptance criteria
- [ ] `dev` and `prod` flavors build on both platforms with distinct app ids, and
  each resolves its backend base URL from build configuration — no committed
  environment-specific URLs in source (Section 14.3, Section 20.4 item 3).
- [ ] Missing/empty prod URL fails fast at startup with a clear message naming the
  missing value (Section 16.2/9.10 startup-validation discipline).
- [ ] The resolved-config module is the single source of the base URL for all
  consumers (client generation, onboarding) — asserted by test.
- [ ] The flavor build instructions document where each URL comes from and how to
  supply the tunnel hostname at build time (Section 15.1).
- [ ] Tests, lint and analyze green in CI for `mobile/` (Section 20.4 item 2).
- [ ] Changelog note added, including the flavor-URL vs onboarding-URL precedence
  decision (item 7).

## Test command
From `mobile/`, run `flutter analyze` and `flutter test` with the flavor-config
tests selected (e.g. `flutter test test/flavor_config_test.dart`); CI runs the
suite for both platforms' analyze steps.

## Attachments
* [Section 15.1 — Hostnames](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.3 — Engineering approach](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Hard-coding a personal tunnel hostname in committed config would break every
  other user and violates Section 20.4 item 3 — keep prod URL a build-time input
  and assert no literal in source.
* Flavor/app-id divergence between Android and iOS is a common source of install
  conflicts; verify side-by-side installation of both flavors as part of the tests.
