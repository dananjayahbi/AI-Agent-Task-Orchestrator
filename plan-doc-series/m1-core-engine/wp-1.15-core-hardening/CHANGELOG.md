# WP-1.15 — Core engine test and hardening suite: changelog

## MT-1.15-06 — dashboard summary endpoint (gap closure)

- **`GET /dashboard/summary` lands (Section 9.2 Dashboard row, caller Owner;
  FR-MOB-01).** The row sat in the catalog with no owning micro-task until
  WP-5.6's "Dashboard endpoint gap" note recommended authoring one (MT-1.6-09
  precedent for unowned-endpoint follow-ups). The endpoint is read-only,
  Owner-session-only (`IsOwnerSession`), and aggregates per project, in
  project-id order: `state_counts` (always the six canonical G-01 keys,
  zero-filled; non-archived tasks only — T19 default visibility), `velocity`
  and `active_agents`. Payload shape matches the WP-5.6 recommendation and the
  hand-authored mobile `DashboardSummary` reconciliation contract exactly:
  `{projects: [{project_id, name, state_counts, velocity, active_agents}]}` —
  no pagination (single-resource GET, pagination.md), no invented fields (the
  needs-review banner derives from `in_human_review` on the client), no event
  emissions (Section 9.6 catalog has no dashboard event).
- **Documented defaults, not plan facts (Section 20.1 item 5):** `velocity` is
  pinned as the count of the project's completions in a trailing **7-day**
  rolling window from the append-only TaskTransition log (`to_state=completed`,
  server clock); `active_agents` counts AgentSession rows with
  `ended_at IS NULL` (no heartbeat freshness invented — OQ-04 stays closed).
  Both are raised as OQs for owner ratification; the payload stays
  authoritative so the mobile client never recomputes either number
  (MT-5.6-01 risk note).
- **Callers:** owner session 200; every agent role, a device token → 403
  `ROLE_NOT_PERMITTED`; anonymous → 401 `AUTH_REQUIRED` — all with the
  five-field Section 9.2 envelope. The deferred
  `/api/v1/dashboard/summary` entry in
  `tests/test_authorization_matrix.py::DEFERRED_ENDPOINTS` is retired per that
  drift guard's own instruction; the real per-caller cases (incl. the
  cross-project proof that a PID-scoped agent token receives no counts) live in
  `tests/test_dashboard_summary.py`.
- **Device cell is an OQ, not a widening:** §9.2 names Owner and §12.2 prints
  no dashboard row, so the mobile's device token is denied exactly like every
  other non-Owner caller. Granting the device a cell (the WP-1.8 checkpoints
  precedent) is an owner decision recorded as a follow-up.
- Tests: `backend/tests/test_dashboard_summary.py` (payload shape, six-key
  zero-fill, archive exclusion, velocity window, active-vs-ended sessions,
  full caller matrix + envelope codes).

### Follow-ups recorded by MT-1.15-06

- `schemas/openapi.yaml` regeneration for the new path — the audit finisher is
  the SOLE OpenAPI regenerator (Section 20.4 item 4); until it runs, the
  committed snapshot has no `/dashboard/summary` path and the mobile typed
  client stays on the hand-authored seam.
- Mobile swap of `DioDashboardSummarySource` to the generated client once the
  schema path lands (the WP-5.6 gap-note recommendation; one-file change
  behind the seam).
- OQ: the server's velocity definition/window (7-day rolling completions here)
  and the dashboard device cell — both await owner ratification.

---

## MT-1.15-01 — Consolidate the claim race test suite (done)

- **Adopted, not duplicated (Section 19.6):** the MT-1.6-08 harness now
  lives behind one shared module — `backend/tests/integration/race_harness.py`
  — carrying the barrier race runner (`race`), the duplicate-request driver
  (`duplicate_posts`, the helper MT-1.6-08/MT-1.15-03 flagged as shared), the
  Postgres skip probe and the `PublishRecorder` listener-noise recorder.
  `test_claim_race_postgres.py` and `test_sweeper_chaos_postgres.py` both
  import it; neither keeps a private copy of the orchestration.
- **Section 18 shape verified green:** 50 parallel service-level claims and
  50 parallel endpoint claims against real Postgres — exactly one winner, 49
  `TASK_ALREADY_CLAIMED` — unchanged through the refactor and run on PG
  (7 passed).
