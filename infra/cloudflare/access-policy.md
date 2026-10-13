# Cloudflare Access policy — the edge gate for the tunnel hostname (MT-5.2-01)

| Field | Value |
|---|---|
| Status | **Defined (as code in this file); dashboard application operator-pending (OQ-11)** |
| Recorded | 2026-10-13 |
| Owner | WP-5.2 — Edge policies and route allowlist (MT-5.2-01) |
| Requirements | FR-NET-01, FR-SEC-05 |
| Source of truth | Parent plan Sections 15.3 (ADR-006, layer 1), 15.1, 12.2, 19.1 (WP-5.2), ADR-006 — the plan wins on any conflict (Section 0) |
| Applies to | The tunnel hostname `orchestrator.<owner-domain>` (OQ-11 notation; the concrete value lives only in `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` and at the edge) |
| Companion files | [`route-allowlist.md`](./route-allowlist.md) (Section 15.2 path rules), [`rate-limits.md`](./rate-limits.md) (layer 4), [`route-verification-checklist.md`](./route-verification-checklist.md) (runs the checks named below), [`README.md`](./README.md) (hostname/token handling) |

## 1. What this is — layer 1 of four, never the whole gate

Section 15.3 (ADR-006) fixes four access-control layers; this file defines
**layer 1** only:

1. Cloudflare Access policy on the hostname (identity or service token) as
   the **edge gate** — *this document*.
2. Django device/agent tokens **always required**; edge identity headers are
   never trusted as authentication on their own.
3. Biometric unlock on the phone (local to the device) — WP-5.3/5.x.
4. Rate limits at both the edge and the API — [`rate-limits.md`](./rate-limits.md)
   (MT-5.2-03).

Two rules follow from that layering and are repeated wherever this policy is
applied, because misreading them is the failure mode ADR-006 exists to
prevent:

* The Access policy is the **first gate** only. It is the *first* gate, not
  the only gate: Django device/agent tokens remain **always required** behind
  it (Sections 12.2, 15.3). A request that passes this policy still gets
  `AUTH_REQUIRED` from Django if it carries no valid Django credential.
* The Access application must **never** be configured with a bypass that
  skips origin authentication (no "bypass origin auth" posture, no
  `Bypass → Everyone` policy on any application below). Edge identity is not
  authentication.

## 2. Principals — who may pass the edge gate

Section 15.3 layer 1 names exactly two principal kinds; nothing else is
invented (Section 20.5 — no principals beyond the plan):

| # | Principal | Plan basis | Concrete binding (operator-supplied) |
|---|---|---|---|
| P1 | **Owner identity** — the single Owner person behind the web/mobile client | Section 15.3 "identity"; Section 12.2 Owner | The Owner's identity in the account's Access Identity Provider, referenced here as `<owner-identity>`. The plan does not name an IdP — the operator binds the one they enable (Section 19 WP-5.2 deliverable is the *policy definition*; IdP choice is account configuration). |
| P2 | **Service token** — machine clients of the remote (VPS) scenarios: the bridge talking to a remote backend (Section 15.2 row 5) and the remote Merge Executor (row 6); also the checklist's non-interactive probe | Section 15.3 "service token"; Section 15.2 rows 5–6 "with a service token" | A Cloudflare Access service token issued in the account, referenced here as `<service-token>` — client id/secret held **only** in the Cloudflare account and in the consuming client's environment (`CF_ACCESS_CLIENT_ID` / `CF_ACCESS_CLIENT_SECRET`, values never committed — Section 20.4 item 3). Service-token *ids* are references, not secrets; secret values are never recorded in this repo. |

Scope discipline (MT-5.2-01 risk note — an over-broad policy is a security
finding, FR-SEC-05 context):

* P1 is **the Owner, named exactly** — never "everyone in the domain",
  never "anyone with the link", never a standing `Bypass → Everyone`.
* P2 exists for the scenarios Section 15.2 names; in the v1 default posture
  the conditional paths themselves are **denied** (see
  [`route-allowlist.md`](./route-allowlist.md)) and the service token gains
  nothing until the operator flips that row through the documented procedure.

### Open point (recorded, not weakened)

