# MT-3.7-06 — Implement crash recovery on executor restart

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-06 |
| Title | Implement crash recovery on executor restart |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-01 (idempotent start/result); MT-3.7-02 (loop and logging); MT-3.7-03 (leftover enumeration) |
| Parent sections | 19 (WP-3.7 acceptance), 10.2, 10.10, 9.9, 7.2 (`merge_status`), 8.2 (T17/T18), 20.4, 20.5; ADR-008, ADR-012, P6 |

## Context
Section 19 WP-3.7 acceptance requires that a "crash mid-merge recovers cleanly on
restart." A crashed executor can leave two kinds of debris: a task stuck in
`merge_status` = `merging` (started via `POST /merge/{task}/start` but never reported)
and temporary worktrees on disk (Section 11.4's isolation makes the developer's tree
safe regardless — MT-3.7-03). The recovery design must respect the plan's existing
machinery: idempotent mutations (P6, ADR-012), the T17/T18 transitions as the only
exits from merge-pending, and the fact that Section 9.9 defines no merge sweeper —
recovery is driven by the executor's own restart.

## Inputs / Prerequisites
* Parent plan Section 19 WP-3.7 — the crash-recovery acceptance criterion.
* Parent plan Section 10.2 — Merge Executor as long-running process or on-demand
  command (recovery runs at every startup, including on-demand invocations).
* Parent plan Section 10.10 — backend unreachable behavior (recovery must tolerate
  outages with backoff).
* Parent plan Sections 7.2 and 8.2 — `merge_status` values; T17/T18 as the only legal
  outcomes of a started merge.
* MT-3.7-03 — leftover worktrees are enumerable at startup.
* MT-3.7-01 — `start`/`result` endpoints are idempotent (ADR-012).

## Scope (in)
* Startup reconciliation in the executor: enumerate tasks it previously started (from
  its own structured log and `GET /merge/pending` plus queue state) and, for any task
  still `merging`, decide and report one terminal outcome — re-attempt the merge from
  a fresh isolated worktree, or report failure (→ T18, `merge_conflict`) when the repo
  state cannot be safely re-derived. Exactly one result is accepted per task
  (idempotency, ADR-012).
* Cleanup of leftover temporary worktrees detected at startup before any new merge
  begins (MT-3.7-03 enumeration).
* Developer-tree safety across crashes: because all merge work happens in the temp
  worktree (Section 11.4 step 5), a crash can never leave the dev tree half-merged —
  the test proves it.
* Tolerance of backend unavailability during recovery (Section 10.10 backoff; recovery
  resumes when the API returns).
* Tests: simulate a crash after `start` (and mid-merge) in a scratch repo, restart the
  executor, assert: leftover worktree cleaned, task reaches `completed` (T17) or
  `in_human_review` (T18) exactly once, dev tree byte-identical, and a second restart
  performs no duplicate work.
* A WP changelog note.

## Out of scope
* A backend merge-timeout sweeper — not in Section 9.9; adding one is a plan change
  (see Risk notes).
* The queue API implementation — MT-3.7-01 (only consumes its idempotency).
* Worktree mechanics — MT-3.7-03.
* The end-to-end test suite — MT-3.7-07 (it includes a recovery scenario check).

## Target paths
* `bridge/` (executor startup reconciliation and cleanup)
* `bridge/` tests (crash simulation and restart tests)
* WP changelog entry

## Acceptance criteria
- [ ] Restarting the executor reconciles every task left in `merging`: one final
  outcome via T17 or T18, never a duplicate or missing report (Section 19 WP-3.7
  acceptance; Sections 7.2, 8.2; ADR-012).
- [ ] Leftover temporary worktrees are removed before new work starts (Section 11.4
  step 5; WP-3.7 cleanup guarantees).
- [ ] The developer's working directory is untouched through crash and recovery —
  proven by test (Section 19 WP-3.7 acceptance).
- [ ] Recovery retries with backoff while the backend is unreachable
  (Section 10.10) and does not fabricate results.
- [ ] `completed` appears only through T17 with a genuine successful merge — ADR-008
  invariant stays honest; failure recovery takes the T18 `merge_conflict` path.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k crash_recovery -q` and confirm: kill-after-start
and kill-mid-merge simulations both converge on exactly one T17/T18 outcome after
restart, leftover worktrees removed, dev tree unchanged, duplicate restart is a no-op,
and backend-down recovery backs off; then `uv run pytest bridge/tests -q` stays green.

## Attachments
* [Section 19 — WP-3.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.4 — Merge Executor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-012 — Idempotency keys plus lease fencing](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan defines no stale-`merging` timeout (Section 9.9 has no merge sweeper), so a
  task whose executor never restarts stays `merging` indefinitely — document this
  operational reality in the runbook and raise a plan amendment if field experience
  warrants a sweeper (Section 20.1 item 5; do not invent the behavior here).
* Distinguishing "merge completed but report lost" from "merge never happened" needs
  local evidence (worktree state, reflog) — the safe default is re-attempt from a
  fresh worktree; when in doubt report failure (T18) so a human decides (ADR-008
  prefers honesty over silent completion).
* On-demand invocations (Section 10.2) may overlap a running instance — startup must
  detect/handle a concurrent executor (single-worker assumption of RISK-03); if no
  locking exists yet, add it as part of this task's startup path.
