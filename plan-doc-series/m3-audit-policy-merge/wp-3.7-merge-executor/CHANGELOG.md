# WP-3.7 — Merge queue API + merge executor

## Unreleased

**MT-3.7-01 — Implement the merge queue API (done).**
Section 9.2's three merge routes land in a new `backend/apps/merge/` app:
`GET /api/v1/merge/pending` (FIFO queue of `merge_status = pending` carriers
in `in_human_review`/`to_be_audited`, canonical `{results, next_cursor}`
envelope, project-scoped for agent tokens, Owner sees all),
`POST /api/v1/merge/{task}/start` (pending → `merging` sub-status write +
`merge.started` event in one transaction — not a dispatch), and
`POST /api/v1/merge/{task}/result` (dispatches new transitions T17 →
`completed` + `merged` + `merge.succeeded` with the sha in payload/note/event
— no schema change — or T18 → `in_human_review` + `review_reason =
merge_conflict` + `merge.failed`, firing WP-3.9's `review.requested` and the
Section 9.8 push). `TransitionReason` gained `merge_succeeded`/`merge_failed`
(migration `tasks.0010`); the dispatcher gained an `extra["event_data"]`
seam that merges payload keys underneath the four pinned core keys.
Authorization per Section 12.2: read = Owner + Merge Executor, write =
Merge Executor only (no owner write bypass), scope-first ADR-004, catalog
codes only, ADR-012 idempotency on both POSTs. T17's `task.completed` plan
cell cannot fire (not in the frozen 24-type catalog — catalog-first,
Section 20.4 item 5; recorded reading in `apps/merge/transitions.py`).
Drift guards updated: matrix probes moved onto the real routes (+ landed
`test_wp37_landed_merge_routes_enforce_their_callers`), Section 9.2
`DEFERRED_ROWS` → `PROOF`, rate-limit rows flipped present.
Tests: `uv run pytest tests/test_merge_queue.py -q` → 22 passed;
`uv run pytest tests/test_authorization_matrix.py tests/auth/
test_section_9_2_authorization.py tests/test_rate_limiting.py -q` → 54
passed; full unit gate `uv run pytest tests/ -q -x --ignore=tests/integration`
green (1467 baseline + new). OpenAPI regenerated (`schemas/openapi.yaml`,
+398 lines: `list_merge_pending`/`start_merge`/`report_merge_result`).

**MT-3.7-02 — Implement the executor loop in the bridge package (done).**
New `bridge/src/orchestrator_bridge/merge_executor/` package hosts the
Section 11.4 five-step loop as one sequential worker (RISK-03: one active
worker per host): `queue.py` is the typed Section 9.2 client over the
shared transport (paths via the `endpoints` catalog, one ADR-012 key per
logical operation, catalog result values `succeeded`/`conflict`/`failed`
only); `loop.py` is the loop contract — poll → claim → injected merge
step → report, Section 10.2 allowlist checked **before** the claim (a
repo outside `merge_repo_paths` is never opened, never claimed),
exponential backoff (capped 60 s) on Section 10.10 outages with the same
idempotency key replayed across retries (never a duplicate completion),
claim/report `TASK_STATE_CONFLICT`/`VERSION_CONFLICT` absorbed as
catalog-designed skips, and a report that stays unconfirmed after
`MUTATION_BACKOFF_ATTEMPTS=3` raising `MergeReportError` — the task is
left `merging` for MT-3.7-06 reconciliation, never double-applied (P6);
`step.py` is the MT-3.7-03/04 wiring point (worktree + strategies),
raising at the WP boundary until they land so this build never claims a
task it cannot finish. Every transition is structured-logged
(`merge_queue_poll`/`merge_claimed`/`merge_attempt`/`merge_reported`/…)
as MT-3.7-06's recovery input; all Git work stays behind the injected
step (Principle P2 / ADR-007 — the loop itself touches no repo).
`entrypoints.executor.run(settings, once=…)` replaces the stub: validates
the Section 10.2 allowlist, resolves the step, then the long-running
loop or the on-demand `--once` pass (`orchestrator-bridge
--mode merge-executor --once`); `endpoints.py` catalog gained the three
merge entries (no `PENDING_BACKEND` flags — the routes are in the
document).
Recorded readings (risk notes): polling is the v1 trigger choice
(event-driven is a future optimization that must not change the loop
contract); default poll interval 30 s (`DEFAULT_POLL_SECONDS`, a
constructor parameter — no new config key); the executor never pushes —
whether the merged default branch reaches a remote is an open owner
decision (Section 10.8's no-push discipline inherited).
Tests: `uv run pytest tests/ -k merge_executor -q` → 23 passed (empty
queue idle, full success cycle pending→merging→result with sha, conflict
and step-crash failure reports, outage backoff with identical replayed
keys and no duplicate reports, unconfirmed-report stop, allowlist
refusal, claim/report conflict absorption, on-demand entry run);
full bridge gate `uv run pytest bridge/tests/ -q` → 764 passed, 10
skipped; `uv run ruff check .` and `uv run ruff format --check .` clean;
`uv run mypy .` adds no new errors (2 pre-existing conftest.py
`attr-defined` notes, verified present with this work stashed).

**MT-3.7-03 — Implement isolated temporary worktree handling (never touches dev tree) (done).**
`bridge/src/orchestrator_bridge/merge_executor/worktree.py` owns the
scratch checkout: a per-run temp root exposed through the module seam
`temp_worktree_root()` (MT-3.7-06's journal and leftover enumerator read the
same location), `git worktree add --detach` at the default branch tip, and
deterministic removal with an `rmtree` fallback (`remove_leftover_worktree`,
used by recovery). Every `git_runner` process now carries an explicit
`--git-dir`/`--work-tree` pair (query flags factored into `_REPO_QUERY_FLAGS`),
so no read or write is derived from an ambient cwd — deterministic on Windows
and POSIX. The developer's working directory is only ever read (Section 11.4
step 5): no checkout/reset/status ever writes into it.
Tests: `uv run pytest tests/test_merge_executor_worktree.py -q` → 30 passed
(temp-root isolation, create/remove/leftover paths, Windows path-separator
and no-raise parametrizations); full bridge gate below stays green; mypy/ruff
clean for these files.

