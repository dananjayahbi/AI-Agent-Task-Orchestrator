# MT-0.1-01 — Define the Monorepo Root Layout and Package Boundaries

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-01 |
| Title | Define the monorepo root layout and package boundaries per parent plan Appendix A |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11; ADR-001 (context for the single-repo decision) |
| Priority | M |
| Dependencies | none (repository initialized) |
| Parent sections | 0, 19.1 (WP-0.1), 20.4, 23 (ADR-001), Appendix A |

## Context
WP-0.1's first slice fixes the physical repository layout so every later micro-task's
target paths resolve against a stable structure. ADR-001 commits the project to a single
monorepo, and Appendix A is the authoritative layout this task implements. Nothing else
in M0 can land reliably until the folder structure and package boundaries exist.

## Inputs / Prerequisites
* Parent plan Appendix A — Proposed Repository Layout (the exact directory tree).
* Parent plan Section 0.2/0.4 — identifier and naming conventions.
* Parent plan Section 23 — ADR-001 (single monorepo for all packages).
* Parent plan 19.1 WP-0.1 — deliverables: folder structure, per-package tooling configs,
  formatter/linter/type-check setup, pre-commit hooks, contribution notes.

## Scope (in)
* Create every top-level directory in Appendix A: `docs/` (with `plan/`, `adr/`,
  `runbooks/`, `agent-guides/`), `backend/` (with `apps/` and `tests/`), `bridge/`
  (with `src/`, `capability_table/`, `tests/`), `web/`, `mobile/`, `schemas/`,
  `infra/` (with `compose/`, `cloudflare/`, `backup/`), and `e2e/`.
* Create the backend `apps/` sub-packages listed in Appendix A as placeholders
  (`accounts`, `projects`, `tasks`, `leases`, `attachments`, `audit`, `merge`,
  `events`, `notifications`, `agents`, `core`).
* Write package-boundary notes: which package owns which responsibility (backend never
  touches repos per P2/ADR-007; bridge owns host-side Git evidence; web/mobile are
  API-only clients; `schemas/` holds shared contracts).
* Add a root `README.md` and `CONTRIBUTING.md` skeleton that document the one-command
  entry point per package (commands themselves are filled by MT-0.1-02..04).
* Add a short note to the M0 changelog per Section 20.4 item 7.

## Out of scope
* Tooling configuration files — MT-0.1-02 (Python), MT-0.1-03 (web), MT-0.1-04 (mobile).
* Pre-commit hooks — MT-0.1-05.
* Documentation content beyond the skeleton — MT-0.1-06 and WP-6.5.
* Compose files and environment templates — WP-0.2.
* Real application code (Django project, Next.js app, Flutter app) — WP-1.1, WP-4.1,
  WP-5.5.

## Target paths
* `README.md`, `CONTRIBUTING.md` (root)
* `docs/plan/`, `docs/adr/`, `docs/runbooks/`, `docs/agent-guides/`
* `backend/apps/` (11 app placeholders), `backend/tests/`
* `bridge/src/`, `bridge/capability_table/`, `bridge/tests/`
* `web/`, `mobile/`, `schemas/`
* `infra/compose/`, `infra/cloudflare/`, `infra/backup/`
* `e2e/`

## Acceptance criteria
- [ ] Every directory in Appendix A exists at its documented location.
- [ ] The 11 backend app placeholders exist under `backend/apps/`.
- [ ] Package boundaries are documented in `CONTRIBUTING.md` (one section per package).
- [ ] `README.md` links to `docs/plan/` and names the per-package command locations.
- [ ] Fresh clone contains no secrets and no environment-specific paths (Section 20.4 item 3).
- [ ] A changelog note records the layout decision (Section 20.4 item 7).

## Test command
Run a layout verification from the repository root: confirm each Appendix A path exists
(e.g. a `Test-Path` loop over the Appendix A path list on PowerShell, or `git ls-files`
grouped per top-level package after committing), then `git status` shows a clean tree.

## Attachments
* [Appendix A — Proposed Repository Layout](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 23 — ADR-001](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Placeholder app directories can confuse later tooling (linters scanning empty packages);
  keep placeholders minimal and documented so WP-1.1 replaces them cleanly.
* Appendix A shows the tree without root-level config files; MT-0.1-02..05 add them —
  do not pre-create conflicting configs here.
