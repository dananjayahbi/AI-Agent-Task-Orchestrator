# WP-1.8 — Checkpoints and token usage: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.8-01 (checkpoint model)** — `TaskCheckpoint` with exactly the
  Section 7.2 nine fields (UUID pk, `task_id` FK, `attempt_number`,
  `session_id`, server `timestamp`, `message`, nullable `percent`
  0–100, `token_usage` JSON, `kind` progress/liveness/system) plus the
  `checkpoint_task_time` (task, timestamp) listing index for MT-1.8-04
  and the app-layer append-only discipline of P8 (queryset
  update/delete/bulk_update and model re-save/delete all raise
  `CheckpointImmutable`; DB-level insert-only grants remain MT-1.9-04's
  pattern, same recorded caveat as the transition history). Recorded
  readings: `timestamp` is a callable server default, **not**
  `auto_now_add` — the value is still server-set in production (P7; the
  create serializer accepts no timestamp field) and the deviation from
  `TaskTransition` exists only so cursor-tiebreak tests can construct
  controlled tied timestamps (insert-time control; the append-only
  guards still refuse every post-insert change); `percent` carries a
  `MaxValueValidator(100)` **and** a DB CheckConstraint (boundary and
  database both, WP-1.8 acceptance); `token_usage` stays a free JSON
  blob — inventing a fixed shape would be an OQ for WP-2.6/WP-4.6;
  `store_checkpoint` is the task-side touch point (copies
  `attempt_number` at write time, moves `last_checkpoint_at`, bumps
  `version` — every change increments, Section 7.2).
- **MT-1.8-02 (ownership/fencing gate)** — the checkpoint write path
  (`apps/tasks/services/checkpoints.py::submit_checkpoint`) runs Flow B
  in **one transaction**: `select_for_update` → ADR-004 project scope →
  the MT-1.6-05 `require_current_lease` helper re-checked **under the
  row lock** (TOCTOU closed; a sweeper reclaim racing the checkpoint
  always wins) → insert → touch → MT-1.6-03 extension → in-transaction
  `task.checkpoint` event. Rejections (`LEASE_EXPIRED` for
  expired/stale-generation, `LEASE_NOT_OWNED` for a foreign session,
  `TASK_NOT_FOUND`, `AUTH_FORBIDDEN_PROJECT`) raise before any write —
  no row, no touch, no extension, no event (Section 8.6 "no
  resurrection"), proven per path in `test_checkpoint_ownership`.
  Recorded readings: kind gating follows OQ-04's outcome — `progress`
  and `system` carry the lease extension; `liveness` extends only under
  the project's `checkpoint_and_liveness` mode (the default
  `checkpoint_only` stores the row and event, leaves the lease
  untouched); an extending checkpoint bumps `version` **twice** (the
  touch and the extension are two row changes — recorded, not
  optimized away); the true parallel race needs Postgres (SQLite's
  no-op `select_for_update` — MT-1.6-06's recorded caveat); the suite
  proves the logic-level interleavings every schedule reduces to, and
  WP-1.15's concurrency suite re-proves the timing.
- **MT-1.8-03 (checkpoint endpoint)** —
  `POST /tasks/{id}/checkpoints` (caller Agent; the owner holds no
  lease session, so the Flow B gate would refuse it — recorded reading
  of the §9.2 "Agent / Owner" row: POST is the agent's write, GET the
  shared read) with the frozen Section 10.5 response: the stored
  checkpoint's identity, `lease_extended`, the **new
  `lease_expires_at`** (the bridge's `next_checkpoint_due` source) and
  `capped` (MT-1.6-03's flag, its docstring names this response as the
  consumer — no other ad-hoc fields). `Idempotency-Key` replay returns
  the stored outcome: no duplicate row, no double extension, no
  re-emitted event (NFR-12). `percent`/`kind`/unknown-field refusals
  answer `VALIDATION_ERROR`; the lease family answers 409/403 as the
  leases app documents. `task.checkpoint` is written through WP-1.9's
  writer inside the same transaction, carrying the §7.2 content fields
  the G-11 feed renders (checkpoint id, attempt, kind, percent,
  message, token usage, session). `AgentEndpointThrottle` on the view
  (FR-SEC-05; the Progress row is a mixed-caller row and the
  rate-limit enumeration lists this path as agent-throttled — owner
  GETs ride their own per-token budget, never an agent's).
  Drift guards updated: the `/api/v1/tasks/1/checkpoints` row flipped
  to `present=True` in `test_rate_limiting.py` (the file's own protocol
  assigns the flip to the landing WP); the matching
  `DEFERRED_ENDPOINTS` entry in `test_authorization_matrix.py`
  **requires the matrix owner (WP-1.10) to remove it and add the real
  POST/GET cases** — reported, not edited (sole-matrix-editor rule).
- **MT-1.8-04 (checkpoint listing)** —
  `GET /tasks/{id}/checkpoints` (caller Agent / Owner —
  `CanReadCheckpoints`, an endpoint-shape adapter in the same pattern
  as the leases app's `CanReleaseTask`; devices are not in the cell and
  answer `ROLE_NOT_PERMITTED`) with WP-0.5-04 cursor pagination over
  the stable `(-timestamp, -id)` keyset: opaque two-part cursor,
  `{results, next_cursor}` envelope, default 25 / maximum 100 (clamped,
  same per-endpoint choice as the other list routes), fetch-one
  lookahead. Timestamp ties page through the UUID id tiebreak (rule 2),
  inserts during paging never shift or duplicate the promised rows, an
  empty task returns an empty page, and malformed cursors answer
  `VALIDATION_ERROR`. Recorded reading: the §9.2 "Agent / Owner" caller
  column excludes devices on this row (FR-MOB-03's stream reads via
  owner session or agent token; a device cell would be an OQ for
  WP-5.x); filtering by `kind`/`attempt_number` and aggregations stay
  out (MT-1.8-04 out-of-scope — OQ before inventing).

## Final battery (WP-1.8)

- `ruff check` / `ruff format --check`: clean (249 files).
- `mypy .`: clean (233 source files) — custom-manager `create()` return
  cast in `store_checkpoint`, `QuerySet[TaskCheckpoint]` return cast in
  `checkpoint_list_queryset`, datetime-None guards in the ownership /
  endpoint tests, and explicit `HTTP_IDEMPOTENCY_KEY=` kwargs instead of
  `**headers` spreads in the idempotency tests.
- `manage.py check`: 0 issues; `makemigrations --check --dry-run`: no
  changes detected.
- Targeted pytest: 190 passed — the four WP-1.8 suites (model 15,
  ownership 17, endpoint 19, listing 16 = 67) plus the WP-1.4/1.5/1.6
  suites touched by the integration seams (test_task_api,
  test_task_list, test_claim_release_endpoints, test_lease_extension,
  test_lease_fencing, test_transition_history, test_rate_limiting).
- OpenAPI: exactly one regen (`manage.py spectacular`) at the end, then
  one immediate re-run — identical sha256 (byte-stable). The regenerated
  file also carries the sibling events agent's `/api/v1/events` path
  (single shared regen; expected). One benign spectacular warning: a
  `kind` enum-name collision auto-resolved to `KindE0dEnum` (no
  `ENUM_NAME_OVERRIDES` configured anywhere in the repo; deterministic
  and byte-stable, left alone to avoid touching shared settings this
  round).
- Not run (coordination): `test_authorization_matrix.py` — its deferred
  drift-guard row for `/api/v1/tasks/1/checkpoints` now fails by design
  (the endpoint exists); the events agent owns that file.