- **Listener-noise gap closed:** the 50-way service race arms
  `PublishRecorder` on the events publisher and asserts the channel carries
  exactly one envelope — the winner's `task.claimed`, envelope id equal to
  the single Event row. The 49 rolled-back losers publish nothing (only
  committed transactions fire `transaction.on_commit`), so no orphaned
  `claimed` rows and no channel noise.
- **Sequential-claims control added:**
  `test_sequential_second_claim_loses_with_the_catalog_code` — claim once,
  replay at the service layer (`TaskAlreadyClaimed` → `TASK_ALREADY_CLAIMED`)
  and at the endpoint (409 with the same code the race losers received), then
  assert the persisted state equals the race's post-race state: one claim,
  one active lease (winner's fencing pair on the row), one transition, one
  event, nothing orphaned.
- **CI wiring:** the suite sits in `backend/tests/integration/`, which the
  integration job already selects (`pytest tests/integration
  --ds apps.core.settings.dev`) — green-in-CI needs no workflow change, and
  none was made (MT-1.15-05 owns coverage gates and is deferred).
- **No behavior changes** to the claim path (Section 9.3 untouched); no
  secrets or environment-specific paths committed — the skip probe's reason
  carries the canonical command only.
- Tests: `backend/tests/integration/test_claim_race_postgres.py`,
  shared: `backend/tests/integration/race_harness.py`.

## MT-1.15-02 — Consolidate the sweeper race test suite (done)

- **Shared runner extracted as flagged (Section 19.6):**
  `test_sweeper_chaos_postgres.py` dropped its private `_race`/skip-probe
  copies and drives every scenario through `race_harness.race`
  (deadline-joined workers, gate-capable) — one harness module, two suites.
  All five original scenarios stayed green through the refactor plus the new
  LS-SHORT scenario (6 passed on PG).
- **Catalog codes on the expiry paths (Section 9.2/9.3):** scenarios assert
  `LEASE_EXPIRED` (checkpoint-vs-expiry; LS-SHORT's dead lease answered to
  its own owner) and — newly asserted — `LEASE_NOT_OWNED` (LS-SHORT's foreign
  session on the live lease). Single-reclaim under two racing sweepers stays
  proven by the row lock + T5 in-progress-only guard (FR-LEA-05): one T5 and
  one event per reclaimed task, no exception escapes the worker.
- **Listener-noise check applied to sweeper scenarios:** the double-sweeper
  race arms `PublishRecorder` after setup and asserts exactly five
  `task.lease_expired` envelopes — one per reclaimed task, ids matching the
  Event rows, nothing duplicated by the loser sweeper.
  *Sequential-baseline check confirmed:* the single-sweeper dead-worker
  scenario is the baseline, and each chaos scenario's terminal asserts equal
  it (same PENDING landing, `failure_retry_count` +1, one event) — no extra
  control needed beyond the existing structure.
- **`LS-SHORT` recorded as a limitation, with rationale (no silent drop):**
  a lease *strictly* shorter than the sweep scan interval is not configurable
  in the current design. `config/celery.py` fixes `lease-sweeper` at 60 s
  ("The intervals are fixed by the plan (not env-tunable)", Section 9.9) and
  the policy serializer floors `lease_duration_minutes` at 1 (= 60 s), so
  the shortest expressible lease *equals* the interval. Making the scenario
  expressible needs either env-tunable beat intervals or sub-minute leases —
  a plan-level behavior change this test task must not make (out of scope).
  Per the risk note the gap is raised as **OQ-17 (proposed)**: should Section
  9.9's sweep interval become configurable (or the lease floor drop below
  it) so a sub-interval lease can exist? No interval was hardcoded for the
  test's benefit.
- **The expressible floor is pinned executably instead:**
  `test_ls_short_1_minute_floor_lease_reclaims_once_with_both_catalog_codes`
  asserts the beat interval == the policy floor (the non-configurability
  fact as an executable assertion), a live floor lease is never swept early,
  both catalog codes answer the ownership races, the next scan after expiry
  reclaims exactly once, and the scan after that is a no-op — terminal
  invariants only, no wall-clock timing.
- Tests: `backend/tests/integration/test_sweeper_chaos_postgres.py`.

## MT-1.15-03 — Consolidate the idempotency test suite (done)