**How the mobile app satisfies this gate.** Section 15.3 says "identity or
service token"; MT-5.2-01 scopes the principals to Owner identity plus the
service tokens of the Section 15.2 scenarios. A phone making API calls
cannot perform an interactive IdP round-trip per request, so whether the
mobile client passes via an Access session obtained during the Owner's
in-app login (identity) or via an Access service token (P2) is decided by
**WP-5.3 / WP-5.5** when the mobile client is built. This document defines
no third principal and grants nothing in the meantime; the checklist's
public probes exercise the gate with (a) no credentials and (b) the optional
service token, which covers both readings. Do not resolve this by weakening
the gate.

## 3. The policy definition (as code)

Application topology on the tunnel hostname. Cloudflare Access matches the
**most specific path** first; an application's path covers its children
unless a more specific application exists (Cloudflare "Application paths"
docs — the operator confirms the same semantics in the dashboard's preview).
`*` in a path below is Cloudflare's single-segment wildcard (e.g.
`/api/v1/tasks/*/transition` matches `.../tasks/PID00007-T004/transition`).

| App | Path (covers children) | Policy action | Principals | Section 15.2 row | v1 state |
|---|---|---|---|---|---|
| A1 `root-gate` | `/` (the whole hostname) | **Allow** | P1 Owner identity; P2 service token | every exposed row behind the gate | active |
| A2 `deny-tokens` | `/api/v1/tokens` | **Block** | — (nobody passes) | Agent token creation… (LAN only) | active |
| A3 `deny-policy` | `/api/v1/projects/*/policy` | **Block** | — | policy editing (LAN only) | active |
| A4 `deny-admin` | `/admin` | **Block** | — | admin (LAN only) | active |
| A5 `deny-health` | `/health` | **Block** | — | Health (internal only) | active |
| A6 `deny-transition` | `/api/v1/tasks/*/transition` | **Block** | — | Task create/publish — OQ-12 | active |
| A7 `deny-attachments` | `/api/v1/attachments` and `/api/v1/tasks/*/attachments` | **Block** | — | *not named in Section 15.2 → default deny* | active |
| A8 `deny-schema` | `/api/v1/schema` | **Block** | — | *not named in Section 15.2 → default deny* | active |
| A9 `deny-agent-work` | `/api/v1/projects/*/work`, `/api/v1/tasks/*/claim`, `/api/v1/tasks/*/release`, `/api/v1/tasks/*/checkpoints`, `/api/v1/tasks/*/resolution`, `/api/v1/tasks/*/resolutions`, `/api/v1/tasks/*/audit-verdict`, `/api/v1/tasks/*/audit-reports`, `/api/v1/resolutions`, `/api/v1/agent-sessions` | **Block** | — | Agent work endpoints (conditional) | active — remote agents **off** |
| A10 `deny-merge` | `/api/v1/merge` | **Block** | — | Merge queue (conditional) | active — remote Merge Executor **off** |

Cross-references and boundaries:

* **Path rules only.** This file and Access express *path* matching, never
  HTTP method. The four Section 9.2 writes that share a path with an allowed
  read (project create/edit, task create/edit) are governed by the
  method-aware rules in [`route-allowlist.md`](./route-allowlist.md)
  §4 — Cloudflare Access cannot express them and neither can `ingress.yaml`.
* **Exposed rows** (Section 15.2 rows 1–2: auth/devices; reads/review/
  dashboard/events) carry **no deny application**: they inherit `A1`, pass
  the gate as P1/P2, and are then subject to Django token authentication
  (layer 2) and the rate limits (layer 4).
