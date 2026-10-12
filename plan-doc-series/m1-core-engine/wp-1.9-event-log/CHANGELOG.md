# WP-1.9 Event log and audit trail: changelog

Short note per completed micro-task (Section 20.4, item 7).

## Unreleased

- **MT-1.9-01** — Event model with monotonic sequence (Sections 9.6, 12.5,
  7.2; FR-SEC-03). New `backend/apps/events/` package: `catalog.py` holds
  the **24 Section 9.6 event types verbatim, in plan order** (the
  authoritative closed set), `models.py` defines `Event` with *exactly*
  the Section 9.6 envelope fields — `id`, `type`, `project_id`,
  `task_id`, `occurred_at`, `actor` (stored as the Section 7.2
  `actor_type`/`actor_ref` column pair, re-grouped into the structured
  `{"type", "ref"}` object by `envelope.py`, never flattened) and
  `data` — plus Section 12.5's `correlation_id` as the only additional
  column. **Id strategy (risk note):** a `BigAutoField` primary key —
  the database's own sequence; strictly increasing, never reused, gaps
  allowed (resume guarantees concern delivery, not contiguous ids), and
  the same value is the SSE event id. Indexes: `(project_id, id)` and
  `(task_id, id)` for filtered replay, `correlation_id` for log
  correlation; CheckConstraints freeze the type catalog and actor triad
  at the database. Append-only is layered like the Task Transition
  history: no API surface, `EventImmutable` hard errors on
  save/delete/update/bulk doors, and the database-level guard of
  MT-1.9-04. Migration `events/0001_initial` applies on a fresh
  database (verified on PostgreSQL 16 as well as SQLite). Tests
  (`tests/events/test_event_model.py`, 8 cases) pin the field set, the
  envelope shape, write-time `occurred_at`, the closed catalogs,
  replay order, and 8-thread concurrent inserts (unique, per-writer
  strictly increasing ids).
