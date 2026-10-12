# WP-1.3 — Project registry, policy and manifest: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.3-01** — Atomic PID identifier generation `PID[0-9]{5}` (Sections 7.3,
  7.4; FR-PRJ-01). `backend/apps/projects/services/pids.py` is now the
  canonical home of the Section 7.3 id machinery — pattern constant
  `PROJECT_ID_PATTERN`, the `validate_project_id` boundary validator,
  `render_pid`, `next_project_number`, `allocate_project_id` and
  `ensure_valid_pid` (the DRF-facing wrapper so a malformed `{pid}` answers
  the catalog's `VALIDATION_ERROR` rather than falling through to
  `SERVER_ERROR`). **Decisions recorded per the MT risk notes:**
  *Sequence:* a real PostgreSQL `CREATE SEQUENCE project_pid_seq` created by
  `apps/projects/migrations/0001_pid_sequence.py` (generator support only —
  Section 20.3; the Project-model migration `0002` depends on it via the
  app's normal migration chain, recorded here so the order cannot be
  silently changed) and consumed by `nextval` in **one atomic statement**,
  so concurrent allocations never reuse a number. *Start value:* `1` —
  `PID00000` is never issued; a fresh database's first project is
  `PID00001`. Gaps are expected and never "repaired" (Section 7.3).
  *Unit-layer branch:* the hermetic test settings are SQLite in-memory
  (which has no sequences — the Postgres-out-of-scope split already
  documented in `apps/core/settings/test.py`), so the same migration
  creates a single-row fallback counter table `project_pid_sequence` and
  `next_project_number` branches on `connection.vendor`; the SQLite path is
  a single `UPDATE ... RETURNING`, atomic for the same reason `nextval` is.
  One migration, both backends, no vendor-specific migration state;
  integration-layer (Postgres) coverage joins WP-1.6's concurrency work.
  *Exhaustion mapping:* values outside `1..99999` raise
  `PidSequenceExhausted` (`apps/projects/exceptions.py`) — **`SERVER_ERROR`
  chosen over `VALIDATION_ERROR`** (MT-1.3-01 asked for one of the two): a
  spent sequence is a server-capacity condition no client input can fix, so
  blaming the request would misdescribe it; the catalog stays closed
  (Section 20.4 item 5). *Validator single-sourcing:* the pattern/validator
  moved here (Section 9.1 — the `projects` module owns ids);
  `apps.accounts.models.tokens` re-exports the same objects, so WP-1.2's
  public names (`PROJECT_ID_PATTERN`, `validate_project_id`) and every
  serialized migration stay byte-identical — a test asserts the re-export
  is one object, not a copy. Tests (`backend/tests/test_pid_generation.py`)
  cover format/capacity, zero-never-issued, sequential uniqueness,
  **uniqueness under concurrent threads** (barrier-synchronized, retrying
  SQLite's table locks — a failed statement consumes nothing), exhaustion
  → `SERVER_ERROR` with a clear message, boundary validation, the
  sequence migration's clean apply **and reverse** (re-seeding to 1), and
  the accounts re-export. Verified: `ruff check`/`format --check`, `mypy .`,
  `manage.py check`, `makemigrations --check --dry-run` clean; targeted
  `pytest -k "pid or project_id"` green.
- **MT-1.3-02** — Project and ProjectPolicy models with migrations and
  defaults (Sections 7.1, 7.2, 7.4; FR-PRJ-02/04/05; G-09, G-26).
  `backend/apps/projects/models/` splits the entities per the modular rule
  — `models/project.py` (`Project`, `ActiveStatus`) and `models/policy.py`
  (`ProjectPolicy`, `LeaseExtensionMode`, `MergeStrategy`), one entity per
  file. *Project* carries exactly the Section 7.2 table (field-set asserted
  literally in tests — none added, dropped or renamed): immutable
  `PID[0-9]{5}` primary key with the Section 7.4 `CheckConstraint`
  `project_id_format` (`id ~ '^PID[0-9]{5}$'` on Postgres, `REGEXP` on the
  SQLite unit layer), `active_status` limited to `active`/`paused`/
  `archived` (FR-PRJ-04, ADR-010 values), `agent_policy` as the Section 7.1
  one-to-one to ProjectPolicy with `on_delete=PROTECT` (the pair is never
  silently cascade-deleted; neither row is deleted by any endpoint —
  projects are PATCH-transitioned, never DELETE'd), `task_counter`
  `PositiveIntegerField` default 0 for MT-1.4-02, and server-clock UTC
  `created_at`/`updated_at`. *Immutability guard (recorded decision):*
  `save()` refuses a loaded row's id change (`_original_pk` captured in
  `__init__` — deliberately not `from_db`, whose django-stubs signature
  carries a `fetch_mode` Django 5.2's runtime does not accept); the API
  exposes id read-only (MT-1.3-03), and `queryset.update()` bypassing
  `save()` is a documented application-level limitation (DB triggers are
  outside Section 20.3's sizing for this MT). *ProjectPolicy* carries
  every Section 7.2 row with the exact documented default (all 15 asserted
  value-for-value, including `max_concurrent_tasks` 1 and
  `branch_prefix` `feat/{PID}-`); **no `created_at`/`updated_at`** — the
  plan's policy table lists none and "never added" outranks convenience
  (policy-edit timestamps arrive with WP-1.9's audit trail).
  *Prose glob defaults translated concretely and flagged for owner
  confirmation (MT risk note, Section 20.1 item 5):* critical =
  `.github/workflows/*`, `.gitlab-ci.yml`, `Jenkinsfile`, `migrations/*`,
  `**/security*.{py,yml,yaml}` (CI/CD, root migrations, security config);
  migration = `**/migrations/*.py`, `alembic/versions/*`, `db/migrate/*`,
  `db/schema.rb` (Django/Alembic/Rails); sensitive = `.env*`, `**/*.env`,
  `**/*.pem`, `**/*.key`, `**/*credentials*`, `**/*secrets*`,
  `**/security_rules*` (env files, key material, security rules). The
  defaults are named factory functions (mutable JSONField defaults must be
  callables — Django's E010; factories also serialize by dotted path), and
  a test proves two rows never share one list. *Migration split
  (Section 20.3):* `0001_pid_sequence` (MT-1.3-01, generator only) →
  `0002_initial` (both models — the pair belongs to one MT, and the
  sequence migration must precede it; the dependency is explicit in
  `0002`'s `dependencies`). `merge_strategy` needs `max_length=24` to fit
  `fast_forward_only` (Django E009). Tests
  (`backend/tests/test_project_models.py`) cover both field sets, every
  default (unsaved *and* DB round-trip), glob-default isolation, the
  status enum + `full_clean` rejection, DB check-constraint rejection of
  four malformed ids, id immutability (with ordinary saves still working),
  the one-to-one + PROTECT pair, `task_counter` 0, and server timestamps.
  Verified: `ruff check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run` clean; targeted
  `pytest -k "project and (model or policy or default)"` green; the
  sequence-migration apply/reverse test still green with `0002` present
  (reverses the whole app).
- **MT-1.3-03** — Project CRUD endpoints with Active/Paused/Archived
  status (Sections 9.2, 7.2, 12.2; FR-PRJ-01/02/04; ADR-004). Routes
  (`apps/projects/urls.py`, included under `/api/v1` next to accounts):
  `GET/POST /projects`, `GET/PATCH /projects/{pid}` — thin views
  (`views/projects.py`) over `services/projects.py` (`create_project`,
  `get_project_or_404`) and hand-written serializers
  (`serializers/projects.py` + a strict-input mixin in
  `serializers/base.py`). **Decisions recorded per the MT risk notes:**
  *Creation:* one transaction allocates the PID (MT-1.3-01) and creates
  the default ProjectPolicy pair (Section 7.1) — either both rows exist or
  neither; a **client-supplied `id` is rejected as an unknown field**
  (`VALIDATION_ERROR`), not silently dropped, which is the provable form
  of "no client id is accepted". *PATCH, not DELETE (recorded reading):*
  projects are never deleted — `active_status` cycles among
  `active`/`paused`/`archived`, mirroring Section 7.3's id-continuity
  intent; the id is rejected if sent (strict mixin) *and* guarded in
  `Model.save()`. *Unknown pid (risk note answered):* the catalog has no
  `PROJECT_NOT_FOUND`, so a well-formed unknown id raises DRF `NotFound`,
  which `apps/core/exceptions.py` already maps to **`VALIDATION_ERROR`
  with HTTP 400** — malformed ids land on the same code with a `pid`
  detail; the asymmetry with `TASK_NOT_FOUND` is flagged here rather than
  inventing a code (Section 20.4 item 5). *Caller enforcement:*
  `[HasProjectScope, CanManageProjects]` on the addressed routes (scope
  outranks role: agent-own-project → `ROLE_NOT_PERMITTED`, agent-other →
  `AUTH_FORBIDDEN_PROJECT`, anonymous → `AUTH_REQUIRED`) and
  `CanManageProjects` on the list/create routes; **agent read-only access
  for a token's own project stays reserved for WP-2.x** — every agent
  credential is denied now, stated explicitly in the OpenAPI descriptions.
  *Pagination (MT-0.5-04):* pagination.md's exact two-member envelope via
  a new `string_id_cursor_page`/`decode_str_cursor` in
  `apps/core/pagination.py` — documented sort is **project id ascending**,
  which zero-padded Section 7.3 ids make identical to creation order;
  `page_size` clamps to 100 (same per-endpoint choice as `GET /tokens`).
  *Events:* `project.created`/`project.updated` emission points recorded
  at the create/update call sites for WP-1.9 (no event emitted yet).
  *Declared errors:* 400/401/403 on every operation plus **500
  `SERVER_ERROR` on POST** for Section 7.3 sequence exhaustion — no 429
  (owner endpoints are deliberately unthrottled, FR-SEC-05); explicit
  `operationId`s (`list_projects`, `create_project`, `retrieve_project`,
  `partial_update_project`) keep the generated document collision-free.
  *WP-1.2 probe/deferred assumptions updated (MT-1.2-07's hand-off):*
  `tests/test_authorization_matrix.py` now runs the *Manage
  projects/policy* row on the real `GET /api/v1/projects`, creates real
  `PID00001`/`PID00002` rows (explicit ids — deterministic on every
  backend, allocation stays the sequence's own test), adds a real-route
  cross-project case (including the body-can't-widen probe), flips the
  owner-revocation case onto the real route, and drops `/projects` +
  `/projects/{pid}` from `DEFERRED_ENDPOINTS` (policy/manifest stay until
  MT-1.3-04/05 land). Tests (`backend/tests/test_project_api.py`, 13)
  cover generated PID + default-policy pair, client-id rejection, full
  FR-PRJ-02 round-trip, status cycling incl. invalid value, id/unknown-key
  rejection, malformed + unknown pid catalog codes, non-owner and
  cross-project codes, cursor pagination shape/order/malformed-input, and
  the declared 500 on exhaustion; matrix suite re-verified (36). OpenAPI:
  regenerated `schemas/openapi.yaml` (schema diff = the four operations
  plus their schemas/descriptions). Verified: `ruff check`/`format --check`,
  `mypy .`, `manage.py check`, `makemigrations --check --dry-run` clean;
  targeted `pytest tests/test_project_api.py` green.
- **MT-1.3-04** — Policy read/patch endpoints with validation (Sections
  9.2, 7.2, 12.5; FR-PRJ-05; G-09, G-26; OQ-04). `GET/PATCH
  /projects/{pid}/policy` (`views/policy.py` over
  `serializers/policy.py` — one strict serializer serving both directions;
  route in `urls.py`). **Decisions recorded per the MT risk notes:**
  *Bounds are exactly what Section 7.2 states, nothing invented:* positive
  durations/retries/thresholds (`lease_duration_minutes`,
  `lease_max_total_minutes`, `max_retries`,
  `autonomous_diff_threshold_lines`, `stalled_after_minutes` ≥ 1),
  `auditor_min_confidence` 1–5, `max_concurrent_tasks` ≥ 0 (G-26's
  semantics: 0 pauses claiming without touching `active_status` — no
  upper bound is invented for durations/concurrency, flagged rather than
  clamped), closed enums `lease_extension_mode` ∈ {`checkpoint_only`,
  `checkpoint_and_liveness` — the per-project OQ-04 option is accepted
  while the product default stays `checkpoint_only`} and `merge_strategy`
  ∈ {`squash`, `merge_commit`, `fast_forward_only`}; branch prefix and
  the three glob lists must be non-empty when supplied (items non-blank) —
  glob *matching semantics* stay with the Policy Engine (WP-3.x).
  *Partial semantics:* patching one field rewrites nothing else (asserted
  by full-document diff); unknown fields are **rejected, not ignored**
  (the strict mixin); wrong types are catalog `VALIDATION_ERROR`s.
  *`branch_prefix` (G-09):* documented in OpenAPI as the canonical prefix
  template (`feat/{PID}-` default) applied when the bridge derives branch
  names from WP-2.x on — changing it changes future branch naming.
  *Caller:* `[HasProjectScope, CanManageProjects]` — the same catalog
  answer set as the CRUD routes (owner-only; agent-own → `ROLE_NOT_PERMITTED`,
  agent-other → `AUTH_FORBIDDEN_PROJECT`, anonymous → `AUTH_REQUIRED`,
  device → `ROLE_NOT_PERMITTED`), plus the shared malformed/unknown pid
  boundary answers. *Audit hook:* policy edits are state changes
  (Section 12.5) — the `save` call site records the WP-1.9
  `policy.updated` emission point (no event emitted yet; only this
  endpoint writes policy). *Scope note:* `ProjectPolicy` deliberately has
  no `created_at`/`updated_at` — the Section 7.2 table lists none; edit
  history arrives with WP-1.9's audit trail. `/policy` removed from the
  matrix's `DEFERRED_ENDPOINTS`. Tests
  (`backend/tests/test_project_policy_api.py`, 10): GET equals the
  literal Section 7.2 table for a fresh project (shared `POLICY_DEFAULTS`
  with the model tests — one drift detector), single-field patch isolation,
  OQ-04 option accepted, enum/bounds/empties/type/unknown-field rejections
  each proven with the rejected patch leaving the document untouched,
  persistence to the ORM row, owner-only codes incl. cross-project, and
  pid boundary answers. Note: policy PATCH tests send **JSON** bodies —
  the test client's multipart default silently drops empty lists, which
  would hide the `allow_empty` rule (recorded so the next list-carrying
  endpoint reuses `format="json"`). OpenAPI: regenerated snapshot
  (`retrieve_project_policy`, `partial_update_project_policy` + the
  ProjectPolicy schema); contract tests green. Verified: `ruff
  check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run`; targeted
  `pytest tests/test_project_policy_api.py` green.

## MT-1.3-05 — Manifest schema & generation

- **Published contract:** `schemas/manifest.v1.json` (JSON Schema draft
  2020-12) transcribes Section 10.3 key-for-key: exactly the seven
  top-level keys (`schema_version` const 1, `project_id` `^PID[0-9]{5}$`,
  `project_name`, `orchestrator_api` format uri, `default_branch`,
  `auto_branch_prefix`, `audit_required_default` boolean) with
  `additionalProperties: false` (FR-SEC-04 allowlist) and the optional
  `agent_hints` object (`test_command_default`, `worktree_mode`) closed
  the same way. `$id` keeps the plan example's placeholder host
  (`https://orchestrator.local/schemas/manifest.v1.json`) — canonical
  hosting/URL confirmation is flagged for WP-2.2 in the report.
- **Renderer:** `apps/projects/services/manifest.py` renders the document
  from a `Project` (no task/task-counter leakage), resolving G-09
  `auto_branch_prefix` from the policy's `branch_prefix` template
  (replacing the `{PID}` placeholder with the concrete id) and passing
  `audit_required_default` through verbatim; `MANIFEST_KEYS` mirrors the
  schema's allowlist so renderer and validator fail together if either
  drifts. `serializers/manifest.py` exposes the `OrchestratorManifest`
  response schema — built with `type()` because `$schema` is not a legal
  Python class attribute — so the endpoint is typed in OpenAPI.
- **Endpoint:** `GET /api/v1/projects/{pid}/manifest` downloads
  `orchestrator.json` as an attachment, `[HasProjectScope,
  CanManageProjects]` (Owner-only: agent-own → `ROLE_NOT_PERMITTED`,
  agent-other → `AUTH_FORBIDDEN_PROJECT`, anonymous → `AUTH_REQUIRED`,
  device → `ROLE_NOT_PERMITTED`), shared malformed/unknown-pid boundary
  answers; no task fields in the payload (§19.1 privacy note).
  `/manifest` removed from the matrix's `DEFERRED_ENDPOINTS` (Owner-only
  catalog codes asserted in the manifest suite itself, matching the
  policy precedent). *Config:* new `ORCHESTRATOR_API_BASE_URL` setting
  (rendered as `orchestrator_api`; default
  `http://localhost:8000/api/v1`, scheme fail-fast) with canonical
  `API_` config-group rows in `docs/plan/conventions/configuration.md`
  and `infra/compose/.env.example`. *Dependency:* `jsonschema` (dev
  group, with `types-jsonschema`) validates generated manifests in tests
  — the published schema stays the artifact of record, not a runtime
  gate. Tests (`backend/tests/test_manifest.py`, 11): schema/Section
  10.3 key-for-key match, fresh (plan-example shape) and customized
  manifests validate, renderer emits exactly the allowlist, a smuggled
  extra key is rejected by the schema (proof the closed contract bites),
  `orchestrator_api` honors the setting override, `{PID}` prefix
  resolution, no-secret-leak scan, endpoint download headers, the four
  owner-only codes, and pid boundary answers. OpenAPI: regenerated
  snapshot (`retrieve_project_manifest` + `OrchestratorManifest`);
  regen stable (byte-identical second run); contract tests green.
  Verified: `ruff check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run`; targeted
  `pytest tests/test_manifest.py` green.
- **Wave 2 gate fix** — `tests/test_pid_generation.py`'s migration test restores the
  full migration state with plain `migrate` after `migrate projects zero`: Django
  unapplies dependent `tasks` migrations too, and re-applying only `projects` left
  `tasks` dropped, breaking later transactional tests in full-suite order.
