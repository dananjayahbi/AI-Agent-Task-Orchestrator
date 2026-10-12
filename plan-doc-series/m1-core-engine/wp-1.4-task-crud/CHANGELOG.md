# WP-1.4 — Task model, id sequencing and CRUD: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.4-01** — Task model with Section 7.2 fields and check constraints
  (Sections 7.2, 7.3, 7.4, 8.1, 8.4; FR-TSK-01/02/06; G-01, ADR-010).
  `backend/apps/tasks/models/task.py` carries **exactly** the Section 7.2
  "Task" table — the field set is asserted literally in tests (none added,
  dropped or renamed). Layout mirrors WP-1.3: `models/task.py` (one entity
  per file; MT-1.4-05 adds `models/dependencies.py`),
  `services/ids.py` (the Section 7.3 id machinery), one migration
  `apps/tasks/migrations/0001_initial.py` (the Task model only — Section
  20.3; depends on `projects.0002_initial` through the normal chain).
  **Decisions recorded per the MT risk notes:**
  *`project_id` naming* — Section 7.2's FK is the Django field `project`
  whose column and attname are literally `project_id` (naming the Django
  field `project_id` would have produced the column `project_id_id`);
  the API renders `project_id`. *Enums* — the six G-01 states
  (`draft` default, Section 8.2 T1), four FR-TSK-05 priorities, coder/
  auditor `claimed_role`, the six `merge_status` values and the twelve
  Section 8.4 review reasons exist as `TextChoices` (ADR-010 machine
  values, no display strings in columns). *Constraints (Section 7.4):*
  six DB `CheckConstraint`s — `task_id_format`
  (`^PID[0-9]{5}-T[0-9]{3,}$`, anchored, growth to `T1000`+ tested),
  `task_state_canonical`, `task_priority_canonical`,
  `task_version_at_least_one` (FR-TSK-06 floor), and the
  `failure_retry_count`/`attempt_number` floors. Out-of-set `state` and
  `priority` are refused **at the database**; the choice columns whose
  owning services do not exist yet (`claimed_role`, `review_reason`,
  `merge_status`) are boundary-checked only (`full_clean` — the WP-1.3
  precedent), recorded so the split is a decision, not an omission.
  *Documented defaults, not plan facts (flagged for owner confirmation):*
  `priority` defaults to `medium` (the plan states no default; `medium` is
  the neutral FR-TSK-05 member), `title` is capped at 200 characters
  (mirroring `Project.name`) and `test_command` at 500. *Readings:*
  `created_by` stores an actor-reference **string** (owner user id — the
  Section 9.6/12.5 `actor_ref` convention; a token reference once
  Decomposer/Device creation activates), not a User FK, so future
  non-user creators do not force a schema change; the FK uses
  `on_delete=PROTECT` (a task is never cascade-deleted — Section 7.3);
  `audit_required` defaults to `True`, mirroring the policy's
  `audit_required_default`, and the create path copies the project
  policy's value (MT-1.4-03). *Section 7.4 rule 4* — a `save()` guard
  refuses reassigning a loaded task's project (same application-level
  reading as Project's id-immutability guard, including the documented
  `queryset.update()` bypass; DB triggers stay outside Section 20.3's
  sizing). *Write contract recorded, not yet enforced:* `state` is written
  only by WP-1.5's state-machine service (Section 9.1 `tasks` owns state
  changes); `version` starts at 1 and every write path increments it —
  the enforcement tests arrive with WP-1.5 as the MT specifies.
  *NFR-09 indexes* ship with the model (`task_proj_prio_created`,
  `task_proj_state`) so MT-1.4-04's list shape never scans at 10,000-task
  scale — the index *use* assertion lands with that MT's list tests.
  Lease/worker/merge fields exist without behavior (Section 7.2 defines
  the entity once — MT risk note; WP-1.6/M3 own them).
  Tests (`backend/tests/test_task_model.py`, 13 cases) cover the literal
  field set + `project_id` column spelling, every canonical default (saved
  *and* DB round-trip), JSON-default isolation, the enum tables, DB
  rejection of seven malformed id shapes (incl. `PID1-T1`,
  `PID00001-T1`, `PID00001-T01`), acceptance of `T001`→`T999`→`T1000`→
  long indexes, the three floor constraints, DB rejection of out-of-set
  state/priority, `full_clean` rejection of every out-of-set enum, the
  declared constraint/index names, project immutability, and the
  migration's clean apply **and reverse** (`migrate tasks zero` →
  re-apply, the Section 18/20.3 pattern). Verified:
  `ruff check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run` clean; targeted
  `pytest -k "task and (model or constraint)"` green (13 passed).