- **MT-1.9-02** — Write-in-transaction helper and wired call sites
  (Sections 9.6, 12.5, 9.3; FR-SEC-03). `services.write_event` is the
  single API for appending events: it joins the caller's open
  transaction (rollback takes the event with it — forced-rollback
  tests prove zero rows survive), refuses any type outside the Section
  9.6 catalog and any non-canonical actor/blank ref *before* writing
  (catalog-first, Section 20.4 item 5), stamps `occurred_at` at call
  time inside the transaction, and resolves `correlation_id`
  explicit → request scope → freshly generated (the column is never
  empty — recorded reading; generated ids join no request but keep
  Section 12.5's letter outside request scopes). **Sequencing OQ
  candidate resolved (flagged by MT-1.5-01/06):** the state machine's
  single in-transaction seam now has a *default/override* split —
  `hooks.set_default_event_hook` (installed by `EventsConfig.ready()`
  with `write_transition_event`) is the production writer, while
  `set_event_hook` remains the test-recorder layer and `reset_hooks()`
  returns to the production default instead of a no-op. No second
  event mechanism was invented. Call sites wired, each in the change's
  own transaction: the dispatcher seam (every registered transition —
  `task.transitioned|claimed|released|lease_expired`), `create_task`
  (`task.created`), `update_task` (`task.updated`, only when something
  changed, with the applied field list), `create_project`
  (`project.created`), `PATCH /projects/{pid}` and
  `PATCH /projects/{pid}/policy` (`project.updated`, wrapped in
  `transaction.atomic()`; the policy edit distinguishes itself with
  `data.scope = "policy"` because the catalog has no `policy.updated`
  type). Owner-session paths pass the user id as `actor.ref`; direct
  service calls without a user context fall back to the role label.
  **Gap, not invented (OQ-16):** Section 12.5's token actions
  (issuance, revocation, login — `accounts/services/tokens.py`,
  `sessions.py`, `devices.py`) emit nothing: the Section 9.6 catalog
  has no `token.*`/`login.*` type and catalog-first discipline
  outranks the acceptance line — raised as **OQ-16** in Section 22
  (OQ-15 is reserved for the accounts WP's Section 9.2 route
  amendment), listed in the catalog test's pending/forbidden sets, and
  to be wired the moment the plan decides. Tests:
  `tests/events/test_event_writes.py` (14 cases: exactly-once per
  site, rollback, correlation resolution, catalog refusals).
- **MT-1.9-03** — Post-commit publish to the Redis channel
  (Sections 9.6, 9.10; FR-SEC-03, NFR-03). `publisher.publish_event`
  serializes the stored row through the shared `envelope.event_envelope`
  (published payload ≡ stored envelope — one projection, two
  consumers) and publishes to `ORCHESTRATOR_EVENTS_CHANNEL` on the
  `ORCHESTRATOR_EVENTS_REDIS_URL` connection; registration happens
  exclusively via `transaction.on_commit` inside `write_event`, so
  nothing is published while a transaction is open and a rollback
  publishes nothing. Failures are logged and swallowed — the committed
  Event row remains the source of truth (durability for missed live
  publishes is the DB-based resume, MT-1.10-03; retry semantics are
  out of scope here). Configuration follows Section 9.10: a new
  `EVENTS_` group with documented defaults (`orchestrator:events`;
  URL empty → falls back to `ORCHESTRATOR_CACHE_URL`, so Compose
  needs no new wiring) added to configuration.md
  (group table + full metadata rows, flagged for owner confirmation
  like the `API_` precedent) and `infra/compose/.env.example`. Client
  is lazy (nothing connects at boot); ordering note recorded for
  MT-1.10-02: consumers must sort/filter by envelope `id`, never by
  arrival order. Tests (`tests/events/test_post_commit_publish.py`,
  6 cases): exactly-once publish with payload equality, deferred while
  open, nothing on rollback, outage logged not raised, documented
  defaults, dispatcher flow.
- **MT-1.9-04** — Insert-only database permissions for both audit
  tables (Sections 12.5, 19.1, 16.1). `apps/events/migrations/_guards.py`
  (underscore prefix — the migration loader imports every other module
  in the package) holds one shared, idempotent PostgreSQL statement
  set applied by `events/0002_insert_only_guard` (`events_event`) and
  `tasks/0005_insert_only_guard` (`tasks_tasktransition`): a row
  trigger refusing UPDATE/DELETE with SQLSTATE `42501`, `REVOKE`s
  closing the ACL layer (PUBLIC + executing role), and a restating
  `GRANT INSERT, SELECT` so writers and replay/history readers keep
  working. **Recorded reading (risk note):** in the dev/Compose
  topology the application role *owns* the tables, and an owner's
  inherent privileges are not removable by REVOKE alone — the trigger
  is the enforcement that holds in every topology; the REVOKEs cover
  shared-grant topologies (Section 16.1's one-shot migrate). Statements
  contain no `%` (driver placeholder safety), run only on PostgreSQL
  (the SQLite unit layer keeps the model-level guards), and were
  verified on a real PostgreSQL 16: apply, deny, re-apply with no
  error — running the migrate service twice is safe. Tests
  (`tests/events/test_insert_only_permissions.py`, 4 cases, real
  database, skip-with-command outside the integration layer):
  pg_trigger presence, INSERT/SELECT ok while raw-SQL UPDATE/DELETE
  are denied on both tables, idempotent re-run.
- **MT-1.9-05** — Event catalog tests covering every required emission
  (Sections 9.6, 12.5, 19.1, 20.4 item 6, 20.5). The catalog reference
  suite (`tests/events/test_event_catalog.py`, 9 cases) pins the
  production tuple to an independently transcribed copy of the
  Section 9.6 list **and** to WP-1.5's frozen twin in
  `tests/wp15_helpers.py` (two suites, one plan list), asserts every
  registered transition row names a catalog type, and asserts coverage
  is total: `COVERED ∪ PENDING == the 24 types`, disjoint. Covered
  today (exactly one event per action, correct envelope, and exactly
  one post-commit publish each): `project.created`,
  `project.updated` (project PATCH and policy PATCH), `task.created`,
  `task.updated`, `task.transitioned`, `task.claimed`,
  `task.released` (through WP-1.6's wired T4/T6 — registry snapshotted
  so the WP-1.5 matrix suites keep their stub rows), and
  `task.lease_expired` (T5). Pending entries name their producing WP:
  `task.checkpoint` (WP-1.8), `task.lease_expiring` (WP-1.7),
  `attachment.*` (WP-1.12), `audit.*`/`review.*`/`merge.*` (WP-3.x),
  `agent.session_*` (WP-2.x), `system.alert` (WP-1.7 detector). Token
  actions stay unwired pending **OQ-16**; a dedicated test fails
  loudly if a `token.*`/`login.*`/`auth.*` type ever appears without
  the catalog-first amendment. No catalog additions were made here.
