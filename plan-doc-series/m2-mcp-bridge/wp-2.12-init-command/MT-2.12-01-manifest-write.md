# MT-2.12-01 — Write the Manifest (`orchestrator init`)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.12-01 |
| Title | Write the manifest (`orchestrator init`) |
| Parent WP | WP-2.12 — Init command (Milestone M2) |
| Requirements | FR-MCP-08 |
| Priority | M |
| Dependencies | MT-2.2-02 (shared manifest schema), MT-2.1-04 (entry-point stubs to wrap), MT-2.1-02 (config for API endpoint) |
| Parent sections | 10.11 (init steps), 10.3 (manifest shape/validation), 19.1 (WP-2.12 first slice), 20.4 (items 1–7), 20.5; Appendix A (agent-guides) |

## Context
FR-MCP-08: "`orchestrator init` bootstraps an `orchestrator.json` manifest at the
repository root, stores the agent's token in user-level config, and runs a
self-test." Section 10.11 expands init into three duties (manifest write — this
task; token storage — MT-2.12-02; self-test — MT-2.12-03) plus a fourth output,
"per-client config snippets" (MT-2.12-04). WP-2.12's acceptance frames the bar:
"new repo usable by agent in under 2 minutes" — so init must be one command, no
manual editing. The manifest written here is the file MT-2.2-01 discovers, MT-2.2-02
validates against the **shared** schema (Section 19.6: one schema, writer and
validator both consume it), and MT-2.2-05 compares project ids from. Section 10.3's
JSON example (project id, name, API/manifest version, created timestamp) plus
MT-2.2-02's frozen field set defines the content; the file lands at the Git
repository root, repo-tracked — which is precisely why FR-SEC-04 forbids secrets in
it.

## Inputs / Prerequisites
* MT-2.2-02 — the shared `orchestrator.json` schema (single source for this writer).
* MT-2.1-04 — entry points / CLI wiring the command hangs off (Section 10.11's
  `orchestrator` CLI surface; full CLI packaging may be a later WP — expose the
  command as a module entry now).
* MT-2.1-02 — config: backend API endpoint used to create/look up the project,
  existing config file location (MT-2.12-02 writes the token into it).
* Parent plan Section 10.11 — init's three duties and outputs; Section 10.3 — the
  manifest JSON example; glossary — filename and one-per-repo rule.
* WP-2.12 acceptance — "under 2 minutes" (interactive defaults, minimal prompts).

## Scope (in)
* The `orchestrator init` command: run at the repo root (or any subdirectory — it
  resolves the Git root the same way MT-2.2-01's walk does and writes
  `orchestrator.json` **at the root**; Section 10.11).
* Manifest content per the shared schema and Section 10.3's example: project id,
  project name, API/manifest version, created timestamp — generated with sensible
  interactive defaults (prompt for project name; default the id from the created
  project or the provided API endpoint) so the "under 2 minutes" acceptance holds.
  **No token, no secret, no absolute user path** goes into the file (FR-SEC-04;
  Section 20.4 item 3).
* Project resolution flow: talk to the configured backend API (MT-2.1-02 endpoint)
  to create or select the project and obtain its id — the backend is the source of
  truth for project identity (Section 19.3: no client-side project derivation);
  offline/no-backend behavior: fail with a clear message (init's remaining steps
  need the API anyway) unless a documented test override is set.
* Overwrite safety: if `orchestrator.json` already exists, confirm before replacing
  (never silently clobber a bound repo); `--force` or equivalent re-runs the
  remaining init steps without rewriting when unchanged.
* Output: print the manifest path and next steps (token storage and self-test are
  MT-2.12-02/03 — chain them in the same invocation once those land; for this slice,
  exit cleanly after a validated write).
* Round-trip proof: the written file passes MT-2.2-02's validator (conformance
  test); open the file permissions note for the companion user-config (MT-2.12-02).
* Tests: write at root from a subdirectory; overwrite confirmation; no-secrets
  assertion (fixture scan); validator round-trip; changelog note (Section 20.4
  item 7).

## Out of scope
* Token storage in user-level config — MT-2.12-02 (FR-MCP-08 second duty).
* Connectivity self-test — MT-2.12-03; per-client config snippets — MT-2.12-04.
* The manifest schema definition itself — MT-2.2-02 owns the shared schema.
* Discovery/reading — MT-2.2-01 … 02 (this task's counterpart only writes).
* Backend project-creation endpoint design — if the M1 API lacks a project
  create/select endpoint usable by init, that is a dependency gap to surface as a
  new OQ (`OQ-15+`), not to paper over with local-only ids.
* Full CLI framework/packaging (installer, `npx`-style distribution) — Section 10.11
  packaging is a later WP.

## Target paths
* `bridge/` init command module (CLI entry alongside MT-2.1-04's entry points;
  declared in `bridge/pyproject.toml`)
* Shared `orchestrator.json` schema (from MT-2.2-02 — referenced, not duplicated)
* `bridge/tests/` (init write tests: root resolution, overwrite, secret scan,
  validator round-trip)
* `agent-guides/` — note the command in the agent-grogetting guide only if one
  already covers setup (Appendix A; do not create new top-level docs beyond the
  assigned file set)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] `orchestrator init` writes a schema-valid `orchestrator.json` at the Git
  repository root from any working subdirectory — FR-MCP-08 first duty; Section
  10.11 (validator round-trip test proves it).
- [ ] The manifest contains only non-secret binding fields (project id/name, version,
  timestamp) — no token, no environment-specific paths (FR-SEC-04; Section 20.4
  item 3).
- [ ] Project id comes from the backend API, not client derivation (Section 19.3);
  no-backend invocation fails with a clear message.
- [ ] Existing manifests are never clobbered without confirmation (overwrite guard
  tested).
- [ ] Command completes its write step quickly enough for the WP's "under 2 minutes"
  end-to-end target — measured in MT-2.12-04's overall flow (record timing in the
  changelog) (WP-2.12 acceptance).
- [ ] Tests, lint and type check green in CI (Section 20.4 items 1–2); changelog
  note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_init_manifest.py -v` — root write from
subdir, overwrite guard, secret scan of output file, validator round-trip;
`uv run --directory bridge ruff check .` green; the 2-minute end-to-end flow is
exercised with MT-2.12-04.

## Attachments
* [FR-MCP-08 — Init command](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Init and packaging](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.3 — Manifest JSON example](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Field-set drift between this writer and MT-2.2-02's validator is the classic
  integration bug — the round-trip test (writer output → validator) must be in CI
  from day one; both tasks must reference the single schema file, never local copies.
* Backend project creation may not exist in the M1 API surface for an unauthenticated
  or differently-authenticated init flow (init runs *before* token storage per
  FR-MCP-08 ordering) — determine which endpoint and credential the plan intends for
  project lookup; if ambiguous, raise `OQ-15+` rather than inventing an anonymous
  project-creation API.
* The "created timestamp" (Section 10.3 example) makes the manifest non-hermetic —
  tests must not assert exact timestamps; assert format only, and consider that
  re-running init changes the file (overwrite guard matters more than idempotent
  bytes).