- **MT-1.4-02** — Atomic per-project task counter for gap-tolerant ids
  (Sections 7.2, 7.3, 9.1, 9.3, 18; FR-TSK-01; WP-1.4 acceptance).
  `backend/apps/tasks/services/ids.py` now owns the complete Section 7.3
  machinery: `render_task_id` (`1`→`T001`, `999`→`T999`, `1000`→
  `T1000` — zero-padding is a *minimum* width; `T000`/negative indexes
  raise `ValueError`, mirroring the PID sequence's never-zero reading)
  and **`allocate_task_id` — the single allocation entry point** for
  MT-1.4-03's create service and WP-1.5's T1 side effect. *Algorithm
  (Section 7.3, verbatim):* inside one transaction (the caller's —
  `atomic` nests as a savepoint, so lock + increment + task INSERT share
  the **creating** transaction) run **one atomic
  `UPDATE {table} SET task_counter = task_counter + 1 ... RETURNING
  task_counter`** and build the id from the returned value. *Recorded
  decisions:* the UPDATE statement itself **is** the Section 7.3 row
  lock (an exclusive Postgres row lock held until commit — stronger than
  a following `SELECT ... FOR UPDATE`, acquired and read back in a single
  statement); the one-statement shape is also load-bearing on the SQLite
  unit layer, where the obvious ORM pattern (read row, then write) made
  every worker hold a shared-cache read lock to end-of-transaction and
  **livelocked the upgrade — 100 concurrent creations made zero progress
  in 105 s until the allocator became a single UPDATE** (diagnosed and
  fixed here; WP-1.6's claim code should read this note before composing
  read-then-write transactions against shared-cache SQLite tests). The
  increment no longer goes through `Model.save()`, so — deliberately —
  creating a task never bumps the project's `updated_at` (task churn is
  not a project edit). *Gap tolerance (FR-TSK-01), documented, never
  "repaired":* the counter increment is transactional, so a rolled-back
  create **refunds** its number (re-issuing it cannot collide — no row
  ever carried it), while a committed increment whose task row never
  materializes leaves a **permanent skip**; no fill-the-gap logic exists
  anywhere (both behaviors asserted). *Lock-ordering note for
  WP-1.5/1.6 reviewers (MT risk note):* the project row is a hot row —
  the locked section is exactly one statement, and every future writer
  must acquire the project lock before task-row locks, consistently.
  Tests (`backend/tests/test_task_id_allocation.py`, 8 cases): render
  format/growth/refusal, sequential allocation `T001`/`T002` with counter
  advancement, contiguous no-failure baseline, a **structural drift
  guard** (any write to `task_counter` outside `services/ids.py` —
  matched as assignments/quoted keys, prose mentions allowed — fails the
  build; `projects/services` scanned too), rollback-refund without reuse
  collision, committed-gap never back-filled, and the WP-1.4 acceptance:
  **100 barrier-synchronized concurrent creations yield 100 unique,
  pattern-valid ids** with `task_counter == 100` (the retry loop is
  time-bounded with capped backoff — a fixed attempt count × SQLite's
  5 s busy timeout can outlive a join window and leak workers into
  teardown; recorded because the first attempt did exactly that).
  *Section 18 integration layer:*
  `backend/tests/integration/test_task_id_allocation_postgres.py` is the
  Postgres twin — same helper (100 threads) with a semaphore capping
  simultaneously open sessions well under the stock
  `max_connections=100`; it self-skips under the hermetic unit settings
  (the skip reason carries the command) and runs when
  `ORCHESTRATOR_DATABASE_URL` points at real Postgres. **CI/CONTRIBUTING
  fix (required for the MT's "runs on real Postgres in CI" acceptance):**
  the documented integration command `uv run --directory backend pytest
  backend/tests/integration` resolved its path against `--directory`'s
  cwd (`backend/backend/...` — nonexistent, which would have failed CI
  the moment the suite landed); the workflow step and CONTRIBUTING.md
  now read `pytest tests/integration --ds apps.core.settings.dev` — the
  `--ds` selects the module that binds `DATABASES`/`CACHES` to the
  CI-provided service URLs, without which the unit SQLite settings would
  silently skip the layer (the bridge row of that table keeps its old
  form — outside this WP's scope, flagged in the report). Verified
  end-to-end locally against a throwaway `postgres:16-alpine` container:
  the integration test **passed** (100 unique ids, counter exact, 1.85 s).
  Verified: `ruff check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run` clean; targeted
  `pytest tests/test_task_id_allocation.py` green (8 passed, plus the
  integration module skipping with its documented reason under unit
  settings).
- **MT-1.4-03** — Task CRUD endpoints (Sections 9.2, 7.2, 7.3, 8.2 T1,
  12.2, 12.3; FR-TSK-01/02/06; ADR-012; ADR-004).
  `POST /projects/{pid}/tasks`, `GET /tasks/{id}` and `PATCH /tasks/{id}`
  landed under the modular layout — `views/tasks.py` (thin adapters),
  `serializers/tasks.py` (read model + the two input contracts),
  `services/tasks.py` (create/update/lookup + the `target_scope` rule),
  `permissions.py`, `exceptions.py`, `urls.py`, wired into the root
  router beside the projects surface. **Decisions recorded per the MT
  risk notes:** *Owner-only now, matrix cells deferred* — Section 12.2
  prints Decomposer = Yes and Device = Yes (Could) on "Create draft
  tasks", but with no distinct decomposer token kind yet (MT-1.2-05
  risk) the real routes enforce Owner-only **today** (`IsOwnerSession`
  behind the scope guard); the two printed cells are recorded
  *explicitly and executably* in `tests/test_authorization_matrix.py`
  as `DEFERRED_MATRIX_CELLS` (a test asserts their current 403
  `ROLE_NOT_PERMITTED` on the real route with a WP-2.x/M5 revisit
  marker — activation = swap the permission class to the already-built,
  cell-tested `CanCreateDraftTasks`), so the matrix is neither silently
  claimed nor silently dropped. *Scope before role* (ADR-004): the
  create route keeps `HasProjectScope`, and the detail route gains
  **`HasTaskProjectScope`** — a tasks-app companion guard that parses
  the addressed PID *out of the task id* (Section 7.3 shape; URL, never
  body — Section 9.3 step 1), so the WP-1.2 acceptance now holds on
  task routes verbatim: a PID00001 agent token answers
  `AUTH_FORBIDDEN_PROJECT` on PID00002's tasks (asserted for both route
  shapes); a malformed id yields no PID to scope against and falls
  through to the role/validation answers. *Status choices* —
  `TASK_NOT_FOUND` answers **404** (the resource-owning status the core
  handler docstring reserved for work packages that have a code of
  their own; projects keep the recorded 400 asymmetry), and
  `VERSION_CONFLICT` answers **409** ("a stale version returns a
  conflict", Section 8.2 rules — the status the plan states for
  `TASK_STATE_CONFLICT`'s conflict class); both in
  `apps/tasks/exceptions.py`, catalog codes only (20.4 item 5).
  *Writable-field allowlist* (MT risk note, tested): `TaskCreate/TaskUpdateSerializer`
  declare exactly the FR-TSK-02 editable set — `title`, `description`,
  `acceptance_criteria`, `target_scope`, `test_command`, `priority` —
  plus the **required `version` CAS token** on PATCH; `state`,
  `version`-as-data, `id`, `project_id`, lease/worker/merge/archive/
  counter/`created_by`/`audit_required` keys are *rejected as unknown*
  by the strict mixin, so PATCH can never bypass WP-1.5's state machine
  (`audit_required` is policy-driven: copied from
  `audit_required_default` at creation, not client-set).
  `StrictSerializerMixin` was **promoted to `apps/core/serializers.py`**
  (the promotion `projects/serializers/base.py` announced for a second
  consumer; the projects module now re-exports the one implementation).
  *`target_scope` globs* — Section 12.3's "validated on creation" made
  concrete (a reading, flagged): non-empty, ≤ 64 globs, ≤ 500 chars
  each, forward slashes only (backslashes rejected), no NUL, relative
  to the repo root (no leading `/`, no drive letter), no `..` segment;
  per-index `VALIDATION_ERROR` details; one shared helper serves create
  *and* PATCH so the rule cannot drift. *Readings:* `created_by`
  records the owner's user id as a string (actor-ref convention,
  Section 9.6/12.5); PATCH increments `version` only when it actually
  changed something (Section 7.2's "on every change" read literally —
  a version-only PATCH is a no-op, and a *stale* version conflicts
  regardless); `state` is set to `draft` explicitly in `create_task`
  (T1's model-level step) with the WP-1.9 `task.created` emission hook
  marked by comment, never faked. *Optimistic concurrency* —
  `update_task` locks the row (`select_for_update`: Postgres row lock;
  SQLite serializes as single-writer), compares the client's version,
  applies the allowlisted fields and increments — the **WP-1.4
  acceptance** (stale → 409 `VERSION_CONFLICT`, tested including "the
  stale writer changed nothing"). *Idempotency* (Section 9.2 rule;
  ADR-012) — `apps/core/idempotency.py`, the minimal headers.md
  exchange record (key scoped by method+path, request fingerprint,
  original 2xx outcome, TTL-driven retention) on the Django cache
  (LocMem unit / Redis dev-prod): same key + same request replays the
  stored response verbatim (create: no second row; PATCH: no second
  version bump); **key reuse with a different request executes
  normally** — headers.md marks that an open point and invents no
  behavior, so no catalog code is emitted for the mismatch (recorded,
  asserted); only 2xx outcomes are stored; the 24 h retention is a
  module constant, *not* a setting, because headers.md keeps the window
  an open point (no configuration.md row invented); concurrent
  same-key linearization stays with WP-1.15's MT-1.15-03 hardening.
  Both mutating operations document the canonical `Idempotency-Key`
  header in OpenAPI (no aliases — headers.md). *Authorization-matrix
  maintenance* (the deferred entries the drift guard named): both
  `/projects/{pid}/tasks` and `/tasks/{id}` entries left
  `DEFERRED_ENDPOINTS`, the `/probe/projects/{pid}/drafts` probe was
  deleted, the *Create draft tasks* row now runs on the real route
  (owner cell → 201 with a valid payload), both cross-project tests
  moved onto the real routes (scope-vs-role outcomes documented per
  case), and the body-widening proof gained a positive leg: the created
  row's project comes from the URL, `project_id` is not client-settable
  at all. Tests (`backend/tests/test_task_api.py`, 37 cases): allocated
  id in `draft` with `version` 1 and counter advancement; policy
  `audit_required` copy; FR-TSK-02 round-trip; server-owned/unknown key
  rejection (8 create + 7 patch cases, nothing persisted); missing
  title; `target_scope` escapes rejected and valid globs accepted;
  malformed pid/id and unknown task → `VALIDATION_ERROR` /
  `TASK_NOT_FOUND` envelopes; matching-version increments; stale
  version → `VERSION_CONFLICT` (409, `retryable: false`, no overwrite);
  missing `version` → `VALIDATION_ERROR`; idempotent create replay /
  no-key default / mismatch-executes / idempotent PATCH replay;
  anonymous `AUTH_REQUIRED`, non-owner agents and device
  `ROLE_NOT_PERMITTED`, foreign-project agent
  `AUTH_FORBIDDEN_PROJECT`. Verified: `ruff check`/`format --check`,
  `mypy .` (127 files), `manage.py check` clean; `schemas/openapi.yaml`
  regenerated (two new paths, `Idempotency-Key` header parameters,
  404/409 envelopes documented) with `pytest tests/test_contract.py`
  green; targeted runs green — `test_task_api.py` (37),
  `test_authorization_matrix.py` (33), regressions
  `test_permission_classes.py` + `test_rate_limiting.py` (107).
- **MT-1.4-04** — Task list endpoint: canonical ordering, filters and
  cursor pagination (Sections 9.2, 7.2; FR-TSK-05; NFR-09; MT-0.5-04,
  conventions/pagination.md). `GET /projects/{pid}/tasks` answers one
  cursor page of the path project's tasks with the whole sort computed
  in the database: priority `urgent > high > medium > low` (FR-TSK-05
  canonical — explicitly *not* the alphabetical enum order), then
  oldest `created_at` (FIFO), then the id's **generation order** via
  `LENGTH(id)` + `id` so `T999 < T1000` (pagination.md rule 2's
  raw-lexicographic warning). Filters: repeatable `state`
  (`?state=draft&state=pending`, the OpenAPI form/explode default),
  single `priority`, and `include_archived` (flag name confirmed here —
  default excludes archived rows, T19 board visibility; MT-1.4-06 owns
  the archive behavior it feeds); unknown filter values and mangled
  cursors answer `VALIDATION_ERROR`. The cursor is base64url of
  `rank|created_at|len(task_id)|task_id` (opaque — rule 1) and
  continuation is a four-way keyset OR-tree over the same sort columns,
  so pages never skip or duplicate under ties; the envelope is exactly
  `{results, next_cursor}`, `page_size` defaults to 25 and clamps to
  100 (`parse_page_size`, the documented `GET /projects` choice).
  Scope and caller: cross-project rows never appear, and the route
  stays Owner-only (agent token → `ROLE_NOT_PERMITTED`, foreign scope
  → `AUTH_FORBIDDEN_PROJECT`, anonymous → `AUTH_REQUIRED`, malformed
  `{pid}` → `VALIDATION_ERROR` — scope first per MT-1.2-05). Tests
  (`backend/tests/test_task_list.py`, 19 cases): mixed-priority FIFO
  and id tie-break; the `T999`/`T1000` three-digit growth case; exact
  state/priority filter sets plus unknown values; archived default
  exclusion and `include_archived` restore; a full page walk with no
  skips/duplicates (alone and under a filter, `next_cursor: null` at
  the end); three malformed-cursor shapes; `page_size=500` clamped
  (100 of 101 rows plus a cursor); cross-project isolation both ways;
  scope-first authorization on the list route; NFR-09 evidence
  (`order_by` = `(priority_rank, created_at, id_length, id)` with
  `CASE`/`LENGTH` in the compiled SQL, both composite indexes declared,
  `EXPLAIN` showing index usage). Verified: `ruff check` /
  `format --check`, `mypy`, `manage.py check` clean;
  `schemas/openapi.yaml` regenerated (`list_tasks` operation with
  `cursor`/`page_size` parameters and the two-member envelope) with
  `pytest tests/test_contract.py` green; targeted runs green —
  `test_task_list.py` (19), regressions `test_task_api.py` (37),
  `test_authorization_matrix.py` (33), `test_permission_classes.py` +
  `test_rate_limiting.py` (107).
- **MT-1.4-05** — Task dependency relation (`depends_on`; Sections 7.1,
  7.2, 9.2; FR-TSK-07). `TaskDependency` is the Section 7.1 N:N join in
  its own `models/dependencies.py` with a **standalone** migration
  (`0002_taskdependency`, Section 20.3 — the relation only): the two
  foreign keys plus a DB unique edge and a DB no-self-edge check; the
  section specifies no join columns, so nothing else was invented.
  **Shape choice (recorded):** `depends_on` is a list of task ids on
  `POST /projects/{pid}/tasks` and `PATCH /tasks/{id}` — matching the
  Section 10 `create_draft_task` tool payload — and is **replace-the-set**
  on PATCH (omit = unchanged, `[]` = clear); it reads back on every task
  representation as `depends_on`, id-ordered. **Validation**
  (`services/dependencies.py`, one entry point both writes compose):
  well-formed §7.3 ids, existence, same-project scope (GOAL-2/ADR-004
  zero-bleed — a cross-project edge is rejected, never silently scoped),
  self-edge, and cycles — all catalog `VALIDATION_ERROR` with per-id
  detail; duplicates collapse; refusal rolls back the whole write
  (task row, id counter, edges) because validation runs inside the
  caller's transaction. Cycle prevention is a **reading** of the plan
  (FR-TSK-07's "all dependencies completed" is unsatisfiable in a cycle,
  deadlocking its members) — flagged for owner confirmation, not
  presented as spec text. `DEPENDENCY_UNMET` stays reserved for WP-1.6's
  offer/claim enforcement. **Readiness:** `all_dependencies_completed()`
  is THE single predicate — one `SELECT ... EXISTS` over edges whose
  target state is `completed` (G-01), never raises, documented as the
  contract for WP-1.6's `GET /work` selection and T4 claim guard
  (Section 9.3 step 4 revalidation runs it inside the claim lock). Read
  path: the list queryset prefetches `dependency_edges` (one query per
  page, NFR-09) and detail/create responses query once. Tests
  (`backend/tests/test_task_dependencies.py`, 17 cases): edges on
  create; default empty set; missing/malformed target with nothing
  persisted *including the refunded id counter*; cross-project refusal
  on both writes; self-edge; two- and three-node cycles with the
  accepted edge surviving; replace/shrink/clear; omit-leaves-edges;
  duplicate collapse; stale `version` → `VERSION_CONFLICT` with the set
  intact; detail+list round-trip; readiness in the three MT cases (no
  deps / mixed states / all completed, plus an `in_progress` flip-back);
  migration apply/reverse keeping the 0001 task table. Also adjusted the
  MT-1.4-01 §7.2 field-set assertion to compare **concrete columns**
  (the two reverse relations are relation metadata, asserted separately).
  Verified: `ruff check`/`format --check`, `mypy`, `manage.py check`,
  `makemigrations --check` clean; `schemas/openapi.yaml` regenerated
  with `pytest tests/test_contract.py` green; targeted runs green —
  `test_task_dependencies.py` (17), regressions `test_task_model.py`
  (12), `test_task_api.py` (37), `test_task_list.py` (19),
  `test_task_id_allocation.py` (8), `test_authorization_matrix.py` (33).
- **MT-1.4-06** — Soft archive and read-only `completed` (Sections 7.2,
  7.3, 8.2; FR-TSK-08; ADR-008). **Recorded catalog choice (20.4 item
  5):** both write refusals — `PATCH` on a `completed` row (T17 side
  effect; §7.4 rule 3 "immutable except `archived_at`") and `PATCH` on
  an archived row — answer **`TASK_STATE_CONFLICT` (409)** via the new
  `TaskStateConflict` exception: the catalog has no
  `TASK_ARCHIVED`/`READ_ONLY` code, a 20th code is forbidden, and
  `VALIDATION_ERROR` would blame a valid payload when the *resource*
  refuses ("not allowed in this state" is §8.2's own 409 language).
  Refusal ordering pinned by test: the `version` CAS still runs first
  (a stale client on a completed task gets `VERSION_CONFLICT`).
  Reads keep serving both kinds of row — GET by id returns archived and
  completed tasks (id continuity, §7.3), the default list excludes only
  archived (T19 "hidden from boards by default") and `include_archived`
  restores them; completed rows stay listed. **No deletion exists**:
  neither task view defines `delete`, live `DELETE` attempts on both
  task paths hit the recorded `MethodNotAllowed` → `VALIDATION_ERROR`
  (400) mapping with the row intact — §7.3 "deleting a task is not
  supported". **Archive setter for WP-1.5 (MT-1.5-02 / T19):**
  `services.tasks.archive_task(task, expected_version=None)` — sets
  `archived_at` to the server clock (P7) and increments `version` under
  the row lock in one transaction, optional FR-TSK-06 CAS, idempotent
  (first timestamp wins, never re-stamped, no double bump); **state
  gating is deliberately not done here** — "any non-`completed`" is
  T19's registry rule and WP-1.5's guard owns it, so the two never
  compete (the boundary the MT risk note asks to record). Not
  implemented (per scope): the `POST /tasks/{id}/transition` archive
  endpoint (WP-1.5), unarchiving (no T19 inverse exists in the plan —
  open point, not invented), retention (OQ-10/M6). Tests
  (`backend/tests/test_task_archive.py`, 12 cases): PATCH refused on
  completed and archived with `TASK_STATE_CONFLICT` and nothing
  persisted (title, version, marker all intact); completed/archived
  GET-by-id and list visibility (default + include flag); stale-version
  precedence; both view classes lack `delete` + live DELETE → recorded
  400 mapping with the row surviving; `archive_task` marker + bump,
  idempotence, stale-CAS `VERSION_CONFLICT`; catalog-code/status
  pinning. Verified: `ruff check`/`format --check`, `mypy`,
  `manage.py check` clean; `schemas/openapi.yaml` regenerated (PATCH
  description documents the 409 refusal) with `pytest
  tests/test_contract.py` green; targeted runs green —
  `test_task_archive.py` (12), regressions `test_task_api.py` (37),
  `test_task_list.py` (19), `test_task_dependencies.py` (17),
  `test_authorization_matrix.py` (33).
