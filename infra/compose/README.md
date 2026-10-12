# Compose stack (WP-0.2)

Runnable skeleton of the parent plan Section 16.1 deployment: eight services —
`postgres`, `redis`, `migrate` (one-shot), `backend`, `worker`, `beat`, `web`,
`cloudflared` — with the exact dependency edges from the 16.1 table, plus one
`dev`-profile helper (`mailhog`). Everything is configured only by environment
variables (NFR-06), so the same files run on Docker Desktop and a Linux VPS.
Since WP-5.1 the `cloudflared` service is real (token-run named tunnel) and is
profile-gated: it renders in `prod` and on explicit opt-in via the `tunnel`
profile, while a plain `dev` run starts the stack without the tunnel (see
"Tunnel service (WP-5.1)" and "Profiles" below).

| File | Concern |
|---|---|
| `compose.yaml` | Base stack: services, dependency edges, volumes (MT-0.2-01); network, port bindings, profiles (MT-0.2-02); health checks (MT-0.2-04) |
| `compose.dev.yaml` | `dev`-profile concern: hot-reload bind mounts and debug wiring for `backend`/`web` (MT-0.2-02) |
| `.env.example` | Documented environment template — copy to `.env` and edit (MT-0.2-03) |
| `stubs/` | Placeholder `web` image (replaced by WP-4.1; the `backend` services build the real image from `backend/` since WP-1.1 / MT-1.1-05 — service names and health paths never change) |

## Service topology (Section 16.1)

```
postgres ──> migrate ──┐
   │                   ├──> backend ──> web ──> cloudflared
   └──> worker ────────┤        ▲
redis ──> worker       │        │
   └──> beat           └────────┘   (backend also depends on postgres, redis, migrate)
```

* Only `backend` and `web` publish host ports; every other service is reachable
  only on the internal Compose network.
* Volumes: `postgres_data` (database), `redis_data` (optional Redis
  persistence, toggled with `ORCHESTRATOR_CACHE_APPENDONLY`), `backend_media`
  (shared by `backend` and `worker`, mounted at `/media` —
  `ORCHESTRATOR_STORAGE_MEDIA_ROOT` contract for WP-1.1).

## Bring-up

From the repository root (Docker with Compose v2 required):

```powershell
# 1. Create your local environment file from the committed template and edit it
Copy-Item infra\compose\.env.example infra\compose\.env
#    -> set at least ORCHESTRATOR_BIND_ADDR (your host's LAN IP) and
#       ORCHESTRATOR_DATABASE_PASSWORD / ORCHESTRATOR_SECRET_KEY (see README "Environment template")

# 2. Start the stack
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml up -d

# 3. Check status
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml ps
```

`infra/compose/.env` is the real values file and is git-ignored; the committed
template never contains real credentials (Section 16.2, plan 20.4 item 3).

## Networking and ports (Section 16.1)

* Exactly **one** network — `internal` — and every service joins it; there is
  no other network and no default network.
* Only `backend` and `web` publish host ports, bound to
  `${ORCHESTRATOR_BIND_ADDR}` (default `127.0.0.1` when unset): set it to the
  host's **LAN interface IP** in `.env` for phone/LAN access, exactly per the
  16.1 "LAN interface by default" posture — never `0.0.0.0` on an
  internet-facing VPS (the tunnel in WP-5.1 is the only public edge).
  Host ports are further adjustable with `ORCHESTRATOR_PORT_BACKEND` /
  `ORCHESTRATOR_PORT_WEB`.
* The network is a plain bridge rather than Docker's `internal: true` flag
  because `cloudflared` needs outbound internet for the tunnel; isolation
  comes from publishing ports only for `backend` and `web`.

## Profiles (dev / prod)

Two Compose profiles per Section 16.1. Pick **one** per invocation:

