# WP-0.5 — Configuration, secrets and error conventions: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of
WP-0.5 (Configuration, secrets and error conventions).

## 2026-10-11 — MT-0.5-01: Environment variable naming and grouping conventions

* Published [`docs/plan/conventions/configuration.md`](../../../docs/plan/conventions/configuration.md):
  the `ORCHESTRATOR_<SETTING>` naming pattern (SCREAMING_SNAKE_CASE, one canonical
  spelling, no aliases — Section 0.4), the grouping rule covering **all eleven
  Section 9.10 groups** with leading-segment mapping and representative names, the
  per-setting metadata contract (documented default + validation note mandatory per
  Section 9.10; `Required in prod` and `Secret` flags per Sections 16.2/20.4), the
  secret-handling rule (placeholders only in Git, real values outside Git, identical
  names via host secrets or Compose secrets, weak/missing-secret refusal in `prod`,
  log scrubbing), and the NFR-06 "same names everywhere" rule.
* Defaults tied to Section 22 recorded as decided/deferred, not remembered:
  description provider default `disabled` (OQ-07 recommended default, deferred to
  M1); no variable invented for OQ-09 before its M1 decision. New config semantics
  beyond 9.10 remain open questions (Section 20.1, rule 5).
* Reconciliation with `infra/compose/.env.example`: at publication the template had
  not yet been landed (WP-0.2 runs in parallel in Wave 1); the document fixes the
  check every template variable must pass and records that divergences are renames
  against the convention, done before M1 code reads any variable.
* Package-doc references added: new `README.md` in `backend/`, `bridge/`, `web/`,
  `mobile/`, each with a "Shared conventions (WP-0.5)" section linking this
  document (WP-0.5 acceptance).

## 2026-10-11 — MT-0.5-02: Canonical error envelope and error-code catalog published

* Published [`docs/plan/conventions/error-envelope.md`](../../../docs/plan/conventions/error-envelope.md):
  the envelope stated by reference to parent plan Section 9.2 with its five fields
  (`code`, `message`, `retryable`, `details`, `correlation_id`) and the wire contract
  quoted verbatim (Section 0.4); all **19 canonical codes** listed in the plan's
  order — none added, dropped or renamed — as the closed catalog, with the
  "currently unused" codes (e.g. `RATE_LIMITED`, `VERSION_CONFLICT`) explicitly kept.
* Documented the implied rules: codes are the stable contract, messages are
  human-readable and never parsed, `retryable` drives client/bridge retry behavior
  (NFR-12, ADR-012, Section 10.10), and the **add-a-code-here-first** rule as part of
  the global DoD (Section 20.4, item 5; catalog changes hit parent plan Section 9.2
  first, then this mirror). No codes or fields invented (Section 20.5).
* Stated the OpenAPI obligation: the envelope becomes a reusable schema in the
  generated OpenAPI document in WP-1.1 (ADR-005), guarded by schema diff in CI
  (NFR-11, Section 18, Section 20.4 item 4).
* Added the error-conventions reference to the "Shared conventions (WP-0.5)" section
  of all four package READMEs (WP-0.5 acceptance).

## 2026-10-11 — MT-0.5-03: Correlation-id and idempotency header conventions

* Published [`docs/plan/conventions/headers.md`](../../../docs/plan/conventions/headers.md)
  fixing exactly one canonical spelling each — correlation id `X-Correlation-ID`,
  idempotency key `Idempotency-Key` — with an explicit no-aliases rule (Section 0.4
  canonical-spelling discipline; no second spelling is ever accepted).
* Correlation id matches Sections 9.2/17/9.6/12.5: caller-generated when absent,
  honored when present, propagated clients → bridge → backend → worker into
  structured logs, Event rows, audit entries and the envelope's `correlation_id`
  field, under Section 17 token/secret scrubbing (RISK-14).
* Idempotency matches Sections 9.2/10.10 and NFR-12: accepted on every mutating
  endpoint, one caller-derived key per logical operation (bridge sends keys on all
  mutating calls), same key + same request replays the original outcome; the
  per-key server record (key, request fingerprint, recorded outcome, creation
  timestamp) is defined. **Retention window recorded as an open point** — the plan
  states no number, so none is invented; configuration route fixed as an
  `ORCHESTRATOR_<SETTING>` environment setting per `configuration.md` once decided.
  Key reuse with a different payload likewise flagged as an open point for WP-1.1,
  not invented.
