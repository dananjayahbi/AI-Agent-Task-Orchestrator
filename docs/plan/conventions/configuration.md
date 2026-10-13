# Configuration conventions — environment variable naming and grouping

| Field | Value |
|---|---|
| Status | Published |
| Published | 2026-10-11 |
| Owner | WP-0.5 — Configuration, secrets and error conventions (MT-0.5-01) |
| Source of truth | Parent plan Sections 9.10 and 16.2 — this document is the published reference; the plan wins on any conflict (Section 0) |
| Applies to | Every environment variable read by any component in this repository (backend, worker, bridge, web, Compose stack) |
| Sibling conventions | [`error-envelope.md`](./error-envelope.md), [`headers.md`](./headers.md), [`pagination.md`](./pagination.md) |

## Purpose

WP-0.5 fixes shared conventions before code spreads. Section 9.10 enumerates the
configuration groups and requires every setting to carry a documented default plus a
fail-fast startup validation; Section 16.2 requires one documented environment template,
real values living outside Git, and the same variable names used everywhere (NFR-06:
the stack is configured only by environment variables). This document fixes the naming
pattern, grouping rule, and secret-handling rule now, so backend, bridge, web and
mobile read one vocabulary from their first line of configuration code.

## Naming pattern

Every environment variable follows `ORCHESTRATOR_<SETTING>`:

1. **Prefix** — every variable starts with `ORCHESTRATOR_`. There is no second,
   component-local prefix: Compose template, host secret mechanism, backend settings
   and bridge configuration all share this one vocabulary (Section 16.2; NFR-06).
2. **Casing** — `SCREAMING_SNAKE_CASE`: ASCII letters, digits and underscores only; no
   other separators; never mixed case.
3. **Group segment** — the setting's Section 9.10 group appears as the leading
   segment(s) after the prefix, per the grouping table below.
4. **Units in names** — every numeric or duration setting carries its unit as a suffix
   (`_SECONDS`, `_MINUTES`, `_HOURS`, `_MB`, `_GB`, `_PER_MINUTE`); no implied units.
5. **Booleans** — boolean settings and feature flags take `true` or `false`.
6. **One name, no aliases** — "canonical" means one authoritative spelling
   (Section 0.4): a setting never answers to two names, and two settings never share
   one name. A rename is a single atomic change — this document first, then the
   template, then every consumer — and happens before any code reads the name.
7. **Third-party images** — where an external image mandates its own variable name,
   the Compose definition maps the canonical value into that name; the canonical name
   remains the one stored in the template and the secret store (single vocabulary,
   NFR-06).

## Grouping — all Section 9.10 groups

Every setting belongs to exactly one group. The leading segment after the prefix
identifies the group in the variable's name.

