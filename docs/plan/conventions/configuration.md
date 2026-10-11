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
| Cloudflare tunnel token | `CLOUDFLARE_TUNNEL_` | `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` | Secret; provisioning lands with WP-5.1. |
| Feature flags | `FEATURE_` | `ORCHESTRATOR_FEATURE_<NAME>` | Booleans (`true`/`false`); default documented per flag. |

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
| `ORCHESTRATOR_IMAGE_POSTGRES`, `ORCHESTRATOR_IMAGE_REDIS`, `ORCHESTRATOR_IMAGE_BACKEND`, `ORCHESTRATOR_IMAGE_WEB`, `ORCHESTRATOR_IMAGE_CLOUDFLARED`, `ORCHESTRATOR_IMAGE_MAILHOG` | Compose image basis (`IMAGE_`) — Section 16.1 | Container image per Compose service | `postgres:16-alpine`, `redis:7.4-alpine`, `orchestrator-backend:stub`, `orchestrator-web:stub`, `cloudflare/cloudflared:2026.10.0`, `mailhog/mailhog:v1.0.1` | Tag must exist at pull time; `prod` tags pinned, never `:latest` | no | no |
| `ORCHESTRATOR_PORT_BACKEND` | Compose published ports (`PORT_`) — Section 16.1 | Host port published for the API | `8000` | Valid port 1–65535; only `backend` and `web` publish | no | no |
| `ORCHESTRATOR_PORT_WEB` | Compose published ports (`PORT_`) — Section 16.1 | Host port published for the UI | `3000` | Valid port 1–65535 | no | no |
| `ORCHESTRATOR_BIND_ADDR` | Compose published ports (`BIND_`) — Section 16.1 | Interface the published ports bind to | `127.0.0.1` when unset (template carries the host's LAN IP) | Must be an IP assigned to this host; never `0.0.0.0` on an internet-facing VPS — the tunnel (WP-5.1) is the only public edge | yes (set to this host's address) | no |
| `ORCHESTRATOR_DATABASE_USER` | Database and cache (`DATABASE_`) | Postgres role; mapped to the image-mandated `POSTGRES_USER` inside the container (rule 7) | `orchestrator` | Non-placeholder value in `prod` | no | no |
| `ORCHESTRATOR_DATABASE_PASSWORD` | Database and cache (`DATABASE_`) | Postgres password; mapped to the image-mandated `POSTGRES_PASSWORD` inside the container (rule 7) | `change-me` placeholder | Required in `prod`; weak/placeholder value refused; never empty | yes | yes |
| `ORCHESTRATOR_DATABASE_NAME` | Database and cache (`DATABASE_`) | Database name; mapped to the image-mandated `POSTGRES_DB` inside the container (rule 7) | `orchestrator` | Valid identifier | no | no |
| `ORCHESTRATOR_CACHE_BROKER_URL` | Database and cache (`CACHE_`) | Celery broker URL (Redis) | `redis://redis:6379/0` | Scheme `redis://` | no | no |
| `ORCHESTRATOR_CACHE_APPENDONLY` | Database and cache (`CACHE_`) | Redis persistence toggle (Section 16.1) | `true` | Booleans take `true`/`false` (rule 5); Compose maps the value to Redis's mandated `--appendonly yes\|no` (rule 7) | no | no |
| `ORCHESTRATOR_DEBUG` | Runtime debug posture (Compose dev/prod split, MT-0.2-02) — `DEBUG_` | Django debug flag | `false` | `prod` boot refused while `true` (Section 16.2); dev overlay sets `true` | yes (must be `false`) | no |
| `ORCHESTRATOR_STORAGE_MEDIA_ROOT` | Storage backend (`STORAGE_`) | Mount point of the shared media volume | `/media` | Absolute path; must equal the Compose volume mount | no | no |
| `ORCHESTRATOR_STORAGE_S3_ENDPOINT` | Storage backend (`STORAGE_`) | S3-compatible API endpoint (Section 16.3) | empty — reserved until WP-6.2 | URL required when `ORCHESTRATOR_STORAGE_BACKEND=s3` | when `s3` | no |
| `ORCHESTRATOR_STORAGE_S3_BUCKET` | Storage backend (`STORAGE_`) | S3 bucket | empty — reserved | Non-empty when `s3` | when `s3` | no |
| `ORCHESTRATOR_STORAGE_S3_ACCESS_KEY_ID` | Storage backend (`STORAGE_`) | S3 credential pair — half 1 | empty — reserved | Required when `s3` | when `s3` | yes |
| `ORCHESTRATOR_STORAGE_S3_SECRET_ACCESS_KEY` | Storage backend (`STORAGE_`) | S3 credential pair — half 2 | empty — reserved | Required when `s3` | when `s3` | yes |
| `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS` | Token lifetimes (`TOKEN_LIFETIME_`) | Agent token lifetime | none — fixed by WP-1.2 when token models land | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_TOKEN_LIFETIME_DEVICE_DAYS` | Token lifetimes (`TOKEN_LIFETIME_`) | Device token lifetime | none — fixed by WP-1.2 when token models land | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_RATE_LIMIT_API_PER_MINUTE` | Rate limits (`RATE_LIMIT_`) | API rate limit | none — fixed with the implementation (WP-1.2 / WP-6.1) | Unit suffix mandatory; positive integer | no | no |
| `ORCHESTRATOR_OCR_ENGINE` | OCR engine (`OCR_`) | OCR engine selection (Section 6.6) | `tesseract` | One of the pluggable engine names | no | no |
| `ORCHESTRATOR_DESCRIPTION_PROVIDER` | Description provider (`DESCRIPTION_`) | Attachment description provider | `disabled` (Section 22) | One of `disabled` or a configured vision-model provider | no | no |
| `ORCHESTRATOR_FCM_PROJECT_ID` | FCM credentials (`FCM_`) | FCM project id (Section 9.8) | empty — reserved (WP-5.4) | Required once push dispatch is enabled | when push enabled | no |
| `ORCHESTRATOR_FCM_CREDENTIALS_JSON` | FCM credentials (`FCM_`) | FCM service-account credentials | empty — reserved (WP-5.4) | Required once push dispatch is enabled | when push enabled | yes |
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
