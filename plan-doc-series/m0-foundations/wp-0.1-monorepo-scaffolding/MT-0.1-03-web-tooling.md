# MT-0.1-03 — Configure Web Tooling and Package Scripts

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-03 |
| Title | Configure web tooling and package scripts for the Next.js app |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11 |
| Priority | M |
| Dependencies | MT-0.1-01 |
| Parent sections | 6.6, 13, 19.1 (WP-0.1), 20.4 |

## Context
The web package is a Next.js (App Router) application per Section 6.6, and WP-0.1's
acceptance requires every package — including `web/` — to run lint and type check from
a fresh clone with one documented command each. This task establishes the npm scripts
and tool configuration that WP-0.3 CI jobs will call, before any UI feature work starts
in WP-4.1.

## Inputs / Prerequisites
* MT-0.1-01 — `web/` directory in the repository layout.
* Parent plan Section 6.6 — Next.js (App Router), React, Tailwind CSS, shadcn/ui.
* Parent plan Section 13 — web client design (context only; no UI built here).
* Node.js and the chosen package manager available in the environment (package manager
  choice is recorded in `CONTRIBUTING.md`).

## Scope (in)
* Initialize `web/package.json` with scripts: `lint`, `typecheck` (TypeScript check with
  no emit), `format`, and `format:check`.
* Add the ESLint configuration (flat config compatible with Next.js) and Prettier
  configuration at the `web/` package level.
* Add the TypeScript configuration so `typecheck` runs green on the initial package.
* Add a minimal placeholder Next.js package skeleton sufficient for the tooling commands
  to run (not the full app — that is WP-4.1).
* Document the single web commands in `CONTRIBUTING.md` and add a WP changelog note.

## Out of scope
* Information architecture, components, pages, state handling — WP-4.1 onwards.
* Component tests, end-to-end web flows — WP-4.11 and WP-0.3 test jobs.
* Backend API wiring — depends on M1 endpoints.
* CI job wiring — MT-0.3-01.
* Pre-commit hook wiring — MT-0.1-05.

## Target paths
* `web/package.json` (scripts), `web/package-lock.json` or equivalent lockfile
* `web/eslint.config.*` (ESLint configuration)
* `web/.prettierrc*` / `web/prettier.config.*` (Prettier configuration)
* `web/tsconfig.json` (TypeScript configuration)
* `CONTRIBUTING.md` (documented one-command entries for web)
* WP changelog entry

## Acceptance criteria
- [ ] `lint`, `typecheck`, and `format:check` scripts exist in `web/package.json`.
- [ ] A fresh clone runs web lint green with one documented command.
- [ ] A fresh clone runs web type check green with one documented command.
- [ ] Format check exits 0 without modifying files.
- [ ] The lockfile is committed so installs are reproducible.
- [ ] No secrets or environment-specific paths committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
From the repository root run the documented web commands, e.g. `npm --prefix web run lint`, `npm --prefix web run typecheck`, and `npm --prefix web run format:check` (or the equivalent with the chosen package manager). All must exit 0.

## Attachments
* [Section 6.6 — Technology decisions summary](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13 — Web Client Design](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The package manager (npm vs pnpm vs yarn) is not fixed by the parent plan; pick one,
  record it in `CONTRIBUTING.md`, and keep CI (MT-0.3-01) consistent with it.
* The placeholder skeleton must not pre-empt WP-4.1's app structure; keep it minimal to
  avoid rework (Section 20.3: keep scaffolding separate from features).