```powershell
# DEV stack: base + dev overlay + dev profile
#   -> hot-reload bind mounts (../../backend, ../../web at /app), debug flags,
#      and the mailhog helper service
docker compose --env-file infra/compose/.env `
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml `
  --profile dev up -d

# PROD stack: base only + prod profile
#   -> pinned images, no debug flags, no bind-mount dev wiring,
#      no helper services
docker compose --env-file infra/compose/.env `
  -f infra/compose/compose.yaml `
  --profile prod up -d
```

Validation without starting anything:

```powershell
docker compose -f infra/compose/compose.yaml --profile dev config   # renders 7 services + mailhog (no cloudflared)
docker compose -f infra/compose/compose.yaml --profile prod config  # renders exactly the 16.1 eight
docker compose -f infra/compose/compose.yaml --profile dev --profile tunnel config  # dev + cloudflared (token required)
docker compose -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml --profile dev config  # full dev render incl. hot-reload mounts
```

Profile behavior:

| Concern | `dev` | `prod` |
|---|---|---|
| Helper services | `mailhog` (SMTP catcher, no host port) | none |
| `cloudflared` tunnel (WP-5.1) | **off by default** — run without the tunnel; opt in with an extra `--profile tunnel` (token required) | on — fails fast without `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` |
| Hot-reload mounts for `backend`/`web` | yes — `compose.dev.yaml` | none (base file only) |
| Debug flags | `ORCHESTRATOR_DEBUG=true`, `NODE_ENV=development` (overlay; `NODE_ENV` is the Node image's mandated name, configuration.md rule 7) | debug off (base: `ORCHESTRATOR_DEBUG` default `false` in `.env` prod settings) |
| Images | env-overridable; `backend` builds the real image from `backend/` (WP-1.1), `web` stays a stub until WP-4.1 | pinned tags via environment (`.env.example` documents pinning) |

Note: Compose cannot change one service's config from the `--profile` flag
alone, so the dev *profile* gates helper services inside `compose.yaml` while
the dev *overlay file* carries the hot-reload/debug wiring; the two are always
used together as shown above (MT-0.2-02 decision recorded in the WP
changelog). The `cloudflared` service uses the same mechanism in reverse: its
`profiles: [prod, tunnel]` list is what lets `dev` run stack-without-tunnel
while `prod` keeps the Section 16.1 eight (MT-5.1-01).

## Tunnel service (WP-5.1)

`cloudflared` runs the official image with a **pinned tag**
(`ORCHESTRATOR_IMAGE_CLOUDFLARED`, never `latest` in prod; the upgrade path is
bumping that variable). The named tunnel is started from the environment:
Compose maps `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` to cloudflared's
image-mandated `TUNNEL_TOKEN` (configuration.md rule 7), and the canonical
ingress rules ([`../cloudflare/ingress.yaml`](../cloudflare/ingress.yaml)) are
mounted read-only at `/etc/cloudflared/config.yaml`.

* **Bring-up with the tunnel:** set `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` in
  `.env` (provisioning and rotation procedure:
  [`../cloudflare/README.md`](../cloudflare/README.md)), then either run the
  prod invocation above or add `--profile tunnel` to the dev invocation. The
  service publishes **no ports** and joins only the internal network
  (FR-NET-01); readiness is cloudflared's own `tunnel ready` probe (Section
  16.1), so `--wait` only goes green on a live tunnel.
* **Fail-fast (Section 16.2):** with the token missing or invalid,
  cloudflared exits non-zero at startup — a prod `up --wait` can never report
  healthy without a valid token (verified: empty token and a bad token both
  exit 255 immediately). In `dev`, running without the tunnel means simply
  not enabling the `tunnel` profile (default dev bring-up, above).
* **Hostname:** the tunnel hostname is environment-only —
  `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` in `.env` (OQ-11 convention
  `orchestrator.<owner-domain>`); no hostname is committed anywhere in this
  repository (plan 20.4 item 3). Full hostname/DNS/route procedure and the
  failure-mode documentation:
  [`../cloudflare/README.md`](../cloudflare/README.md).

