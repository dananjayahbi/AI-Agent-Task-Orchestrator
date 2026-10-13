# Route allowlist for the tunnel hostname — Section 15.2 (MT-5.2-02)

| Field | Value |
|---|---|
| Status | Configured locally (rules in `ingress.yaml` + this file); **edge application of the deny half is operator-pending (OQ-11)** — proven by [`route-verification-checklist.md`](./route-verification-checklist.md) |
| Recorded | 2026-10-13 |
| Owner | WP-5.2 — Edge policies and route allowlist (MT-5.2-02) |
| Requirements | FR-NET-01, FR-SEC-05 |
| Source of truth | Parent plan Sections 15.2 (the table), 15.1 (two hostnames), 12.1 (public-exposure mitigation), 9.2 (concrete endpoint paths), 19.1 (WP-5.2 acceptance), 20.5 (traceability) — the plan wins on any conflict |
| Machine-readable form | §7 below — the fenced JSON block is the canonical table the tests parse (one source, no drift) |

## 1. How to read these rules

* **Default deny.** Anything not explicitly allowed for the tunnel hostname
  is denied (Section 15.2; MT-5.2-02 scope). Every Section 9.2 path appears
  below with an explicit decision — §7 carries the full enumeration.
* **Two hostnames, two vantage points** (Section 15.1): the **LAN address**
  reaches the Compose host directly and never passes any rule in this file;
  the **tunnel hostname** passes the edge gate
  ([`access-policy.md`](./access-policy.md), layer 1) and then *these* route
  rules (layer 2 of the Section 15.3 stack). "LAN-only" therefore means
  denied at the edge **and still working on the LAN** — the Section 19
  WP-5.2 acceptance.