| Section 9.10 group | Leading segment | Representative names | Notes |
|---|---|---|---|
| Database and cache URLs | `DATABASE_`, `CACHE_` | `ORCHESTRATOR_DATABASE_URL`, `ORCHESTRATOR_CACHE_URL` | Consumed by backend, worker, migrate. Default documented in the environment template. |
| Secret keys | `SECRET_` | `ORCHESTRATOR_SECRET_KEY` | Secret; required in `prod`. Refusal of weak or missing secrets at startup in `prod` (Section 16.2). |
| Allowed hosts and CORS/CSRF origins | `ALLOWED_`, `CORS_`, `CSRF_` | `ORCHESTRATOR_ALLOWED_HOSTS`, `ORCHESTRATOR_CORS_ORIGINS`, `ORCHESTRATOR_CSRF_ORIGINS` | Allowed hosts required in `prod` (Section 16.2; per WP-0.2's required-in-prod set). |
| Storage backend | `STORAGE_` | `ORCHESTRATOR_STORAGE_BACKEND`, `ORCHESTRATOR_STORAGE_S3_*` (endpoint, bucket, credential pair) | `local` volume by default (Section 16.3); switching to S3-compatible is configuration only (Section 16.3). S3 credentials are secret. |
| Token lifetimes | `TOKEN_LIFETIME_` | `ORCHESTRATOR_TOKEN_LIFETIME_<KIND>_<UNIT>` | Token kinds are named when their models land (WP-1.2); unit suffix mandatory. |
| Rate limits | `RATE_LIMIT_` | `ORCHESTRATOR_RATE_LIMIT_<SCOPE>_PER_MINUTE` | Unit suffix mandatory; per-scope rows documented where the limits land. |
| OCR engine | `OCR_` | `ORCHESTRATOR_OCR_ENGINE`, `ORCHESTRATOR_OCR_*` | Consumed by the attachment pipeline (Section 9.5). |
| Description provider settings | `DESCRIPTION_` | `ORCHESTRATOR_DESCRIPTION_PROVIDER`, `ORCHESTRATOR_DESCRIPTION_*` | Implementations per Section 9.5: `disabled`, Anthropic-compatible vision model, local model. Default: `disabled` (Section 22, OQ-07 recommended default; enabling decision deferred to M1). Any API credential in this group is secret. |
| FCM credentials | `FCM_` | `ORCHESTRATOR_FCM_*` | Secret; push dispatch (Section 9.8). Provisioning lands with WP-5.4. |
| Cloudflare tunnel | `CLOUDFLARE_TUNNEL_` | `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN`, `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` | Secret token plus the parameterized public hostname; provisioned in WP-5.1 (Section 15.4). |
| Feature flags | `FEATURE_` | `ORCHESTRATOR_FEATURE_<NAME>` | Booleans (`true`/`false`); default documented per flag. |
| Orchestrator API base URL (manifest binding) — Section 10.3, **added by MT-1.3-05** | `API_` | `ORCHESTRATOR_API_BASE_URL` | The `orchestrator_api` value of every generated manifest (Section 10.3; NFR-06 env-only). Section 9.10 enumerates groups without an API-base entry while the manifest contract requires the value — the group was created here first, following this document, and is flagged for owner confirmation (Section 20.1 item 5). |
| Event publish — Section 9.6 post-commit fan-out, **added by MT-1.9-03** | `EVENTS_` | `ORCHESTRATOR_EVENTS_CHANNEL`, `ORCHESTRATOR_EVENTS_REDIS_URL` | The Redis channel and connection for publishing committed Event envelopes (Section 9.6; WP-1.10 subscribes). Section 9.10's group list does not enumerate an events entry while the publish contract requires the values — the group was created here first, following this document, and is flagged for owner confirmation (Section 20.1 item 5). |
| Attachment limits — Section 9.5 limits/safety, **added by MT-1.11-02** | `ATTACHMENT_` | `ORCHESTRATOR_ATTACHMENT_MAX_FILE_BYTES`, `ORCHESTRATOR_ATTACHMENT_MAX_PER_TASK`, `ORCHESTRATOR_ATTACHMENT_MAX_TOTAL_BYTES`, `ORCHESTRATOR_ATTACHMENT_RETENTION_GRACE_DAYS` | The Section 9.5 defaults (25 MB / 10 / 100 MB) and the Section 12.4 retention grace period (OQ-10 default 30 days) as environment-overridable values. Byte settings carry the `_BYTES` unit suffix; the day count says `_DAYS` (units rule). Section 9.10 enumerates the limits as "default, configurable" without naming the variables — the group was created here first, following this document, and is flagged for owner confirmation (Section 20.1 item 5). |
| Attachment pipeline processing — Section 9.5 worker stages, **added by WP-1.12** | `ATTACHMENT_` | `ORCHESTRATOR_ATTACHMENT_IMAGE_MAX_EDGE_PX`, `ORCHESTRATOR_ATTACHMENT_CHUNK_MAX_TOKENS`, `ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR`, `ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER`, `ORCHESTRATOR_ATTACHMENT_SUMMARY_BUDGET_TOKENS`, `ORCHESTRATOR_ATTACHMENT_SUMMARY_MAX_TOKENS`, `ORCHESTRATOR_ATTACHMENT_RETRY_MAX_ATTEMPTS`, `ORCHESTRATOR_ATTACHMENT_RETRY_BACKOFF_SECONDS`, `ORCHESTRATOR_ATTACHMENT_PARSE_TIMEOUT_SECONDS` | The pipeline's documented defaults (Section 9.10: settings are "environment-driven" with "a documented default"; Section 20.4 item 3). The plan fixes the *shape* — configurable splitting, estimation, summary, retry — but no values; each default below is a WP-1.12 choice recorded in the WP changelog and flagged for owner confirmation (Section 20.1 item 5), never presented as a plan fact. Shares the `ATTACHMENT_` segment with the limits group above (same domain); OCR engine and description provider keep their own groups. |
| Request body sizing — Section 9.7 submission uploads, **added by WP-3.2** | `REQUEST_` | `ORCHESTRATOR_REQUEST_BODY_MAX_BYTES` | The bound on in-memory request bodies (Django `DATA_UPLOAD_MAX_MEMORY_SIZE`) so the Section 9.7 degraded path is reachable: the submission endpoint must *accept* an oversize patch to store "stats and file list only". Default `33554432` (32 MiB) — a WP-3.2 recorded reading (the plan fixes the 5 MB *storage* cap, not the receive bound), flagged for owner confirmation (Section 20.1 item 5). Byte setting, `_BYTES` suffix per the units rule. |

The table is a pattern record with representative names, not a closed list: each
setting that lands in a later work package is added with its full metadata below,
following this pattern. No name may be invented outside it.

## Per-setting metadata contract (Sections 9.10, 16.2)

Every setting — in the environment template, in the backend settings module when
WP-1.1 lands, and in bridge configuration — carries all of these fields:

| Field | Meaning |
|---|---|
| Name | The canonical variable name per the pattern above. |
| Group | Its Section 9.10 group. |
| Purpose | What it configures, in one line. |
| Default | A documented default — required by Section 9.10. A setting with no safe default is instead marked *required*. |
| Validation note | What startup validation checks for this setting; missing required values fail fast at startup with a clear error (Section 9.10). Startup-validation code lands in WP-1.1 — the contract is fixed here. |
| Required in `prod` | `yes` / `no` — at minimum secret keys and allowed hosts are `yes`; `prod` startup refuses weak or missing secrets (Section 16.2). |
| Secret | `yes` / `no` — drives the secret-handling rule below. |

The authoritative record for every Compose-consumed setting is the environment
template (`infra/compose/.env.example`, WP-0.2), whose per-variable comments carry
these fields. Non-Compose settings (e.g. bridge-only configuration) are recorded with
the same fields in their consumer's package documentation.

## Compose-consumed settings — full metadata rows (WP-0.2 × WP-0.5 reconciliation, 2026-10-12)

The group table above is a pattern record, not a closed list, and several names
the M0 Compose stack actually consumes were only implied by it (compose images,
host ports, the bind address, database container credentials, and reserved
placeholders for later groups). Every name below follows the naming pattern and
was fixed at the WP-0.2 × WP-0.5 reconciliation; together with the representative
names above this document is the authoritative catalog (MT-0.5-01).

| Name | Group (leading segment) | Purpose | Default | Validation note | Required in `prod` | Secret |
|---|---|---|---|---|---|---|
| `ORCHESTRATOR_IMAGE_POSTGRES`, `ORCHESTRATOR_IMAGE_REDIS`, `ORCHESTRATOR_IMAGE_BACKEND`, `ORCHESTRATOR_IMAGE_WEB`, `ORCHESTRATOR_IMAGE_CLOUDFLARED`, `ORCHESTRATOR_IMAGE_MAILHOG` | Compose image basis (`IMAGE_`) — Section 16.1 | Container image per Compose service | `postgres:16-alpine`, `redis:7.4-alpine`, `orchestrator-backend:dev`, `orchestrator-web:stub`, `cloudflare/cloudflared:2026.10.0`, `mailhog/mailhog:v1.0.1` | Tag must exist at pull time; `prod` tags pinned, never `:latest` | no | no |
| `ORCHESTRATOR_PORT_BACKEND` | Compose published ports (`PORT_`) — Section 16.1 | Host port published for the API | `8000` | Valid port 1–65535; only `backend` and `web` publish | no | no |
| `ORCHESTRATOR_PORT_WEB` | Compose published ports (`PORT_`) — Section 16.1 | Host port published for the UI | `3000` | Valid port 1–65535 | no | no |
| `ORCHESTRATOR_BIND_ADDR` | Compose published ports (`BIND_`) — Section 16.1 | Interface the published ports bind to | `127.0.0.1` when unset (template carries the host's LAN IP) | Must be an IP assigned to this host; never `0.0.0.0` on an internet-facing VPS — the tunnel (WP-5.1) is the only public edge | yes (set to this host's address) | no |
| `ORCHESTRATOR_DATABASE_USER` | Database and cache (`DATABASE_`) | Postgres role; mapped to the image-mandated `POSTGRES_USER` inside the container (rule 7) | `orchestrator` | Non-placeholder value in `prod` | no | no |
| `ORCHESTRATOR_DATABASE_PASSWORD` | Database and cache (`DATABASE_`) | Postgres password; mapped to the image-mandated `POSTGRES_PASSWORD` inside the container (rule 7) | `change-me` placeholder | Required in `prod`; weak/placeholder value refused; never empty | yes | yes |
| `ORCHESTRATOR_DATABASE_NAME` | Database and cache (`DATABASE_`) | Database name; mapped to the image-mandated `POSTGRES_DB` inside the container (rule 7) | `orchestrator` | Valid identifier | no | no |
| `ORCHESTRATOR_CACHE_BROKER_URL` | Database and cache (`CACHE_`) | Celery broker URL (Redis) | `redis://redis:6379/0` | Scheme `redis://` | no | no |
| `ORCHESTRATOR_CACHE_APPENDONLY` | Database and cache (`CACHE_`) | Redis persistence toggle (Section 16.1) | `true` | Booleans take `true`/`false` (rule 5); Compose maps the value to Redis's mandated `--appendonly yes\|no` (rule 7) | no | no |
| `ORCHESTRATOR_EVENTS_CHANNEL` | Event publish (`EVENTS_`) — Section 9.6 | Redis channel for post-commit Event-envelope publish (MT-1.9-03; WP-1.10 subscribes) | `orchestrator:events` | Non-empty | no | no |
| `ORCHESTRATOR_EVENTS_REDIS_URL` | Event publish (`EVENTS_`) — Section 9.6 | Redis connection for that publish | empty → falls back to `ORCHESTRATOR_CACHE_URL` (same Redis; no extra Compose wiring) | Scheme `redis://` when set | no | no |
| `ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS` | Event publish (`EVENTS_`) — Section 9.6 SSE gateway, **added by MT-1.10-04** | Cadence of the `GET /events/stream` heartbeat comment (Section 9.6: "Heartbeat comments every 15 s") | `15` seconds — the plan's fixed value; configurable for tests and downward review only | Positive number; values approaching proxy idle timeouts (Cloudflare ~100 s class) re-open RISK-05 and belong to WP-5.1's verification, not an ops tweak | no | no |
| `ORCHESTRATOR_DEBUG` | Runtime debug posture (Compose dev/prod split, MT-0.2-02) — `DEBUG_` | Django debug flag | `false` | `prod` boot refused while `true` (Section 16.2); dev overlay sets `true` | yes (must be `false`) | no |
| `ORCHESTRATOR_LOG_LEVEL` | Structured logging (`LOG_`) — Section 17 | Level of the JSON service/request logs (WP-1.1, MT-1.1-02) | `INFO` in the base/prod settings; `DEBUG` in the dev settings module | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; an unknown level fails boot when the logging dict configures it | no | no |
| `ORCHESTRATOR_STORAGE_MEDIA_ROOT` | Storage backend (`STORAGE_`) | Mount point of the shared media volume | `/media` | Absolute path; must equal the Compose volume mount | no | no |
| `ORCHESTRATOR_STORAGE_S3_ENDPOINT` | Storage backend (`STORAGE_`) | S3-compatible API endpoint (Section 16.3) | empty — reserved until WP-6.2 | URL required when `ORCHESTRATOR_STORAGE_BACKEND=s3` | when `s3` | no |
| `ORCHESTRATOR_STORAGE_S3_BUCKET` | Storage backend (`STORAGE_`) | S3 bucket | empty — reserved | Non-empty when `s3` | when `s3` | no |
| `ORCHESTRATOR_STORAGE_S3_ACCESS_KEY_ID` | Storage backend (`STORAGE_`) | S3 credential pair — half 1 | empty — reserved | Required when `s3` | when `s3` | yes |
| `ORCHESTRATOR_STORAGE_S3_SECRET_ACCESS_KEY` | Storage backend (`STORAGE_`) | S3 credential pair — half 2 | empty — reserved | Required when `s3` | when `s3` | yes |
| `ORCHESTRATOR_ATTACHMENT_MAX_FILE_BYTES` | Attachment limits (`ATTACHMENT_`) — Section 9.5, added by MT-1.11-02 | Per-file size cap for `POST /tasks/{id}/attachments` | `26214400` (25 MB) — the Section 9.5 default; flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_MAX_PER_TASK` | Attachment limits (`ATTACHMENT_`) — Section 9.5, added by MT-1.11-02 | Per-task attachment count cap (live, non-deleted records) | `10` — the Section 9.5 default; flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_MAX_TOTAL_BYTES` | Attachment limits (`ATTACHMENT_`) — Section 9.5, added by MT-1.11-02 | Per-task total-size cap across live attachments | `104857600` (100 MB) — the Section 9.5 default; flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_RETENTION_GRACE_DAYS` | Attachment limits (`ATTACHMENT_`) — Section 12.4 / OQ-10, added by MT-1.11-05 | Grace period after a task is archived before the retention job purges its attachments | `30` days — OQ-10's recorded default (deferred to M6 for the final decision; the default is used, never re-decided) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_IMAGE_MAX_EDGE_PX` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 2, added by MT-1.12-02 | Long-edge cap (pixels) for the normalized image; aspect ratio preserved | `2048` px — WP-1.12's documented choice (plan fixes "cap long edge", not the value); flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_CHUNK_MAX_TOKENS` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 3, added by MT-1.12-05 | Token bound for chunk splitting (pages/segments longer than this split further) | `512` tokens — WP-1.12's documented choice (plan fixes "token-bounded", not the bound); flagged for owner confirmation | Unit suffix mandatory; positive integer ≥ 1 | no | no |
| `ORCHESTRATOR_ATTACHMENT_TOKEN_ESTIMATOR` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 3, added by MT-1.12-05 | Deterministic token-estimation method | `chars_div_4` — `ceil(chars/4)`, the documented default method (plan says "estimate", not a tokenizer; a model-accurate tokenizer would be a new OQ) | One of the supported estimator names; unknown value fails fast at first use (Section 9.10) | no | no |
| `ORCHESTRATOR_ATTACHMENT_SUMMARY_PROVIDER` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 3 / Section 22 OQ-07, added by MT-1.12-06 | Summary generation provider; `disabled` selects the deterministic extractive fallback | `disabled` — the OQ-07-style default; no generative provider is invented before the owner decision | One of `disabled` (any other value fails fast pointing at the OQ-07/WP-1.13 decision) | no | no |
| `ORCHESTRATOR_ATTACHMENT_SUMMARY_BUDGET_TOKENS` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 3, added by MT-1.12-06 | Token budget for summary *input* (chunks taken in sequence up to this bound) | `512` tokens — WP-1.12's documented choice; flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_SUMMARY_MAX_TOKENS` | Attachment pipeline (`ATTACHMENT_`) — Section 9.5 stage 3, added by MT-1.12-06 | Output bound for the short summary (the documented meaning of "short") | `120` tokens — WP-1.12's documented choice (plan says "short", not how short; recorded in the changelog) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_RETRY_MAX_ATTEMPTS` | Attachment pipeline (`ATTACHMENT_`) — Section 9.9 retry with backoff, added by MT-1.12-07 | Total pipeline attempts per attachment before landing `failed` with the reason | `3` attempts — WP-1.12's documented choice consistent with the Section 9.9 schedule class; flagged for owner confirmation | Unit suffix mandatory; positive integer ≥ 1 | no | no |
| `ORCHESTRATOR_ATTACHMENT_RETRY_BACKOFF_SECONDS` | Attachment pipeline (`ATTACHMENT_`) — Section 9.9 retry with backoff, added by MT-1.12-07 | Base backoff; attempt *n* waits `base × 2^(n-1)` seconds (jitter none — deterministic for review) | `60` seconds — WP-1.12's documented choice; flagged for owner confirmation | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_ATTACHMENT_PARSE_TIMEOUT_SECONDS` | Attachment pipeline (`ATTACHMENT_`) — Section 12.1 worker-safety limit, added by MT-1.12-03/04 | Cooperative parse-time budget per attachment (checked between pages/blocks; expiry is transient and retried) | `60` seconds — WP-1.12's documented in-process limit (Section 12.3 records OS-level sandboxing as post-v1) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_REQUEST_BODY_MAX_BYTES` | Request body sizing (`REQUEST_`) — Section 9.7 submission uploads, added by WP-3.2 | In-memory request-body bound (`DATA_UPLOAD_MAX_MEMORY_SIZE`): how large a `POST /tasks/{id}/resolution` body (the captured patch) the API accepts before refusing | `33554432` (32 MiB) — WP-3.2's recorded reading; the plan fixes the 5 MB *storage* cap and the oversize degraded path but no receive bound, so a memory-safe ceiling is chosen here and flagged for owner confirmation (Section 20.1 item 5) | Unit suffix mandatory; positive integer ≥ the 5 MB storage cap | no | no |
| `ORCHESTRATOR_OCR_TESSERACT_CMD` | OCR engine (`OCR_`) — Section 6.6 default engine, added by MT-1.12-02 | The `tesseract` executable (name on PATH or absolute path) used by the default engine | `tesseract` | Non-empty; a missing binary fails the stage with a human-readable reason (never a silent empty transcript) | no | no |
| `ORCHESTRATOR_TOKEN_LIFETIME_OWNER_SESSION_HOURS` | Token lifetimes (`TOKEN_LIFETIME_`) | Owner session (login) lifetime — drives the `owner_session` token expiry and the session cookie max-age (Section 12.2; MT-1.2-01) | `12` hours (fixed by WP-1.2; flagged for owner confirmation) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS` | Token lifetimes (`TOKEN_LIFETIME_`) | Agent bearer-token lifetime — the Section 12.2 "long-lived but revocable" default behind `POST /tokens/agent` (MT-1.2-03) | `720` hours / 30 days (fixed by WP-1.2; flagged for owner confirmation) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_TOKEN_LIFETIME_DEVICE_DAYS` | Token lifetimes (`TOKEN_LIFETIME_`) | Device-bound token lifetime — the Section 12.2 mobile credential behind `POST /devices` (MT-1.2-04); remote revocation, not expiry, is the primary lost-phone control | `90` days (fixed by WP-1.2; flagged for owner confirmation) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE` | Rate limits (`RATE_LIMIT_`) | Per-token budget for Section 9.2 agent-facing endpoints (Agent/Auditor/Bridge callers; FR-SEC-05; MT-1.2-06) | `120` per minute (fixed by WP-1.2; flagged for owner confirmation) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE` | Rate limits (`RATE_LIMIT_`) | Per-token budget for the Section 9.2 Devices endpoints (Mobile caller; FR-SEC-05; MT-1.2-06) | `60` per minute (fixed by WP-1.2; flagged for owner confirmation) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_RATE_LIMIT_API_PER_MINUTE` | Rate limits (`RATE_LIMIT_`) | API-wide budget beyond FR-SEC-05's agent/device scope (owner-session endpoints stay unthrottled until then) | none — reserved; fixed with the WP-6.1 hardening | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_API_BASE_URL` | Orchestrator API base URL (`API_`) — Section 10.3 manifest binding, added by MT-1.3-05 | Public base URL rendered as `orchestrator_api` in every project manifest (`GET /projects/{pid}/manifest`) | `http://localhost:8000/api/v1` — the Section 10.3 example's shape; **new group, flagged for owner confirmation** (Section 20.1 item 5) | Absolute `http(s)://` URL; startup fails fast otherwise (Section 9.10) | no | no |
| `ORCHESTRATOR_OCR_ENGINE` | OCR engine (`OCR_`) | OCR engine selection (Section 6.6) | `tesseract` | One of the pluggable engine names | no | no |
| `ORCHESTRATOR_DESCRIPTION_PROVIDER` | Description provider (`DESCRIPTION_`) | Attachment description provider | `disabled` (Section 22) | One of `disabled` or a configured vision-model provider | no | no |
| `ORCHESTRATOR_FCM_PROJECT_ID` | FCM credentials (`FCM_`) | FCM project id (Section 9.8) | empty — reserved (WP-5.4) | Required once push dispatch is enabled | when push enabled | no |
| `ORCHESTRATOR_FCM_CREDENTIALS_JSON` | FCM credentials (`FCM_`) | FCM service-account credentials | empty — reserved (WP-5.4) | Required once push dispatch is enabled | when push enabled | yes |
| `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` | Cloudflare tunnel (`CLOUDFLARE_TUNNEL_`) — Section 15.4 | Secret that starts the named tunnel from the environment (mapped to the container's image-mandated `TUNNEL_TOKEN`, rule 7) | empty — template placeholder | Non-empty once remote access is enabled; cloudflared refuses to run with a missing/invalid token (WP-5.1 fail-fast, verified); rotated via the Cloudflare dashboard (Section 15.4) | yes (when remote access is enabled) | yes |
| `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` | Cloudflare tunnel (`CLOUDFLARE_TUNNEL_`) — Sections 15.1, 15.4 | Public tunnel hostname parameterizing the edge route mirrored from `infra/cloudflare/ingress.yaml` and the tunnel entry of the CORS/CSRF trusted origins (OQ-11: `orchestrator.<owner-domain>`) | empty — no environment-specific hostname in Git (plan 20.4 item 3) | Absolute DNS name (no scheme, no path) once remote access is enabled; consumed by the tunnel operations procedure (`infra/cloudflare/README.md`) | yes (when remote access is enabled) | no |
| `ORCHESTRATOR_FEATURE_FLAGS` | Feature flags (`FEATURE_`) | Comma-separated list of enabled `ORCHESTRATOR_FEATURE_<NAME>` flags | empty — none enabled | Each member matches `ORCHESTRATOR_FEATURE_<NAME>`; flag values are `true`/`false` | no | no |
| `ORCHESTRATOR_AGENT_TOKEN` | Secret keys — bridge agent token (Section 10.3; name fixed in "Secret handling" above) | Bridge → backend agent token, environment fallback | none — required when the bridge runs | Required; weak or missing refused | yes (when bridge runs) | yes |
| `NODE_ENV` | Image-mandated (rule 7) — Node.js runtime | Dev-overlay mode marker for the future WP-4.1 web image | `development` in the dev overlay; absent in the prod render | Fixed literal set by `compose.dev.yaml`; not host-configurable | no | no |

Third-party container interface (rule 7): the Postgres service keeps the image's
mandated `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` environment keys —
including the `pg_isready -U $POSTGRES_USER` health probe and the same mandated
names on the CI service containers in `.github/workflows/test.yaml` — while the
Compose definition maps the canonical `ORCHESTRATOR_DATABASE_*` value into that
name and the template and secret store hold only canonical names. `NODE_ENV` is
likewise the Node runtime's mandated name; it has no template twin because its
value is a fixed dev-overlay literal, not a host-configurable setting.
`TUNNEL_TOKEN` (cloudflared, since WP-5.1) follows the Postgres pattern: the
Compose definition maps the canonical `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN`
into the image-mandated key, while the template and secret store hold only the
canonical name.

## The "same names everywhere" rule (NFR-06, Section 16.2)

The Compose template, the host secret mechanism (or Compose secrets), the backend
settings module and the bridge configuration share one vocabulary. A component never
invents a local alias for a shared setting, and never silently renames one: renames
follow the atomic-change rule in the naming pattern above.

## Secret handling (Sections 16.2, 17, 20.4 item 3)

* A name ending in `_KEY`, `_TOKEN`, `_SECRET`, `_PASSWORD` or `_CREDENTIALS` is a
  secret unless its metadata row explicitly marks it otherwise (e.g.
  `ORCHESTRATOR_TOKEN_LIFETIME_*` names a token but stores a duration). The `Secret`
  field on the row is authoritative.
* No real secret or environment-specific value is ever committed (Section 20.4,
  item 3). The template carries placeholders and comments only; the real `.env` file
  is excluded from Git.
* Real values live outside Git (Section 16.2): on a VPS they come from the host's
  secret mechanism or Compose secrets — always under the identical canonical names
  (Section 16.2, NFR-06).
* `prod` startup refuses weak or missing secrets (Section 16.2); the strength checks
  are implemented in WP-1.1, the refusal contract is fixed here.
* Secrets never appear in structured logs (Section 17 token/secret scrubbing,
  RISK-14) and never in the project manifest (Section 10.3). The bridge reads its
  agent token from the environment or the user-level config (Section 10.3); the
  environment fallback is named `ORCHESTRATOR_AGENT_TOKEN` and is secret-flagged.

## Defaults tied to Section 22 decisions

* Description provider: default `disabled` — the OQ-07 recommended default recorded
  in Section 22 (deferral to M1 recorded 2026-10-11; WP-0.4 session notes). Remembered
  defaults are not authoritative; Section 22 is.
* Owner authentication strength (OQ-09): recommended default "strong password plus
  optional TOTP", deferred to M1 — no variable is invented for it before the decision
  lands; any future setting follows this pattern.
* Configuration semantics beyond the Section 9.10 groups are not decided here; they
  become an open question first (Section 20.1, rule 5).

## Reconciliation with `infra/compose/.env.example`

MT-0.2-03 created the environment template and explicitly deferred name
formalization to this document. Every name in the template must follow the pattern
and grouping rules above; a divergent name is renamed **now**, before M1 code reads
any variable (renaming after that breaks the Compose README examples and every
consumer at once).

Reconciliation status at publication (checked 2026-10-11): `infra/compose/.env.example`
had not yet been landed — WP-0.2 runs in parallel with WP-0.5 in Wave 1. The
reconciliation check is: every variable in the template starts with `ORCHESTRATOR_`,
matches its group's leading segment, and carries the per-setting metadata fields; any
violation is a rename against this document, not an extension of it.

Reconciliation completed 2026-10-12 (WP-0.2 × WP-0.5 conflict resolution): the
template and every consumer — `infra/compose/compose.yaml`,
`infra/compose/compose.dev.yaml`, `infra/compose/README.md`,
`.github/workflows/test.yaml`, `CONTRIBUTING.md` — now use only the canonical names
above; the WP-0.2 provisional names (`POSTGRES_*`, `REDIS_*`, `DJANGO_*`,
`DATABASE_URL`, `CELERY_BROKER_URL`, `MEDIA_ROOT`, `STORAGE_BACKEND`, `BACKEND_PORT`,
`WEB_PORT`, `CLOUDFLARED_TUNNEL_TOKEN`, …) were renamed in one atomic change (this
document first, then the template, then every consumer), with the full rename map
recorded in the WP-0.5 changelog. The only surviving non-canonical spellings are the
rule 7 third-party container interfaces documented above.

## References

* Parent plan Section 9.10 — configuration groups, documented defaults, fail-fast
  startup validation.
* Parent plan Section 16.2 — one template, real values outside Git, weak/missing
  secret refusal in `prod`, identical names everywhere.
* Referenced from the package documentation of `backend/`, `bridge/`, `web/` and
  `mobile/` (WP-0.5 acceptance).
* Error responses: [`error-envelope.md`](./error-envelope.md) · Correlation and
  idempotency headers: [`headers.md`](./headers.md) · List paging:
  [`pagination.md`](./pagination.md)
