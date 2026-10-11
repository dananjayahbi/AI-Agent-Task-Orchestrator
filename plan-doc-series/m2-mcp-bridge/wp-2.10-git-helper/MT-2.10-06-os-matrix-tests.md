# MT-2.10-06 — Write OS matrix tests (Windows, macOS, Linux; paths with spaces)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-06 |
| Title | Write OS matrix tests (Windows, macOS, Linux; paths with spaces) |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07; NFR-07 (CI quality gates, via Section 18) |
| Priority | M |
| Dependencies | MT-2.10-01..05 (all helper capabilities implemented); WP-0.3 (CI pipeline) |
| Parent sections | 10.8, 18 (Unit/Contract rows), 19 (WP-2.10), 20.4, 20.5 |

## Context
WP-2.10's acceptance criterion is explicitly cross-platform: the helper "works on
repos with spaces in paths and on all three host operating systems that are supported;
never pushes or deletes." Agents run on developer machines — the compatibility matrix
clients (Section 10.9) span Windows, macOS and Linux, and Windows path handling
(backslashes, drive letters, spaces, quoting) is where Git wrappers classically
break. This final slice of WP-2.10 makes the whole helper suite prove that on the CI
matrix rather than on a single developer's OS.

## Inputs / Prerequisites
* Parent plan Section 19 WP-2.10 — acceptance: spaces in paths, three host OSes,
  never pushes or deletes.
* Parent plan Section 18 — test strategy and CI quality gates.
* MT-2.10-01..05 — identity/state, branch naming, merge-base diff, secret scan,
  worktree helper under test.
* WP-0.3 — CI pipeline to host the matrix jobs.

## Scope (in)
* Fixture repositories created under paths containing spaces (and, on Windows,
  non-ASCII characters) exercising every helper capability against them: identity,
  status, branch create/switch, merge-base diff/stats/changed files, secret scan,
  worktree create/lookup when enabled.
* A CI matrix running the bridge Git-helper suite on Windows, macOS and Linux,
  failing the pipeline on any leg (Section 18 quality gates, NFR-07).
* Path-handling assertions: repository-relative output paths use forward slashes
  regardless of OS (the MT-2.10-03 normalization contract), and command invocation
  survives spaces/quoting without shell interpolation (MT-2.10-01 guard).
* A regression sentinel test asserting the allowlist still rejects push/reset/delete
  on every OS (the Section 10.8 guarantee is platform-independent).
* Skips handled honestly: any capability genuinely untestable on an OS is skipped
  with a named reason in the report, never silently passing.

## Out of scope
* Implementing or fixing helper capabilities — MT-2.10-01..05 own the code; this
  task reports matrix failures back to them (fixes land in the owning slice).
* End-to-end agent-client runs per OS — WP-2.11.
* Mobile/web platform testing — their WPs.
* Performance benchmarking — Section 18 performance layer.

## Target paths
* `bridge/tests/` (matrix-safe fixtures and path-handling assertions)
* CI pipeline config (Windows/macOS/Linux matrix jobs)
* WP changelog entry

## Acceptance criteria
- [ ] The Git-helper suite passes on Windows, macOS and Linux in CI, including
  repositories whose paths contain spaces (WP-2.10 acceptance, Section 18).
- [ ] Changed-file and diff outputs are asserted to use forward-slash,
  repository-relative paths on every OS.
- [ ] The push/reset/delete rejection sentinel runs and passes on all three OS legs
  (Section 10.8, "never pushes or deletes").
- [ ] Any OS-specific skip is explicitly named with a reason in the test output —
  no silent skips (Section 20.4 item 1: acceptance demonstrably met).
- [ ] Lint, type check and tests green in CI across the matrix
  (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the helper suite with the space-path fixtures on each OS leg of the CI matrix
(e.g. `uv run pytest bridge/tests/ -k "git_helper or space_path"` locally, plus the
pipeline matrix job); all three legs must be green.

## Attachments
* [Section 19 — WP-2.10 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Windows legs are slower and flakier (file locks on Git objects); retries must not
  mask real failures — stabilize fixtures rather than adding retry-until-green.
* Fixture creation itself can hide path bugs (a fixture that avoids spaces proves
  nothing); assert the fixture path really contains a space before running
  assertions against it.
