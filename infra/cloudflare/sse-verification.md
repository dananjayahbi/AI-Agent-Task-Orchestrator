# SSE stability through the tunnel — verification notes (MT-5.1-04)

| Field | Value |
|---|---|
| Status | **Partially verified** — LAN control run recorded below; through-tunnel run **operator-pending** (OQ-11) |
| Recorded | 2026-10-13 |
| Owner | WP-5.1 — `cloudflared` service and tunnel ingress |
| Requirements | FR-NET-01, FR-NET-02, NFR-03, NFR-04, ADR-002 (Sections 9.6, 15.4) |
| Test client | [`e2e/sse_tunnel_stability.py`](../../e2e/sse_tunnel_stability.py) (stdlib-only Python; no dependencies) |

## What is verified, and where

Section 15.4 requires the 30-minute idle proof that the 15 s heartbeat keeps
Cloudflare's edge (and any proxy in between) from dropping or buffering
`GET /api/v1/events/stream` (RISK-05). The Cloudflare edge is only involved
when a real tunnel hostname exists, so the verification splits:

| Half | Path | Status |
|---|---|---|
| **LAN control run** | direct to the Compose backend (`ORCHESTRATOR_PORT_BACKEND`, no tunnel, no Cloudflare) | **done — results below** |
| **Through the tunnel** | `https://<ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME>` via the Cloudflare edge, `cloudflared` connector, ingress rule 1 | **operator-pending** — requires the provisioned hostname/token (OQ-11, MT-5.1-03 §2). Invocation documented below; results to be appended here on the first run. |

The same client runs both halves unchanged — only `--base-url` differs — so
the tunnel run adds the edge to a path whose backend behavior is already
proven, rather than testing something new end to end.

## The test client — `e2e/sse_tunnel_stability.py`

Stdlib only (`http.client`, `urllib`, `json`), owner-session bearer auth
(Section 15.4 token transport), credentials from the `SSE_SOAK_USERNAME` /
`SSE_SOAK_PASSWORD` environment variables. One *cycle* does what
MT-5.1-04's scope spells out:

1. **Idle soak** — open `GET /api/v1/events/stream` (no filters), stay idle
   for `--idle-seconds`, and assert:
   * zero unplanned disconnects (EOF or socket starvation before the planned
     close fails the run — nothing is silently retried);
   * at least `idle/heartbeat - 1` heartbeat comments observed;
   * max inter-frame gap ≤ `heartbeat × --gap-factor` (default 2 = 30 s).
2. **No-buffering probe** — `--probe-lead-seconds` before the window ends,
   publish one real event (`POST /projects` → `project.created`, the
   production fan-out path — no test hooks) and assert it arrives on the
   still-open stream within the NFR-03 budget (default 2 s). A held frame is
   the buffering artifact Section 15.4 exists to catch.
3. **Deliberate drop + lossless resume** — close the connection, publish
   `MISSED_EVENTS_PER_CYCLE = 2` more events, reconnect with
   `Last-Event-ID`, and assert the replay equals the stored history exactly
   (no gaps, no duplicates — Section 9.6), then publish one more event and
   assert the *same* connection delivers it live (handover works).
4. Repeat the whole cycle (`--cycles`, minimum enforced: 2 — stability, not
   a one-off).

Output: a JSON results document (`--output`) with timestamps, heartbeat
counts, max gap, disconnect count, probe latency, and the replay id sets —
the evidence recorded below.

### Duration policy (CI vs acceptance)

The client asserts the *same* properties at any duration; it never
shortens the acceptance bar itself:

* **Acceptance run (30 min idle, per plan):**
  `--idle-seconds 1800 --cycles 2` → ~65 min. Runs **on demand/nightly**,
  not on every PR (Section 20.4 item 2 — CI stays green; the soak is far
  too long for a per-PR gate and the Cloudflare edge is outside CI's
  control anyway). Invocation below.
* **CI / local control run (reduced):** `--idle-seconds 150 --cycles 2`
  (~6 min) — 10 heartbeat intervals per cycle: enough to measure cadence,
  gaps, buffering and resume. This is what the recorded LAN run used.

## LAN control run — 2026-10-13

| Field | Value |
|---|---|
| Environment | Windows 11 host, Docker Compose v5.4.0, `dev` profile (`compose.yaml` + `compose.dev.yaml`, `--env-file .env.example`) |
| Path under test | `http://127.0.0.1:8010` → published backend port (`ORCHESTRATOR_PORT_BACKEND=8010`; alternate port because concurrent agents hold 8000 — absorbed by the environment, no file change) |
| Backend image | `orchestrator-backend:dev`, **rebuilt** from the current tree (the cached pre-WP-1.7 image lacked celery in its venv and refused to boot — rebuild, not a code change) |
| Heartbeat setting | `ORCHESTRATOR_EVENTS_HEARTBEAT_SECONDS=15` (template default) |
| Command | `python e2e/sse_tunnel_stability.py --base-url http://127.0.0.1:8010 --idle-seconds 150 --cycles 2 --label lan-control --output e2e/sse_lan_control_results.json` |
| Result | **PASS** — all assertions in both cycles; zero unplanned disconnects |
| Evidence | [`e2e/sse_lan_control_results.json`](../../e2e/sse_lan_control_results.json) (full JSON results document) |

