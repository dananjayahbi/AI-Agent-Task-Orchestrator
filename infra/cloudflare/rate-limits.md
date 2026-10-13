# Edge and API rate limits — Section 15.3 layer 4 (MT-5.2-03)

| Field | Value |
|---|---|
| Status | **Defined (this file); edge rule application operator-pending (OQ-11)**; API half live since WP-1.2 (MT-1.2-06) |
| Recorded | 2026-10-13 |
| Owner | WP-5.2 — Edge policies and route allowlist (MT-5.2-03) |
| Requirements | FR-SEC-05; Sections 15.3 (layer 4), 12.1 (token-theft mitigation), 12.2, 9.2, 9.10, 19.1 (WP-5.2) |
| Source of truth | Parent plan — the plan fixes *that* both layers exist and *which endpoints* they cover; it fixes **no numbers**, so every threshold below is recorded as a configuration choice (MT-5.2-03 risk note), never as a plan fact |
| Verification | `backend/tests/test_rate_limits_tunnel.py` (local, runs in CI) + checklist hooks in [`route-verification-checklist.md`](./route-verification-checklist.md) (live, operator) |

## 1. Two layers, one stack

Section 15.3 layer 4: *"Rate limits at both the edge and the API; anomaly
alerts on repeated auth failures."* This file defines the **edge** half;
the **API** half already exists (MT-1.2-06) and is reused, never duplicated:

| Layer | Where | Keys on | Denial behavior |
|---|---|---|---|
| Edge (here) | Cloudflare rate-limit rules on the tunnel hostname | the **edge-seen client IP** (`ip.src` at Cloudflare — the real client, before `cloudflared`; not spoofable by request headers) | Cloudflare's own 429, no Django envelope |
| API | Django/DRF throttles (`apps/core/throttling.py`) | the **authenticated Django token id**; client address only as fallback for unauthenticated callers | canonical `RATE_LIMITED` envelope — 429, `retryable: true` (Section 9.2 catalog; WP-0.5 conventions) |

The LAN address (Section 15.1) bypasses the edge by design, so these edge
rules target **the public hostname only**; the API layer applies to every
vantage point, LAN included (documented in [`route-verification-checklist.md`](route-verification-checklist.md)
§environment assumptions).

## 2. Edge rules — every exposed Section 15.2 group, thresholds as choices

Rules are ordered most-specific first; every path on the tunnel hostname
matches exactly one. `per minute` = requests per 60 s per client IP,
action **block** (Cloudflare rate-limiting rule on the tunnel hostname).

