# MT-3.7-04 — Implement merge strategies (squash, merge_commit, fast_forward_only, manual)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-04 |
| Title | Implement merge strategies (squash, merge_commit, fast_forward_only, manual) |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-02 (executor loop); MT-3.7-03 (worktree); WP-3.1 complete (policy model with `merge_strategy`); WP-3.6 complete (approval side of `manual`) |
| Parent sections | 11.4 (step 3), 7.2 (Project Policy `merge_strategy`), 8.1 (merge pending note), 8.2 (T15, T17), 19 (WP-3.7), 20.4, 20.5; ADR-008; OQ-06 |

## Context
Section 11.4 step 3: "Merge the task branch using the project's `merge_strategy`."
Section 7.2 defines the policy field with default `squash` and values `squash` /
`merge_commit` / `fast_forward_only`. OQ-06 (decided per Section 19.1) adds the fourth
value `manual`: "approval marks `completed` without executor involvement" — for
projects without a local merge step (manual or PR-based). Section 8.1's invariant
conversation (invariant 2, Section 8.3) allows `completed` without a merge only via
this OQ-06 path. The executor applies the three executable strategies inside the
isolated worktree; `manual` never reaches the executor at all.

## Inputs / Prerequisites
* Parent plan Section 7.2 — `merge_strategy` field, default `squash`, three values.
* Parent plan Section 22 OQ-06 — the `manual` value and its semantics (recommended
  default, decided in WP-0.4 per Section 19.1).
* Parent plan Section 11.4 steps 3–4 — strategy applied in the worktree; conflict or
  failure reported, not forced.
* Parent plan Section 10.8 — Git helper never pushes or force-resets; the strategy
  implementation inherits that discipline.
* MT-3.7-01 / MT-3.7-02 — result reporting paths each strategy must feed.
* WP-3.1 — policy storage the executor reads (via task/project data on queue items).

## Scope (in)
* Strategy dispatch in the executor: read the project's `merge_strategy` for the queued
  task and perform exactly that merge inside the temporary worktree.
* `squash` — collapse the task branch into a single commit on the default branch;
  `merge_commit` — a true merge commit preserving branch history; `fast_forward_only` —
  fast-forward the default branch, failing (not forcing) when the merge base does not
  allow it.
* Failure classification: any strategy that cannot complete (non-fast-forward under
  `fast_forward_only`, conflicts, empty merge) aborts cleanly and reports through the
  failure path (Section 11.4 step 4) → T18 (Section 8.2).
* `manual` handling: tasks in projects with `merge_strategy` = `manual` never enter the
  executor queue — approval marks the task `completed` without executor involvement
  (OQ-06); implement the queue-side guard so an accidentally enqueued manual task is
  resolved without performing a merge, and coordinate with the WP-3.6 approval path.
* Table-driven tests: one success case per executable strategy in a scratch repo, one
  non-fast-forward failure under `fast_forward_only`, and `manual` never producing an
  executor merge attempt.
* A WP changelog note.

## Out of scope
* Worktree lifecycle — MT-3.7-03.
* Conflict escalation details (`review_reason` plumbing) — MT-3.7-05.
* The policy form UI for `merge_strategy` — WP-4.10 (MT-4.10-03).
* Remote pushing of the merged branch — not specified by the plan (see Risk notes).
* Adding new strategy values — only the four names above may exist (Section 20.5).

## Target paths
* `bridge/` (strategy dispatch inside the merge executor)
* `bridge/` tests (per-strategy table-driven tests)
* WP changelog entry

## Acceptance criteria
- [ ] The executor performs `squash`, `merge_commit` and `fast_forward_only` exactly as
  named — no renamed or extra strategy values (Sections 7.2, 20.5).
- [ ] Strategy is taken from the project's `merge_strategy` (default `squash`) — no
  executor-side configuration of strategy (Section 7.2).
- [ ] `fast_forward_only` failure and any conflict abort cleanly and take the failure
  report path → T18 (Sections 11.4 step 4, 8.2).
- [ ] `manual` tasks never trigger an executor merge; approval completes them without
  executor involvement per OQ-06 (Section 8.3 invariant 2 exception).
- [ ] All merges happen in the MT-3.7-03 worktree; dev tree untouched
  (Section 11.4 step 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k merge_strategy -q` and confirm: one green case for
each of `squash`, `merge_commit`, `fast_forward_only` in a scratch repo, the
non-fast-forward case reported as a failure (T18 path), and a `manual` project queued
by mistake producing no merge attempt; then `uv run pytest bridge/tests -q` stays
green.

## Attachments
* [Section 7.2 — Project Policy (`merge_strategy`)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 22 — OQ-06 manual strategy decision](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.4 — Merge Executor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 7.2 lists only three `merge_strategy` values while OQ-06 introduces
  `manual` — treat Section 7.2 as needing the OQ-06 extension; flag the doc mismatch
  for the plan owner instead of silently choosing one (Section 20.5 traceability).
* Where exactly the `manual` short-circuit lives (review approval in WP-3.6 vs queue
  guard here) is not fixed by the plan — this task implements the queue-side guard;
  the approval-side behavior must be confirmed with WP-3.6 so `completed` is reached
  exactly once (ADR-008 invariant must stay honest).
* Squash-commit message content and authorship are unspecified — reuse the default
  Git behavior and record the choice; do not invent metadata conventions.
