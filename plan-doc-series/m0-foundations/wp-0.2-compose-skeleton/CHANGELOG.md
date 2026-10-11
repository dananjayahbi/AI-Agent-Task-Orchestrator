# WP-0.2 — Compose skeleton and environment template: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-0.2-01** — `infra/compose/compose.yaml` defines all eight Section 16.1
  services (`postgres`, `redis`, `migrate`, `backend`, `worker`, `beat`, `web`,
  `cloudflared`) with the exact dependency edges from the 16.1 table
  (`migrate`→`postgres`; `backend`→`postgres`, `redis`, `migrate`;
  `worker`→`postgres`, `redis`; `beat`→`redis`; `web`→`backend`;
  `cloudflared`→`backend`, `web`) and the 16.1/16.3 volumes (`postgres_data`,
  `redis_data` with `REDIS_APPENDONLY`-toggled persistence, `backend_media`
  shared by `backend`/`worker` at `/media` — the `MEDIA_ROOT` contract for
  WP-1.1). Only `backend` and `web` publish ports (bind behavior arrives with
  MT-0.2-02). Placeholder images for `backend`/`web` are local stub builds
  (`infra/compose/stubs/`): one Python stub image serving the four
  backend-image roles (`serve`/`worker`/`beat`/`migrate`, `/health/ready`
  answered with HTTP 200) and an nginx stub on port 3000 — service names,
  ports and the `/health/ready` path are the stable contract WP-1.1/WP-4.1
  replace behind. `cloudflared` uses a tokenless quick-tunnel placeholder
  command (named-tunnel token wiring is WP-5.1). `docker compose -f
  infra/compose/compose.yaml config` renders all eight services with the
  correct edges and volumes; decisions: official images pinned to major tags
  (`postgres:16-alpine`, `redis:7.4-alpine`, `cloudflared:2026.10.0`), images
  all overridable by environment (NFR-06). `infra/compose/README.md` created
  with the service topology, copy-and-edit bring-up and the safe tear-down
  (`down` keeps volumes; `down -v` destroys them). Placeholder `.gitkeep`
  removed from `infra/compose/`.
- **MT-0.2-02** — Networking and profiles added. Exactly one network
  (`internal`, plain bridge) is declared; every service — including the
  dev-only `mailhog` helper — joins it and no other network exists in either
  profile render. Published ports remain limited to `backend` and `web`, now
  bound through `${ORCHESTRATOR_BIND_ADDR:-127.0.0.1}` (plus
  `BACKEND_PORT`/`WEB_PORT`), so the bind address is environment-driven per
  NFR-06; `.env.example` (MT-0.2-03) documents setting it to the host's LAN
  interface IP as the plan default posture. Profiles: `dev` gates the
  `mailhog` helper service inside `compose.yaml` and pairs with the new
  `infra/compose/compose.dev.yaml` overlay, which carries the hot-reload bind
  mounts (`../../backend` and `../../web` at `/app`) and debug flags for
  `backend`/`web`; `prod` runs the base file only — pinned images, no debug,
  no bind mounts (risk note verified: prod render contains no bind-mount dev
  wiring). Decision recorded: Compose cannot vary a single service's config
  from the `--profile` flag alone (one service = one definition), so
  profile-gated helpers live in `compose.yaml` while hot-reload/debug wiring
  lives in the always-paired dev overlay file; both `--profile dev config`
  and `--profile prod config` validate and render the single network with
  ports only on `backend`/`web`. README gained the networking/ports and
  profile-selection documentation.
- **MT-0.2-03** — Environment template created at
  `infra/compose/.env.example`: every 9.10 configuration group either consumed
  by the M0 stack (images, LAN bind address and ports, database/cache URLs,
  secret key, allowed hosts, storage/local media, tunnel token) or present as
  an explicitly marked reserved placeholder (S3 credentials, token lifetimes,
  rate limits, OCR engine, description provider, FCM, feature flags, CORS/CSRF
  origins pending WP-1.1). Each variable carries purpose, default and
  validation note; required-in-prod values are listed in the header together
  with the Section 16.2 weak/missing-secret refusal rule (backend enforces in
  WP-1.1). Decisions: `DJANGO_DEBUG` defaults to `false` (prod posture, dev
  overlay flips it); description provider default `disabled` per the OQ-07
  recommendation (decision itself deferred to M1); token-lifetime and
  rate-limit numbers deliberately NOT invented — flagged for WP-1.2 (plan
  20.1 principle 5). Verification: `docker compose -f
  infra/compose/compose.yaml --env-file infra/compose/.env.example config`
  renders clean; `git check-ignore infra/compose/.env` reports the real file
  ignored while `.env.example` stays trackable (root `.gitignore` already had
  the `.env` / `!.env.example` rules — no change needed, verified only).
  README gained the copy-and-edit steps and the validation-notes section.
- **MT-0.2-04** — Health checks added for all eight Section 16.1 services:
  `postgres` (`pg_isready` readiness), `redis` (`redis-cli ping`), `migrate`
  (exit code — expressed as the `service_completed_successfully` condition on
  its dependents, no probe block), `backend` (`GET /health/ready` — stub
  answers 200, WP-1.1 implements the real endpoint on the same path),
  `worker` (ping on `:8001`; WP-1.7 swaps in `celery inspect ping`), `beat`
  (process check), `web` (HTTP check on `:3000`), `cloudflared`
  (`cloudflared tunnel ready` against a fixed `--metrics 0.0.0.0:20240`
  address — discovered during the live proof: the bare `tunnel ready` probe
  fails with "‑-metrics has to be provided", so both the daemon command and
  the probe now pin the metrics port; image is distroless, exec form only).
  The dev-only `mailhog` helper got an SMTP listener check so `--wait` covers
  it too. All `depends_on` edges upgraded from `service_started` to
  `service_healthy` (kept exact edges), and the `cloudflared` placeholder
  command was fixed to place global flags before the `tunnel` subcommand.
  **Runtime proof executed on this host (Docker Desktop engine 29.7.2 /
  Compose v5.4.0):** the documented one-command dev bring-up
  (`up -d --wait --wait-timeout 180`) exited 0 with all eight services plus
  `mailhog` healthy; `restart` returned everything green in ~10–30 s; a
  marker row inserted into `wp02_marker` (Postgres named volume) survived
  both `restart` and a full `down` → `up` cycle; ports observed bound to
  `127.0.0.1` only on `backend`/`web` (LAN bind driven by
  `ORCHESTRATOR_BIND_ADDR` in the local `.env`). README gained the
  one-command bring-up with the documented startup window, the health-check
  table, the restart procedure, and the data-survival check (SQL fed over
  stdin to avoid shell-quoting pitfalls; safe tear-down vs `down -v`
  restated).
