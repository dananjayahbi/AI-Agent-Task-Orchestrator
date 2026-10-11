# MT-2.2-01 — Implement Upward Manifest Discovery

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.2-01 |
| Title | Implement upward manifest discovery |
| Parent WP | WP-2.2 — Manifest discovery and session binding (Milestone M2) |
| Requirements | FR-MCP-02 |
| Priority | M |
| Dependencies | MT-2.1-01/MT-2.1-02 (package + config override hook), WP-2.12 (writes the manifest this reads) |
| Parent sections | 10.1 (manifest resolution), 10.3 (discovery steps 1–2), 19.1 (WP-2.2 first slice), 20.4, 20.5 |

## Context
Section 10.3 states the algorithm in one sentence: "resolution walks up from the
current directory to the Git root, finding `orchestrator.json`" — with the glossary
confirming the filename (`orchestrator.json` at the repo root, one per repo). WP-2.2's
first slice is "upward discovery," and its acceptance begins "repo subfolder binds
correctly": an agent launched from a nested directory must resolve the same manifest
as one launched from the root, because per-repo binding (FR-MCP-02) is meaningless if
discovery depends on cwd luck. Steps 1–2 of Section 10.3 (discover, then validate vs.
published schema) are split here (discovery) and in MT-2.2-02 (validation); steps 3–5
(token, session open, cache) follow in MT-2.2-03 … 05. The walk terminates at the Git
root — not the filesystem root — so unrelated parent directories never leak manifests
into a different repo's session.

## Inputs / Prerequisites
* MT-2.1-01 / MT-2.1-02 — `bridge/` package, config (for a test-only explicit
  manifest path override; production discovery is the upward walk).
* Parent plan Section 10.3 — the walk algorithm and filename; glossary entry for
  `orchestrator.json`.
* WP-2.12 — creates manifests for new repos (this reader is its counterpart; schema
  file comes from there or from `schemas/`).
* Section 10.1 — manifest resolution as a bridge responsibility.
* A boundary case the plan leaves implicit: what happens when no manifest is found —
  Section 10.3's flow assumes one exists (init creates it); discovery must fail with
  a clear, actionable message naming `orchestrator init` rather than proceeding
  unbound (recorded as this task's decision, verified against WP-2.12's UX).

## Scope (in)
* The upward walk: start at cwd, look for `orchestrator.json`, move to the parent
  directory, stop at (and including) the Git repository root — `.git` detection
  defines the ceiling; beyond it, "not found."
* Git-root determination that works with worktrees/submodules cautiously: if `.git`
  is a file (worktree/submodule pointer), treat its location as the root boundary and
  record the behavior in tests; do not walk past it.
* A test-only explicit path override (config/env from MT-2.1-02) that bypasses the
  walk — required for tests and non-repo invocations; production flow never uses it
  (keep FR-MCP-02's repo-bound semantics intact).
* Not-found behavior: fail fast with a structured message telling the user to run
  init (Section 10.11's command), logged via MT-2.1-03; no silent fallback to an
  unbound session (per-repo binding is the requirement).
* Found behavior: return the manifest's absolute path and raw parsed JSON (parsing
  for validation is MT-2.2-02's; this task only locates and reads bytes/JSON
  structurally — keep the seam clean).
* Tests: nested-subfolder resolution to the same file as root; stop-at-Git-root (a
  decoy `orchestrator.json` above the repo is ignored); worktree pointer; no-manifest
  error message; override path; changelog note (Section 20.4 item 7).

## Out of scope
* Schema validation, version compatibility — MT-2.2-02 (Section 10.3 step 2).
* Token loading and session open/end — MT-2.2-03 / MT-2.2-04.
* Project mismatch handling — MT-2.2-05.
* Creating/editing the manifest — MT-2.12-01 (WP-2.12).
* Backend-side manifest publication or schema hosting details beyond "published
  schema" reference — Section 10.3 step 2 owns the contract; hosting is backend's
  concern (WP-1.x).
* Searching alternate locations (user-level, env-specified manifest in production) —
  not in the plan; config override is test-only here.

## Target paths
* `bridge/` manifest-resolution module (Section 10.1 seam from MT-2.1-01)
* `bridge/tests/` (discovery fixtures: nested dirs, decoy above repo, worktree
  pointer, missing manifest)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Discovery walks up from cwd to the Git root and finds `orchestrator.json`
  there — Section 10.3 step 1 verbatim (FR-MCP-02).
- [ ] A subfolder of the repo resolves the identical manifest as the repo root —
  WP-2.2 acceptance first half, "repo subfolder binds correctly."
- [ ] The walk never crosses the Git root; a decoy manifest above the repo is ignored
  (Section 10.3 "to the Git root").
- [ ] Missing manifest fails fast with a message naming `orchestrator init`; no
  unbound session proceeds (Section 10.3 flow; WP-2.12 counterpart).
- [ ] Test-only override bypasses the walk without changing production semantics
  (FR-MCP-02 preserved).
- [ ] Tests, lint and type check green in CI (Section 20.4 items 1–2); no secrets or
  environment-specific paths (item 3); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_manifest_discovery.py -v` — nested
resolution, Git-root stop with decoy above, worktree pointer, missing-manifest
message, override path; `uv run --directory bridge ruff check .` green.

## Attachments
* [Section 10.3 — Manifest discovery and binding](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-MCP-02 — Repo-bound agent session](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Init command (counterpart)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Monorepos with nested packages: the plan says one `orchestrator.json` per repo at
  the root — discovery must not stop at a nested `package.json`-style boundary the
  plan does not mention; document the "first `orchestrator.json` up to Git root"
  rule explicitly (if a nested manifest is found first, that IS the nearest one —
  state which reading is implemented: first-found wins, ceiling = Git root).
* The no-manifest error message naming init couples this task to WP-2.12's command
  name — use the Section 10.11 name (`orchestrator init` per FR-MCP-08) and keep the
  string in one constant so a later rename does not scatter.
* `.git` absence (exported source tree, tarball) makes the ceiling undefined —
  without a Git root the walk would hit the filesystem root; cap it there and fail
  with the same not-found message, recording this edge in the changelog.
