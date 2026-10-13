# Blocked-vs-allowed route verification checklist — WP-5.2 (MT-5.2-04)

| Field | Value |
|---|---|
| Status | **Local half recorded (ingress structural proof + LAN vantage run, §5); public-hostname run operator-pending (OQ-11)** |
| Recorded | 2026-10-13 |
| Owner | WP-5.2 — Edge policies and route allowlist (MT-5.2-04) |
| Requirements | FR-NET-01, FR-SEC-05; Sections 15.2, 15.3, 18, 19.1 (WP-5.2 acceptance), 20.4 item 1 |
| Test client | [`e2e/route_verify.py`](../../e2e/route_verify.py) (stdlib-only Python) + this document's matrix |
| Drift detector for | [`access-policy.md`](./access-policy.md), [`route-allowlist.md`](./route-allowlist.md), [`rate-limits.md`](./rate-limits.md), [`ingress.yaml`](./ingress.yaml) |

## 0. Environment assumptions (read first — MT-5.2-04 risk note)

* **LAN vantage** = a direct request to the Compose backend on the host's
  LAN address (`ORCHESTRATOR_BIND_ADDR`:`ORCHESTRATOR_PORT_BACKEND`) —
  **no Cloudflare in the path at all** (Section 15.1). Any HTTP answer from
  the application (2xx/4xx envelope or Django page) counts as
  *reachable*; only a connection failure fails the LAN half.
* **Public vantage** = `https://<ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME>`
  through the Cloudflare edge: Access gate `A1` → route rules → (for
  allowed paths) the origin. The concrete hostname never appears here
  (Section 20.4 item 3).
* **Same backend behind both** is assumed: if a deployment ever put edge
  config in front of the LAN path too, the LAN expectations below diverge
  and the run must record that environment instead of this one.
* **v1 posture** = `remote_agents_enabled: false`,
  `remote_merge_executor_enabled: false`, OQ-12 task create/publish **off**
  (see [`route-allowlist.md`](./route-allowlist.md) §2). A §5 flip changes
  the listed expectations — re-run after any flip (§5 rule).

## 1. How to run

```powershell
# 1) Local structural proof — no network, needs Docker (pinned cloudflared image):
python e2e/route_verify.py --ingress --output e2e/route_verification_results.json

# 2) LAN half — needs a reachable backend (e.g. dev-profile Compose stack):
python e2e/route_verify.py --lan-url http://127.0.0.1:<backend-port> --ingress `
    --output e2e/route_verification_results.json

# 3) Public half — operator, after applying access-policy.md §4 (apps A1-A10,
#    method rules W1-W4); service token optional but sharpens the checks:
#      $env:CF_ACCESS_CLIENT_ID = "<client id>"      # env only, never committed
#      $env:CF_ACCESS_CLIENT_SECRET = "<secret>"
python e2e/route_verify.py --lan-url http://127.0.0.1:<backend-port> `
    --public-url https://<ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME> `
    --output e2e/route_verification_results.json

# 4) API rate-limit probe on the LAN half (credential env, budget+1 requests):
#      $env:ROUTE_VERIFY_USERNAME = "..."   $env:ROUTE_VERIFY_PASSWORD = "..."
python e2e/route_verify.py --lan-url http://127.0.0.1:<backend-port> --rate-probe `
    --output e2e/route_verification_results.json
