# MT-0.1-05 — Add Pre-commit Hooks Enforcing Format, Lint, and Secret Scans

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.1-05 |
| Title | Add pre-commit hooks enforcing format, lint, and secret scans |
| Parent WP | WP-0.1 — Monorepo scaffolding and tooling (Milestone M0) |
| Requirements | NFR-11; NFR-07 (secret scanning baseline, see Section 18) |
| Priority | S |
| Dependencies | MT-0.1-02, MT-0.1-03, MT-0.1-04 |
| Parent sections | 12.4, 18, 19.1 (WP-0.1), 20.4, 21 (RISK-08) |

## Context
WP-0.1 lists pre-commit hooks among its deliverables. Section 18 requires secret
scanning as a quality gate, and RISK-08 calls for conservative patterns plus
config-file globs as the first line of defense. Hooks running the exact tooling
commands from MT-0.1-02..04 give contributors an immediate local gate before CI
(WP-0.3) enforces the same checks remotely.

## Inputs / Prerequisites
* MT-0.1-02 (Python tooling commands), MT-0.1-03 (web tooling commands),
  MT-0.1-04 (mobile tooling commands) — hooks call the documented commands.
* Parent plan Section 18 — quality gates include dependency and secret scans.
* Parent plan Section 12.4 — data protection; Section 21 RISK-08/RISK-14 (secret leaks).
* A hooks framework available (e.g. `pre-commit` framework) and a secret scanner
  (e.g. gitleaks or an equivalent conservative-pattern scanner).

## Scope (in)
* Add a root hook configuration that runs on commit: format check, lint, and type check
  for the staged package(s), reusing the exact commands documented in `CONTRIBUTING.md`.
* Add a secret-scan hook covering staged files with conservative patterns and config-file
  globs (RISK-08), including `.env`-style files so real values can never be staged.
* Document the one-command hook installation in `CONTRIBUTING.md`.
* Verify hooks block a deliberately failing staged file and a fake credential pattern
  (removed immediately afterwards; nothing fake is committed).
* Add a WP changelog note.

## Out of scope
* CI enforcement of the same gates — WP-0.3 (MT-0.3-01, MT-0.3-04).
* Optional external/managed secret scanner integration — RISK-08 mitigation scheduled
  for M3.
* Full security review and penetration testing — WP-6.1.
* Fixing lint issues in application code that does not exist yet — later WPs.

## Target paths
* `.pre-commit-config.yaml` (root hook definition)
* `.gitleaks.toml` or equivalent scanner config (if the chosen scanner needs one)
* `.gitignore` (ensure `.env` and secret files are excluded)
* `CONTRIBUTING.md` (hook installation command)
* WP changelog entry

## Acceptance criteria
- [ ] One documented command installs the hooks on a fresh clone.
- [ ] Running the hooks across all files passes green on the current tree.
- [ ] A staged file violating format or lint is rejected by the hook (verified then reverted).
- [ ] A staged file containing a fake credential pattern is rejected by the secret scan
  (verified then removed; Section 20.4 item 3).
- [ ] Hook commands are identical to the documented per-package commands (single source).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Install hooks with the documented command, then run them over the whole tree (e.g. `pre-commit run --all-files`) and confirm exit 0. Then stage a throwaway file with a known fake credential string, attempt to commit, confirm the secret scan blocks it, and unstage/delete the file so the tree is clean.

## Attachments
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.4 — Data protection](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* RISK-08: pattern-based secret detection misses leaks — hooks are a conservative
  baseline only; human review of config changes remains required.
* Hook runtime cost grows with the monorepo; keep hooks scoped to staged files and
  revisit if commit latency becomes painful (Section 20.3 sizing spirit).
