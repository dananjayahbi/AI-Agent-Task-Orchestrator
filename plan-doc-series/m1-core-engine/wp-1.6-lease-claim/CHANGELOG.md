# WP-1.6 — Lease and claim service: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.6-01 (atomic claim transaction)** — `POST /tasks/{id}/claim`'s
  service half: Section 9.3's algorithm step for step (scope from token,
  task-addressed read, from-state check, in-transaction T4 dispatch with the
  lease acquire side effect), losers answer `TASK_ALREADY_CLAIMED` (409) and
  never touch a generation. Recorded readings: a paused project's claim is
  `TASK_STATE_CONFLICT` (the T4 "Project active" guard, not a project code —
  the catalog has no paused-project code for agents); claim does **not**
  require a pre-existing `AgentSession` row (neither Section 9.3 nor the
  request contract gates on it); state writes happen only through the
  dispatcher's public API — no direct `state` assignment (Section 9.1).
- **MT-1.6-02 (next-available selection)** — `GET /projects/{id}/work`'s
  offer queryset (offerable = pending, non-archived, dependencies completed,
  role filter, ordered urgent > high > medium > low then oldest) and the
  claim-next service that selects from it under `skip_locked`. Recorded
  readings: a paused project's work list is an **empty 200**, never an error
  (FR-PRJ-04); `WorkQuery` exposes `role` + `priority` (and paging) but no
  `state` parameter — offerability *is* the state filter.
- **MT-1.6-03 (lease extension / cap)** — checkpoint-triggered extension
  computes `min(now + duration, acquired_at + lease_max_total_minutes)` and
  returns a `capped` flag; a capped lease answers `LEASE_EXPIRED`-family
  behavior instead of extending past the hard cap (Section 7.2). Recorded
  reading: extension bumps the task `version` like every other transition
  input change (CAS discipline, WP-1.4).
- **MT-1.6-04 (voluntary release)** — T6 release through the dispatcher
  (side effect clears the lease fields, generation is *not* decremented) and
  the Owner override path (`owner_override`, no fencing pair required — the
  Section 8.2 T6 Actor column is C, O). Recorded reading: a **late owner**
  whose lease was swept while it was away (state already back to `pending`,
  generation current) answers `LEASE_EXPIRED` (409), not a silent success.
- **MT-1.6-05 (lease fencing generation)** — one fencing helper for all
  lease operations with a deliberate check order: stale generation →
  `LEASE_EXPIRED`; dead/absent lease → `LEASE_EXPIRED`; wrong session →
  `LEASE_NOT_OWNED` (403). Every claim increments `lease_generation` (Section
  8.6), so a stale writer can never act on a re-acquired lease.
- **MT-1.6-06 (concurrency limit)** — `max_concurrent_tasks` enforced inside
  the T4 guard *after* locking the project row (the cross-task mutex that
  makes the count race-free) → `CONCURRENCY_LIMIT_REACHED` (409). Counted:
  `state=in_progress AND claimed_role=coder`. The serialization itself is
  proven only on real Postgres (MT-1.6-08's twin) — SQLite's no-op
  `select_for_update` cannot race.
- **MT-1.6-07 (claim / release / work endpoints)** — the three Section 9.2
  Agent-work routes with catalog-closed errors, `AgentEndpointThrottle`,
  and the WP-1.4/1.5 idempotency convention (local `_replay_or_none` /
  `_store_outcome` helpers — 2xx outcomes only, fingerprint-checked).
  Recorded readings: claim's permission cell is **state-dependent** — one
  route carries two Section 12.2 rows (pending → coder, `to_be_audited` →
  auditor), so `CanClaimTask` picks the accounts row from the task's state;
  an auditor reaching a `to_be_audited` claim today gets
  `TASK_STATE_CONFLICT` (409) because T11's wiring is WP-3.x's (the matrix
  accepts 200/409 for that cell with the comment); owner **may** release
  (T6 override) but **may not** read the work list (caller Agent). Drift
  guards updated: the claim/release/work/agent-sessions entries left
  `DEFERRED_ENDPOINTS` (real cases replaced them, `test_authorization_matrix`)
  and five `AGENT_OR_DEVICE_ROUTES` rows flipped to `present=True`
  (`test_rate_limiting`).
- **MT-1.6-08 (exhaustive claim-race tests)** — `tests/integration/
  test_claim_race_postgres.py`: NFR-01's *50 concurrent claims → exactly one
  winner* at **both** levels (service: 1 won + 49 `TASK_ALREADY_CLAIMED`;
  endpoint: one 200 + forty-nine 409 envelopes, no 404/500 leaks), the
  next-available disjointness race, the project-mutex concurrency-limit
  race, the same-`Idempotency-Key` race (exactly one lease, byte-identical
  replays, sequential retry identical), and claim/release interleavings
  holding the Section 8.3 invariants (generation = leases, version =
  transitions, history paired). Skip harness mirrors MT-1.4-02's twin:
  SQLite unit layer skips; runs with
  `pytest tests/integration --ds apps.core.settings.dev` on reachable
  Postgres.
- **MT-1.6-09 (documentation first; implementation below)** — Agent session open
  and end endpoints (Sections 9.2 Sessions row, 7.2 Agent Session entity, 12.2;
  FR-SEC-01/02/05; G-18). **Plan gap closed:** `POST /agent-sessions` and
  `POST /agent-sessions/{id}/end` are required by MT-2.2-04, MT-2.9-03 and
  MT-2.12-03, but no micro-document owned them — MT-1.2-03's out-of-scope note
  deferred them to a "WP-1.x sessions slice" that was never created (roadmap
  rule 7: an added MT updates `overview.md`). New micro-document
  `MT-1.6-09-agent-session-lifecycle.md` follows the Section 20.2 template and
  derives strictly from Sections 9.2 + 7.2 + 12.2; index row added to
  `plan-doc-series/overview.md`. Recorded readings fixed here: session `id` is
  bridge-issued and opaque (G-18 — shape-validated, never parsed); `project_id`
  and `token_id` come from the token, never the body (ADR-004; Section 9.3 step
  1 reading); duplicate id and unknown id answer `VALIDATION_ERROR` (the closed
  19-code catalog has no id-collision/not-found code for sessions — the same
  "no catalog code of its own" mapping the core handler documents for projects);
  double-end is a `200` replay (best-effort shutdown calls must be safe);
  Section 9.6 `agent.session_started`/`agent.session_ended` emission is wired
  when WP-1.9 lands its single in-transaction event writer (no second event
  mechanism invented here); claim does **not** require a pre-existing session
  row (the Section 9.3 algorithm and MT-1.6-01's contract never gate on it —
  recorded reading, not a hidden decision).
- **Cross-cutting follow-ups landed with the WP** — `Task` gained
  `lease_generation` (PositiveIntegerField, Section 7.2/8.6; the
  `test_task_model` field-set assertion updated to include it); a stale,
  unused `type: ignore[attr-defined]` was removed from
  `apps/tasks/serializers/tasks.py` (it failed full-repo mypy);
  `plan-doc-series/overview.md` now indexes 329 micro-tasks (328 + the new
  MT-1.6-09) — roadmap's printed count needs the same +1 when it is next
  touched; no new `ORCHESTRATOR_*` settings were introduced (canonical env
  names unchanged, no configuration.md/.env.example edits required).