## Environment template and validation notes (Section 16.2, plan 9.10)

One template — [`infra/compose/.env.example`](./.env.example) — documents
every setting the M0 stack consumes, each with purpose, default and
validation note, plus reserved placeholders for the plan's 9.10 groups that
have no Compose consumer yet (token lifetimes, rate limits, OCR, description
provider, FCM, S3 storage). Copy-and-edit bring-up:

```powershell
Copy-Item infra\compose\.env.example infra\compose\.env   # git-ignored real values
# edit infra\compose\.env: ORCHESTRATOR_BIND_ADDR (your LAN IP),
#   ORCHESTRATOR_DATABASE_PASSWORD, ORCHESTRATOR_SECRET_KEY, ORCHESTRATOR_ALLOWED_HOSTS
#   + for remote access (WP-5.1): ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN (secret)
#     and ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME (owner domain; both documented
#     in ../cloudflare/README.md)
```

Rules fixed now (implemented by `backend/apps/core/settings/prod.py` since
WP-1.1):

* **Real values never enter Git.** `.env` is ignored (verified with
  `git check-ignore infra/compose/.env`); the committed template holds
  placeholders only (plan 20.4 item 3).
* **Required in prod vs optional-with-default** are marked per variable in
  the template. Required-in-prod: `ORCHESTRATOR_DATABASE_PASSWORD`,
  `ORCHESTRATOR_DATABASE_URL`, `ORCHESTRATOR_SECRET_KEY`,
  `ORCHESTRATOR_ALLOWED_HOSTS`, `ORCHESTRATOR_DEBUG=false`,
  `ORCHESTRATOR_BIND_ADDR`, and `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` once
  the named tunnel exists (WP-5.1) — with `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME`
  set to the owner's tunnel hostname when remote access is enabled.
* **Startup validation (plan 9.10 / 16.2):** in prod the backend must refuse
  to boot when a required value is missing, still equals this template's
  placeholder, or is otherwise weak; missing/weak secrets are a hard failure,
  never a warning. Dev may run with placeholders (compose fallbacks) so the
  skeleton stays one-command startable.
* **Naming:** every variable follows
  [`configuration.md`](../../docs/plan/conventions/configuration.md)
  (WP-0.5, MT-0.5-01): `ORCHESTRATOR_<SETTING>`, one name, no aliases. The
  WP-0.2 provisional names were renamed at the WP-0.2 × WP-0.5
  reconciliation (2026-10-12; rename map in the WP-0.5 changelog). The only
  non-canonical spellings are third-party container interfaces mapped from
  canonical values (configuration.md rule 7): the Postgres image's
  `POSTGRES_*` inside the container and the dev overlay's `NODE_ENV`.

## One-command health bring-up (Section 16.1 / 16.3, WP-0.2 acceptance)

One command builds/starts the whole stack, runs the one-shot `migrate` first,
and **blocks until every health check is green**:

```powershell
# Dev stack (base + dev overlay + dev profile) — the documented bring-up:
docker compose --env-file infra/compose/.env `
  -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml `
  --profile dev up -d --wait --wait-timeout 180

# Prod stack equivalent:
docker compose --env-file infra/compose/.env `
  -f infra/compose/compose.yaml `
  --profile prod up -d --wait --wait-timeout 180

docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml ps
```

**Documented startup window:** first run up to ~3 minutes (image pulls plus
the `backend` image build); steady-state restarts green within **60 seconds**
(`--wait-timeout 180` covers the first run). `migrate` finishes first and
shows `exited (0)` under `ps --all` — that exit code is its health check;
every other service must report `healthy`. The dev invocation intentionally
starts **without** the tunnel (no `cloudflared` container, no token needed —
WP-5.1); the prod invocation includes it and therefore fails fast until
`ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` is set (see "Tunnel service (WP-5.1)").

Health checks exactly per Section 16.1:

