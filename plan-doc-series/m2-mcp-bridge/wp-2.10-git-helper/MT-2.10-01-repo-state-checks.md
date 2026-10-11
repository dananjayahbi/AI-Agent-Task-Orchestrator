# MT-2.10-01 — Implement repository identity and clean-state checks

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-01 |
| Title | Implement repository identity and clean-state checks |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07 (collect Git evidence locally) |
| Priority | M |
| Dependencies | WP-2.1 (bridge skeleton), WP-2.2 (manifest discovery establishes the repo root) |
| Parent sections | 10.8, 12.3, 19 (WP-2.10), 20.4, 20.5 |

## Context
Section 10.8 opens the Git helper's capability list with "verify repository identity
and clean state" — the foundation every later capability (branch derivation, merge-base
diff, secret scan, submission verification) builds on. The helper must establish that
the working directory really is the expected repository (the one the manifest bound to
the session) and report the state of the working tree before it is asked to create
branches or compute evidence for submission. Section 12.3's path rules matter here:
payload and path handling must never allow traversal outside the repo root. The helper
is read-mostly: only read operations plus branch creation, never push, force-reset, or
delete (Section 10.8).

## Inputs / Prerequisites
* Parent plan Section 10.8 — helper capabilities and the read-only-plus-branch
  restriction.
* Parent plan Section 10.3 — manifest discovery walking to the Git root; the session
  is bound to that repository.
* Parent plan Section 12.3 — path normalization and traversal rejection at the repo
  root.
* Parent plan Section 9.4 rule R5/SWP-2.6 — clean-state expectations feed submission
  evidence (branch/sha verification in WP-2.6).
* WP-2.1 — bridge package and its `bridge/src/` layout.

## Scope (in)
* A repository-identity function: from the bound session's root, confirm a Git
  repository exists, resolve its top-level directory, and confirm it matches the
  manifest-discovered root (mismatch → clear structured error, no Git invocation
  beyond identification).
* A clean-state check: report whether the working tree has uncommitted changes and
  untracked files, and whether a merge/rebase is in progress, as structured fields
  (clean boolean, counts, short status summary) — surfaced for tool/workflow use,
  not enforced here.
* Path safety: all Git invocations are executed with the repository root as the
  working directory and validated inputs; no shell string concatenation (arguments
  passed as arrays), no operation outside the repo root (Section 12.3).
* Capability guard: a shared invocation wrapper that whitelists read-only Git
  subcommands plus branch creation, rejecting anything else (push, reset --hard,
  clean, rebase, delete) — enforcing Section 10.8's "never pushes, force-resets, or
  deletes" structurally, not by convention.
* Unit tests: identity match/mismatch, clean/dirty/in-progress detection, wrapper
  allows `status`/`rev-parse`/`branch` and rejects `push`/`reset`/`tag -d`.

## Out of scope
* Branch naming and creation — MT-2.10-02.
* Merge-base diff, stats and changed files — MT-2.10-03.
* Secret-pattern scanning — MT-2.10-04.
* Worktree creation — MT-2.10-05.
* Enforcing cleanliness before submission (rejecting dirty submissions) — WP-2.6
  branch/sha verification; this task only reports state.
* OS matrix testing — MT-2.10-06.

## Target paths
* `bridge/src/` (Git helper module: identity, status, invocation guard)
* `bridge/tests/` (helper unit tests with fixture repositories)
* WP changelog entry

## Acceptance criteria
- [ ] Repository identity resolves the top-level directory and confirms it equals the
  session's manifest-discovered root; mismatch yields a structured error
  (Section 10.3, 10.8).
- [ ] Clean-state check reports clean vs uncommitted/untracked/in-progress states as
  structured output with no parsing fragility (test-asserted fixtures).
- [ ] The invocation guard structurally forbids push, force-reset and delete —
  tests prove such calls cannot be issued through the helper (Section 10.8,
  WP-2.10 acceptance "never pushes or deletes").
- [ ] No path can escape the repository root; commands run with array arguments and
  the repo root as working directory (Section 12.3, Section 20.4 item 3 — no
  env-specific paths).
- [ ] Tests pass in CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
Run the Git helper identity/state tests, e.g.
`uv run pytest bridge/tests/ -k git_repo_state`; assert identity match/mismatch,
status fixtures, and guard rejections of push/reset/delete.

## Attachments
* [Section 10.8 — Local Git helper](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.3 — Path and scope enforcement](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The guard is a security boundary: a permissive default (allow unknown
  subcommands) would defeat Section 10.8 — the allowlist must be explicit and
  tested both ways.
* Fixture repositories with unusual states (mid-rebase, bare, worktree-linked) are
  easy to get wrong cross-platform; cover the states the plan names and defer exotic
  ones to MT-2.10-06.
