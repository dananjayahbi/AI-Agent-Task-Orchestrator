# WP-1.1 — Django project skeleton: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.1-01** — Django 5.x ASGI project created under `backend/` per Appendix A:
  `manage.py`, project package `config/` (`asgi.py`, `urls.py`), and the Section 9.1
  module layout wired as thin stubs — 11 apps (`accounts`, `agents`, `attachments`,
  `audit`, `core`, `events`, `leases`, `merge`, `notifications`, `projects`, `tasks`)
  each with an `AppConfig`; `.gitkeep` placeholders removed. **Settings split decision
  (recorded here per the MT risk note): one module per environment** under
  `apps/core/settings/` — `base.py` (shared, every value read from canonical
  `ORCHESTRATOR_*` names with documented defaults, Section 9.10 / configuration.md),
  `dev.py` (host default: debug on unless overridden, ephemeral secret when none is
  set, loopback + `testserver` hosts so a fresh clone boots with no committed
  secrets), `prod.py` (Section 16.2 fail-fast validation: refuses `DEBUG=true`,
  missing/weak `ORCHESTRATOR_SECRET_KEY` (≥ 32 chars, no template placeholder, no
  `django-insecure-` prefix), missing/localhost/wildcard `ORCHESTRATOR_ALLOWED_HOSTS`,
  missing/weak `ORCHESTRATOR_DATABASE_PASSWORD` — including one derived through the
  documented URL construction — and missing/weak S3 credentials when
  `STORAGE_BACKEND=s3`; errors name variables, never values). Selection uses
  Django's `DJANGO_SETTINGS_MODULE` exactly once (framework-mandated name, analogous
  to configuration.md rule 7): `manage.py`/`config/asgi.py` default to `dev` for host
  runs and CI; the container image sets `prod` (MT-1.1-05), the compose dev overlay
  overrides to `dev`. Documented in CONTRIBUTING.md ("Settings layout") together with
  the Section 6.6 run command (`python -m uvicorn config.asgi:application …
  --no-access-log`). Dependencies added (uv, locked): Django 5.x, DRF, drf-spectacular,
  uvicorn, `psycopg[binary]`, `redis`; dev: pytest, django-stubs + mypy plugins
  (`mypy_django_plugin.main`, `mypy_drf_plugin.main`, settings module
  `apps.core.settings.dev`), djangorestframework-stubs. Smoke tests
  (`backend/tests/test_settings_boot.py`) boot `manage.py check` in a subprocess per
  environment: dev boots env-less; prod boots strong and refuses missing/weak secret,
  weak DB password and `DEBUG=true` (each naming the offending variable only).
  Verified: `ruff check`/`format --check`, `mypy .`, `manage.py check`,
  `makemigrations --check --dry-run` all green; ASGI boot confirmed under the
  documented run command.
- **MT-1.1-02** — Structured JSON logging with correlation-id propagation (Sections 17,
  12.4; MT-0.5-03). Log field spellings are defined **once** in
  `backend/apps/core/logging.py` (the single authority per the MT risk note):
  `timestamp` (ISO-8601 UTC ms), `level`, `logger`, `message`, `correlation_id`
  (present iff in a request scope), `exception` (when `exc_info`), plus scrubbed
  `extra=` telemetry. `apps/core/correlation.py` holds the scope contextvar;
  `apps/core/middleware.py` adds `CorrelationIdMiddleware` (honors a well-formed
  incoming `X-Correlation-ID`, generates one otherwise — malformed/oversized values
  are replaced defensively; the id is stable across the request and echoed on the
  response) and `RequestLoggingMiddleware` (one JSON line per request with method,
  path, status, duration). `apps/core/scrub.py` is the one scrubbing/truncation
  implementation (redact bearer + credential-shaped key/values, cap strings at
  2000 chars) shared by logs **and** the error envelope — the risk-note case
  (a `VALIDATION_ERROR` echoing a token through `details`) is covered by a test.
  `apps/core/errors.py` fixes the Section 9.2 envelope builder + closed 19-code
  catalog; `apps/core/exceptions.py` wires the DRF `EXCEPTION_HANDLER` so every
  API non-2xx is the five-field envelope with a catalog code, scrubbed
  `message`/`details`, this request's `correlation_id`, and one documented
  `retryable` rule (5xx and `RATE_LIMITED` true, other 4xx false); unhandled
  exceptions log their traceback and answer `SERVER_ERROR` (never the raw error).
  Settings: `ORCHESTRATOR_LOG_LEVEL` (documented defaults INFO / dev DEBUG),
  `LOGGING` dict on the root handler, middleware order fixed (correlation first).
  Decision recorded: Uvicorn's plain access log stays off (`--no-access-log`) so
  all request lines flow through the JSON pipeline. Tests
  (`backend/tests/test_logging.py`, `tests/conftest.py` bootstrap) cover JSON
  shape, header honored/generated/replaced, same id across a request, log and
  envelope scrubbing, truncation, and the 500 envelope. Verified live over
  HTTP (JSON lines, correlation echo, `?token=` query scrubbed) plus
  ruff/format/mypy/`manage.py check` green.