| # | Path pattern | Covers Section 15.2 row(s) | Edge limit (choice) | API limit behind it | Why this number (choice, not plan fact) |
|---|---|---|---|---|---|
| E1 | `^/api/v1/auth/` (login, logout, refresh) | R1 Auth, devices | **30/min per IP** | *none by plan scope* — see §3 | The API layer deliberately leaves Owner auth unthrottled (FR-SEC-05 covers agent/device endpoints; enforced by `test_owner_session_endpoints_are_not_throttled`), so the edge is auth's only layer: 30/min stops credential-stuffing bursts while 10× headroom-ing the worst flaky-phone retry cadence |
| E2 | `^/api/v1/devices` (register, list, revoke) | R1 Auth, devices | **120/min per IP** | **60/min per token** (`ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE`) | Edge budget is deliberately **2× the API budget** so a single token-holder crosses the API limit first and gets the canonical `RATE_LIMITED` envelope (§3); the edge rule catches only address-level floods (many tokens/one IP) |
| E3 | `^/api/v1/` (every other API path) | R2 reads/review/dashboard/events; R5 agent work and R6 merge queue (flip-ready, [`route-allowlist.md`](./route-allowlist.md) §5) | **300/min per IP** | **120/min per token** for agent-scoped rows (`ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE`); Owner-session reads are unthrottled API-side (§3) | ≥ the agent budget for the same §3 reason; 300/min tolerates SSE reconnect storms and page-sized reads from one address without tripping |
| E4 | `^/` (the web default route, Section 15.1) | web UI behind the tunnel (dashboard row's UI half) | **600/min per IP** | n/a (static assets never hit the API) | Asset-burst headroom for a Next.js page load; the UI's *API calls* fall under E1-E3 via their own paths |

Coverage rule (acceptance: *"Edge rate limits are defined for every route
group exposed by Section 15.2"*): rows **R1** and **R2** are the v1-exposed
groups and rows **R5/R6** are the conditional groups — all four appear in
the table above (R1 via E1+E2, R2/R5/R6 via E3). Rows that the allowlist
**denies outright** (R3 task create/publish, R4 LAN-only, R7 health, and
the unnamed default-deny paths) are answered 403 before any origin contact —
a request that never reaches a service needs no rate limit; re-evaluate that
sentence if an allowlist row ever flips to `allow`.

The machine-readable form of this table is §6 (parsed by
`test_rate_limits_tunnel.py`).

## 3. No contradiction with the API layer (the double-limiting arithmetic)

* **The edge never masks the API's canonical envelope for one client.**
  Every edge limit that has an API counterpart is numerically **greater
  than or equal to** the API budget (E2 120 ≥ device 60; E3 300 ≥ agent
  120). A single well-behaved client therefore crosses its *per-token* API
  budget first and receives the `RATE_LIMITED` envelope it is entitled to
  (Section 9.2); only sustained floods from one address (many tokens or
  header-retry storms) trip the edge's own 429. `test_rate_limits_tunnel.py`
  asserts this arithmetic against the live settings, so a future threshold
  change cannot silently invert it.
* **Auth is edge-only by plan scope, not by omission.** FR-SEC-05 requires
  rate limiting on *agent and device* endpoints; MT-1.2-06 wired the API
  layer to exactly that scope and a backend test pins Owner auth as
  unthrottled (widening it would violate the recorded scope). The
  "Auth, devices" Section 15.2 row is covered on **both** layers where the
  plan requires it: devices at edge (E2) *and* API (device scope); auth at
  edge (E1), which fills precisely the API-side gap the scope leaves.
* **Edge thresholds are choices.** The plan specifies none; these numbers
  were reasoned as above and are expected to be tuned from checklist runs.
  Changing one = edit §2 + §6 together (the test checks internal
  consistency, not the specific numbers).

## 4. Keying across the tunnel — edge identity never keys the API

MT-5.2-03 acceptance: *"[e]dge rules cannot be bypassed by edge-identity
spoofing: API limits key off Django authentication context, not edge
headers."*

* The API throttle's key is the **authenticated token id**
  (`TokenKeyedRateThrottle.get_cache_key` — `apps/core/throttling.py`).
  Headers the edge adds or an attacker forges (`Cf-Access-Jwt-Assertion`,
  `Cf-Access-Service-Token`, `Cf-Connecting-IP`, `X-Forwarded-For`, …) are
  invisible to that key: they cannot grant a budget, split one, or reset
  one. Proven by `test_rate_limits_tunnel.py` with a tunnel-representing
  header set.
* **The shared tunnel address cannot collapse remote clients into one
  API bucket** (the MT's risk note): behind the tunnel every origin
  request arrives from the same connector address, but throttled endpoints
  are authenticated, so budgets are per-token — two devices behind one
  address hold independent budgets (same test, asserted).
* **Address fallback is a theoretical residual, recorded honestly:** DRF's
  address key uses `X-Forwarded-For` when present (with `NUM_PROXIES`
  unset, the whole forwarded chain). Today *every* throttled endpoint
  requires authentication, so the fallback is unreachable in production —
  verified by the endpoint enumeration in `backend/tests/test_rate_limiting.py`.
  **Cross-WP condition:** if a future WP lands an *unauthenticated*
  throttled endpoint, its address key behind the tunnel must be reviewed
  (proxy-aware `NUM_PROXIES` or token-only keying) — that is WP-1.2's
  throttle-keying territory (MT-5.2-03 risk note), flagged here, not fixed
  here.
* The edge's own counter keys on Cloudflare's `ip.src` (the real client at
  the edge), which headers cannot forge — the two layers deliberately key
  on *different* signals, so spoofing one never moves the other.

## 5. Application steps (operator) and the alerting dependency

1. In the Cloudflare dashboard, add rate-limiting rules E1-E4 to the **tunnel
   hostname only** (Zone → Rules → Rate limiting rules), ordered as §2,
   action **Block**, counting per IP per 60 s, response 429.
2. Do **not** enable them on the LAN-side (they cannot be — LAN traffic
   never touches Cloudflare; recorded so nobody "fixes" the asymmetry).
3. Re-run [`route-verification-checklist.md`](./route-verification-checklist.md)
   (rate-limit hooks) after any threshold or rule change.
4. **Anomaly alerts on repeated auth failures** (the second half of
   layer 4) are Section 17 observability — **WP-6.4**; this WP notes the
   dependency and implements neither the detection nor the alerting
   (MT-5.2-03 out of scope).

## 6. Machine-readable coverage block

Canonical — `backend/tests/test_rate_limits_tunnel.py` parses this fence
(first JSON block under this heading) and cross-checks it against the
allowlist rows and the live `ORCHESTRATOR_RATE_LIMIT_*` settings.

```json
{
  "meta": {
    "plan_sections": ["15.3", "12.1", "12.2", "9.10", "FR-SEC-05"],
    "api_settings": {
      "ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE": 120,
      "ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE": 60
    },
    "api_keying": "django-authenticated-token-id; address fallback for unauthenticated callers only", <!-- pragma: allowlist secret -->
    "edge_keying": "ip.src at the Cloudflare edge",
    "denial_codes": {"api": "RATE_LIMITED", "edge": "cloudflare-429 (no Django envelope)"},
    "anomaly_alerts": "Section 17 / WP-6.4 - dependency noted, not implemented here"
  },
  "edge_rules": [
    {
      "id": "E1",
      "pattern": "^/api/v1/auth/",
      "per_minute": 30,
      "key": "ip",
      "groups": ["auth-devices"],
      "api_scopes": [],
      "note": "Owner auth is API-unthrottled by FR-SEC-05 scope (MT-1.2-06) - the edge is its only layer"
    },
    {
      "id": "E2",
      "pattern": "^/api/v1/devices",
      "per_minute": 120,
      "key": "ip",
      "groups": ["auth-devices"],
      "api_scopes": ["device"],
      "note": "2x the API device budget so a single token trips RATE_LIMITED first"
    },
    {
      "id": "E3",
      "pattern": "^/api/v1/",
      "per_minute": 300,
      "key": "ip",
      "groups": ["reads-review-dashboard-events", "agent-work", "merge-queue"],
      "api_scopes": ["agent"],
      "note": "covers R2 reads plus the conditional R5/R6 groups for the service-token flip"
    },
    {
      "id": "E4",
      "pattern": "^/",
      "per_minute": 600,
      "key": "ip",
      "groups": ["web-ui"],
      "api_scopes": [],
      "note": "web default route (Section 15.1); not a Section 15.2 API row"
    }
  ]
}
```
