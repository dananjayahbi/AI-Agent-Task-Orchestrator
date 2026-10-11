# MT-4.2-03 — Implement manifest download and copy UI

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.2-03 |
| Title | Implement manifest download and copy UI |
| Parent WP | WP-4.2 — Project switcher, project CRUD, manifest and tokens UI (Milestone M4) |
| Requirements | FR-PRJ-03 (downloadable `orchestrator.json` manifest for a project) |
| Priority | M |
| Dependencies | MT-4.2-01/02 (project exists in the UI flow), WP-4.1 (client), WP-1.3 (`GET /projects/{pid}/manifest`) |
| Parent sections | 10.3 (manifest shape, no secrets), 13.1 (Project settings), 19 (WP-4.2), 20.4, 20.5 |

## Context
FR-PRJ-03 requires a downloadable `orchestrator.json` manifest per project, served by
`GET /projects/{pid}/manifest` (Section 9.2). The manifest is the artifact that ties
a repository to the control plane: the bridge discovers it by walking up to the Git
root (Section 10.3) and the `init` command consumes it (FR-MCP-08). WP-4.2's
acceptance criterion is the end-to-end flow: "a new project's manifest can be
downloaded and used by `init` in one flow." This slice is the Project-settings UI
that makes that possible — download to `orchestrator.json`, plus copy-to-clipboard
for pasting into an existing repository.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /projects/{pid}/manifest`, callers Owner and
  agents-read-only-for-own-project.
* Parent plan Section 10.3 — extended manifest content (`schema_version`,
  `project_id`, `project_name`, `orchestrator_api`, `default_branch`,
  `auto_branch_prefix`, `audit_required_default`, `agent_hints`); "The manifest holds
  no secrets and is safe to commit."
* Parent plan FR-PRJ-03, FR-MCP-08 (`init` consumes the file).
* WP-4.1 — generated client and error mapping; MT-4.2-01/02 — project context in
  which the settings section renders.

## Scope (in)
* A manifest section in Project settings: "Download `orchestrator.json`" using the
  backend response as-is (no client-side field assembly — the server owns the
  manifest shape per Section 10.3), and "Copy to clipboard" for the same content.
* File naming: downloaded as `orchestrator.json` so it drops into a repository root
  unchanged (Section 10.3 discovery expects that name/path).
* A short usage note in the UI pointing at the next step: place the file at the
  repository root and run the bridge's `init` command (FR-MCP-08) — phrased as
  guidance only; no invented command flags.
* Safety note surfaced in the UI: the manifest contains no secrets and is safe to
  commit (Section 10.3) — while agent tokens are deliberately a separate flow
  (MT-4.2-04).
* Loading/error states (permission denied, project not found) mapped from canonical
  codes; component tests for download blob/name, copy behavior, and error states.

## Out of scope
* Generating manifest content client-side — server endpoint owns it (WP-1.3).
* The `init` command itself — WP-2.12 (FR-MCP-08).
* Agent token creation/management — MT-4.2-04 (tokens never appear in the manifest,
  Section 10.3 step 3).
* Manifest schema validation — bridge WP-2.2.
* Editing manifest fields in the UI — not a plan feature; project fields are edited
  via MT-4.2-02 forms and the server regenerates.

## Target paths
* `web/` (manifest download/copy section under Project settings)
* `web/` tests (component tests)
* WP changelog entry

## Acceptance criteria
- [ ] Downloading from Project settings produces a file named `orchestrator.json`
  whose content matches `GET /projects/{pid}/manifest` byte-for-byte (FR-PRJ-03).
- [ ] Copy-to-clipboard places the same manifest content, with a success
  acknowledgement.
- [ ] The UI states the manifest is secret-free and safe to commit, and never mixes
  token material into it (Section 10.3, Section 12.4).
- [ ] The documented flow "download → place at repo root → run `init`" is present
  and matches WP-4.2's acceptance path (new project's manifest usable by `init` in
  one flow).
- [ ] Error states (`AUTH_REQUIRED`, `AUTH_FORBIDDEN_PROJECT`, `TASK_NOT_FOUND`-style
  project-not-found per catalog) map to friendly messages (Section 13.3); tests pass
  in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the manifest UI component tests in `web/` (e.g.
`npm test -- manifest-download`), asserting file name/content fidelity, clipboard
copy, safety note presence and error-state mapping.

## Attachments
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-PRJ-03 — Downloadable manifest](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Assembling the manifest client-side would create a second source of truth that
  could drift from the bridge's expectations (Section 10.3/WP-2.2 validation) —
  download only what the server returns.
* Clipboard APIs can fail on non-secure origins; the copy path needs a tested
  fallback (selectable text) rather than a dead button.
