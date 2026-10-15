# Operator setup guide (MT-6.5-01)

The spine of WP-6.5's acceptance — someone following only this guide can stand up
the stack from a fresh clone, verify it, upgrade and roll it back. Every command
and path here is the **single documented path** consolidated from the sources
cited next to it; nothing is restated from memory and nothing here overrides the
parent plan (Sections 9.10, 16.1, 16.2, 16.4, 16.5 are the source of truth).

| Link target | Doc |
|---|---|
| Stack reference (services, profiles, health checks, worker/beat) | [`infra/compose/README.md`](../infra/compose/README.md) |
| Environment template (all variables, defaults, validation notes) | [`infra/compose/.env.example`](../infra/compose/.env.example) |
| Configuration naming and secret rules | [`docs/plan/conventions/configuration.md`](plan/conventions/configuration.md) |
| Backup procedure | [`infra/backup/README.md`](../infra/backup/README.md) |
| Restore procedure (drill-derived) | [`docs/runbooks/restore-from-backup.md`](runbooks/restore-from-backup.md) |
| Mobile distribution path (MT-5.10-04) | [`mobile/docs/distribution.md`](../mobile/docs/distribution.md) |
| Parent plan, Section 16 (deployment) | [`ai_agent_task_orchestrator_architecture_plan.md`](../ai_agent_task_orchestrator_architecture_plan.md) |

## What you are operating

The Compose stack is the eight Section 16.1 services — `postgres`, `redis`,
`migrate` (one-shot), `backend`, `worker`, `beat`, `web`, `cloudflared` — plus
the `dev`-profile `mailhog` helper; only `backend` (API, default host port
`ORCHESTRATOR_PORT_BACKEND`, 8000) and `web` (default `ORCHESTRATOR_PORT_WEB`,
3000) publish host ports. The feature set as it stands today:

* **Control plane** — Django backend serving `/api/v1` (contract:
  [`schemas/openapi.yaml`](../schemas/openapi.yaml)); tasks, leases,
  attachments, audit, policy, merge, SSE events.