* **Conditional rows** (`A9`/`A10`) flip, they are not deleted: when the
  operator enables the remote-agent / remote Merge-Executor scenario, each
  Block application is replaced by an application with the **same path**
  whose policy is **Allow → P2 service token only** (exactly "with a service
  token", Section 15.2). The flip procedure and the config coupling live in
  [`route-allowlist.md`](./route-allowlist.md) §5 and the WP-5.2 changelog;
  the [`route-verification-checklist.md`](./route-verification-checklist.md)
  expectations are updated in the same change.
* **LAN is untouched.** The LAN address (Section 15.1) never reaches
  Cloudflare, so no application here can affect it; LAN-only rows keep
  working there — that split is the WP-5.2 acceptance (Section 19).

## 4. Application steps (operator — dashboard, applied once per environment)

Procedures are recorded, not executed here: applying Cloudflare-side
configuration is an operator action against the account (the same split
WP-5.1 used for the hostname procedure). Steps at the level the plan fixes:

1. **Prerequisite** — the tunnel hostname exists and serves traffic
   ([`README.md`](./README.md) §2, WP-5.1); without it there is nothing to
   gate.
2. **Zero Trust → Access → Applications → Add a self-hosted application**:
   create `A1` first — domain = `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME`
   value, path `/`. Type the hostname from the environment; never commit the
   concrete value (Section 20.4 item 3).
3. **P1 policy on `A1`** — Allow, include rule = the Owner's identity
   (exactly one person; if the dashboard offers "Everyone", "Valid email",
   or whole-domain groups, do **not** use them — over-broad is a security
   finding, MT-5.2-01 risk note).
4. **P2 policy on `A1`** — Allow (Service Auth) with the service token
   issued for the machine clients of Section 15.2 rows 5–6. Record the
   token's **client id** here only as `<service-token>` reference; the
   secret goes to the consuming client's environment, never Git.
5. **Create `A2`–`A10`** with their paths from §3 and policy **Block →
   Everyone**. One path per application if the UI only accepts a single
   path — same semantics, no other change.
6. **Method-aware rules** — add the four Block rules from
   [`route-allowlist.md`](./route-allowlist.md) §4 (WAF Custom Rules matched
   to the tunnel hostname) so the method-split writes are denied too; this
   is part of applying the allowlist, recorded there.
7. **Never add a Bypass policy** anywhere on this hostname; never enable a
   "bypass origin authentication" option. If any screen offers one, decline
   — it would collapse layers 1 and 2 into one (ADR-006).
8. **Verify** — run the checklist ([`route-verification-checklist.md`](./route-verification-checklist.md))
   against the hostname and append the results; unverified dashboard state
   is drift (risk note below).

## 5. Named verification hooks (executed by MT-5.2-04's checklist)

| Hook | Request | Expected (public hostname) | Proves |
|---|---|---|---|
| V1 | Unauthenticated request to an **exposed** path (e.g. `GET /api/v1/projects`) | edge challenge/denial — 302 to the IdP or 403, **no Django error envelope** | layer 1 active (gate before origin) |
| V2 | Unauthenticated request to a **denied** path (e.g. `GET /api/v1/tokens`) | edge block — 403, no Django envelope | A2-style deny app active |
| V3 | Request with the P2 service-token headers (`CF-Access-Client-Id`/`CF-Access-Client-Secret`) to an exposed path, **without** Django credentials | gate passes, Django answers `401 AUTH_REQUIRED` envelope | edge identity is **not** authentication (layer 2 still required) |
| V4 | Same denied-path request **with** P2 headers | still blocked at the edge | Block beats credentials; deny is unconditional |
| V5 | The same paths on the **LAN address** | plain Django responses (no Access redirect anywhere) | Section 15.1 split; LAN bypasses the edge by design |

V3/V4 need a provisioned service token and are skipped-as-operator-pending
until P2 exists; V1/V2/V5 run with no credentials at all.

## 6. Drift and re-run rule

The Cloudflare dashboard is external state (risk note): **this file is the
source of truth** and [`route-verification-checklist.md`](./route-verification-checklist.md)
is the drift detector. Re-run the checklist after **any** dashboard change
to this hostname (application, policy, path edit) and after any change under
`infra/cloudflare/`; a skipped re-run leaves acceptance unverified
(Section 20.4 item 1).

## 7. Dependencies recorded (out of scope here)

* **Anomaly alerts on repeated auth failures** (Section 15.3 layer 4's
  second half) are Section 17 observability work — WP-6.4; noted in
  [`rate-limits.md`](./rate-limits.md) §5, not implemented by this WP.
* Django authentication itself — WP-1.2 / WP-5.3.
* Tunnel/ingress structure — WP-5.1 ([`ingress.yaml`](./ingress.yaml)).