* The three mechanisms are explicitly disambiguated: correlation id vs idempotency
  key vs SSE resume by event id (Section 9.6 stream recovery — not a header
  substitute for either). Lease fencing (ADR-012's other half), middleware/storage,
  bridge retries and client sending behavior kept out of scope per the MT.
* Added the header-conventions reference to all four package READMEs (WP-0.5
  acceptance).

## 2026-10-11 — MT-0.5-04: Cursor-based pagination conventions

* Published [`docs/plan/conventions/pagination.md`](../../../docs/plan/conventions/pagination.md):
  one canonical cursor query parameter (`cursor`) and one two-member response
  envelope (`results` + `next_cursor`, JSON wire contract quoted) covering **every
  list endpoint of the Section 9.2 table** (tokens, projects, tasks, work,
  checkpoints, resolutions, audit reports, merge pending, attachments, events
  history); end-of-list signaled solely by an absent/`null` `next_cursor`.
* Rules fixed: cursor opacity (clients never construct or parse; valid only under
  the same endpoint and filters), stable deterministic ordering per endpoint
  (server-clock `created_at` + Section 7.3 identifier tiebreak ordered by the id's
  generation rule — not raw lexicographic), and no offset pagination anywhere.
* Page sizes documented as explicit **WP-0.5 defaults, not plan facts**: default
  `25`, maximum `100` via `page_size`; the cap exists for RISK-13; over-max handling
  deferred to each endpoint's OpenAPI contract (WP-1.1); configurability only via
  existing Section 9.10 groups per `configuration.md`.
* The Section 9.5 attachment `content` page-numbering exception (`page`,
  `page_number`, `total_pages`) is documented as plan-specified and not to be
  "unified"; `GET /events` history stays on cursors while SSE resume by event id
  (Section 9.6) remains a stream concern.
* OpenAPI obligation stated per NFR-11: parameters, envelope and sorts are part of
  the typed contract generated in WP-1.1, guarded by schema diff in CI. Added the
  pagination reference to all four package READMEs (WP-0.5 acceptance).

## 2026-10-12 — WP-0.2 × WP-0.5 conflict resolution: compose environment names renamed to the canonical vocabulary

Cross-workpackage conflict: WP-0.2 landed `infra/compose/.env.example`,
`compose.yaml`, `compose.dev.yaml` and the Compose `README.md` with names it
explicitly declared provisional ("WP-0.5 formalizes … without renaming"), while
`docs/plan/conventions/configuration.md` (MT-0.5-01, parent plan §9.10/§16.2)
is authoritative and mandates `ORCHESTRATOR_<SETTING>` — one name, no aliases.
Resolved in configuration.md's order: the conventions document first (metadata
rows added), then the template, then every consumer, in one atomic change.

**Rename map applied (provisional → canonical):**

