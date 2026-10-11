# MT-0.3-01 — Add Lint and Type-Check Jobs for Every Package

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.3-01 |
| Title | Add lint and type-check jobs for every package |
| Parent WP | WP-0.3 — CI pipeline (Milestone M0) |
| Requirements | NFR-07, NFR-11 |
| Priority | M |
| Dependencies | MT-0.1-02, MT-0.1-03, MT-0.1-04 |
| Parent sections | 18, 19.1 (WP-0.3), 20.4 |

## Context
WP-0.3 automates the quality gates defined in Section 18, whose first entries are lint
and type checks, with the rule that a failing gate blocks merge. This task creates the
CI jobs that invoke the exact per-package commands documented in WP-0.1, for backend,
bridge, web and mobile, and seeds the schema-diff placeholder named in WP-0.3's
deliverables (real migrations appear with WP-1.1).

## Inputs / Prerequisites
* MT-0.1-02/03/04 — the documented one-command lint and type-check commands per package.
* MT-0.1-05 — hook commands (same commands, so CI and hooks stay identical).
* Parent plan Section 18 — quality gates list: lint, type checks, unit and integration
  tests, migration check, schema diff check, container build, dependency and secret
  scans.
* Parent plan 19.1 WP-0.3 — acceptance: failing a gate blocks merge; pipeline under
  10 minutes for the skeleton.
* Repository CI platform (GitHub Actions workflows under `.github/workflows/` unless
  the repository standard differs — record the choice).

## Scope (in)
* Create the CI workflow with a lint job and a type-check job covering all four
  packages: `backend/`, `bridge/`, `web/`, `mobile/`, calling the documented commands.
* Add a migration/schema-diff placeholder job that passes now and becomes a real check
  when Django models arrive (WP-1.1).
* Configure the jobs as required status checks so a failing gate blocks merge
  (branch protection / required checks).
* Ensure CI runs on pull requests and pushes to the main branch.
* Add a WP changelog note.

## Out of scope
* Unit and integration test jobs — MT-0.3-02.
* Container build job — MT-0.3-03.
* Dependency and secret scanning — MT-0.3-04.
* Caching optimizations — MT-0.3-05.
* Writing lint fixes for application code — belongs to each feature WP.

## Target paths
* `.github/workflows/` (or the repository's CI directory) — lint/type-check workflow
* `CONTRIBUTING.md` (note that CI runs the same documented commands)
* WP changelog entry

## Acceptance criteria
- [ ] Lint and type-check jobs exist and cover backend, bridge, web and mobile.
- [ ] Jobs invoke the same documented commands used by WP-0.1 and the hooks.
- [ ] A migration/schema-diff placeholder job exists and passes (Section 18 deliverable).
- [ ] Jobs are required checks: a PR failing lint is blocked from merging
  (WP-0.3 acceptance).
- [ ] No secrets or environment-specific paths in workflow files (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Open a pull request that deliberately violates lint (a throwaway branch with a
trivially unformatted/failing file) and confirm the required check reports failure and
merge is blocked; push the correction and confirm lint and type-check jobs pass green.

## Attachments
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-0.3](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The CI platform is not named in the parent plan — confirm GitHub Actions (repository
  host) and record it; a different platform changes file location only, not gates.
* Mobile jobs need the Flutter SDK on the runner; pin the SDK version to avoid runner
  drift (RISK-15 cross-host differences).