**MT-3.7-04 — Implement merge strategies (squash, merge_commit, fast_forward_only, manual) (done).**
Bridge: `git_runner` gained an audited allowlist (`merge`, `commit`,
`update-ref`) with structural validators — `merge` accepts exactly
`--ff-only`/`--no-ff` (+ `--no-edit`) or `--squash`, plus the lone
`--abort`; `update-ref` only `refs/heads/<default>` with the two hex shas
(CAS: refuses if the default branch moved concurrently — never forced).
New `strategies.py` (`STRATEGY_VALUES` = the four MT names, no extras;
`merge_shape_for`, `worktree_head`, `apply_strategy` classifies conflicts
vs plain failures via the `CONFLICT` marker, refuses empty merges, lands
via CAS) and `strategy_step.py` (`WorktreeStrategyStep`: **manual
refusal before any git process**, input validation, temp worktree +
apply) — `step.py` now resolves this step (its raised-not-wired boundary
deleted), and `queue.py` parses `merge_strategy` off the Section 9.2
entry (default `squash`). Landing advances `refs/heads/<default>` only;
the task branch itself is never pushed (MT-3.7-02's discipline inherited).
Backend: the queue-side OQ-06 guard — `list_merge_pending` resolves an
accidentally enqueued `merge_strategy = manual` carrier through the new
**T20 `merge_manual`** transition (`apps/merge/transitions.py`:
in_human_review/to_be_audited + `merge_status = pending` → `completed` +
`merge_status = none`, actor `agent`, cataloged `task.transitioned`
event, `TransitionReason.MERGE_MANUAL`, migration `tasks.0011`) and
never returns it to the caller; executable-strategy entries list
unchanged. Item payloads carry `merge_strategy` (serializer/view).
Recorded readings: T20 is not a Section 8.2 plan row (plan table ends
at T19) — flagged here for the plan owner per Section 20.5, catalog-first
event type as with T17's note; commit identity is default Git behavior
(repo-local/OS autodetect, global/system config scrubbed) — an absent
identity fails cleanly into T18, no metadata invented (risk note);
`MergeStrategy.choices` in `apps/projects` still lists §7.2's three
executable values (outside this WP's touch area) — OQ-06's fourth value
is accepted at the DB/state-machine layer, and widening the policy
serializer belongs to the policy-form work (WP-4.10-03); the WP-3.6
approval-side short-circuit does not exist yet, so this guard is the
operative completion path (the approval half, if added later, simply
makes it never fire); after a landing the dev checkout shows phantom
staged changes until the developer resyncs (`git reset`/`pull`) — file
bytes are never touched.
Tests: `uv run pytest bridge/tests/ -k merge_strategy -q` → 10 passed
(one case per executable strategy, non-ff → failed/T18, empty merge
refused, concurrent-move refusal, manual refused before any git, manual
queued by mistake producing no merge attempt, squash default, allowlist
shape); backend `uv run pytest tests/test_merge_manual_guard.py -q` → 4
passed (queue resolves manual entry with T20 history + event and no
merge event, executable entries untouched, T20 service happy path +
both refusals); `uv run pytest tests/test_merge_queue.py -q` → 22
passed; `manage.py makemigrations --check` clean.

**MT-3.7-05 — Implement conflict reporting back to in_human_review (merge_conflict) (done).**
`strategies.apply_strategy` separates the two failure classes the report
path needs: a conflicted squash/merge leaves `CONFLICT` lines in git's
output (reported as `conflict` with those details), anything else is a
plain `failed` — the worktree is always removed so the dev tree and the
scratch area return byte-identical, and `merge --abort` unwinds an
`--no-ff` conflict (a conflicted squash has no `MERGE_HEAD` and is
covered by worktree removal instead — recorded). T18's payload-flavor
`merge_status` (`conflict` vs `failed`) plus `review_reason =
merge_conflict` flow through the existing result route unchanged.
Tests: `uv run pytest tests/test_merge_conflict_report.py -q` → 3
passed (both strategy shapes through the full step: conflict details on
the task, dev-tree `git status` byte-identical before/after, worktree
cleaned, repeat run stable); backend `uv run pytest tests/ -k t18 -q` →
1 passed (failed-flavor T18 application).

**MT-3.7-06 — Implement crash recovery on executor restart (done).**
New `merge_executor/journal.py` — a JSONL journal at
`<temp-root>/merge-executor-journal.jsonl` (fsynced appends; survives
restarts; `unresolved()` + atomic `compact()`), and
`merge_executor/recovery.py` — `startup_recovery` acquires an advisory
OS executor lock (msvcrt on NT / fcntl elsewhere; auto-released on
process death, RISK-03's one-worker-per-host enforcement), reconciles
unresolved journal entries through `reconcile_on_startup`, and cleans
`remove_leftover_worktree` debris from prior runs. Entry enumeration is
the journal plus `GET /tasks/{id}` (the pending list structurally
excludes merging, and logs are stream-only per MT-2-1-03 — recorded
deviation from a log-tail reading). Reconciliation is **T18-only**
(recovery reports an honest `failed` result; squash success evidence is
unprovable after a crash, and re-approval re-runs the merge — the risk
note's safe default; nothing is ever fabricated as merged). Backend
`TASK_STATE_CONFLICT`/`VERSION_CONFLICT`/`TASK_NOT_FOUND` decide "already
handled"; other terminal errors raise `MergeRecoveryError`, which the
executor turns into `EXIT_CONFIG_ERROR` (startup stops, no loops).
`loop.py` writes `started` on claim and `reported` after success or
refused-conflict (OSError → loud log). Identity/one-off decisions as in
MT-3.7-04 above.
Tests: `uv run pytest tests/test_merge_crash_recovery.py -q` → 9 passed
(journal append/replay/compact, lock hold + contention + death-release,
leftover-worktree cleanup, startup reconcile happy/decided/outage paths);
`uv run pytest tests/test_merge_executor_loop.py -q` → 21 passed;
`uv run pytest tests/test_entrypoints.py -q` → 23 passed (executor
startup wiring); full bridge gate below green.

**MT-3.7-07 — Write the merge end-to-end test (success + conflict paths) (done).**
`bridge/tests/test_merge_e2e.py` runs the real stack against a live
backend (opt-in `ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`, module-scoped
`wp16-pg` harness with the conformance-style patch-artifact preclean;
each scenario builds its own scratch clone — RISK-15 isolation): seed a
pending carrier + fixed-token `merge_executor` client, run
`run_once()` through the real queue/step/transport, then assert through
Django DB queries. Four cases: **success** (T17 → `completed` +
`merged`, `main`'s new tip carries the feature file, dev tree
byte-identical, `merge.succeeded` + `task.transitioned` events);
**conflict** (T18 → `in_human_review` + `review_reason =
merge_conflict` + `merge_status = conflict`, `merge.failed` event, dev
tree byte-identical, worktree gone); **recovery** (kill after claim,
restart → exactly one reconciled T18 with the honest `failed` flavor,
never a double completion); **invariant sweep** (queue/transition/event
counters consistent, no leaked locks/worktrees). Gated live pattern:
without the flag the module skips with the exact run command.
Tests: `ORCHESTRATOR_BRIDGE_LIVE_TESTS=1 uv run pytest
tests/test_merge_e2e.py -q` → 4 passed (29.9 s); default suite skips it
(clean `uv run pytest -q` above).