| Service | Check |
|---|---|
| `postgres` | `pg_isready` readiness probe |
| `redis` | `redis-cli ping` |
| `migrate` | exit code of `manage.py migrate --noinput` (gates `backend` via `service_completed_successfully`) |
| `backend` | `GET /health/ready` — the real endpoint (WP-1.1, MT-1.1-03), probed with stdlib `urllib` (the slim image ships no `wget`) |
| `worker` | worker-ping: `celery -A config.celery inspect ping -d celery@$HOSTNAME` piped through `grep -q pong` (the worker answers through the broker; a silent/no-reply exit is unhealthy) |
| `beat` | process check — beat is pid 1 in its container (`os.kill(1, 0)`) |
| `web` | HTTP check on `:3000` |
| `cloudflared` | `cloudflared tunnel ready` (tunnel status; `prod`/`tunnel` profiles only — WP-5.1) |

## Verifying worker and beat (WP-1.7, MT-1.7-01)

Both services run the backend image's Celery entry points (`celery -A
config.celery worker` / `beat`; the schedule lives in `backend/config/celery.py`
— the two Section 9.9 jobs `lease-sweeper` and `lease-expiring-notifier`, each
every 60 s). No ports are published; the broker is the stack's Redis via
`ORCHESTRATOR_CACHE_BROKER_URL`. From the repo root, with the stack healthy:

```bash
# Worker: startup banner plus the ready line; the health check pings it.
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev logs -f worker

# Direct worker-ping (same probe the health check runs):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev exec worker \
  celery -A config.celery inspect ping -d celery@$HOSTNAME   # expect: pong from celery@<id>

# Beat: logs show "Scheduler: Sending due task lease-sweeper (...)" every 60 s.
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev logs -f beat

# Beat schedule listing (the registered jobs and intervals):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev exec beat \
  python -c "from config.celery import app; [print(name, entry['schedule'], entry['task']) for name, entry in app.conf.beat_schedule.items()]"
```

Running beat twice (two schedulers) is tolerated: both jobs are idempotent
(exactly-once reclaims via `FOR UPDATE SKIP LOCKED` + the state machine guards,
one lease-expiring event per generation-window — WP-1.7 MTs). In the dev
overlay, worker/beat have **no** source bind mount (that belongs to `backend`
alone), so code changes reach them via `docker compose build worker beat` or a
`--build` up.

## Restart procedure and data-survival check (WP-0.2 acceptance)

Restart the running stack (preserves all volumes):

```powershell
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev restart
# or a clean cycle that also re-checks health:
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev down
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml --profile dev up -d --wait --wait-timeout 180
```

Prove data survives — write a marker row, restart, read it back (named volume
per Section 16.3). Feed SQL over stdin so no shell quoting is needed:

```powershell
# 1. insert a marker row
"CREATE TABLE IF NOT EXISTS wp02_marker (id int PRIMARY KEY, note text NOT NULL); INSERT INTO wp02_marker VALUES (1, 'survives restart') ON CONFLICT (id) DO NOTHING;" |
  docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml exec -T postgres `
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# 2. restart the stack (any procedure above), wait for health, then read it back
"SELECT * FROM wp02_marker;" |
  docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml exec -T postgres `
  sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
```

Expected: `1 | survives restart`. Verified in the WP-0.2 bring-up: the row
survives both `restart` and a full `down` → `up` cycle.

**Safe tear-down reminder:** plain `down` keeps `postgres_data` (the marker
row persists across `down`/`up`); `down -v` **destroys** it — never use `-v`
for the restart proof or routine work.

## Tear-down

```powershell
# Stop the stack but KEEP all data volumes (safe default):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml down

# Full wipe — DESTROYS postgres/redis/media data (never part of routine use):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml down -v
```

`down` without `-v` preserves `postgres_data`, `redis_data` and
`backend_media`; `down -v` deletes them. The data-survival check (MT-0.2-04)
relies on this distinction — always tear down with plain `down`.
