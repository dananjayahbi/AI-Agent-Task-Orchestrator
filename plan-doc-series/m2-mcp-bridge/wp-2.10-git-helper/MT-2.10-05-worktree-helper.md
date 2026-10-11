# MT-2.10-05 — Implement optional per-task worktree helper (OQ-03)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-05 |
| Title | Implement optional per-task worktree helper (OQ-03) |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07; gap G-26 (concurrent agents on one repo); OQ-03 decision: default one concurrent task per project, optional per-task worktrees as a later improvement |
| Priority | M |
| Dependencies | MT-2.10-01 (identity/guard), MT-2.10-02 (branch derivation); WP-2.2 (manifest `agent_hints.worktree_mode`) |
| Parent sections | 10.3 (manifest `agent_hints`), 10.8, 19 (WP-2.10), 20.4, 20.5, 22 (OQ-03) |

## Context
Gap G-26 names the hazard: several agents on the same repository share one working
directory, so concurrent work corrupts each other's files and branches. The OQ-03
decision (Section 22) sets the default — `max_concurrent_tasks` of 1 per project —
with optional per-task Git worktrees as a later improvement, and Section 10.8 lists
"optional per-task worktree creation (OQ-03)" as a helper capability. The manifest's
`agent_hints.worktree_mode` (default `false`, Section 10.3 extended manifest) is the
switch. This slice implements the optional, opt-in worktree helper so multi-agent
projects can run isolated working trees without changing the default behavior.

## Inputs / Prerequisites
* Parent plan Section 22 — OQ-03 and its recorded decision (default 1; worktrees
  optional later improvement — this WP's "Could" deliverable).
* Parent plan gap G-26 — `max_concurrent_tasks` policy plus optional worktree mode
  (WP-2.10).
* Parent plan Section 10.3 — extended manifest `agent_hints.worktree_mode` (false by
  default) and Section 10.8's optional worktree capability.
* Parent plan Section 10.8 — read operations plus branch creation only; never push,
  force-reset, or delete.
* MT-2.10-01/02 — guard, identity, branch derivation; WP-1.3 — policy
  `max_concurrent_tasks`.

## Scope (in)
* A worktree helper gated on `agent_hints.worktree_mode`: when disabled (default),
  every call short-circuits with a structured "worktree mode disabled" result so
  callers behave exactly as before (zero behavior change when off).
* When enabled: create a per-task worktree at a documented location under the
  repository's control (for example a sibling `.worktrees/` directory excluded from
  the manifest-tracked tree), tied to the canonical task branch from MT-2.10-02;
  resolve an existing worktree idempotently instead of duplicating it.
* A lookup path: given the bound session and task id, return the task's worktree
  root so downstream Git evidence (diff, secret scan) can run there — those
  functions accept an explicit repo-root argument to support this.
* Teardown restraint: the helper may report that a worktree exists and is stale, but
  per Section 10.8 it must not delete branches; worktree removal is deliberately not
  auto-implemented — if removal is required, note it as an OQ-xx rather than adding
  a destructive operation the plan forbids.
* Tests: disabled-by-default no-op, enable-via-manifest creation, idempotent lookup,
  isolation (two tasks get distinct roots), guard still forbidding push/reset/delete
  with worktrees in play.

## Out of scope
* Enforcing `max_concurrent_tasks` — backend policy (WP-1.3/claim service).
* Changing the default single-working-directory flow — OQ-03 decision keeps it
  default; this is additive and opt-in.
* Deleting worktrees/branches — Section 10.8 forbids deletes; deferred as OQ-xx.
* OS-specific worktree edge cases beyond the happy path — MT-2.10-06 matrix.
* Wiring worktree paths into submission capture — WP-2.6 (note the explicit
  repo-root parameter as the integration seam).

## Target paths
* `bridge/src/` (worktree helper in the Git helper module)
* `bridge/tests/` (worktree tests with fixture repositories)
* WP changelog entry

## Acceptance criteria
- [ ] With `agent_hints.worktree_mode` absent or false, behavior is unchanged — the
  helper returns a disabled result and creates nothing (OQ-03: default preserved),
  asserted by test.
- [ ] When enabled, per-task worktrees are created/look up idempotently for the
  canonical task branch and two tasks yield distinct roots (G-26 mitigation
  exercised).
- [ ] No destructive operations: creation uses branch creation plus worktree add
  only; push/reset/delete remain blocked by the MT-2.10-01 guard (Section 10.8,
  WP-2.10 acceptance).
- [ ] Worktree roots are documented, excluded from scope/diff globs of other tasks,
  and never outside the repository's control (Section 12.3).
- [ ] Tests pass in CI (Section 20.4 item 2); changelog note added (item 7).
- [ ] Any requested capability beyond the plan (worktree removal) is recorded as
  OQ-xx, not implemented (Section 20.1 item 5).

## Test command
Run the worktree tests, e.g. `uv run pytest bridge/tests/ -k worktree_helper`;
assert disabled-by-default no-op, enabled creation, idempotent lookup, per-task
isolation and guard enforcement.

## Attachments
* [Section 22 — OQ-03 decision](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Gap G-26 — Concurrent agents on one repository](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* OQ-03 was decided as "later improvement" — scope creep risk is real: keep this
  helper strictly opt-in and report-only elsewhere; the default flow must not
  subtly depend on it.
* Worktree paths interact with `target_scope` globs and secret-scan inputs;
  document the layout so R2/R5 evidence computed in a worktree still maps to
  repository-relative paths correctly.
