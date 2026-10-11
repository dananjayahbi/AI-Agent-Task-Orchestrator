# MT-0.1-02 — Configure Python Tooling for Backend and Bridge

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-02 |
| Title | Configure Python tooling (formatter, linter, type checker) for backend and bridge |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11 |
| Priority | M |
| Dependencies | MT-0.1-01 |
| Parent sections | 6.6, 19.1 (WP-0.1), 20.4 |

## Context
WP-0.1 requires consistent tooling across all packages, and its acceptance criterion is
that a fresh clone runs every package's lint and type check with one documented command
each. The backend (Django, Python 3.12+) and the bridge (Python, `uv`-managed — Section
6.6) are the two Python packages, and they must share the same formatter, linter and
type-checker conventions so CI (WP-0.3) can invoke them uniformly.

## Inputs / Prerequisites
* MT-0.1-01 — repository layout with `backend/` and `bridge/` in place.
* Parent plan Section 6.6 — backend on Python 3.12+; bridge `uv`-managed.
* Parent plan 19.1 WP-0.1 — deliverable "per-package tooling configs,
  formatter/linter/type-check setup"; acceptance "one documented command each".
* Tooling available in the environment: `uv` (or equivalent Python package runner).

## Scope (in)
* Configure formatter and linter for `backend/` and `bridge/` in each package's
  `pyproject.toml` (recommended default: Ruff for both format and lint; record the
  choice in `CONTRIBUTING.md`).
* Configure the type checker (recommended default: mypy) for both packages, with a
  baseline strictness that passes on the initial skeleton.
* Ensure the bridge is `uv`-managed with a lockfile, per Section 6.6 packaging.
* Add exactly one documented command per package for lint and one for type check
  (plus one format command), wired into `CONTRIBUTING.md`.
* Add a short note to the WP changelog (Section 20.4 item 7).

## Out of scope
* Running these tools in CI — MT-0.3-01.
* Pre-commit hook wiring — MT-0.1-05.
* Django/DRF dependencies and the real backend code — WP-1.1.
* Bridge source code and MCP SDK dependencies — WP-2.1.
* Web and mobile tooling — MT-0.1-03 and MT-0.1-04.

## Target paths
* `backend/pyproject.toml` (tooling configuration; app code arrives with WP-1.1)
* `bridge/pyproject.toml`, `bridge/uv.lock`
* `CONTRIBUTING.md` (documented one-command entries for backend and bridge)

## Acceptance criteria
- [ ] Formatter, linter and type checker are configured for both `backend/` and `bridge/`.
- [ ] A fresh clone runs backend lint and type check green with one documented command each.
- [ ] A fresh clone runs bridge lint and type check green with one documented command each.
- [ ] Format check runs green without modifying files.
- [ ] The same tool names and versions apply to both packages (no divergent configs).
- [ ] No secrets or environment-specific paths in configs (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
From a fresh clone run the documented commands: bridge via `uv run` (e.g. `uv run --directory bridge ruff check .` and the documented mypy invocation) and backend via its documented runner (e.g. `uv run --directory backend ruff check .` plus mypy). All must exit 0; the format check must report no changes.

## Attachments
* [Section 6.6 — Technology decisions summary](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-0.1](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The parent plan fixes the languages but not the linter/type-checker brands; choosing
  defaults (Ruff, mypy) is part of this task — record the choice in `CONTRIBUTING.md`
  so CI and hooks reuse the identical command (RISK-09 scope discipline).
* Backend dependencies do not exist until WP-1.1; the type-checker baseline must pass on
  an empty/near-empty package without pretending coverage that does not exist.