- **MT-1.1-03** — Ops health endpoints (Sections 9.2 Ops row, 16.1 probe,
  17). `backend/apps/core/health.py` adds `GET /health/live` (always 200,
  no dependency checks) and `GET /health/ready` (ping-level checks:
  `SELECT 1` for the database, a cache write for Redis — cheap by design so a
  slow dependency cannot restart-loop the container). Both views set
  `authentication_classes = []` + `AllowAny`: never behind user or agent
  auth. A failed check answers **503 in the Section 9.2 envelope** with the
  catalog code `SERVER_ERROR` (the plan's Ops row; `retryable: true` from the
  5xx rule), `correlation_id` included — no bespoke error shape. Routes are
  registered **at the root** (`/health/live`, `/health/ready`, no trailing
  slash), matching the exact probe path `infra/compose` uses
  (Section 16.1 `healthcheck: GET /health/ready`) — recorded here because the
  MT said "compose healthcheck path" while its own endpoint list says
  root-level; the OpenAPI document will show the same two paths (MT-1.1-04).
  Check functions are module-level so tests simulate an unreachable
  dependency with monkeypatching (deterministic with no Postgres/Redis
  present). Tests: `backend/tests/test_health.py` — live up while deps are
  down, ready 200 with both checks ok, ready 503 envelope for each single
  dependency failure (the other patched healthy so the scenario doesn't
  depend on what runs on the test machine), no credentials needed. Verified:
  live `200 {"status":"live"}`; ready over HTTP `503` envelope with
  `SERVER_ERROR` / `retryable:true` / echoed `X-Correlation-ID`
  `ready-check-001`; ruff/format/mypy/`manage.py check`/
  `makemigrations --check` green.
- **MT-1.1-04** — OpenAPI document generated, served, snapshotted and CI-gated
  (ADR-005; NFR-11; Sections 9.2, 18, 20.4 items 4–5). **Risk-note decisions:**
  (1) generator = **drf-spectacular 0.30.0 pinned** in `pyproject.toml`
  (mature, DRF-native, built-in Swagger/Redoc views; swapping generators later
  is a contract-breaking event); (2) **serving path = `GET /api/v1/schema`**
  (YAML by default, `?format=json` for JSON) with Swagger UI at
  `GET /api/v1/schema/swagger-ui` — fixed now because WP-2.3's bridge and both
  clients hardcode or discover it. The serving route itself is excluded from
  the document (`@extend_schema(exclude=True)` on `config/urls.py`'s
  `ContractSchemaView`) so the generator's `format`/`lang` negotiation enums
  never pollute the client contract. Config: `DEFAULT_SCHEMA_CLASS` +
  `SPECTACULAR_SETTINGS` in `settings/base.py`; `rest_framework` and
  `drf_spectacular` added to `INSTALLED_APPS`. **Envelope obligation
  (MT-0.5-02):** `apps/core/serializers.py::ErrorEnvelopeSerializer` is the one
  reusable schema — exactly the five Section 9.2 fields (`details` optional),
  field order matching the wire order — and `/health/ready` declares it on its
  503 through `@extend_schema`; the document carries a single
  `components.schemas.ErrorEnvelope` plus an auto-named `CodeEnum` component
  holding all 19 catalog codes (subset-verified by test, Section 20.4 item 5).
  Rule for later WPs: each endpoint declares its own error responses with this
  serializer; no other error shape is allowed. **Snapshot:** `schemas/openapi.yaml`
  (Appendix A; `schemas/.gitkeep` removed) — currently documents
  `/health/live` + `/health/ready`; regeneration is byte-identical
  (determinism proven locally). **CI gate:** `lint-type.yaml`'s existing
  `migration-schema-diff` job (id kept stable as the check name) gained a
  "contract check: OpenAPI snapshot drift" step — regenerate, then
  `git diff --exit-code -- schemas/openapi.yaml`, plus a `git status
  --porcelain` guard so a *missing* snapshot also fails (git diff ignores
  untracked files). **Pagination AC (MT-0.5-04):** vacuous today — no list
  endpoint exists; `tests/test_contract.py::test_list_endpoints_follow_the_
  cursor_pagination_convention` recognises list endpoints by their
  `results`-bearing 200 object and enforces the exact two-member envelope
  (`results` + `next_cursor`) plus canonical `cursor`/`page_size` parameters
  the moment WP-1.2 adds the first one (extend the test with the endpoint,
  never bypass it). **Gap found and fixed:** MT-1.1-01 never configured
  `TEMPLATES` (nothing rendered templates until Swagger UI) — `base.py` now
  declares the DjangoTemplates backend with `APP_DIRS` and the request/auth
  context processors. `CONTRIBUTING.md` gained the regen command row and the
  "snapshot is generated, never hand-edited" rule. Contract tests:
  `backend/tests/test_contract.py` — envelope component shape/required set,
  every 4xx/5xx response references the shared component, codes ⊆
  `CANONICAL_ERROR_CODES`, every `$ref` resolves, cursor-pagination checker.
  Verified: document served over HTTP (200 YAML + 200 JSON + 200 Swagger UI),
  regenerate → byte-identical snapshot, CI drift command exits 0 on a clean
  tree, ruff/format/mypy/`manage.py check`/`makemigrations --check` green.