```

Exit code 0 = every *executed* check matched its expectation (skips are
recorded, not silently passed); 1 = at least one mismatch, details in the
JSON results document. Edge-threshold behavior (`R-EDGE`) is a
**manual operator check** — see §4; the script never hammers the public
hostname. The API-side proof that `RATE_LIMITED` survives the tunnel path
also runs in CI: `pytest backend/tests/test_rate_limits_tunnel.py -v`.

## 2. Expectation vocabulary (no blank cells)

| Value | Meaning |
|---|---|
| `app-response` | The **application** answered (envelope, status page or route 404). On the LAN that always passes; on the public vantage it means the request reached the origin (gate/rule not applied → a check failure when an edge answer was expected). |
| `app-response:RATE_LIMITED` | Application answered 429 with the canonical `RATE_LIMITED` envelope (Section 9.2 catalog). |
| `edge-gate` | The edge answered before origin because the caller has no Access credentials: 3xx to the Access start URL, **or** a 403 without a Django envelope. Either proves layer 1 fired. |
| `edge-block` | 403 from the edge with **no** Django envelope (deny application A2-A10, deny ingress rule, or method rule W1-W4). |
| `edge-rate-limit` | 429 from the edge with no Django envelope (Cloudflare counter). |
| `connection-error` | No HTTP answer — always a failure. |

A Django envelope is recognizable by the body's `error.code` /
`correlation_id` fields (Section 9.2); the script classifies on that,
never on status alone.

## 3. The matrix — every Section 15.2 row, both vantage points

Public columns: **no-cred** = plain request (the V1/V2 hooks);
**token** = with `CF-Access-Client-Id`/`-Secret` headers (V3/V4 — skipped
until the operator issues `<service-token>`). Full per-path detail is the
§6 machine block; expectations are grouped here by outcome class.

| Row (verbatim) | Paths (samples) | Public: no-cred | Public: token | LAN | Notes |
|---|---|---|---|---|---|
| **Auth, devices** — Yes | `/api/v1/auth/login` `POST`, `/auth/logout`, `/auth/refresh`; `/api/v1/devices` `POST`/`GET`, `/devices/1` `DELETE` | `edge-gate` | `app-response` (401 `AUTH_REQUIRED` without a Django credential — proves V3) | `app-response` | Edge rules E1/E2 apply here (§4) |
| **Projects (read), tasks (read), review, dashboard, events stream** — Yes | `GET /api/v1/projects`, `/projects/{pid}`, `/{pid}/manifest`, `/{pid}/tasks`, `/tasks/{id}`, `POST /tasks/{id}/review`, `GET /dashboard/summary`, `/events`, `/events/stream` | `edge-gate` | `app-response` | `app-response` | deferred routes answer LAN 404 — still `app-response`; SSE probe uses `Accept: */*` (strict header = 406, recorded WP-5.1) |
| *(same row — unnamed writes)* | `POST /api/v1/projects`, `PATCH /projects/{pid}`, `PATCH /tasks/{id}` | `edge-block` | `edge-block` | `app-response` | denied by method rules **W1/W2/W4** — a LAN `app-response` proves the LAN half unaffected |
| **Task create/publish** — Yes (Could) → OQ-12 | `POST /api/v1/projects/{pid}/tasks` (method rule **W3**), `POST /tasks/{id}/transition` (deny app A6) | `edge-block` | `edge-block` | `app-response` | OQ-12 default: blocked in v1, recorded not defaulted |
| **Agent token creation, policy editing, admin** — No (LAN only) | `POST/GET/DELETE /api/v1/tokens*`, `GET/PATCH /projects/{pid}/policy`, `/admin/` | `edge-block` | `edge-block` | `app-response` | **the Section 19 acceptance row** — denial public, success LAN |
| **Agent work endpoints (claim, checkpoints, submit)** — service token | work, claim, release, checkpoints, resolution(s), audit-verdict/reports, resolutions patch, agent-sessions (11 paths) | `edge-block` | `edge-block` | `app-response` | v1 conditional-deny; §5 flip changes public cols to `app-response`-behind-service-token |
| **Merge queue** — service token | `/api/v1/merge/pending`, `/{task}/start`, `/{task}/result` | `edge-block` | `edge-block` | `app-response` | same flip rule as above |
| **Health** — Internal only | `/health/live`, `/health/ready` | `edge-block` | `edge-block` | `app-response` (200 from the backend) | internal only: Compose probes never traverse the tunnel |
| *(unnamed default-deny)* | attachments (3 paths), `/api/v1/schema` | `edge-block` | `edge-block` | `app-response` | Section 15.2 names none of them → default deny (allowlist §6) |

Reading the acceptance (Section 19 WP-5.2): *"blocked routes return denial
from the public hostname and succeed on LAN"* = every `edge-block` public
cell **and** the matching `app-response` LAN cell of the same row must hold
in one recorded run.

## 4. Layer checks (Section 15.3 layers 1 and 4 exercised together)

| Hook | Request | Expected | Where defined |
|---|---|---|---|
| V1 | `GET /api/v1/projects`, public, no credentials | `edge-gate` | [`access-policy.md`](./access-policy.md) §5 |
| V2 | `GET /api/v1/tokens`, public, no credentials | `edge-block` | same |
| V3 | `GET /api/v1/projects` + service-token headers, no Django credential | `app-response` (401 `AUTH_REQUIRED` — edge identity is **not** authentication) | same |
| V4 | `GET /api/v1/tokens` + service-token headers | `edge-block` (Block beats credentials) | same |
| V5 | `GET /api/v1/tokens` on the **LAN** | `app-response` (no Access anywhere on this path) | same |
| INGRESS | every §6 sample against `ingress.yaml` via `cloudflared tunnel ingress validate` + `ingress rule` | first match equals the allowlist's `ingress` field (`deny-403` / `backend`) | [`route-allowlist.md`](./route-allowlist.md) §3; script `--ingress` |
| R-API | LAN rate probe: `device budget + 1` requests on `/api/v1/devices` with owner credentials | final answer `app-response:RATE_LIMITED` | [`rate-limits.md`](./rate-limits.md) §3; script `--rate-probe` |
| R-API-tunnel | *CI:* `pytest backend/tests/test_rate_limits_tunnel.py -v` | throttled request with tunnel headers → `RATE_LIMITED` envelope | rate-limits.md §1 |
| R-EDGE | *Manual operator:* controlled burst over E1's 30/min on `POST /api/v1/auth/login` from one address (≤ 40 requests, once, off-peak) **or** the dashboard rule's test action | `edge-rate-limit` (Cloudflare 429) then recovery next window | rate-limits.md §2/§5 — **not automated on purpose** |

## 5. Results template and recorded runs

Re-run after **any** change under `infra/cloudflare/` (allowlist rule,
Access application, threshold, ingress edit) and after any dashboard
change; append a dated block below (Section 20.4 item 1 — a skipped re-run
leaves WP-5.2 acceptance unverified):

```markdown
### Run <YYYY-MM-DD> — environment: <host/OS; compose profile; ports>
| Half | Status | Evidence |
|---|---|---|
| INGRESS structural | pass/fail/skip | results JSON + matched-rule table |
| LAN vantage | pass/fail | results JSON (counts), notes |
| Public vantage (no creds) | pass/fail/skip (pre-apply) | results JSON |
| Public vantage (service token) | pass/fail/skip (no token yet) | results JSON |
| R-API rate probe | pass/fail/skip (no creds) | results JSON |
| R-EDGE manual burst | pass/fail/skip | dashboard screenshot / note |
Notes / follow-ups: <...>
```

### Recorded run — 2026-10-13 (local half)

| Field | Value |
|---|---|
| Environment | Windows 11 host, Docker Desktop, Python 3.14 (stdlib), dev-profile Compose stack (project `wp52route`, own postgres/redis volumes) on `ORCHESTRATOR_BIND_ADDR=192.168.1.244:8030` — LAN IP and port absorbed from the environment: the committed template records `192.168.1.100`, no longer this host's address, and concurrent agents hold the default ports (no file change; documented here per WP-5.1's precedent). Backend bind-mount hot-reload ran the working tree; the image's venv needed the in-flight attachments deps (`pillow`, `pypdf`) installed into the container — environment setup, not a code change. |
| INGRESS structural | **PASS** — `cloudflared tunnel ingress validate` → OK; all 45 samples' first-match rule equals the allowlist `ingress` field (**26 × `http_status:403`**, **19 → `http://backend:8000`**); zero deny rules catch an allowed path |
| LAN vantage | **PASS** — all 49 probes answered by the application (`connection-error` count 0, `fail` count 0): every §6 sample reachable, including the LAN-only rows (R4), health (R7), the conditional rows (R5/R6) and the unnamed default-deny paths |
| Public vantage | **operator-pending (OQ-11)** — requires the provisioned hostname/token *and* the Access applications + method rules of [`access-policy.md`](./access-policy.md) §4; invocation in §1, results to be appended on the first run |
| R-API rate probe | **PASS** — 61 device posts against the configured budget 60 → final answer `app-response:RATE_LIMITED` (canonical envelope on the LAN path) |
| R-EDGE manual burst | operator-pending with the public run |

Totals for this run: **executed 96, pass 96, fail 0, skip 0 → PASS**
(evidence: [`e2e/route_verification_results.json`](../../e2e/route_verification_results.json)).

## 6. Machine-readable checklist

Canonical — `backend/tests/test_route_checklist_coverage.py` parses this
block (first JSON fence under this heading) and fails if any Section 15.2
row, vantage point or layer check disappears; `e2e/route_verify.py` executes
it. Keep it in sync with [`route-allowlist.md`](./route-allowlist.md) §7
(the test enforces the pairing).

```json
{
  "meta": {
    "plan_sections": ["15.2", "15.3", "18", "19.1", "20.4"],
    "v1_posture": {"remote_agents_enabled": false, "remote_merge_executor_enabled": false, "oq12_task_create_in_v1": false},
    "environment": {
      "lan": "direct to the Compose backend (ORCHESTRATOR_BIND_ADDR:ORCHESTRATOR_PORT_BACKEND) - no Cloudflare in path",
      "public": "https://<ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME> - Access gate A1 then route rules",
      "assumption": "both vantages reach the same backend; diverging deployments must re-record the environment (MT-5.2-04 risk note)"
    },
    "vocabulary": ["app-response", "app-response:RATE_LIMITED", "edge-gate", "edge-block", "edge-rate-limit", "connection-error"],
    "re_run": "re-run after any infra/cloudflare/ or dashboard change and append to section 5 (Section 20.4 item 1)",
    "script": "e2e/route_verify.py"
  },
  "rows": [
    {
      "id": "auth-devices",
      "plan_row": "Auth, devices",
      "checks": [
        {"sample": "/api/v1/auth/login", "methods": ["POST"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "edge rule E1; API leaves owner auth unthrottled by FR-SEC-05 scope"},
        {"sample": "/api/v1/auth/logout", "methods": ["POST"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/auth/refresh", "methods": ["POST"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/devices", "methods": ["POST"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "edge rule E2 + API device budget (dual layer)"},
        {"sample": "/api/v1/devices", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "implementation row beyond the 9.2 table"},
        {"sample": "/api/v1/devices/1", "methods": ["DELETE"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""}
      ]
    },
    {
      "id": "reads-review-dashboard-events",
      "plan_row": "Projects (read), tasks (read), review, dashboard, events stream",
      "checks": [
        {"sample": "/api/v1/projects", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "V1 hook path"},
        {"sample": "/api/v1/projects", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "method rule W1 - unnamed write, default deny"},
        {"sample": "/api/v1/projects/PID00007", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/projects/PID00007", "methods": ["PATCH"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "method rule W2"},
        {"sample": "/api/v1/projects/PID00007/manifest", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/projects/PID00007/tasks", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "read half of the path-shared create row"},
        {"sample": "/api/v1/tasks/PID00007-T004", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004", "methods": ["PATCH"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "method rule W4"},
        {"sample": "/api/v1/tasks/PID00007-T004/review", "methods": ["POST"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "route deferred - LAN may answer 404, still app-response"},
        {"sample": "/api/v1/dashboard/summary", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "route deferred - same"},
        {"sample": "/api/v1/events", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/events/stream", "methods": ["GET"], "public_no_credentials": "edge-gate", "public_with_service_token": "app-response", "lan": "app-response", "note": "SSE - probe with Accept: */* (strict header = 406, WP-5.1 record)"}
      ]
    },
    {
      "id": "task-create-publish",
      "plan_row": "Task create/publish",
      "checks": [
        {"sample": "/api/v1/projects/PID00007/tasks", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "OQ-12 - method rule W3; path-shared with the allowed GET"},
        {"sample": "/api/v1/tasks/PID00007-T004/transition", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "OQ-12 - deny application A6 / ingress 403"}
      ]
    },
    {
      "id": "tokens-policy-admin",
      "plan_row": "Agent token creation, policy editing, admin",
      "checks": [
        {"sample": "/api/v1/tokens/agent", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "V2/V4/V5 hook path; LAN success = Section 19 acceptance"},
        {"sample": "/api/v1/tokens", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tokens/42", "methods": ["DELETE"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/projects/PID00007/policy", "methods": ["GET", "PATCH"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "method-blind deny: the read rides the policy deny (allowlist section 6)"},
        {"sample": "/admin/", "methods": ["*"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "defensive - no admin surface registered; LAN 404 is still app-response"}
      ]
    },
    {
      "id": "agent-work",
      "plan_row": "Agent work endpoints (claim, checkpoints, submit)",
      "checks": [
        {"sample": "/api/v1/projects/PID00007/work", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "v1 conditional-deny; section 5 flip changes public cols to service-token app-response"},
        {"sample": "/api/v1/tasks/PID00007-T004/claim", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004/release", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004/checkpoints", "methods": ["POST", "GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004/resolution", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004/resolutions", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/resolutions/1/patch", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/tasks/PID00007-T004/audit-verdict", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "route deferred - LAN 404 possible, still app-response"},
        {"sample": "/api/v1/tasks/PID00007-T004/audit-reports", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "route deferred - same"},
        {"sample": "/api/v1/agent-sessions", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "bridge VPS scenario row"},
        {"sample": "/api/v1/agent-sessions/sess-1/end", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""}
      ]
    },
    {
      "id": "merge-queue",
      "plan_row": "Merge queue",
      "checks": [
        {"sample": "/api/v1/merge/pending", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "v1 conditional-deny; flip rule as agent-work"},
        {"sample": "/api/v1/merge/PID00007-T004/start", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "route deferred - LAN 404 possible, still app-response"},
        {"sample": "/api/v1/merge/PID00007-T004/result", "methods": ["POST"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "route deferred - same"}
      ]
    },
    {
      "id": "health",
      "plan_row": "Health",
      "checks": [
        {"sample": "/health/live", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "root-level path; internal only - Compose probes never traverse the tunnel"},
        {"sample": "/health/ready", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "LAN expectation is 200 from the backend"}
      ]
    },
    {
      "id": "unnamed-default-deny",
      "plan_row": null,
      "checks": [
        {"sample": "/api/v1/tasks/PID00007-T004/attachments", "methods": ["POST", "GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "not named in 15.2 - default deny (allowlist section 6)"},
        {"sample": "/api/v1/attachments/1", "methods": ["GET", "DELETE"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/attachments/1/content", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": ""},
        {"sample": "/api/v1/schema", "methods": ["GET"], "public_no_credentials": "edge-block", "public_with_service_token": "edge-block", "lan": "app-response", "note": "OpenAPI document (ADR-005) not in 15.2 - default deny"}
      ]
    }
  ],
  "layer_checks": [
    {"id": "V1", "kind": "access-gate", "sample": "/api/v1/projects", "methods": ["GET"], "vantage": "public-no-credentials", "expected": "edge-gate"},
    {"id": "V2", "kind": "access-gate", "sample": "/api/v1/tokens", "methods": ["GET"], "vantage": "public-no-credentials", "expected": "edge-block"},
    {"id": "V3", "kind": "access-gate", "sample": "/api/v1/projects", "methods": ["GET"], "vantage": "public-service-token", "expected": "app-response", "note": "401 AUTH_REQUIRED - edge identity is not authentication"},
    {"id": "V4", "kind": "access-gate", "sample": "/api/v1/tokens", "methods": ["GET"], "vantage": "public-service-token", "expected": "edge-block", "note": "Block beats credentials"},
    {"id": "V5", "kind": "access-gate", "sample": "/api/v1/tokens", "methods": ["GET"], "vantage": "lan", "expected": "app-response"},
    {"id": "INGRESS", "kind": "structural", "note": "script --ingress: validate + first-match rule for every row check equals route-allowlist ingress field"},
    {"id": "R-API", "kind": "rate-limit", "vantage": "lan", "expected": "app-response:RATE_LIMITED", "note": "script --rate-probe with ROUTE_VERIFY_USERNAME/ROUTE_VERIFY_PASSWORD env credentials"},
    {"id": "R-API-TUNNEL", "kind": "rate-limit", "note": "CI: pytest backend/tests/test_rate_limits_tunnel.py -v"},
    {"id": "R-EDGE", "kind": "rate-limit", "vantage": "public", "expected": "edge-rate-limit", "note": "manual operator burst over E1 (30/min) or dashboard rule test - deliberately not automated"}
  ]
}
```