* **MCP bridge + Merge Executor** — [`bridge/`](../bridge/) (see its README);
  agent connection steps are MT-6.5-02's, linked in
  [Next steps](#next-steps).
* **Operations board** — Next.js app in [`web/`](../web/); runs per
  [`web/README.md`](../web/README.md). *As of this guide the Compose `web`
  service still serves the Section 16.1 health-check placeholder*
  (`infra/compose/stubs/web/default.conf`, "WP-4.1 replaces this"), so the real
  board is started from `web/` as documented there — see
  [Running the board](#running-the-operations-board).
* **Mobile client** — Flutter app in [`mobile/`](../mobile/); Android internal
  distribution is the live path, per
  [distribution.md](../mobile/docs/distribution.md).
* **Backups** — daily dump + media mirror to a second location, weekly restore
  drill ([`infra/backup/README.md`](../infra/backup/README.md)).
* **Remote access** — named Cloudflare tunnel
  ([`infra/cloudflare/README.md`](../infra/cloudflare/README.md)).
* **Metrics** — `GET /metrics` on the backend, format and flags in
  [`docs/plan/metrics.md`](plan/metrics.md).

Operator-blocked items are **not** claimed here; they carry recorded Deferred
entries in their work-package changelogs:

* **iOS / TestFlight distribution** — deferred (MT-5.10-03: no Apple
  Developer account/team on the build host) — recorded under
  [`### Deferred`](../plan-doc-series/m5-remote-mobile/wp-5.10-mobile-release/CHANGELOG.md).
  Android sideload is the standing v1 path.
* **Real-device release checklist execution** — checklist authored, execution
  deferred (MT-5.10-05, same changelog).
* **Verified agent-client compatibility rows** — MT-2.11-02 … MT-2.11-07
  deferred for missing client credentials, recorded under
  [`### Deferred`](../plan-doc-series/m2-mcp-bridge/wp-2.11-client-compatibility/CHANGELOG.md);
  the per-client guides (MT-6.5-02) are therefore deferred too.
* **Off-repo backup of the Android release keystore** — outstanding operator
  action, tracked in [`mobile/docs/release-signing.md`](../mobile/docs/release-signing.md).

## 1. Prerequisites

* Docker with Compose v2 (`docker compose version` — verified: Compose v5.4.0
  on this repo's reference host).
* A clone of this repository; all commands run **from the repository root**.
* For the operations board: Node.js + npm (commands:
  [`web/README.md`](../web/README.md)).
* For the mobile app: Flutter SDK on `PATH`
  ([`CONTRIBUTING.md` — Mobile](../CONTRIBUTING.md#mobile-flutter)) and the
  distribution docs under [`mobile/docs/`](../mobile/docs/).
* Optional, remote access only: a Cloudflare account and named tunnel —
  provisioning procedure in
  [`infra/cloudflare/README.md`](../infra/cloudflare/README.md).

## 2. Bring-up from a fresh clone

One documented path (WP-0.2's bring-up, consolidated from
[`infra/compose/README.md`](../infra/compose/README.md); the dev profile is the
default working configuration — pick it or the prod profile, never both):

```powershell
# 1. Create the local environment file from the committed template.
#    infra/compose/.env is git-ignored — the only place real values live.
Copy-Item infra\compose\.env.example infra\compose\.env
#    (bash equivalent: cp infra/compose/.env.example infra/compose/.env)

# 2. Edit infra/compose/.env — at minimum:
#      ORCHESTRATOR_BIND_ADDR            your host's LAN interface IP, or 127.0.0.1 for local-only
#      ORCHESTRATOR_DATABASE_PASSWORD    a strong value (required in prod)
#      ORCHESTRATOR_SECRET_KEY           a strong value, >= 32 chars (required in prod)
#      ORCHESTRATOR_ALLOWED_HOSTS        your hostnames (required in prod)
#    Section 16.2: real values never enter Git — this file is ignored.

# 3. Start the stack; --wait blocks until every health check is green.
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml --profile dev up -d --wait --wait-timeout 180

# 4. Check status.
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml ps
```

Expected, matching [`infra/compose/README.md`](../infra/compose/README.md)
("One-command health bring-up"):

* First run up to ~3 minutes (image pulls plus the backend image build);
  steady-state restarts green within 60 seconds (`--wait-timeout 180` covers
  the first run).
* `migrate` shows `exited (0)` under `ps --all` — its exit code is its health
  check; every other service reports `healthy`.
* The dev invocation starts **without** the tunnel (no `cloudflared` container,
  no token needed).

Prod equivalent (pinned images, no debug, tunnel included — fails fast until
`ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` is set): same command with the base file
only and `--profile prod`; render it without starting anything via
`docker compose -f infra/compose/compose.yaml --profile prod config`. Details:
[`infra/compose/README.md`](../infra/compose/README.md) → "Profiles".

## 3. Environment template walkthrough (Sections 9.10 / 16.2)

[`infra/compose/.env.example`](../infra/compose/.env.example) is the one
documented template: every variable carries purpose, default and validation
note. Groups, as headed in the template (Section 9.10):

| Group | Key variables (defaults live in the template) |
|---|---|
| Compose images | `ORCHESTRATOR_IMAGE_POSTGRES`, `_REDIS`, `_BACKEND`, `_WEB`, `_CLOUDFLARED`, `_MAILHOG` — pinned tags, never `:latest` in prod |
| Published ports | `ORCHESTRATOR_BIND_ADDR`, `ORCHESTRATOR_PORT_BACKEND`, `ORCHESTRATOR_PORT_WEB` |
| Database and cache URLs | `ORCHESTRATOR_DATABASE_USER/PASSWORD/NAME/URL`, `ORCHESTRATOR_CACHE_URL`, `ORCHESTRATOR_CACHE_BROKER_URL`, `ORCHESTRATOR_CACHE_APPENDONLY` |
| Event publish / realtime | `ORCHESTRATOR_EVENTS_CHANNEL`, `ORCHESTRATOR_EVENTS_REDIS_URL`, `ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS` |
| Secret keys | `ORCHESTRATOR_SECRET_KEY` |
| Allowed hosts and CORS/CSRF origins | `ORCHESTRATOR_DEBUG`, `ORCHESTRATOR_ALLOWED_HOSTS`, `ORCHESTRATOR_CORS_ORIGINS`, `ORCHESTRATOR_CSRF_ORIGINS` |
| Structured logging | `ORCHESTRATOR_LOG_LEVEL` |
| Storage backend (Section 16.3) | `ORCHESTRATOR_STORAGE_BACKEND` (`local` default, `s3` reserved), `ORCHESTRATOR_STORAGE_MEDIA_ROOT` |
| Backup trigger (Section 9.9) | `ORCHESTRATOR_BACKUP_HOST_DIR`, `ORCHESTRATOR_BACKUP_ROOT`, `ORCHESTRATOR_BACKUP_TRIGGER_HOUR/MINUTE`, `ORCHESTRATOR_BACKUP_RETENTION_DAYS`, `ORCHESTRATOR_BACKUP_MIN_KEEP` |
| Attachment limits / pipeline / retrieval | `ORCHESTRATOR_ATTACHMENT_*` (Section 9.5 limits, pipeline budgets, untrusted banner) |
| Token lifetimes | `ORCHESTRATOR_TOKEN_LIFETIME_OWNER_SESSION_HOURS`, `_AGENT_HOURS`, `_DEVICE_DAYS` |
| Rate limits | `ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE`, `_DEVICE_PER_MINUTE` |
| Orchestrator API base URL | `ORCHESTRATOR_API_BASE_URL` (manifest binding; also the board's proxy target) |
| OCR engine | `ORCHESTRATOR_OCR_ENGINE`, `ORCHESTRATOR_OCR_TESSERACT_CMD` |
| Description provider | `ORCHESTRATOR_DESCRIPTION_PROVIDER`, `ORCHESTRATOR_DESCRIPTION_REMOTE_*` |
| FCM credentials / push dispatch | `ORCHESTRATOR_PUSH_ENABLED` (default `false`) and the FCM credential variables — **shape only**: real credentials live only in `.env` (Section 16.2) |
| Cloudflare tunnel | `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` (secret), `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` |
| Feature flags | `ORCHESTRATOR_FEATURE_FLAGS` |

Rules (template header + [`configuration.md`](plan/conventions/configuration.md)
+ `backend/apps/core/settings/prod.py`):

* **Required in prod** — `ORCHESTRATOR_DATABASE_PASSWORD`,
  `ORCHESTRATOR_DATABASE_URL`, `ORCHESTRATOR_SECRET_KEY`,
  `ORCHESTRATOR_ALLOWED_HOSTS`, `ORCHESTRATOR_DEBUG=false`,
  `ORCHESTRATOR_BIND_ADDR`, and `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` once a
  named tunnel exists. Startup validation **refuses to boot** on missing,
  placeholder or weak values — errors name the variable, never the value.
  Dev may run on template placeholders (Compose fallbacks) so the skeleton
  stays one-command startable.
* **Naming** — every variable is `ORCHESTRATOR_<SETTING>`, one name, no
  aliases; the only non-canonical spellings are third-party container
  interfaces mapped from canonical values (configuration.md rule 7), e.g. the
  Postgres image's `POSTGRES_*` and the dev overlay's `NODE_ENV`.
* **Never commit real values** — `infra/compose/.env` is git-ignored; the
  committed template holds placeholders only (Section 20.4 item 3).

## 4. Profiles (`dev` / `prod`)

Pick **one** per invocation (base file always; the dev overlay is always
paired with `--profile dev`):

| Concern | `dev` | `prod` |
|---|---|---|
| Invocation | base + `compose.dev.yaml` + `--profile dev` (the [bring-up](#2-bring-up-from-a-fresh-clone) path) | base only + `--profile prod` |
| Helper services | `mailhog` (SMTP catcher, no host port) | none |
| `cloudflared` tunnel | off by default; opt in with an extra `--profile tunnel` | on — fails fast without `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` |
| Hot reload / debug | hot-reload bind mounts, debug flags | pinned images, no debug |
| Settings module | dev settings selected by the overlay | prod settings with fail-fast validation |

Validate a render without starting anything:
`docker compose -f infra/compose/compose.yaml --profile dev config`.

## 5. Health verification (Section 16.1)

After `up --wait`:

1. **Per service** — `docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml ps`
   must show `postgres` (readiness probe), `redis` (ping), `backend`
   (`GET /health/ready`), `worker` (worker-ping), `beat` (process check),
   `web` (HTTP check), `migrate` `exited (0)`; in a tunnel run, `cloudflared`
   (`tunnel ready`). The exact probe commands are tabulated in
   [`infra/compose/README.md`](../infra/compose/README.md) → "Health checks".
2. **Backend endpoints** — `/health/live` (process serving; no dependency
   checks) and `/health/ready` (database `SELECT 1` + cache write; 503 error
   envelope otherwise). Probe them from the host at
   `http://<ORCHESTRATOR_BIND_ADDR>:<ORCHESTRATOR_PORT_BACKEND>/health/live`
   and `/health/ready`, or from inside the stack (works regardless of bind
   address):

   ```powershell
   docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=2).read().decode())"
   ```

   Expected: `{"status":"ready","checks":{"database":"ok","cache":"ok"}}`
   (live answers `{"status":"live"}` on `/health/live`).
3. **Worker and beat** — logs and direct worker-ping:
   [`infra/compose/README.md`](../infra/compose/README.md) → "Verifying worker
   and beat".

## 6. Tear-down and data preservation

```powershell
# Safe default — stops the stack, KEEPS postgres_data, redis_data, backend_media:
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev down

# Full wipe — DESTROYS all of the above (never routine):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml --profile dev down -v
```

Pass the **same profile** you started with: without it, Compose exits 0 but
leaves profile-gated services (e.g. the dev `mailhog` helper) running —
verified against this repo's Compose files. Plain `down` preserves data — the
marker-row survival proof is documented in
[`infra/compose/README.md`](../infra/compose/README.md) → "Restart procedure
and data-survival check". Use `down -v` only for a deliberate wipe (if you
wipe, restore afterwards from the second location — see below).

## 7. Upgrade and rollback (Section 16.5)

This is WP-6.5's named "upgrade and rollback guide" deliverable. One flow,
executed in order (dev-profile form shown; the prod form is the same steps on
the base file with `--profile prod`):

```powershell
# 0. Take a fresh backup first (the rollback path if a migration misbehaves):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml exec worker celery -A config.celery call backup.run_daily_backup

# 1. Pull the new pinned base images (bump the ORCHESTRATOR_IMAGE_* tags in
#    infra/compose/.env first — pinned tags are the upgrade mechanism):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml pull postgres redis

# 2. Rebuild images built from this repo (backend family):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml build backend worker beat

# 3. Run migrations (the one-shot migrate service; it also runs automatically
#    as the gate before backend on every `up`):
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml run --rm migrate

# 4. Restart the stack on the new images and wait for health:
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml -f infra/compose/compose.dev.yaml --profile dev up -d --wait --wait-timeout 180
```

**API version compatibility.** The API changes backward-compatibly within
`/v1` (Section 16.5). The bridge and clients check an API version header and
warn on mismatch: the header is `X-API-Version`, expected major `1`
(`bridge/src/orchestrator_bridge/transport.py`, Section 10.11) — a mismatched
or unparseable advertised version aborts bridge startup with an actionable
error; a backend that advertises nothing is accepted with an
`api_version_unverified` warning, not a mismatch.

**Rollback.**

1. Set the `ORCHESTRATOR_IMAGE_*` variables in `infra/compose/.env` back to
   the **previous pinned tags** (previous image tags are retained by the
   registry/local daemon — Section 16.5) and re-run step 4.
2. Database migrations are written to be reversible where practical
   (Section 16.5). If the rolled-back application version cannot run on the
   current schema, restore the pre-upgrade dump from step 0 — the restore
   procedure is
   [`docs/runbooks/restore-from-backup.md`](runbooks/restore-from-backup.md)
   (drill-derived, rehearsed — the weekly drill is required by Section 16.5
   and recorded in [`infra/backup/README.md`](../infra/backup/README.md)).

## 8. Backups and restore (pointer)

Do not duplicate the backup docs — they are the procedure:

* Schedule, retention, second location, manual invocation:
  [`infra/backup/README.md`](../infra/backup/README.md).
* Restore procedure: [`docs/runbooks/restore-from-backup.md`](runbooks/restore-from-backup.md);
  drill runner `e2e/restore_drill.py`; drill records under
  [`docs/plan/`](plan/) (`wp-6.2-restore-drill-*.md`).
* Retention decision: [`docs/plan/wp-6.2-backup-retention-decision.md`](plan/wp-6.2-backup-retention-decision.md).
  Any change to the retention step requires re-running the restore drill.

## 9. Remote access and the VPS checklist (Section 16.4 / NFR-06 / GOAL-5)

The edge is the Cloudflare tunnel only — never publish ports to `0.0.0.0` on
an internet-facing VPS; `ORCHESTRATOR_BIND_ADDR` stays the LAN interface
(Section 16.1 posture). Tunnel provisioning, ingress and verification:
[`infra/cloudflare/README.md`](../infra/cloudflare/README.md).

Section 16.4's migration checklist, summarized (the plan is authoritative):

1. Provision the host, install the container runtime, copy the environment
   file with changed hostnames and storage settings.
2. Restore the latest database dump and media backup.
3. Start the stack; run the readiness checks ([§5](#5-health-verification-section-161)).
4. Point the tunnel at the new host (or move the connector); update
   `orchestrator_api` in manifests (or rely on the tunnel hostname).
5. Reissue agent tokens if the secret key changed; update bridge configs.
6. Verify with the smoke test suite (parent plan Section 18).

Because the backend never touches repositories (P2, ADR-007), nothing in the
stack depends on any workstation's file system.

## 10. Mobile distribution (pointer)

The written v1 distribution path — who gets which build, install, updates —
is [`mobile/docs/distribution.md`](../mobile/docs/distribution.md)
(MT-5.10-04's link target for this guide), with siblings
[`release-signing.md`](../mobile/docs/release-signing.md),
[`release-build.md`](../mobile/docs/release-build.md) and
[`release-checklist.md`](../mobile/docs/release-checklist.md). Android internal
sideload is the standing path; iOS/TestFlight and checklist execution remain
the Deferred entries cited at the top of this guide.

## Running the operations board

The board is the Next.js app in `web/`, an API-only client of the backend:

```powershell
npm ci --prefix web              # once, from the repository root
npm --prefix web run dev         # dev server — commands table: web/README.md
```

Configuration: `ORCHESTRATOR_API_BASE_URL` (default
`http://localhost:8000/api/v1`) is what `next.config.ts` proxies `/api/v1/*`
to server-side — the browser only talks to the board's own origin (same-origin
cookies/CSRF, Section 12.2); see [`web/README.md`](../web/README.md).

The Compose `web` service currently serves only the health-check placeholder
and binds `ORCHESTRATOR_PORT_WEB` when the stack is up — stop it before
starting the board on the same port:

```powershell
docker compose --env-file infra/compose/.env -f infra/compose/compose.yaml stop web
```

## Next steps

* **Onboard a repo** — project registration procedure:
  [`docs/runbooks/add-a-project.md`](runbooks/add-a-project.md) (content lands
  with MT-6.5-03); manifest schema
  [`schemas/manifest.v1.json`](../schemas/manifest.v1.json), binding rules in
  parent plan Section 10.3.
* **Connect an agent** — per-client guides:
  [`docs/agent-guides/`](agent-guides/README.md) (MT-6.5-02, deferred on the
  client-verification entries cited at the top; the index and compatibility
  matrix are live).
* **Operations procedures** — [`docs/runbooks/`](runbooks/README.md)
  (stuck lease, failed merge, tunnel down, restore, rotate tokens, add a
  project, onboard an agent client; content: MT-6.5-03).
* **Troubleshooting decision trees** — MT-6.5-04
  ([plan doc](../plan-doc-series/m6-hardening-release/wp-6.5-documentation/MT-6.5-04-troubleshooting-guide.md),
  deferred on MT-6.5-02/03).
