# MT-5.5-01 — Scaffold the Flutter application with feature-first structure

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.5-01 |
| Title | Scaffold the Flutter application with feature-first structure |
| Parent WP | WP-5.5 — Flutter skeleton and API client (Milestone M5) |
| Requirements | NFR-11 (typed contract discipline starts here); NFR-07 (CI gates) |
| Priority | M |
| Dependencies | WP-0.1 (monorepo `mobile/` layout), WP-5.3 (device-auth backend flows, later MTs consume) |
| Parent sections | 14.1, 14.3, 19 (WP-5.5), 20.4, 20.5 |

## Context
WP-5.5's first slice creates the Flutter app itself. Section 14.3 fixes the
engineering approach: "feature-first folders," a single predictable state-management
pattern, generated API client from the shared OpenAPI schema, flavor configs, widget
tests and integration tests against a mocked backend. Section 14.1 lists the screen
areas the structure must host — Onboarding, Home/Overview, Board, Task detail,
Review sheet, Notifications, Audit log, Settings. Getting the skeleton right gives
every later mobile WP (5.6 through 5.10) a stable home for its code and a CI-checked
baseline (lint, type check, tests).

## Inputs / Prerequisites
* Parent plan Section 14.1 — navigation and screen areas (the feature list).
* Parent plan Section 14.3 — engineering approach: feature-first folders, single
  state-management pattern, generated client, flavors, widget/integration tests,
  release signing documented later (WP-5.10).
* Parent plan Appendix A (via WP-0.1) — `mobile/` package location in the monorepo.
* WP-0.1 — mobile tooling (formatting, linting, type checks) configured in M0.

## Scope (in)
* A runnable Flutter application in `mobile/` (both platforms build in debug):
  app entry point, theme baseline, and top-level navigation shell hosting the
  Section 14.1 areas as feature folders.
* Feature-first directory structure — one folder per Section 14.1 area (onboarding,
  home, board, task_detail, review, notifications, audit_log, settings) with a
  shared layer for networking, models, storage and utils beneath them.
* One documented state-management pattern chosen and applied consistently (Section
  14.3 requires a single predictable pattern; the plan does not name a library —
  record the choice in the changelog as a WP-level decision, not an ad-hoc per-file
  choice).
* Placeholder screens wired to navigation so every route renders and is testable;
  empty-state first, no mocked business logic pretending to be real.
* Widget tests for navigation shell integrity (each Section 14.1 area reachable)
  and CI wiring running format/lint/analyze/tests for `mobile/`
  (Section 20.4 item 2).

## Out of scope
* Environment flavors and endpoints — MT-5.5-02.
* Generated API client — MT-5.5-03.
* Secure storage and biometric gate — MT-5.5-04.
* SSE client — MT-5.5-05.
* Onboarding flow logic (URL/login/device registration behavior) — MT-5.5-06; real
  screens' data wiring — WP-5.6/5.7/5.8.
* Push notifications, release signing — WP-5.4, WP-5.10.

## Target paths
* `mobile/` (Flutter project: entry point, navigation shell, feature folders)
* `mobile/` test directory (widget tests)
* CI pipeline config (mobile lint/analyze/test jobs)
* WP changelog entry

## Acceptance criteria
- [ ] The app builds and runs in debug on both platforms with the navigation shell
  rendering all Section 14.1 areas (WP-5.5 deliverable: app shell).
- [ ] Feature-first folders exist per Section 14.1 with a shared layer beneath them;
  the structure is documented in the package README (Section 14.3).
- [ ] Exactly one state-management pattern is in use and documented (Section 14.3).
- [ ] Placeholder screens contain no fake business data presented as real; loading
  and empty states are honest defaults (Section 20.3 state discipline).
- [ ] Format/lint/analyze/tests run green in CI for `mobile/`
  (Section 20.4 item 2); no secrets or env-specific paths committed (item 3).
- [ ] Changelog note added, including the state-management choice rationale
  (item 7).

## Test command
From `mobile/`, run the scaffold checks: `flutter analyze` plus
`flutter test`; CI runs the same. Navigation widget tests must find every
Section 14.1 area.

## Attachments
* [Section 14.1 — Navigation and screens](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.3 — Engineering approach](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan deliberately does not name a state-management library — record the
  selection as a WP-5.5 decision with rationale; changing it later is a cross-cutting
  refactor, so choose with Section 14.3's "single predictable pattern" in mind.
* Scaffolding too much (full screens with stubbed API calls) invites fake-data
  habits that survive into production code; keep placeholders empty and honest.