| Provisional (WP-0.2) | Canonical (configuration.md) |
|---|---|
| `POSTGRES_IMAGE` | `ORCHESTRATOR_IMAGE_POSTGRES` |
| `REDIS_IMAGE` | `ORCHESTRATOR_IMAGE_REDIS` |
| `BACKEND_IMAGE` | `ORCHESTRATOR_IMAGE_BACKEND` |
| `WEB_IMAGE` | `ORCHESTRATOR_IMAGE_WEB` |
| `CLOUDFLARED_IMAGE` | `ORCHESTRATOR_IMAGE_CLOUDFLARED` |
| `MAILHOG_IMAGE` | `ORCHESTRATOR_IMAGE_MAILHOG` |
| `BACKEND_PORT` | `ORCHESTRATOR_PORT_BACKEND` |
| `WEB_PORT` | `ORCHESTRATOR_PORT_WEB` |
| `ORCHESTRATOR_BIND_ADDR` | unchanged (already canonical; metadata row added) |
| `POSTGRES_USER` (template value) | `ORCHESTRATOR_DATABASE_USER` |
| `POSTGRES_PASSWORD` (template value) | `ORCHESTRATOR_DATABASE_PASSWORD` |
| `POSTGRES_DB` (template value) | `ORCHESTRATOR_DATABASE_NAME` |
| `DATABASE_URL` | `ORCHESTRATOR_DATABASE_URL` |
| `REDIS_URL` | `ORCHESTRATOR_CACHE_URL` |
| `CELERY_BROKER_URL` | `ORCHESTRATOR_CACHE_BROKER_URL` |
| `REDIS_APPENDONLY` | `ORCHESTRATOR_CACHE_APPENDONLY` (value now `true`/`false` per rule 5; Compose maps it to Redis's `--appendonly yes\|no`, rule 7) |
| `DJANGO_SECRET_KEY` | `ORCHESTRATOR_SECRET_KEY` |
| `DJANGO_DEBUG` | `ORCHESTRATOR_DEBUG` |
| `DJANGO_ALLOWED_HOSTS` | `ORCHESTRATOR_ALLOWED_HOSTS` |
| `DJANGO_CORS_ALLOWED_ORIGINS` | `ORCHESTRATOR_CORS_ORIGINS` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `ORCHESTRATOR_CSRF_ORIGINS` |
| `STORAGE_BACKEND` | `ORCHESTRATOR_STORAGE_BACKEND` |
| `MEDIA_ROOT` | `ORCHESTRATOR_STORAGE_MEDIA_ROOT` |
| `S3_ENDPOINT_URL` | `ORCHESTRATOR_STORAGE_S3_ENDPOINT` |
| `S3_BUCKET` | `ORCHESTRATOR_STORAGE_S3_BUCKET` |
| `S3_ACCESS_KEY_ID` | `ORCHESTRATOR_STORAGE_S3_ACCESS_KEY_ID` |
| `S3_SECRET_ACCESS_KEY` | `ORCHESTRATOR_STORAGE_S3_SECRET_ACCESS_KEY` |
| `AGENT_TOKEN_LIFETIME_HOURS` | `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS` |
| `DEVICE_TOKEN_LIFETIME_DAYS` | `ORCHESTRATOR_TOKEN_LIFETIME_DEVICE_DAYS` |
| `API_RATE_LIMIT_PER_MINUTE` | `ORCHESTRATOR_RATE_LIMIT_API_PER_MINUTE` |
| `OCR_ENGINE` | `ORCHESTRATOR_OCR_ENGINE` |
| `DESCRIPTION_PROVIDER` | `ORCHESTRATOR_DESCRIPTION_PROVIDER` |
| `FCM_PROJECT_ID` | `ORCHESTRATOR_FCM_PROJECT_ID` |
| `FCM_CREDENTIALS_JSON` | `ORCHESTRATOR_FCM_CREDENTIALS_JSON` |
| `CLOUDFLARED_TUNNEL_TOKEN` | `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` |
| `FEATURE_FLAGS` | `ORCHESTRATOR_FEATURE_FLAGS` |

**configuration.md rows added (deviation — settings the group table only implied):**
`ORCHESTRATOR_IMAGE_<SERVICE>` (six images), `ORCHESTRATOR_PORT_BACKEND`,
`ORCHESTRATOR_PORT_WEB`, `ORCHESTRATOR_BIND_ADDR`, `ORCHESTRATOR_DATABASE_USER` /
`_PASSWORD` / `_NAME`, `ORCHESTRATOR_CACHE_BROKER_URL`,
`ORCHESTRATOR_CACHE_APPENDONLY`, `ORCHESTRATOR_DEBUG` (no §9.10 group — Compose
dev/prod posture), `ORCHESTRATOR_STORAGE_MEDIA_ROOT`, the four
`ORCHESTRATOR_STORAGE_S3_*` names, `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS` /
`_DEVICE_DAYS`, `ORCHESTRATOR_RATE_LIMIT_API_PER_MINUTE`,
`ORCHESTRATOR_OCR_ENGINE`, `ORCHESTRATOR_DESCRIPTION_PROVIDER`,
`ORCHESTRATOR_FCM_PROJECT_ID` / `_CREDENTIALS_JSON`,
`ORCHESTRATOR_FEATURE_FLAGS`, `ORCHESTRATOR_AGENT_TOKEN`, and the rule-7
image-mandated `NODE_ENV`. All carry the per-setting metadata contract fields.

**Third-party container interfaces kept (rule 7), mapped from canonical values:**
Compose postgres `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` env keys and
the `pg_isready -U $POSTGRES_USER` probe; the `psql -U "$POSTGRES_USER"` examples
in the Compose README; the postgres service-container env in
`.github/workflows/test.yaml`; `NODE_ENV` in `compose.dev.yaml`.

**Files touched:** `docs/plan/conventions/configuration.md`,
`infra/compose/.env.example`, `infra/compose/.env` (git-ignored local copy),
`infra/compose/compose.yaml`, `infra/compose/compose.dev.yaml`,
`infra/compose/README.md`, `.github/workflows/test.yaml` (rule-7 comment only).
No occurrence existed in root `README.md`, `CONTRIBUTING.md` (its single env
citation already used the canonical names) or any package README, so neither was
edited.

**Validation (all green):**
* `docker compose --env-file infra/compose/.env.example config` renders, as do
  the `compose.dev.yaml` overlay and `--profile dev` / `--profile prod` renders
  (compose v5.4.0); no unrendered `${…}` and no divergent names in any render.
* MT-0.5-01 re-check: all 45 `ORCHESTRATOR_*` catalog tokens in
  configuration.md appear in `.env.example` (commented reserved rows count);
  all 37 template assignments start with `ORCHESTRATOR_`.
* Live proof with Docker Desktop: documented one-command dev bring-up
  (`--profile dev up -d --wait`) → all 8 services healthy; Redis
  `appendonly=yes` (canonical `true` mapped); documented `wp02_marker` row
  inserted, stack restarted → all healthy, row still `1 | survives restart`;
  torn down with plain `down` — `postgres_data`, `redis_data`, `backend_media`
  preserved.
* Observation (pre-existing, not this rename): Docker Engine 29 scrubs
  credential-bearing URL env values to `******…` inside containers — reproduced
  with a plain `docker run -e`, same as the pre-rename stack; noted for WP-1.1.
