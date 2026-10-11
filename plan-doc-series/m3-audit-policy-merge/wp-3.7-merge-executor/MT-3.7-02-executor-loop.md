# MT-3.7-02 — Implement the executor loop in the bridge package

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.7-02 |
| Title | Implement the executor loop in the bridge package |
| Parent WP | WP-3.7 — Merge queue and Merge Executor (Milestone M3) |
| Requirements | FR-AUD-06 |
| Priority | M |
| Dependencies | MT-3.7-01 (queue API); WP-2.10 complete (Git helper); WP-2.1 complete (bridge package skeleton) |
| Parent sections | 10.1 (item 7), 10.2 (Merge Executor run mode), 10.10 (resilience), 11.4 (Merge Executor workflow), 9.2 (merge queue), 19 (WP-3.7), 20.4, 20.5; ADR-007, ADR-012 |

## Context
Section 10.1 item 7 makes the bridge package host the Merge Executor as a separate
entry point, and Section 10.2 defines its run mode: a long-running host process or
on-demand command, bound by a config listing allowed repo paths, serving approvals from
web/mobile. Section 11.4 gives the five-step loop: poll for `merge_status` = `pending`
tasks in allowed repos; mark `merging` via the start endpoint; create a clean temporary
worktree of the default branch; merge with the project's `merge_strategy`; report the
resulting sha on success or abort cleanly on conflict — never leaving the developer's
working directory modified. This micro-task builds the loop skeleton that
MT-3.7-03 (worktree) and MT-3.7-04 (strategies) plug into.

## Inputs / Prerequisites
* Parent plan Section 10.2 — run mode, launch forms, config-listed allowed repo paths.
* Parent plan Section 11.4 — the exact five workflow steps.
* Parent plan Section 9.2 — `GET /merge/pending`, `POST /merge/{task}/start`,
  `POST /merge/{task}/result` (from MT-3.7-01), all with idempotency keys (ADR-012).
* Parent plan Section 10.10 — backend unreachable: retryable errors, backoff.
* Parent plan Section 7.2 — `merge_status` state values the loop observes.
* WP-2.10 — read-mostly Git helper conventions (never pushes, force-resets or deletes).

## Scope (in)
* A `merge-executor` entry point in the bridge package (Section 10.1 item 7) runnable
  as a long-running process or an on-demand command (Section 10.2).
* Executor config: the list of allowed repo paths it will operate on; a repo not in the
  list is never touched (Section 10.2 binding source).
* The loop: poll `GET /merge/pending` (Section 11.4 allows poll or event), claim one
  task with `POST /merge/{task}/start` (`merging`), delegate to worktree + strategy
  handling, then report via `POST /merge/{task}/result` — success with the resulting
  sha, failure with conflict details.
* Sequential, one-task-at-a-time processing with idempotency keys on mutations
  (ADR-012); retry with backoff when the backend is unreachable (Section 10.10) without
  duplicating completed reports.
* Structured logging of each queue transition (poll, start, merge attempt, report) for
  the crash-recovery work in MT-3.7-06.
* Unit tests with a mocked backend and a scratch repository covering: empty queue,
  one successful cycle, failure report, backend outage backoff, repo-not-allowed skip.
* A WP changelog note.

## Out of scope
* Worktree creation/cleanup details — MT-3.7-03.
* Strategy-specific merge commands — MT-3.7-04.
* Conflict → review escalation semantics — MT-3.7-05 (the loop only calls the failure
  result path).
* Restart reconciliation — MT-3.7-06.
* Backend queue endpoints — MT-3.7-01.
* STDIO/HTTP agent modes — Sections 10.2 (other rows).

## Target paths
* `bridge/` (merge executor entry point and queue loop)
* `bridge/` tests (executor loop tests with mocked backend and scratch repo)
* WP changelog entry

## Acceptance criteria
- [ ] The bridge package exposes a Merge Executor mode runnable as a long-running
  process or on-demand command, configured with allowed repo paths (Section 10.2).
- [ ] The loop performs the Section 11.4 sequence: poll pending → start (mark
  `merging`) → worktree/merge → result report, one task at a time.
- [ ] Every mutation carries an idempotency key; a backend outage yields backoff and
  retry, never a duplicate completion (Sections 10.10, ADR-012, P6).
- [ ] Repos outside the configured allowlist are never opened (Section 10.2).
- [ ] The developer's working directory is untouched by the loop — all Git work is
  delegated to the isolated-worktree step (Section 11.4 step 5; backend/executors
  never access repos directly, Principle P2 / ADR-007).
- [ ] Only catalog error codes used in error handling (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `uv run pytest bridge/tests/ -k merge_executor -q` and confirm: empty-queue idle,
full success cycle (pending → merging → result), failure report path, backoff during a
simulated outage with no duplicate reports, and allowlist refusal; then
`uv run pytest bridge/tests/ -q` stays green.

## Attachments
* [Section 10.2 — Run modes (Merge Executor row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.4 — Merge Executor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-008 — Host-side Merge Executor](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan says "Poll (or receive event)" (Section 11.4) — polling is the v1 choice;
  event-driven triggering is an optimization that must not change the loop contract.
* Whether the executor pushes the merged default branch to a remote is not specified
  anywhere (Section 11.4 reports a sha; Section 10.8 says the helper never pushes) —
  do not push without an explicit owner decision; record the question before execution
  (Section 20.1 item 5).
* Poll interval and single- vs multi-worker execution are unspecified — defaults belong
  to the executor config; keep one active worker per host to avoid repo contention
  (RISK-03).