- **MT-1.1-05** — Real backend image wired into Compose (Sections 16.1, 16.2;
  NFR-06, NFR-10). **Image:** `backend/Dockerfile` + `.dockerignore` —
  `python:3.12-slim` with **uv 0.12.10 pinned** (identical to the CI
  toolchain — RISK-15 cross-host drift), `UV_PROJECT_ENVIRONMENT=/opt/venv`
  so the dev overlay's `/app` bind mount cannot mask the environment,
  lockfile-first dependency layer (`uv sync --frozen --no-dev`),
  `ENV DJANGO_SETTINGS_MODULE=apps.core.settings.prod` (the image default is
  prod; the dev overlay overrides it), `CMD` = Uvicorn ASGI
  (Section 6.6, `--no-access-log` so Section 17's JSON pipeline stays the only
  request log), `EXPOSE 8000`. **Compose rewiring** (base file):
  `backend`/`migrate`/`worker`/`beat` all build `../../backend` (they share
  one `${ORCHESTRATOR_IMAGE_BACKEND}` tag — four contexts would conflict);
  migrate's command is now `python manage.py migrate --noinput`; the backend
  health check probes `/health/ready` **with stdlib urllib** (the slim image
  ships no `wget`; the path is unchanged per Section 16.1); `worker`/`beat`
  run placeholder idle-loop commands with PID-1 liveness checks — forced by
  the shared image (`/opt/stub/stub.py` no longer exists) and by the slim
  image having neither `ps` nor `wget`; their Celery behaviour stays WP-1.7's
  scope. `ORCHESTRATOR_DEBUG` fallback flipped `true` → `false` (the base/prod
  render must never ship debug-on; the dev overlay still sets `true`), and
  `ORCHESTRATOR_LOG_LEVEL` (MT-1.1-02's new name) joined the shared
  `&backend-env` anchor at default `INFO`. **Dev overlay:** sets
  `DJANGO_SETTINGS_MODULE=apps.core.settings.dev` for all four backend-image
  services (otherwise the image's prod default would refuse the placeholder
  secrets on `migrate` before the backend could start) and adds the real
  `--reload` Uvicorn command this file's own header promised. **Template +
  conventions:** `.env.example` gains the `ORCHESTRATOR_LOG_LEVEL` row and
  `ORCHESTRATOR_IMAGE_BACKEND=orchestrator-backend:dev` (compose defaults
  updated to match); `configuration.md` gains the `LOG_` metadata row and the
  updated image default. **Bug found and fixed (loopback rule):** the health
  probe requests `127.0.0.1`, which Django rejected (`DisallowedHost` →
  unhealthy) whenever `ALLOWED_HOSTS` was exactly `localhost`; the compose
  fallback, the template and prod validation now encode the correct rule —
  loopback entries stay (the container's own probe needs them) while **prod
  refuses a loopback-ONLY list** as the localhost placeholder in disguise
  (new `test_settings_boot` cases cover both directions; the message tells
  operators to keep `127.0.0.1` and add real serving hostnames). **CI:** no
  edit needed — `container-build.yaml` discovers every `Dockerfile`
  pattern-wise (its header already anticipated the real backend image), so
  `backend/Dockerfile` builds on the next PR automatically. **README**
  refreshed (stubs/health-table/startup-window references now describe the
  real image). **Verification (MT test command, executed):**
  `docker compose -f compose.yaml -f compose.dev.yaml --profile dev up -d
  --wait --wait-timeout 180` → **exit 0, all eight services healthy**
  (migrate `exited (0)` gating backend; only `backend`+`web` publish ports);
  `GET /health/ready` 200 through the published port with db+cache ok;
  `/api/v1/schema` 200 inside the container; JSON request lines with
  `correlation_id` stream from the container; hot reload proven (server
  process 8 → 332 after a source touch); marker row survives
  `restart backend` **and** a full `down` → `up` cycle (volumes kept);
  prod-render `run` refuses the template's weak `SECRET_KEY`/`DATABASE_PASSWORD`
  with exit 1, naming variables only (Section 16.2 from the real image); final
  `down` left `postgres_data`/`redis_data`/`backend_media` in place.
  ruff/format/mypy/`manage.py check`/`makemigrations --check`/
  OpenAPI-drift all green after the final edits.
- **Wave 2 gate fixes** — (1) `apps/core/scrub.py`: the key/value pattern accepts an
  optional closing quote before `=`/`:` so secret-bearing `str(ValidationError)` reprs
  (`'password': …`) are redacted from `message` (envelope scrub leak); (2)
  `apps/core/serializers.py`: `ErrorEnvelopeSerializer` now nests the five fields under
  `error` (Section 9.2 wire shape — the flat schema was a contract bug), body modelled
  by `ErrorEnvelopeBodySerializer`; `tests/test_contract.py` asserts the nested
  component and `schemas/openapi.yaml` was regenerated (CodeEnum / 19-code catalog
  intact).