- **One suite, four operation classes — consolidation, not duplication:**
  `backend/tests/integration/test_idempotency_postgres.py` (the repo's PG
  home for this gate; the docs' `backend/tests/idsempotency/` path maps onto
  the existing integration layout so CI's `pytest tests/integration` job
  gates it with no `.github` change). Coverage map, stated in the module
  docstring so nothing is silently implied:
  - **claim** — *adopted by reference* (same gate): the 50-attempt
    same-session service storm, the 50-attempt endpoint race, the
    same-`Idempotency-Key` endpoint race with byte-identical replays and the
    new sequential control in `test_claim_race_postgres.py`, plus
    `test_claim_release_endpoints.py`'s sequential unit replays. Not
    re-implemented here.
  - **checkpoint** — *new PG proofs:* sequential same-key replay (one row,
    no double extension, byte-identical body, exactly one `task.checkpoint`
    event) and the concurrent same-key storm (every response 2xx; one row +
    one event per executed request — distinct outcomes == row count; task
    never regresses; Section 8.6 lease cap holds; no transitions dispatched;
    a post-storm sequential retry replays byte-identically with zero writes).
  - **submit** — *new PG proofs:* sequential same-key replay (one
    resolution, one T7 transition, one `task.transitioned`, one stored patch
    file) and the concurrent same-key storm (statuses ⊆ {201, 409}; one
    byte-identical 201; every 409 is `TASK_STATE_CONFLICT`; one resolution,
    one transition, one event, one patch file — no second completion side
    effect at either the row layer or the storage layer).
  - **decision** — *deferred to WP-3.6 M3 (deferred-investigation note):*
    no decision endpoint exists — `/api/v1/tasks/{id}/review` remains in
    `tests/test_authorization_matrix.py::DEFERRED_ENDPOINTS`. Per the MT's
    do-not-invent rule nothing was invented; MT-1.6-07's duplicate-decision
    assertions are adopted by reference once the surface lands.
- **Shared scaffolding (Section 19.6):** concurrent duplicates for claim
  (keyed race), checkpoint and submit all drive through the single
  `race_harness.duplicate_posts` implementation.
- **Submit-replay reading recorded (risk note; for WP-2.6 / WP-4.x
  clients):** per Section 8.2's table a *repeat* submit on the same attempt
  is not a no-op 2xx — a re-execution answers `TASK_STATE_CONFLICT` (409),
  while an `Idempotency-Key` replay returns the stored 201 byte-identically.
  Clients must treat 409-after-submit as "already submitted on this attempt"
  and not retry it as a different request.
- **Finding recorded, mechanism untouched (out of scope):**
  `apps/core/idempotency.py`'s cache store does not linearize concurrent
  same-key requests (its own docstring), so concurrent checkpoint POSTs that
  all miss the cache each append before any outcome is stored. The suite
  proves the invariants that hold under either interleaving (rows ==
  distinct outcomes == events; capped lease; no transitions; byte-identical
  post-storm replay) and deliberately does not change the mechanism —
  MT-1.15-03 out-of-scope puts idempotency-key mechanism work in follow-ups.
  The mechanism question is raised as **OQ-18 (proposed)**: should NFR-12's
  retry-safety extend to linearizing *concurrent* same-key execution (fence
  in the store), or is concurrency outside NFR-12's retry contract? Owner
  ratification required.
- Tests: `backend/tests/integration/test_idempotency_postgres.py` (4 passed
  on PG).

## MT-1.15-04 / MT-1.15-05 — deferred (roadmap 4a)

- **MT-1.15-04 (authorization suite)** — DEFERRED: depends on MT-1.13-05
  (attachments authorization rows) and MT-1.14-05 (audit authorization
  rows), neither landed. No edits made; `test_authorization_matrix.py` keeps
  its existing coverage and deferred-endpoint drift guard.
- **MT-1.15-05 (coverage gates)** — DEFERRED: needs all four WP-1.15 suites
  (01–03 now done; 04 deferred) and owns the `.github` coverage-gate wiring,
  which is explicitly out of bounds for this pass.
- **Convergence gate:** OQ-17 (sub-interval `LS-SHORT` leases) and OQ-18
  (idempotency-cache linearization) were added to parent plan Section 22's
  table as OPEN rows following OQ-16's format; backend full suite green
  (1326 passed, 26 skipped).
