# MT-0.1-04 — Configure Mobile Tooling and Package Scripts

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-04 |
| Title | Configure mobile tooling and package scripts for the Flutter app |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11 |
| Priority | M |
| Dependencies | MT-0.1-01 |
| Parent sections | 6.6, 14.3, 19.1 (WP-0.1), 20.4 |

## Context
The mobile package is a Flutter (Dart) application per Section 6.6, and WP-0.1's
acceptance requires every package — including `mobile/` — to run lint and type check
from a fresh clone with one documented command each. This task establishes the Flutter
project tooling (analyzer configuration, formatting, documented commands) that WP-0.3
CI will invoke, ahead of the real app skeleton in WP-5.5.

## Inputs / Prerequisites
* MT-0.1-01 — `mobile/` directory in the repository layout.
* Parent plan Section 6.6 — Flutter (Dart), Riverpod, `local_auth`, FCM.
* Parent plan 14.3 — engineering approach for the Flutter client (context only).
* Flutter SDK installed and on `PATH` (prerequisite for verification).

## Scope (in)
* Initialize the `mobile/` Flutter package (`pubspec.yaml`) as a minimal placeholder
  sufficient for the tooling commands to run — not the app itself (WP-5.5).
* Configure the Dart analyzer (`analysis_options.yaml`) with lint rules appropriate for
  the project, and document the format command with a change-detection flag.
* Define the documented single commands: analyze (type check), format check, and
  dependency resolution.
* Record the commands in `CONTRIBUTING.md` and add a WP changelog note.

## Out of scope
* Navigation, screens, state management, push notifications, biometrics — WP-5.5 onwards.
* Widget and integration tests — WP-0.3 test jobs and M5 mobile WPs.
* iOS/Android signing and distribution — WP-5.10 (OQ-08).
* CI job wiring — MT-0.3-01.
* Pre-commit hook wiring — MT-0.1-05.

## Target paths
* `mobile/pubspec.yaml` (package manifest)
* `mobile/analysis_options.yaml` (analyzer/lint configuration)
* `CONTRIBUTING.md` (documented one-command entries for mobile)
* WP changelog entry

## Acceptance criteria
- [ ] The Flutter package initializes and resolves dependencies.
- [ ] A fresh clone runs mobile analyze (the package's type check) green with one
  documented command.
- [ ] Format check runs green with the documented command and fails on unformatted files.
- [ ] Analyzer configuration is committed with the chosen lint rules.
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
From the repository root run the documented commands: `flutter pub get --directory mobile` (or equivalent resolution step) followed by the documented `flutter analyze` in `mobile/` and the documented format check (e.g. `dart format --set-exit-if-changed mobile/`). All must exit 0.

## Attachments
* [Section 6.6 — Technology decisions summary](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.3 — Engineering approach](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The Flutter SDK may be absent on some machines (RISK-15 host differences); document
  the required SDK setup in `CONTRIBUTING.md` and let CI install a pinned version.
* Analyzer strictness must pass on the placeholder package; tune rules later with real
  code in WP-5.5 rather than lowering them now.
