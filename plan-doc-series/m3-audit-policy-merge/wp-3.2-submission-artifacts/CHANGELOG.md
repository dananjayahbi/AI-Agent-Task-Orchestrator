# WP-3.2 — Submission handling and artifacts

## Unreleased

### MT-3.2-01 — Task Resolution model and submission endpoint

**Model** — `backend/apps/tasks/models/resolutions.py` adds
`TaskResolution` with exactly the Section 7.2 "Task Resolution" field
set (twelve fields: `id`, `task_id`, `attempt_number`, `branch_name`,
`commit_sha`, `execution_summary`, `diff_summary`, `changed_files`,
`requires_human_attention`, `risk_justification`,
`submitted_by_session`, `submitted_at`) — no extras (Section 20.5
traceability, asserted field-for-field in
`tests/test_resolution_submission.py`). Cardinality is enforced twice:
a `unique(task, attempt_number)` database constraint (Section 7.2's
"one per submission attempt") and a service pre-check that answers the
catalog `TASK_STATE_CONFLICT` instead of leaking an `IntegrityError`.
The row is insert-only (P8, `TaskCheckpoint`'s discipline): the
queryset/model refuse update/delete, and the service computes
`diff_summary`/`changed_files` from the patch *before* the single
insert, so no post-write rewrite is ever needed. Migration:
`apps/tasks/migrations/0007_alter_tasktransition_reason_code_taskresolution_and_more.py`
(also carries the two new `TransitionReason` trigger codes below).

**Endpoints** — `backend/apps/tasks/views/resolutions.py` + URLs:

* `POST /api/v1/tasks/{id}/resolution` (caller: Agent — §12.2 "Submit
  resolution: lease owner"): `HasTaskProjectScope` +
  `CanSubmitResolution` + `AgentEndpointThrottle`; the canonical
  `Idempotency-Key` replay (same stored outcome, no second row, no
  second transition — NFR-12/ADR-012); 201 with the stored Section 7.2
  row plus the post-transition task identity and `scope_violations`
  (Section 10.5 outcome reporting).
* `GET /api/v1/tasks/{id}/resolutions` (Agent / Owner): newest first,
  cursor-paginated (`results` + `next_cursor`, pagination.md).
* `GET /api/v1/resolutions/{id}/patch` (Agent / Owner): serves the
  stored patch or the Section 9.7 marker (MT-3.2-02).

**Wire contract** (derived from Section 10.5 `submit_task_resolution`
inputs per the MT risk note): `session_id` + `lease_generation` (the
ADR-012 fencing pair every agent mutation carries — checkpoints,
release and claim already use it, so one contract across WP-1.6/1.8),
`git_branch`, `commit_sha`, `execution_summary`,
`requires_human_attention`, `risk_justification`, `patch` (the captured
unified diff as text), and the bridge's provisional
`changed_files`/`diff_summary` — accepted for MT-2.6-04 wire
compatibility and **replaced** by the server parse (Section 9.7;
MT-3.2-03). `patch` is `trim_whitespace=False`: the trailing newline is
content and the bridge's locally computed sha256 must match the stored
bytes.

**Authorization** — the shared lease gate
(`leases.fencing.require_current_lease`) under the row lock answers
`LEASE_NOT_OWNED` (403) / `LEASE_EXPIRED` (409); non-coder roles answer
`ROLE_NOT_PERMITTED` (403), anonymous `AUTH_REQUIRED` (401), foreign
projects `AUTH_FORBIDDEN_PROJECT` (403), unknown tasks
`TASK_NOT_FOUND` (404), a task that is not `in_progress`
`TASK_STATE_CONFLICT` (409) — closed catalog only (Section 20.4 item
5). The resolution-addressed patch route embeds no PID, so
`services.resolutions.assert_same_project` applies the ADR-004 scope
check after role admission; an unknown resolution id rides the core
handler's documented generic-NotFound → `VALIDATION_ERROR` (400)
mapping rather than an invented not-found code.

Recorded: the Section 9.2 Submission row's three paths had deferred
entries in `tests/test_authorization_matrix.py` (commented "WP-1.6");
they are retired here and the *Submit resolution* matrix row now runs
on the real route (`test_wp32_landed_resolution_routes_enforce_their_
callers` carries the per-actor cases), and the FR-SEC-05 drift guard in
`tests/test_rate_limiting.py` flipped its `present` flag (all three
routes carry `AgentEndpointThrottle`, the WP-1.8/WP-1.11 shared-class
pattern — the owner GET rides the same class budget).

### MT-3.2-02 — Patch artifact storage, 5 MB cap

**Model** — `TaskArtifact` (`id`, `resolution_id`, `kind`,
`storage_key`, `size_bytes`, `sha256`) with `kind = patch`
(`output_tail` reserved for the deferred MT-2.6-06 tail) and a
`unique(resolution, kind)` constraint; migration as above.

**Storage** — `services/resolutions.store_patch_artifact` computes
`sha256`/`size_bytes` from the received UTF-8 bytes (server-side, never
client-supplied) and stores through the configured backend
(`attachments.storage.get_storage` — Section 9.10; the suite runs on a
per-test `MEDIA_ROOT`). The key is **content-derived** via the shared
`content_key()` (`objects/<aa>/<sha256>`), which the storage Protocol
itself sanctions for "patch artifacts in M3". Readings:

* **The 5 MB cap is inclusive** (MT risk note): `<= 5 * 1024 * 1024`
  stores the body; one byte more is the Section 9.7 degraded path —
  **not an error**: the artifact row still records size/sha, stats and
  file list are still parsed and stored, and no body is written
  (`storage_key` empty).
* **The marker** is derived, not a new column (Section 7.2's field set
  is closed): `GET /resolutions/{id}/patch` keys off `size_bytes >
  PATCH_MAX_BYTES` and answers the one response shape
  (`diff_too_large: true`, `patch: null`, `marker: "diff too large"` —
  the literal §9.7/§13.2 wording).
* **The cap stays a module constant** (`PATCH_MAX_BYTES`), never a
  setting: MT-3.2-02 puts configurability beyond the default out of
  scope.
* Shared content keys mean an attachment-retention delete of identical
  bytes would take the patch body with it — flagged as an OQ for
  Section 9.9's retention job (WP-6.x ref-count question), not papered
  over here.

**Receive bound (settings)** — Django's `DATA_UPLOAD_MAX_MEMORY_SIZE`
default (2.5 MB) answered 500 *before the view ran*, making the
degraded path unreachable end to end. Added
`ORCHESTRATOR_REQUEST_BODY_MAX_BYTES` (default `33554432`, 32 MiB) in
`apps/core/settings/base.py` + a configuration.md group/variable row
(Section 9.10 discipline; flagged for owner confirmation — the plan
fixes the 5 MB *storage* cap, not the receive bound). Beyond that bound
the submission view maps `RequestDataTooBig` to the catalog
`VALIDATION_ERROR` (400) — no invented 413 code, no 500.

### MT-3.2-03 — Authoritative patch parsing

New pure module `backend/apps/tasks/services/patch_parse.py`:
`parse_unified_diff()` derives `changed_files` (repo-relative, one
entry per file, first-seen order) and `diff_summary` (`files` =
`len(changed_files)`; `insertions`/`deletions` counted from hunk body
lines — the `git diff --numstat` definition) with hunk-header line
counts tracking section boundaries. Deterministic (ADR-009: same bytes
→ same output, asserted). Format readings documented next to the
fixtures (MT risk note): git `diff --git` headers delimit sections and
carry mode-only/renamed files (rename counts once, under the b-side
new path); a section's own `---`/`+++` pair wins when present;
`/dev/null` sides, diff -u tab-timestamps, quoted paths and binary
trailers are handled; a hunk-body line that *looks* like a header
(`--- ` content) counts as stats, never a new file. The parse runs
inside the submission transaction and **replaces** any bridge-supplied
provisional values — the two are never merged (Section 9.7;
MT-3.2-03's "never merge or average" risk note). Oversize artifacts are
parsed from the received bytes too: the *body* is dropped at storage
time, never the parse.

### MT-3.2-04 — Scope violation check

New module `backend/apps/tasks/services/scope.py`:
`evaluate_scope(target_scope, changed_files) -> ScopeVerdict` — a pure
check whose every comparison goes through
`apps.projects.services.globs.glob_matches` (**imported, never forked**
— locked by object identity in `tests/test_scope_check.py::test_the_single_shared_matcher_is_used_verbatim`;
WP-3.4's rule R2 recomputes from `resolution.changed_files` through the
same function, so submission and rule time cannot disagree).
Path handling per Section 12.3: `./` prefixes and interior `a/../b`
climb normalise; absolute paths (POSIX and drive-letter), backslashes,
NUL and root-escaping `..` are **rejected as violations rather than
matched**. The verdict rides the dispatch context (`scope_verdict`) so
the T8 guard, the response payload and the transition note read one
computed result.

Recorded readings (Section 20.1 item 5 — flagged as OQs for the plan
owner):

* **Empty `target_scope` is fail-closed** — every changed file
  violates (with an empty change set there is no file to violate). The
  plan states no semantics (MT risk note); the strict reading matches
  G-06's honest-enforcement posture.
* A stored glob that no longer parses also fails closed (an
  unverifiable scope claim proves nothing).

The error shape, where one is raised (the T7 guard refusing an
out-of-scope patch that reached it directly), is the catalog
`SCOPE_VIOLATION` (409) — new exception class `ScopeViolation` in
`apps/tasks/exceptions.py`, existing code only (Section 20.4 item 5).
The normal path raises nothing: the submission routes out-of-scope
patches through T8 into `in_human_review`.

### MT-3.2-05 — Submission transitions T7, T8, T10

New module `backend/apps/tasks/state_machine/transitions_submission.py`
— the sanctioned extension point only (`DEFAULT_REGISTRY.register(...,
replace=True)`); dispatcher/registry/loader/hooks untouched (WP-1.6's
`ensure_wired` pattern: registered **lazily** from
`submit_resolution`, so the WP-1.5 suites keep seeing the loader's
stub rows — snapshot/restore in every suite that can trigger it).

* **T7** (`submit`) — all five Section 8.2 guards verbatim, in order:
  lease owner/unexpired (the shared fencing gate), resolution valid
  (attempt linkage checked), `audit_required` true, not self-flagged,
  scope ok (catalog `SCOPE_VIOLATION` refusal); side effect clears the
  worker (`guards.clear_coder_lease`) — storage happened in the
  submission service's transaction *before* dispatch (sequencing
  required so T8's guard can read the scope verdict; same transaction
  either way, Section 8.2 rule 2), and the row asserts the stored
  resolution rides the context.
* **T8** (`submit_flagged`) — guard is its own cell (flag **or** out
  of scope; neither answers `TASK_STATE_CONFLICT`); side effect sets
  `review_reason` to the strict Section 8.4 pair (`T8_REVIEW_REASONS`:
  `self_flagged` / `scope_violation`) and clears the worker; the
  Section 9.8 push rides the dispatcher's `in_human_review`-entry rule.
* **T10** — Section 8.2's `To = "policy decision"` is a *decision*, not
  one of the six G-01 states, so no single registry row can carry it
  (the registry refuses a non-canonical `to_state`). **Recorded
  reading:** T10 registers as the two outcomes Section 8.5 names —
  `submit_unreviewed` → `in_human_review` with an enumerated §8.4
  reason, and `submit_policy_approved` → `to_be_audited` with
  `merge_status = pending` ("merge-pending", which §8.2's T13
  parenthetical records as a *sub-status* on `to_be_audited`, never a
  seventh state). Both are `transition_id="T10"`.
* **The engine seam** (single, explicit): `resolve_policy_decision()`
  / `set_policy_decision_hook()` in the same module — WP-3.4's
  MT-3.4-07 installs the hook. Without it the fail-closed default is
  *escalate* with `policy_forced_review` (§8.4's member for "policy
  forced this review"; no new code — the exact engine-supplied reason
  arrives with MT-3.4-07; OQ-flagged below). Invariant 8.3.4 is
  structural: each branch's side effect **re-consults the seam** (§9.4
  fixes the evaluator as pure/deterministic, so the service's trigger
  choice and the row's re-check agree) and refuses a branch the engine
  did not choose — a forged `submit_policy_approved` dispatch answers
  `TASK_STATE_CONFLICT` without an approving engine, and the default
  stub can only escalate.

**Trigger precedence** (MT risk note, recorded): scope violation beats
`self_flagged` when both hold ("prefer `self_flagged` only when scope
is clean"); either beats `audit_required` (T8 first); `audit_required`
false reaches the T10 seam last. Two trigger codes were added to
`TransitionReason` **first** (catalog-first, Section 20.4 item 5):
`submit_unreviewed`, `submit_policy_approved` — carried in migration
0007.

All four rows emit `task.transitioned` (already in the Section 9.6
catalog; Section 20.4 item 6) and write Transition rows with the actor
(`agent` → session id) through the single dispatcher transaction.

### Tests

Six new files, all green:

* `backend/tests/test_resolution_submission.py`
  (`-k resolution_submission`) — §7.2 field set, authoritative parse
  over claims, worker clearing, idempotent replay, per-attempt
  uniqueness, the full caller catalog, listing/cursor, patch round trip.
* `backend/tests/test_patch_artifacts.py` (`-k patch_artifacts`) —
  round trip with server-side sha256, inclusive 5 MB boundary,
  +1-byte degraded path unit-wise, oversize end to end (201 + marker),
  no new error codes.
* `backend/tests/test_patch_parsing.py` (`-k patch_parsing`) — 12
  hand-computed fixtures (multi-file, additions/deletions-only, rename,
  binary, mode-only, header-lookalike hunk lines, plain diff with
  timestamps, determinism, empty patch).
* `backend/tests/test_scope_check.py` (`-k scope_check`) — clean/flagged
  cases, glob anchoring, traversal/absolute/backslash rejection,
  normalisation, the two fail-closed readings, shared-matcher identity.
* `backend/tests/test_submission_transitions.py`
  (`-k submission_transitions`) — §19 acceptance (self-flag →
  `self_flagged`, out-of-scope → `scope_violation`), T7 row/event/clear
  side effects, every guard cell, illegal pair + wrong actor, T10
  fail-closed + seam-only approve + forged-trigger refusal, catalog
  checks.
* `backend/tests/wp32_helpers.py` — registry-restore + local-storage +
  throttle-cache autouse fixtures (wp16's promotion trick; no shared
  conftest touched).

Drift guards updated (both files' own rules demanded it when the routes
landed): `test_authorization_matrix.py` (deferred entries retired, row
moved onto the real route, storage on the suite's tmp_path) and
`test_rate_limiting.py` (`present` flipped for all three routes).

**Cross-WP edit (disclosed):** `backend/tests/test_checkpoint_ownership.py`
(WP-1.8) — `test_liveness_checkpoint_extends_under_checkpoint_and_liveness`
flaked 3×/30 in this WP's battery runs: on Windows `timezone.now()` ticks
~15.6 ms, so a claim and a checkpoint inside one tick yield *identical*
microseconds and the strict `>` after extension is unprovable. Fixed by
backdating the stored expiry one minute (the same pattern WP-1.8 itself
already documents in `test_checkpoint_extends_the_stored_lease`); the
assertion stays strict. Re-hammered 0/30 failures afterwards.

### Verification (final battery)

* `ruff check` ✓, `ruff format --check` ✓ (275 files), `mypy` ✓ (299
  files), `manage.py check` ✓, `makemigrations --check` → "No changes
  detected" ✓ (the dev-DB RuntimeWarning is cosmetic — DB not running
  on this machine).
* Targeted pytest: 65 new WP-3.2 tests ✓; partitions 300 ✓ / 137 ✓ /
  140 ✓; drift guards (`test_authorization_matrix.py` 45 ✓,
  `test_rate_limiting.py` 12 ✓); extras — events + route allowlist +
  route checklist + rate-limit tunnel 112 ✓/4 skipped, dashboard 13 ✓,
  manifest ✓; checkpoint file 17 ✓ after the fix above.
* `schemas/openapi.yaml` — regenerated once, then byte-stable across
  two further runs; SHA256
  `D95BC0DB7E906E868AEE78CA567D3F05EC001AE7C58303CE99F783B8C87DAB7F`.
* `bridge/tests/test_openapi_contract.py` — 13/13 ✓ (including the
  coordination fix for attachments' missing `failure_reason` sample).

### Public contract

* `schemas/openapi.yaml` — regenerated **once** at WP convergence
  (sole-regenerator rule; byte-stable across two consecutive runs) with
  the three Submission-row operations and their schemas.
* `bridge/src/orchestrator_bridge/endpoints.py` — `resolution_submit`
  moved out of `PENDING_BACKEND` (it is declared now; the documented
  stale-flag rule) and `bridge/tests/test_openapi_contract.py` gained
  its request/response samples.

### Risk notes / follow-ups

* **T10's two-row shape** (recorded reading above) is the one place the
  registry departs from a literal one-row-per-plan-row transcription;
  if the plan owner prefers a single row with a dynamic outcome, the
  extension point makes the rewire local to this module.
* **`policy_forced_review` as the fail-closed escalation reason** —
  OQ: §8.4 has no "engine not yet wired" member; the closest
  enumerated reason was chosen rather than inventing a thirteenth (or
  leaving the review unexplained). MT-3.4-07 replaces it with the
  engine's real failing-rule reason.
* **Empty `target_scope` semantics** — OQ (recorded under
  MT-3.2-04): fail-closed chosen; if "unrestricted" was intended, the
  one-function change is `evaluate_scope`'s early return.
* **Receive bound** — OQ: `ORCHESTRATOR_REQUEST_BODY_MAX_BYTES`
  (32 MiB) is a WP choice, flagged in configuration.md for owner
  confirmation.
* **Content-key sharing** — OQ for WP-6.x: Section 9.9 retention must
  ref-count (or namespace) patch bodies shared with attachments.
* **WP-3.4** fills `set_policy_decision_hook` (rules R1–R9) and T13/T14;
  until then T10 ships failing-closed as specified (never auto-approve,
  invariant 8.3.4).
* **WP-2.6** (bridge submit tool) lands against this contract: the
  payload shape above, `Idempotency-Key` on the POST, outcome states
  `to_be_audited` / `in_human_review` (+ `review_reason`) in the 201
  body; `LEASE_EXPIRED`/`TASK_STATE_CONFLICT` map to stop-and-orient
  (Section 11.1 step 7).

### Convergence gate (2026-10-13)

- `test_task_model.py` reverse-relation assertion gained `resolutions`
  (TaskResolution's FK — the exact-relation set was missing it); the
  frozen `commit_sha` fixture in `bridge/tests/test_openapi_contract.py`
  got a `pragma: allowlist secret` (detect-secrets false positive); the
  schema move here (+ MT-1.15-06) drove the downstream web/mobile typed-
  client regens — both byte-stable, no WP-3.2 model changed.