* **Three enforcement mechanisms**, deliberately separable:

  | Mechanism | File / product | What it can match | Enforced |
  |---|---|---|---|
  | M1 `cloudflared` ingress deny rules | [`ingress.yaml`](./ingress.yaml) — `path` regex → `http_status:403`, listed **before** the `^/api/` rule | hostname + path (never HTTP method) | locally now: `cloudflared tunnel ingress validate` + per-path `ingress rule` probes; at runtime for a token-run tunnel the same rules exist as the M2 deny applications (README §2 mirror) |
  | M2 Cloudflare Access deny applications | [`access-policy.md`](./access-policy.md) §3 (`Block` apps A2–A10) | hostname + path (never HTTP method) | at the edge — **operator-pending**, checklist hooks V2/V4 |
  | M3 method-aware edge rules | WAF Custom Rules on the tunnel hostname (§4 below) | path + HTTP method | **operator-pending**, checklist §4 rows |

  M1 and M2 are the *same* rule expressed twice (canonical local file ↔ edge
  application for a remotely-managed tunnel, which ignores local `ingress:`
  — WP-5.1's recorded run mode). M3 exists because neither M1 nor M2 can
  deny `POST`/`PATCH` without also killing the allowed `GET` on the same
  path (risk note: edge-vs-app divergence — §4 names those paths).
* **This is defense in depth, not Django's replacement** — Django
  permission classes (WP-1.2) still enforce authorization per request
  (Section 12.1; MT-5.2-02 out of scope).

## 2. Section 15.2 table, mirrored row for row (v1 decisions)

`remote_agents_enabled` = **false** and `remote_merge_executor_enabled` =
**false** in v1 (no VPS scenario yet — WP-5.1's recorded posture), so the
conditional rows are **denied** until §5's flip runs.

| # | Section 15.2 row (verbatim) | Exposed through tunnel (verbatim) | v1 decision on the tunnel hostname | On the LAN |
|---|---|---|---|---|
| R1 | Auth, devices | Yes | **allow** — behind the gate (M2 `A1`), then Django tokens | reachable |
| R2 | Projects (read), tasks (read), review, dashboard, events stream | Yes | **allow** — same gate; writes *not* named by the row are denied (§4) | reachable |
| R3 | Task create/publish | Yes (Could) | **deny** — OQ-12: *"No (Could), review and monitoring only"* | reachable |
| R4 | Agent token creation, policy editing, admin | No (LAN only) | **deny** (M1+M2) | **reachable — unaffected** |
| R5 | Agent work endpoints (claim, checkpoints, submit) | Only if remote agents are used, with a service token | **conditional-deny** (v1 off) — flips to *Allow → service token only* via §5 | reachable |
| R6 | Merge queue | Only for a remote Merge Executor, with a service token | **conditional-deny** (v1 off) — same flip | reachable |
| R7 | Health | Internal only | **deny** (M1+M2) | reachable (Compose probes + LAN publish) |

Paths that appear in Section 9.2 but in **no** Section 15.2 row (project
create/edit, task edit, attachments, the OpenAPI schema) are **default
denied** and flagged in §6 — never silently allowed.

## 3. Concrete path rules (Section 9.2 enumeration)

Decision vocabulary: `allow` = reachable through the tunnel after the edge
gate; `deny` = edge-blocked (403, no Django envelope); `conditional-deny` =
edge-blocked while §5's flags are false. Samples are the concrete instances
the coverage test and the checklist probe (placeholders: `{pid}` →
`PID00007`, `{id}`/`{task}` → `PID00007-T004` or a numeric id).

### R1 — Auth, devices → allow

| Method | Path | Sample | Edge | Ingress rule |
|---|---|---|---|---|
| POST | `/api/v1/auth/login` | same | M2 `A1` gate | `^/api/` → backend |
| POST | `/api/v1/auth/logout` | same | M2 `A1` gate | `^/api/` → backend |
| POST | `/api/v1/auth/refresh` | same | M2 `A1` gate | `^/api/` → backend |
| POST | `/api/v1/devices` | same | M2 `A1` gate | `^/api/` → backend |
| GET | `/api/v1/devices` | same | M2 `A1` gate | `^/api/` → backend — *implementation row beyond the §9.2 table (device list); same Owner/device family* |
| DELETE | `/api/v1/devices/{id}` | `/api/v1/devices/1` | M2 `A1` gate | `^/api/` → backend |

### R2 — Projects (read), tasks (read), review, dashboard, events stream → allow

| Method | Path | Sample | Decision | Edge | Ingress rule |
|---|---|---|---|---|---|
| GET | `/api/v1/projects` | same | allow | `A1` gate | backend |
| GET | `/api/v1/projects/{pid}` | `/api/v1/projects/PID00007` | allow | `A1` gate | backend |
| GET | `/api/v1/projects/{pid}/manifest` | `/api/v1/projects/PID00007/manifest` | allow | `A1` gate | backend |
| GET | `/api/v1/projects/{pid}/tasks` | `/api/v1/projects/PID00007/tasks` | allow | `A1` gate | backend |
| GET | `/api/v1/tasks/{id}` | `/api/v1/tasks/PID00007-T004` | allow | `A1` gate | backend |
| POST | `/api/v1/tasks/{id}/review` | `/api/v1/tasks/PID00007-T004/review` | allow | `A1` gate | backend — *route deferred to a later WP (drift guards in `backend/tests`); rule exists the day the route lands* |
| GET | `/api/v1/dashboard/summary` | same | allow | `A1` gate | backend — *route deferred, same note* |
| GET | `/api/v1/events` | same | allow | `A1` gate | backend |
| GET | `/api/v1/events/stream` (SSE) | same | allow | `A1` gate | backend — *no buffering anywhere (Section 15.4; MT-5.1-04)* |
| POST | `/api/v1/projects` | same | **deny (default)** | M3 method rule §4 | rides `^/api/` (path-shared with the allowed GET) |
| PATCH | `/api/v1/projects/{pid}` | `/api/v1/projects/PID00007` | **deny (default)** | M3 method rule §4 | rides `^/api/` (path-shared with the allowed GET) |
| PATCH | `/api/v1/tasks/{id}` | `/api/v1/tasks/PID00007-T004` | **deny (default)** | M3 method rule §4 | rides `^/api/` (path-shared with the allowed GET) |

### R3 — Task create/publish → deny (OQ-12)

OQ-12 resolution (plan Appendix, recorded verbatim): *"Is task creation from
mobile in scope for v1? → **No (Could), review and monitoring only**."* The
row is therefore **blocked**, not silently passed — flipping it on later is
a §5-style one-line change that must update this file *and* the checklist
(risk-note coupling).

| Method | Path | Sample | Edge | Ingress rule |
|---|---|---|---|---|
| POST | `/api/v1/projects/{pid}/tasks` | `/api/v1/projects/PID00007/tasks` | M3 method rule §4 | rides `^/api/` (path-shared with the allowed GET) |
| POST | `/api/v1/tasks/{id}/transition` | `/api/v1/tasks/PID00007-T004/transition` | M2 `A6` | **`^/api/v1/tasks/[^/]+/transition` → 403** |

### R4 — Agent token creation, policy editing, admin → deny (LAN only)

Every method on these paths is denied at the edge; all of them keep working
on the LAN (Section 19 acceptance).

| Method | Path | Sample | Edge | Ingress rule |
|---|---|---|---|---|
| POST | `/api/v1/tokens/agent` | same | M2 `A2` | **`^/api/v1/tokens` → 403** |
| GET | `/api/v1/tokens` | same | M2 `A2` | **`^/api/v1/tokens` → 403** |
| DELETE | `/api/v1/tokens/{id}` | `/api/v1/tokens/42` | M2 `A2` | **`^/api/v1/tokens` → 403** |
| GET | `/api/v1/projects/{pid}/policy` | `/api/v1/projects/PID00007/policy` | M2 `A3` | **`^/api/v1/projects/[^/]+/policy` → 403** — *the read rides the deny too: M1/M2 match paths, not methods (§6)* |
| PATCH | `/api/v1/projects/{pid}/policy` | `/api/v1/projects/PID00007/policy` | M2 `A3` | **`^/api/v1/projects/[^/]+/policy` → 403** |
| \* | `/admin` (any subpath) | `/admin/` | M2 `A4` | **`^/admin` → 403** — *defensive: no admin surface is registered in the backend today; the row exists because Section 15.2 names "admin"* |

### R5 — Agent work endpoints (claim, checkpoints, submit) → conditional-deny (v1)

Row-level flag `requires_service_token` = **true**; v1 flag
`remote_agents_enabled` = **false** → edge deny via M1+M2. §5 flips both
halves together (deny applications → *Allow → service token only*).

| Method | Path | Sample | Edge (v1) | Ingress rule (v1) |
|---|---|---|---|---|
| GET | `/api/v1/projects/{pid}/work` | `/api/v1/projects/PID00007/work` | `A9` | **`^/api/v1/projects/[^/]+/work` → 403** |
| POST | `/api/v1/tasks/{id}/claim` | `/api/v1/tasks/PID00007-T004/claim` | `A9` | **claim rule → 403** |
| POST | `/api/v1/tasks/{id}/release` | `/api/v1/tasks/PID00007-T004/release` | `A9` | **release rule → 403** |
| POST/GET | `/api/v1/tasks/{id}/checkpoints` | `/api/v1/tasks/PID00007-T004/checkpoints` | `A9` | **checkpoints rule → 403** |
| POST | `/api/v1/tasks/{id}/resolution` | `/api/v1/tasks/PID00007-T004/resolution` | `A9` | **resolution rule → 403** |
| GET | `/api/v1/tasks/{id}/resolutions` | `/api/v1/tasks/PID00007-T004/resolutions` | `A9` | **resolutions rule → 403** |
| GET | `/api/v1/resolutions/{id}/patch` | `/api/v1/resolutions/1/patch` | `A9` | **`^/api/v1/resolutions` → 403** |
| POST | `/api/v1/tasks/{id}/audit-verdict` | `/api/v1/tasks/PID00007-T004/audit-verdict` | `A9` | **audit-verdict rule → 403** |
| GET | `/api/v1/tasks/{id}/audit-reports` | `/api/v1/tasks/PID00007-T004/audit-reports` | `A9` | **audit-reports rule → 403** |
| POST | `/api/v1/agent-sessions` | same | `A9` | **`^/api/v1/agent-sessions` → 403** |
| POST | `/api/v1/agent-sessions/{id}/end` | `/api/v1/agent-sessions/sess-1/end` | `A9` | **`^/api/v1/agent-sessions` → 403** |

### R6 — Merge queue → conditional-deny (v1)

Row-level `requires_service_token` = **true**; v1 flag
`remote_merge_executor_enabled` = **false**.

| Method | Path | Sample | Edge (v1) | Ingress rule (v1) |
|---|---|---|---|---|
| GET | `/api/v1/merge/pending` | same | `A10` | **`^/api/v1/merge` → 403** |
| POST | `/api/v1/merge/{task}/start` | `/api/v1/merge/PID00007-T004/start` | `A10` | **`^/api/v1/merge` → 403** |
| POST | `/api/v1/merge/{task}/result` | `/api/v1/merge/PID00007-T004/result` | `A10` | **`^/api/v1/merge` → 403** |

### R7 — Health → deny (internal only)

Root-level paths (Section 9.2 Ops row — *not* under `/api/v1`).

| Method | Path | Sample | Edge | Ingress rule |
|---|---|---|---|---|
| GET | `/health/live` | same | M2 `A5` | **`^/health/` → 403** |
| GET | `/health/ready` | same | M2 `A5` | **`^/health/` → 403** |

Compose health checks and the LAN publish reach these on the Compose
network/LAN address; through the tunnel they never reach the backend.

### Not named in Section 15.2 → default deny (flagged, §6)

| Method | Path | Sample | Edge | Ingress rule |
|---|---|---|---|---|
| POST/GET | `/api/v1/tasks/{id}/attachments` | `/api/v1/tasks/PID00007-T004/attachments` | M2 `A7` | **`^/api/v1/tasks/[^/]+/attachments` → 403** |
| GET/DELETE | `/api/v1/attachments/{id}` | `/api/v1/attachments/1` | M2 `A7` | **`^/api/v1/attachments` → 403** |
| GET | `/api/v1/attachments/{id}/content` | `/api/v1/attachments/1/content` | M2 `A7` | **`^/api/v1/attachments` → 403** |
| GET | `/api/v1/schema` (+ `/swagger-ui` child) | `/api/v1/schema` | M2 `A8` | **`^/api/v1/schema` → 403** |

## 4. Method-aware rules (M3) — the four path-shared writes

`ingress.yaml` (M1) and Access applications (M2) match **paths only**.
Four Section 9.2 writes share their path with an allowed read, so they are
denied by method-aware edge rules instead — Cloudflare **WAF Custom Rules**
matched to the tunnel hostname, **Block** action, one per row (operator step
of [`access-policy.md`](./access-policy.md) §4 step 6, checklist §4):

| # | Rule expression (path + method) | Serves row |
|---|---|---|
| W1 | `POST` on `http.request.uri.path eq "/api/v1/projects"` | R2 default-deny (project create) |
| W2 | `http.request.uri.path matches "^/api/v1/projects/[^/]+$"` and `method eq PATCH` | R2 default-deny (project edit) |
| W3 | `http.request.uri.path matches "^/api/v1/projects/[^/]+/tasks$"` and `method eq POST` | R3 OQ-12 (task create) |
| W4 | `http.request.uri.path matches "^/api/v1/tasks/[^/]+$"` and `method eq PATCH` | R2 default-deny (task edit) |

* Configuration choice, not a plan fact: the plan fixes the route policy
  (Section 15.2) but names no edge product for method matching; WAF Custom
  Rules are used because Access and `cloudflared` ingress cannot express
  methods. If the account tier cannot host them, the checklist records those
  four rows as **FAIL** and a follow-up task is filed — the residual is
  never silently accepted (MT-5.2-04 out of scope: the checklist does not
  patch policy itself).
* Flipping R3 on (future OQ-12 reversal) = delete W3 **and** the `A6`/
  transition rules **and** update this file + the checklist in the same
  change (risk-note coupling, recorded in the WP-5.2 changelog).

## 5. Conditional-row flip procedure (R5/R6 → enabled)

When — and only when — the remote-agent or remote Merge-Executor scenario
goes live (VPS posture, Section 16.4):

1. Issue the Access service token (`<service-token>` reference in
   [`access-policy.md`](./access-policy.md) §2) and give its id/secret to
   the client (bridge / Merge Executor) via environment — never Git
   (Section 20.4 item 3).
2. Set `remote_agents_enabled` / `remote_merge_executor_enabled` to `true`
   in §7 of **this file** (and the corresponding flag in the checklist's
   machine block).
3. Replace deny application `A9`/`A10` with an application on the **same
   paths** whose policy is **Allow → Service Auth (`<service-token>`)**
   only. `Block` must be gone — a still-blocked path would fail closed
   against the legitimate remote agent.
4. Remove the matching deny rules from `ingress.yaml` (R5/R6 rows above),
   so the canonical local file keeps mirroring the edge.
5. Re-run [`route-verification-checklist.md`](./route-verification-checklist.md)
   end to end (Section 20.4 item 1) — the conditional rows' expected
   outcomes change from *denied* to *service-token-gated*; a skip leaves the
   matrix unverified.

No other row changes with the flip; `A1`'s root gate and every `Block` in
R4/R7/R3 stay exactly as they are.

## 6. Interpretations and flagged items (honest, reviewable)

1. **Attachments are denied** though §9.2 lists them and Section 15.2 does
   not name them anywhere → default deny (flagged in §7). *If* the Owner
   decides mobile review needs image reads, or the VPS bridge needs
   attachment reads, the change is: move those three paths into R5's flip
   (or R2) — one edit here, the matching `A7` app change, and a checklist
   re-run. Recorded rather than guessed either way (Section 20.5).
2. **Policy read rides the policy deny** — R4 says "policy *editing*", but
   M1/M2 cannot match methods, and the mobile feature set (R2) reads no
   policy; denying the read too is the stricter reading. Flagged as a
   method-blind consequence, not a plan quote.
3. **Project create/edit and task edit are default-denied** (§4 W1/W2/W4):
   they appear in no Section 15.2 row, and OQ-12's resolution ("review and
   monitoring only") is the documented v1 posture for mobile writes. Same
   one-line reversal path as §4's note if the plan changes.
4. **`GET /api/v1/devices`** exists in the implementation but not the §9.2
   table (Owner-row read); grouped with R1, flagged in §7 with
   `source: "implementation"`.
5. **Admin row is defensive** — no `/admin` surface is registered today;
   the rule exists so the Section 15.2 row is represented *before* any
   admin surface could appear (traceability, Section 20.5).
6. **Web UI through the tunnel** keeps its WP-5.1 default route
   (Section 15.1) — its *API calls* are governed by the rules above, so the
   remote web board can read and review, while token management, policy
   editing and task creation answer `403` from the edge (by design).

## 7. Machine-readable rule table

Canonical — `backend/tests/test_route_allowlist_coverage.py` parses this
block (the first JSON fence under this heading) and asserts the §2/§3
content against `ingress.yaml`, `access-policy.md` and the Section 15.2
row texts. Edit here and in §2/§3 together; the test fails on drift.

```json
{
  "meta": {
    "plan_sections": ["15.2", "9.2", "12.1", "19.1", "20.5"],
    "default_decision": "deny",
    "hostname_notation": "orchestrator.<owner-domain>",
    "remote_agents_enabled": false,
    "remote_merge_executor_enabled": false,
    "oq12_task_create_in_v1": false,
    "oq12_resolution": "No (Could), review and monitoring only"
  },
  "rows": [
    {
      "id": "auth-devices",
      "plan_row": "Auth, devices",
      "plan_exposed": "Yes",
      "reason": "Mobile login and registration",
      "decision": "allow",
      "paths": [
        {"path": "/api/v1/auth/login", "methods": ["POST"], "sample": "/api/v1/auth/login", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/auth/logout", "methods": ["POST"], "sample": "/api/v1/auth/logout", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/auth/refresh", "methods": ["POST"], "sample": "/api/v1/auth/refresh", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/devices", "methods": ["POST"], "sample": "/api/v1/devices", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/devices", "methods": ["GET"], "sample": "/api/v1/devices", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "implementation"},
        {"path": "/api/v1/devices/{id}", "methods": ["DELETE"], "sample": "/api/v1/devices/1", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"}
      ]
    },
    {
      "id": "reads-review-dashboard-events",
      "plan_row": "Projects (read), tasks (read), review, dashboard, events stream",
      "plan_exposed": "Yes",
      "reason": "Mobile feature set",
      "decision": "allow",
      "paths": [
        {"path": "/api/v1/projects", "methods": ["GET"], "sample": "/api/v1/projects", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/projects", "methods": ["POST"], "sample": "/api/v1/projects", "decision": "deny", "edge": "method-rule", "app": null, "ingress": "backend", "source": "unnamed", "flagged": "project create appears in no Section 15.2 row - default deny via W1"},
        {"path": "/api/v1/projects/{pid}", "methods": ["GET"], "sample": "/api/v1/projects/PID00007", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/projects/{pid}", "methods": ["PATCH"], "sample": "/api/v1/projects/PID00007", "decision": "deny", "edge": "method-rule", "app": null, "ingress": "backend", "source": "unnamed", "flagged": "project edit appears in no Section 15.2 row - default deny via W2"},
        {"path": "/api/v1/projects/{pid}/manifest", "methods": ["GET"], "sample": "/api/v1/projects/PID00007/manifest", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/projects/{pid}/tasks", "methods": ["GET"], "sample": "/api/v1/projects/PID00007/tasks", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}", "methods": ["GET"], "sample": "/api/v1/tasks/PID00007-T004", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}", "methods": ["PATCH"], "sample": "/api/v1/tasks/PID00007-T004", "decision": "deny", "edge": "method-rule", "app": null, "ingress": "backend", "source": "unnamed", "flagged": "task edit appears in no Section 15.2 row - default deny via W4"},
        {"path": "/api/v1/tasks/{id}/review", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/review", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2", "note": "route deferred - rule stands the day it lands"},
        {"path": "/api/v1/dashboard/summary", "methods": ["GET"], "sample": "/api/v1/dashboard/summary", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2", "note": "route deferred - rule stands the day it lands"},
        {"path": "/api/v1/events", "methods": ["GET"], "sample": "/api/v1/events", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"},
        {"path": "/api/v1/events/stream", "methods": ["GET"], "sample": "/api/v1/events/stream", "decision": "allow", "edge": "access-root", "app": "A1", "ingress": "backend", "source": "9.2"}
      ]
    },
    {
      "id": "task-create-publish",
      "plan_row": "Task create/publish",
      "plan_exposed": "Yes (Could)",
      "reason": "Mobile task creation (FR-MOB-08)",
      "decision": "deny",
      "oq12": "No (Could), review and monitoring only - blocked in v1, recorded not silently defaulted",
      "paths": [
        {"path": "/api/v1/projects/{pid}/tasks", "methods": ["POST"], "sample": "/api/v1/projects/PID00007/tasks", "decision": "deny", "edge": "method-rule", "app": null, "ingress": "backend", "source": "9.2", "flagged": "OQ-12 - deny via W3 (path-shared with the allowed GET)"},
        {"path": "/api/v1/tasks/{id}/transition", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/transition", "decision": "deny", "edge": "access-block", "app": "A6", "ingress": "deny-403", "source": "9.2"}
      ]
    },
    {
      "id": "tokens-policy-admin",
      "plan_row": "Agent token creation, policy editing, admin",
      "plan_exposed": "No (LAN only)",
      "reason": "High privilege",
      "decision": "deny",
      "lan_unaffected": true,
      "paths": [
        {"path": "/api/v1/tokens/agent", "methods": ["POST"], "sample": "/api/v1/tokens/agent", "decision": "deny", "edge": "access-block", "app": "A2", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tokens", "methods": ["GET"], "sample": "/api/v1/tokens", "decision": "deny", "edge": "access-block", "app": "A2", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tokens/{id}", "methods": ["DELETE"], "sample": "/api/v1/tokens/42", "decision": "deny", "edge": "access-block", "app": "A2", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/projects/{pid}/policy", "methods": ["GET", "PATCH"], "sample": "/api/v1/projects/PID00007/policy", "decision": "deny", "edge": "access-block", "app": "A3", "ingress": "deny-403", "source": "9.2", "flagged": "read rides the deny - M1/M2 match paths, not methods"},
        {"path": "/admin", "methods": ["*"], "sample": "/admin/", "decision": "deny", "edge": "access-block", "app": "A4", "ingress": "deny-403", "source": "15.2-defensive", "flagged": "no admin surface registered today; rule represents the Section 15.2 admin row"}
      ]
    },
    {
      "id": "agent-work",
      "plan_row": "Agent work endpoints (claim, checkpoints, submit)",
      "plan_exposed": "Only if remote agents are used, with a service token",
      "reason": "VPS scenario: bridge on laptop talks to remote backend",
      "decision": "conditional-deny",
      "requires_service_token": true,
      "flip_flag": "remote_agents_enabled",
      "paths": [
        {"path": "/api/v1/projects/{pid}/work", "methods": ["GET"], "sample": "/api/v1/projects/PID00007/work", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/claim", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/claim", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/release", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/release", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/checkpoints", "methods": ["POST", "GET"], "sample": "/api/v1/tasks/PID00007-T004/checkpoints", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/resolution", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/resolution", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/resolutions", "methods": ["GET"], "sample": "/api/v1/tasks/PID00007-T004/resolutions", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/resolutions/{id}/patch", "methods": ["GET"], "sample": "/api/v1/resolutions/1/patch", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/audit-verdict", "methods": ["POST"], "sample": "/api/v1/tasks/PID00007-T004/audit-verdict", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/tasks/{id}/audit-reports", "methods": ["GET"], "sample": "/api/v1/tasks/PID00007-T004/audit-reports", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/agent-sessions", "methods": ["POST"], "sample": "/api/v1/agent-sessions", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/agent-sessions/{id}/end", "methods": ["POST"], "sample": "/api/v1/agent-sessions/sess-1/end", "decision": "conditional-deny", "edge": "access-block", "app": "A9", "ingress": "deny-403", "source": "9.2"}
      ]
    },
    {
      "id": "merge-queue",
      "plan_row": "Merge queue",
      "plan_exposed": "Only for a remote Merge Executor, with a service token",
      "reason": "Same",
      "decision": "conditional-deny",
      "requires_service_token": true,
      "flip_flag": "remote_merge_executor_enabled",
      "paths": [
        {"path": "/api/v1/merge/pending", "methods": ["GET"], "sample": "/api/v1/merge/pending", "decision": "conditional-deny", "edge": "access-block", "app": "A10", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/merge/{task}/start", "methods": ["POST"], "sample": "/api/v1/merge/PID00007-T004/start", "decision": "conditional-deny", "edge": "access-block", "app": "A10", "ingress": "deny-403", "source": "9.2"},
        {"path": "/api/v1/merge/{task}/result", "methods": ["POST"], "sample": "/api/v1/merge/PID00007-T004/result", "decision": "conditional-deny", "edge": "access-block", "app": "A10", "ingress": "deny-403", "source": "9.2"}
      ]
    },
    {
      "id": "health",
      "plan_row": "Health",
      "plan_exposed": "Internal only",
      "reason": "",
      "decision": "deny",
      "paths": [
        {"path": "/health/live", "methods": ["GET"], "sample": "/health/live", "decision": "deny", "edge": "access-block", "app": "A5", "ingress": "deny-403", "source": "9.2"},
        {"path": "/health/ready", "methods": ["GET"], "sample": "/health/ready", "decision": "deny", "edge": "access-block", "app": "A5", "ingress": "deny-403", "source": "9.2"}
      ]
    },
    {
      "id": "unnamed-default-deny",
      "plan_row": null,
      "plan_exposed": null,
      "reason": "Paths in Section 9.2 but in no Section 15.2 row - default deny (Section 15.2)",
      "decision": "deny",
      "paths": [
        {"path": "/api/v1/tasks/{id}/attachments", "methods": ["POST", "GET"], "sample": "/api/v1/tasks/PID00007-T004/attachments", "decision": "deny", "edge": "access-block", "app": "A7", "ingress": "deny-403", "source": "9.2", "flagged": "attachments appear in no Section 15.2 row - default deny; flip requires this file + A7 + a checklist re-run"},
        {"path": "/api/v1/attachments/{id}", "methods": ["GET", "DELETE"], "sample": "/api/v1/attachments/1", "decision": "deny", "edge": "access-block", "app": "A7", "ingress": "deny-403", "source": "9.2", "flagged": "same as above"},
        {"path": "/api/v1/attachments/{id}/content", "methods": ["GET"], "sample": "/api/v1/attachments/1/content", "decision": "deny", "edge": "access-block", "app": "A7", "ingress": "deny-403", "source": "9.2", "flagged": "same as above"},
        {"path": "/api/v1/schema", "methods": ["GET"], "sample": "/api/v1/schema", "decision": "deny", "edge": "access-block", "app": "A8", "ingress": "deny-403", "source": "9.2-adjacent", "flagged": "OpenAPI document (ADR-005) is not a Section 15.2 exposure - default deny"}
      ]
    }
  ]
}
```

**Traceability rule (Section 20.5):** a Section 15.2 row or a Section 9.2
path that is missing here fails `test_route_allowlist_coverage.py`; any
change to `ingress.yaml`, [`access-policy.md`](./access-policy.md) or this
block requires re-running [`route-verification-checklist.md`](./route-verification-checklist.md)
(the results template's re-run instruction).
