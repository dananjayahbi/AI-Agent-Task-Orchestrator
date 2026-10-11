# MT-3.7-03 — Implement isolated temporary worktree handling (never touches dev tree)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-03 |
| Title | Implement isolated temporary worktree handling (never touches dev tree) |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-02 (executor loop); WP-2.10 complete (Git helper; optional worktree helper MT-2.10-05 / OQ-03) |
| Parent sections | 11.4 (steps 2, 4, 5), 19 (WP-3.7 acceptance), 10.8, 16.3, 20.4, 20.5; ADR-007, ADR-013 |

## Context
Section 11.4 step 2 requires the executor to "create a clean temporary worktree of the
default branch" and step 5 guarantees it "Never leaves the developer's working
directory modified." Section 19 makes this a hard acceptance: a conflict "leaves the
developer's working tree untouched." This is the isolation core of ADR-008: all Git
actions run host-side (Principle P2 — the backend never reads or writes repositories;
ADR-007), and they happen in a throwaway worktree, not in the directory the developer
works in. WP-3.7 also lists "cleanup guarantees" as a deliverable.

## Inputs / Prerequisites
* Parent plan Section 11.4 — steps 2, 4, 5 (create worktree of the default branch;
  abort cleanly on conflict; never modify the developer's directory).
* Parent plan Section 19 WP-3.7 — acceptance: conflict leaves the developer's working
  tree untouched; deliverable "cleanup guarantees".
* Parent plan Section 10.8 — Git helper discipline: read operations plus branch
  creation; never pushes, force-resets or deletes.
* Parent plan Section 10.3 manifest — `default_branch` is the worktree base.
* ADR-013 / OQ-03 — optional per-task worktrees (MT-2.10-05) are the coder-side
  counterpart; this task is executor-side only.

## Scope (in)
* A worktree manager used by the executor: create a temporary worktree of the project's
  default branch inside a dedicated temp location under the host's control, resolve it
  as the working directory for the merge attempt, and remove it on every exit path
  (success, conflict, exception).
* Guards before creation: repository identity matches the configured allowlist entry
  (Section 10.2), default branch exists — failures are reported, not retried blindly.
* Guarantee that no operation writes into the developer's checked-out working tree:
  no checkout of branches in the dev directory, no `reset`, no index manipulation there
  (Sections 11.4 step 5, 10.8; Principle P2, ADR-007 — the backend's API-only role is
  untouched by this task, but the executor inherits the same "host-side, isolated"
  consequence).
* Leftover detection at startup (input for MT-3.7-06): recognizable temp worktrees
  from a previous run are enumerable and removable.
* Tests with a scratch repository carrying a dirty working tree and untracked files:
  run create → simulate merge attempt → destroy; assert the dev tree is byte-identical
  before/after and no temp artifacts remain.

## Out of scope
* The executor queue loop — MT-3.7-02.
* Which merge command/strategy runs inside the worktree — MT-3.7-04.
* Crash-time reconciliation decisions — MT-3.7-06 (this task only guarantees cleanup
  on handled exit paths and enumerability of leftovers).
* Coder-side optional worktrees — WP-2.10 / MT-2.10-05 (OQ-03).
* Any backend filesystem access — forbidden by Principle P2 / ADR-007.

## Target paths
* `bridge/` (worktree manager used by the merge executor)
* `bridge/` tests (scratch-repo isolation and cleanup tests)
* WP changelog entry

## Acceptance criteria
- [ ] The executor creates a clean temporary worktree of the default branch before
  merging (Section 11.4 step 2).
- [ ] No operation during create/merge/destroy modifies the developer's working
  directory — proven by a dirty-tree fixture that is byte-identical afterwards
  (Section 11.4 step 5; Section 19 WP-3.7 acceptance).
- [ ] The worktree and any temporary refs are removed on success and on handled
  failure — WP-3.7 "cleanup guarantees" deliverable.
- [ ] Leftover worktrees from a previous run are detectable (input to MT-3.7-06).
- [ ] No push, force-reset or delete of branches occurs (Section 10.8 discipline).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k worktree -q` and confirm: worktree created from
the default branch, dirty dev tree untouched (snapshot comparison) through create and
destroy, cleanup on simulated failure, and leftover enumeration after an aborted run;
then `uv run pytest bridge/tests/ -q` stays green.

## Attachments
* [Section 11.4 — Merge Executor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-008 — Host-side Merge Executor](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not name a temp-worktree location (Section 16.3 covers storage
  generally) — choose a host-local temp dir outside the repo to avoid polluting
  `git status`, and record the choice in the WP changelog rather than as a new plan
  concept.
* On Windows, worktree removal can fail while file handles are open (RISK-15 host path
  differences) — the cleanup path must retry/report, never silently pass; verify on the
  OS matrix of WP-2.10.
* Git worktrees share the repository's object database; a concurrent developer fetch
  or GC during a merge is possible — treat worktree failures as merge failures
  (T18 path) instead of crashing the loop.