| Cycle | Heartbeats (≥9 expected) | Max gap (≤30 s) | Probe latency (≤2 s) | Resume replay | Live after resume |
|---|---|---|---|---|---|
| 1 | 10 | 15.00 s | 0.077 s | expected `[2,3]`, delivered `[2,3,4]` — exact, no gaps/dupes | event 4, 0.062 s |
| 2 | 10 | 15.00 s | 0.059 s | expected `[6,7]`, delivered `[6,7,8]` — exact, no gaps/dupes | event 8, 0.076 s |

(The JSON results document carries the verbatim timestamps, per-event ids
and latencies; both cycles: `unplanned_disconnects: 0`, `pass: true`.)

Observations recorded along the way (not acceptance failures, but worth
knowing for the tunnel run and later WPs):

* **`Accept: text/event-stream` answers 406** (`VALIDATION_ERROR` — DRF
  content negotiation has only JSON renderers registered; the stream view
  sets `content_type` on the response itself). The backend's own tests and
  the web fetch-based SSE client open the stream with a normal `*/*`
  Accept, so no product client is affected; a native browser `EventSource`
  or a naive scripted client that sends the strict header would be. The
  soak client therefore opens the stream with `Accept: */*` (the transport
  the plan's clients actually use). If a future client (e.g. mobile, WP-5.5)
  needs the strict header accepted, that is a backend contract change —
  raised here rather than silently worked around.
* Owner-session bearer auth on `/api/v1/projects` and the stream requires
  no CSRF handling (token transport, Section 15.4), so the client stays
  dependency-free.

## Through the tunnel — operator procedure (pending OQ-11)

Prerequisite: the named tunnel is provisioned and running (MT-5.1-01/03),
`ORCHESTRATOR_CLOUDFLARE_TUNNEL_TOKEN` and
`ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` are set in the git-ignored
`infra/compose/.env`, and the edge public-hostname routes mirror
[`ingress.yaml`](./ingress.yaml) (README §2 step 4).

1. Bring the stack up with the tunnel (`prod` invocation, or
   `--profile dev --profile tunnel` — see
   [`../compose/README.md`](../compose/README.md) "Tunnel service (WP-5.1)").
2. Confirm the edge serves the API path before the soak (the tunnel carries
   everything; a quick `curl https://<hostname>/api/v1/schema/...` or the
   board loading proves reachability):

   ```powershell
   $env:SSE_SOAK_USERNAME = "<owner username>"
   $env:SSE_SOAK_PASSWORD = "<owner password>"   # or a device token setup per §15.4
   python e2e/sse_tunnel_stability.py `
     --base-url "https://$env:ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME" `
     --idle-seconds 1800 --cycles 2 --label tunnel `
     --output infra/cloudflare/sse-tunnel-results.json
   ```

3. Re-run once for stability (MT scope: "repeat at least once" — the
   `--cycles 2` default already does this within one invocation; a second
   invocation on a different day/edge conditions is the "not a one-off"
   record).
4. Append the results (date, edge conditions, heartbeat/gap/latency
   numbers, any disconnects) to this document, and update the status row
   at the top and the WP changelog. If any assertion fails, capture the
   client output plus `docker compose logs cloudflared` and raise it
   against MT-5.1-02's ingress or an OQ — **do not** shorten
   `--idle-seconds` to make it pass (MT risk note).

Notes for the operator:

* The Cloudflare Free plan's idle timeouts are exactly what this run
  measures; the 15 s heartbeat is designed to stay inside them (Section
  15.4). If the tunnel run drops where the LAN run did not, the evidence
  decides between heartbeat interval, edge limits and ingress buffering —
  never the acceptance bar.
* The owner session lives 12 h by default (Section 9.10), so it cannot
  expire inside a 30-minute window and masquerade as a tunnel drop (MT
  risk note). The client records `session_expires_at` in the results to
  make this auditable.
* Edge Access policy interaction is WP-5.2 (out of scope here); run this
  soak *before* enabling Access, or use a service token that Access
  allows through.
* `X-Accel-Buffering: no` and `Cache-Control: no-cache` are set by the
  stream view (WP-1.10); the soak's probe latency is the end-to-end proof
  that no hop honors/ignores them in a harmful way.

## Acceptance criteria (MT-5.1-04)

| # | Criterion | Status |
|---|---|---|
| 1 | SSE connection stays connected ≥ 30 min idle with 15 s heartbeats, zero disconnects | **Local (reduced):** verified at 150 s × 2 cycles (LAN). **Full 30 min + tunnel edge:** operator-pending |
| 2 | Published event delivered without buffering artifacts | **Local:** verified (probe latency recorded, within NFR-03). **Tunnel:** operator-pending |
| 3 | Reconnect with last event id: no gaps, no duplicates | **Local:** verified (exact replay match, both cycles). **Tunnel:** operator-pending |
| 4 | Uses the tunnel hostname end-to-end, no inbound ports; LAN control documented | Script and procedure ready; LAN control documented above; **tunnel run operator-pending** (FR-NET-01 is structurally verified — the connector publishes no ports — but the end-to-end hostname run needs OQ-11) |
| 5 | Verification notes with evidence committed; changelog note added | **Done** (this document + WP changelog) |
| 6 | CI remains green — 30-min test on demand/nightly, not every PR | **Done** (documented invocation and duration policy above; no CI workflow was added, so no CI surface changed) |
