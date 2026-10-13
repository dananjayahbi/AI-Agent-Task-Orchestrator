# WP-5.2 — Edge policies and route allowlist: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-5.2-01 — policy defined as code; live application operator-pending
  (OQ-11):** `infra/cloudflare/access-policy.md` created as the Section
  15.3 layer-1 policy definition for the tunnel hostname: principals are
  exactly the plan's two — **P1 Owner identity** (single named person; no
  IdP invented, over-broad rules called out as security findings per the
  MT risk note) and **P2 service token** (the Section 15.2 row-5/6 machine
  clients; client id/secret referenced as env-only `CF_ACCESS_CLIENT_ID` /
  `CF_ACCESS_CLIENT_SECRET`, never committed — 20.4 item 3). The layering
  rule is stated where it can be misread: the Access policy is the **first
  gate** only, Django device/agent tokens remain **always required**, and
  no application may ever carry a bypass-origin-auth posture (verified by
  the MT's named grep). Policy topology is tabulated as applications A1
  (root gate: Allow P1/P2) + A2–A10 (Block: the LAN-only, health, OQ-12
  publish, unnamed-default-deny and conditional rows), with §15.2 row
  cross-references, dashboard application steps (§4 — recorded, not
  executed: Cloudflare-side apply is an operator action against the
  account), and the named V1–V5 verification hooks (§5) that MT-5.2-04's
  checklist executes. **Honest split:** the policy *definition* (the
  Section 19 WP-5.2 deliverable) is complete and versioned here; the
  *live application* cannot happen locally (no account access) and stays
  operator-pending under OQ-11 — never weakened to pretend otherwise. One
  recorded open point: how the mobile client satisfies the gate (identity
  session vs service token) is left to WP-5.3/5.5 with no third principal
  granted in the meantime. Review checks: grep finds the layering
  statement and both principals; no secret or concrete hostname in the
  file.
- **MT-5.2-02 — route allowlist enforced in config; edge application of
  the deny half operator-pending (OQ-11):**
  `infra/cloudflare/route-allowlist.md` reproduces Section 15.2 line for
  line (all seven rows, verbatim text) with **every** Section 9.2 path
  assigned an explicit decision — canonical machine block in §7; default
  for the tunnel hostname is deny. Decisions: R1/R2 allow behind the
  `A1` gate; R3 task create/publish **blocked** with the OQ-12 resolution
  recorded verbatim (*"No (Could), review and monitoring only"*) rather
  than silently defaulted; R4 tokens/policy/admin denied (LAN untouched);
  R5 agent-work and R6 merge **conditional-deny** in v1 with a documented
  flip procedure (§5: deny apps → *Allow → service token only* on the same
  paths, ingress rules dropped, checklist re-run — the coupling the MT
  risk note demands); R7 health denied; paths in no §15.2 row
  (attachments ×3, OpenAPI schema) denied and **flagged** with the
  one-edit flip, plus flagged interpretations (policy *read* rides the
  method-blind deny; project create/edit and task edit are unnamed writes;
  `GET /api/v1/devices` is an implementation row; `/admin` is defensive).
  `ingress.yaml` extended with **13 deny rules** (`path` regex →
  `http_status:403`) inserted *before* the `^/api/` rule — the MT's
  prefix-divergence guard — and the Section 15.2 review block updated to
  the enforced state. Four path-**shared** writes cannot be expressed by
  path regexes (same path, allowed GET + denied POST/PATCH) and are
  documented as method-aware edge rules **W1–W4** (WAF Custom Rules — a
  configuration choice the plan does not name or forbid; account-tier
  caveat and the "checklist-FAIL → follow-up, never silently accepted"
  fallback recorded). Local structural proof now: official image
  `cloudflared tunnel ingress validate` → OK, and per-sample
  `ingress rule` probes for all 45 samples match the allowlist exactly
  (26 → `http_status:403`, 19 → `http://backend:8000`, `/board` → web,
  catch-all 404 last). Traceability test
  `backend/tests/test_route_allowlist_coverage.py` (**15 passed**) asserts
  row-for-row mapping, default-deny, OQ-12/conditional/health cells,
  rule-for-rule `ingress.yaml` agreement (including "no deny rule catches
  an allowed path"), A-app references in `access-policy.md`, W1–W4
  presence, and no secrets/concrete hostname. `infra/cloudflare/README.md`
  §2 step 4 now explains how the deny half mirrors to the edge (routes
  cannot deny → Access deny apps + method rules) and §7 links the four
  WP-5.2 documents. Full live blocked-vs-allowed execution = MT-5.2-04's
  checklist (operator half pending).
- **MT-5.2-03 — edge limits defined, API limits proven through the tunnel
  context; edge rule application operator-pending (OQ-11):**
  `infra/cloudflare/rate-limits.md` defines edge rules **E1** auth
  30/min/IP, **E2** devices 120/min/IP, **E3** remaining API 300/min/IP,
  **E4** web default 600/min/IP — every Section 15.2-exposed group
  covered (R1 via E1+E2; R2/R5/R6 via E3, flip-ready), denied rows
  explicitly excluded (403 before origin, no counter needed). Every
  threshold is recorded as a **configuration choice with its reasoning**
  (the plan fixes no numbers — MT risk note), and the "no contradiction"
  arithmetic is both documented (§3) and machine-checked: every edge
  budget that has an API counterpart is ≥ the live
  `ORCHESTRATOR_RATE_LIMIT_*` value (device 120 ≥ 60, agent 300 ≥ 120), so
  a single token-holder trips the API's canonical `RATE_LIMITED` envelope
  first and only address-level floods hit the edge's own 429. Auth being
  edge-only is the **recorded FR-SEC-05 scope** (MT-1.2-06; Owner auth
  stays API-unthrottled per the backend's pinned test — deliberately not
  widened), with E1 filling exactly that gap; device endpoints carry both
  layers as Section 15.3 requires. Keying analysis (§4): API budgets key
  on the Django token id, so edge headers cannot grant, split or reset a
  budget and the shared tunnel connector address cannot collapse remote
  clients into one bucket — both proven in
  `backend/tests/test_rate_limits_tunnel.py` (**7 passed**: `RATE_LIMITED`
  envelope under tunnel-representing headers with `Retry-After`, two
  edge-identity header variants sharing one budget, anonymous request
  with forged Access headers → `AUTH_REQUIRED`, two tokens one address →
  independent budgets, doc↔settings↔allowlist consistency, E1 coverage,
  owner-auth scope guard). The DRF address-fallback/XFF residual is
  recorded honestly as unreachable today (every throttled endpoint is
  authenticated) with a **cross-WP condition** on WP-1.2 keying if an
  unauthenticated throttled endpoint ever lands. Anomaly alerts on
  repeated auth failures stay flagged as Section 17 / WP-6.4 (out of
  scope, dependency noted). No secrets: thresholds and rule ids only.
- **MT-5.2-04 — checklist written and the local half executed (96/96
  PASS); public-hostname run operator-pending (OQ-11):**
  `infra/cloudflare/route-verification-checklist.md` enumerates every
  Section 15.2 row with concrete Section 9.2 samples and **both**
  vantage-point expectations per check — no blank cells (public no-creds,
  public with service token, LAN) — plus the expectation vocabulary, the
  layer hooks V1–V5 (Access gate), INGRESS (structural), R-API /
  R-API-TUNNEL / R-EDGE (rate limits), a results template with the
  re-run rule (20.4 item 1), and the recorded run below. Runner:
  `e2e/route_verify.py` (stdlib-only, sibling of the SSE soak client) with
  `--ingress` (cloudflared validate + one rule probe per allowlist
  sample), `--lan-url`, `--public-url` (+ optional env service-token
  headers — the sharp allow-vs-deny discriminator) and `--rate-probe`
  (env credentials `ROUTE_VERIFY_USERNAME`/`ROUTE_VERIFY_PASSWORD`,
  budget+1 posts expecting the canonical envelope); it never bursts the
  public hostname (R-EDGE is a documented manual operator check).
  **Recorded local run (2026-10-13, evidence
  `e2e/route_verification_results.json`):** isolated dev-profile Compose
  stack (project `wp52route`, `ORCHESTRATOR_BIND_ADDR=192.168.1.244:8030`
  — LAN IP and port absorbed from the environment; the committed template
  records an older address and concurrent agents hold the default ports;
  container-local install of the in-flight `pillow`/`pypdf` attachments
  deps — environment setup, no code change) → **executed 96, pass 96,
  fail 0, skip 0**: ingress structural 46/46 (validate OK, 45/45 samples
  match the allowlist: 26 × 403, 19 → backend), LAN vantage 49/49
  (`app-response` everywhere, zero connection failures — including the
  LAN-only rows the Section 19 acceptance names), and the R-API rate
  probe PASS (61 device posts vs budget 60 → `RATE_LIMITED` envelope).
  **Operator-pending, honestly:** the public-hostname half cannot run
  until (a) OQ-11 provisions hostname/token and (b) `access-policy.md` §4
  applies A1–A10 + W1–W4 — invocation, prerequisites and the append-results
  procedure are in the checklist §1/§5; a pre-apply public run failing its
  edge expectations is the drift detector working, recorded as such. The
  completeness half is automated: `backend/tests/test_route_checklist_coverage.py`
  (**8 passed**) fails if a §15.2 row, a vantage cell, a layer hook, the
  results template or the allowlist pairing ever disappears. Re-run rule
  (delivered per the MT): **re-run the checklist after any
  `infra/cloudflare/` change or dashboard edit and append the dated block
  to the checklist §5 — a skipped re-run leaves WP-5.2 acceptance
  unverified.**

### Section 20.4 checks for this WP

1. Acceptance: blocked-vs-allowed demonstrably executed on every locally
   reachable half (96/96 recorded); the two genuinely remote halves (live
   edge application, public vantage) are named, invocable and
   operator-pending under OQ-11 — acceptance not weakened.
2. Tests green locally: `pytest tests/test_route_allowlist_coverage.py
   tests/test_rate_limits_tunnel.py tests/test_route_checklist_coverage.py`
   → 30 passed; `cloudflared tunnel ingress validate` → OK.
3. No secrets: service-token references and env var *names* only; no
   concrete hostname (placeholder notation everywhere); thresholds are
   documented numbers, not credentials.
4. No public contract (OpenAPI/tool schemas) changed — configuration and
   documentation only.
5. Error codes used: `RATE_LIMITED`, `AUTH_REQUIRED` — both catalog
   (Section 9.2).
6. No new events (no behavior change behind the edge).
7. This changelog.

## Verification-finisher audit (2026-10-13)

Run by the WP-5.2 verification finisher after the original agent died at
its final report (network outage). The four MT entries above were all
present in this file at audit start and were re-checked line-by-line
against the MT acceptance criteria and the parent plan (Sections 15.1,
15.2, 15.3, 12.1, 12.2, 18, 19.1, ADR-006, 20.4/20.5) — **no entry was
missing, no acceptance was found weakened, and no policy decision was
changed by the finisher.**

* **Audit result per MT — all survived locally complete:**
  MT-5.2-01 `access-policy.md` (P1/P2 principals, layering rule,
  A1–A10, §4 operator steps, V1–V5 hooks, honest OQ-11 split);
  MT-5.2-02 `route-allowlist.md` + 13 deny rules in `ingress.yaml` +
  W1–W4 method rules + `README.md` §2/§7 updates;
  MT-5.2-03 `rate-limits.md` (E1–E4 aligned with the live
  `ORCHESTRATOR_RATE_LIMIT_*` values, no contradiction);
  MT-5.2-04 `route-verification-checklist.md` + runner
  `e2e/route_verify.py` + the three traceability tests.
* **Re-executed by the finisher (all green):**
  `uv run --project backend pytest backend/tests/test_route_allowlist_coverage.py
  backend/tests/test_rate_limits_tunnel.py backend/tests/test_route_checklist_coverage.py`
  → **30 passed**; MT-5.2-01's and MT-5.2-03's named greps → layering
  statement present, `limit` hits present; official pinned cloudflared
  image → `tunnel ingress validate` **exit 0 / OK** and **45/45**
  `tunnel ingress rule` probes matching the allowlist (26 →
  `http_status:403`, 19 → `http://backend:8000`);
  full local-half reproduction against the still-running dev stack
  (`wp52route`, LAN `http://192.168.1.244:8030`; dedicated ephemeral
  rate-probe user, credential env-only) → **executed 96, pass 96,
  fail 0, skip 0** (ingress 46/46, LAN 49/49, R-API
  `app-response:RATE_LIMITED` on 61 device posts vs budget 60) — the
  check set, expectations and statuses are identical to the recorded run
  above; the fresh results document replaced
  `e2e/route_verification_results.json`.
* **Secrets/hostname scan** across every file of this WP's surface: no
  secret values and no concrete hostname — placeholders and env *names*
  only (Section 20.4 item 3).
* **Still operator-pending (unchanged, OQ-11):** live edge application of
  A1–A10 / W1–W4 / E1–E4 and the public-vantage half of the checklist —
  the finisher re-verified the split, did not narrow it and did not
  pretend the edge half ran. LAN-vs-tunnel verifiability stays documented
  in the checklist §0, `ingress.yaml`'s header and `README.md` §2.
* No `git add`/`git commit` was performed; everything above sits in the
  working tree. Re-run rule stands: re-execute the checklist after any
  `infra/cloudflare/` change or dashboard edit.
