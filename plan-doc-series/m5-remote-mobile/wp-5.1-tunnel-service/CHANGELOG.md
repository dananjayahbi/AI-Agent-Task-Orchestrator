# WP-5.1 — `cloudflared` service and tunnel ingress: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-5.1-01** — The `cloudflared` service in `infra/compose/compose.yaml` is
  now the real named tunnel: official image, pinned tag
  (`cloudflare/cloudflared:2026.10.0`, `ORCHESTRATOR_IMAGE_CLOUDFLARED`
  override, never `latest`), started from the environment — Compose maps the
  canonical `ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` to cloudflared's
  image-mandated `TUNNEL_TOKEN` (configuration.md rule 7; the template keeps
  the canonical name with an empty default, row untouched, plan 20.4 item 3).
  The M0 quick-tunnel placeholder command is removed. **Decision (per the
  MT-5.1-01 scope):** `profiles: [prod, tunnel]` — `--profile prod` keeps the
  Section 16.1 eight and fail-fasts without a token; `--profile dev` runs the
  stack **without** the tunnel (the documented "service disabled via
  profile" behavior); `--profile dev --profile tunnel` opts a dev stack into
  the tunnel. Zero published ports and the `depends_on` edges to `backend`/
  `web` are preserved; the health check remains cloudflared's own
  `tunnel ready` status probe (Section 16.1). Fail-fast verified live on this
  host: empty token → `docker compose --profile prod run --no-deps
  cloudflared` exits 255 immediately; a deliberately invalid token against the
  official image exits 255 with "Provided Tunnel token is not valid."
  Render checks: `docker compose ... config` exits 0 for `dev`,
  `prod`, `dev+tunnel` and `dev`+`compose.dev.yaml` — cloudflared present
  only in the latter two, and the only published ports in any render are
  `backend`/`web` (LAN-bounded, FR-NET-01). Documented dev bring-up
  (base + dev overlay + `--profile dev`) ran `up -d --wait` → exit 0, every
  started service healthy, no cloudflared container, then plain `down`
  (volumes kept); it used alternate host ports because concurrent agents hold
  127.0.0.1:8000/:3000 locally — `ORCHESTRATOR_PORT_*` absorbed it (no file
  change). New environment-template row (genuinely new setting, pattern
  followed): `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` (empty default, OQ-11
  `orchestrator.<owner-domain>` convention) in `infra/compose/.env.example`,
  with full metadata rows for both tunnel variables, the extended
  `CLOUDFLARE_TUNNEL_` group row and the `TUNNEL_TOKEN` rule-7 sentence added
  to `docs/plan/conventions/configuration.md`. `infra/compose/README.md`
  gained the "Tunnel service (WP-5.1)" section (bring-up, fail-fast, token
  provisioning pointer to `infra/cloudflare/README.md`) and updated
  profile/validation documentation.
- **MT-5.1-02** — Ingress mapping authored at
  `infra/cloudflare/ingress.yaml` and mounted read-only into the service at
  `/etc/cloudflared/config.yaml` (referenced in `docker compose config`):
  rule 1 — tunnel hostname + path `^/api/` → `http://backend:8000`
  (internal service name only, no published ports; the SSE events stream
  `/api/v1/events/stream` rides it with no buffering directives anywhere and
  the 15 s heartbeat per Section 15.4/9.6 — live proof is MT-5.1-04);
  rule 2 — default route for the tunnel hostname → `http://web:3000`;
  rule 3 — documented catch-all → `http_status:404` (no silent fallback).
  The Section 15.2 route groups are recorded line for line next to the rules
  with exposed / "Yes (Could)" / LAN-only / service-token-only / internal-only
  markers, task-create kept disabled pending OQ-12/WP-5.2, and enforcement
  explicitly deferred to WP-5.2. **Mode confirmation (MT-5.1-01 risk note):**
  a token run is a *remotely-managed* tunnel — cloudflared fetches ingress
  from the edge and ignores local `ingress:` (cloudflare/cloudflared#633) —
  so the file is the canonical, validated rule set that
  `infra/cloudflare/README.md` §2 mirrors rule-for-rule to the edge; the
  hostname stays environment-only (placeholder notation in the file, real
  value in `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` — no
  environment-specific hostname committed, plan 20.4 item 3). Verification
  with the official image: `cloudflared tunnel ingress validate` → OK
  (exit 0); `tunnel ingress rule` matched `/api/v1/events/stream` → backend
  rule, `/board` → web rule, another hostname → `http_status:404` catch-all;
  all four compose renders exit 0 with the ingress mount visible.
- **MT-5.1-03** — Tunnel operations document created at
  `infra/cloudflare/README.md`: both hostnames (LAN address vs tunnel
  hostname) with the OQ-11 `orchestrator.<owner-domain>` convention and
  Section 15.1 citation; dashboard-driven hostname/DNS/route procedure that
  mirrors the ingress file; token handling per Sections 15.4/16.2
  (environment-only secret, empty template default, real value in the
  git-ignored `.env`, rotation via the Cloudflare dashboard — the
  old/new-token overlap guarantee is deliberately recorded as
  "observe and record at first rotation", not invented); the two trusted
  origins (LAN + tunnel) for the CORS/CSRF lists plus the mobile
  token-auth/no-cookie rule and the explicit "edge is layer 1 only, Django
  tokens always required" caveat (Section 15.3); the failure mode point for
  point (LAN continues, agents continue, mobile "unreachable", FCM push
  outbound-only) cross-linked to the `docs/runbooks/tunnel-down.md` stub
  (WP-6.5); and the Section 16.4 step-4 VPS pointer for GOAL-5. Supporting:
  `infra/cloudflare/.gitignore` keeps any credentials JSON/env file out of
  Git (MT-5.1-01 risk note), and `infra/compose/README.md` links to the
  document. Review checks: greps inside `infra/cloudflare/` find the token
  variable, both hostnames, `rotate`, `CORS`, `unreachable` and the 16.4
  pointer; `git grep --no-index -iE "(tunnel|cf)_token.*[A-Za-z0-9]{20,}"`
  over `infra/cloudflare` + `infra/compose` returns no match (no secret or
  environment-specific value committed).
- **MT-5.1-04 — deferred:** Dependencies (WP-1.9 events, WP-1.10 SSE stream endpoint) not yet met — deferred until WP-1.9/1.10 per roadmap.md §4a (recorded 2026-10-12).
