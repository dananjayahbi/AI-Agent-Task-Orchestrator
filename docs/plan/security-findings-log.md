# Security findings log — WP-6.1 deliverable (MT-6.1-01)

| Field | Value |
|---|---|
| Document | Findings log for WP-6.1 — Security review (Section 19: "findings log"; acceptance "no open high or critical findings") |
| Created by | MT-6.1-01 (authorization review); appended by MT-6.1-02 … MT-6.1-05 (shared log) |
| Companion | [`security-threat-test-mapping.md`](./security-threat-test-mapping.md) |
| Rule | Every finding carries severity, status, and a follow-up id. Severity is judgment — the scale below is fixed **here** so all slices classify consistently (MT-6.1-01 risk note). Plan-text outranks code: a finding whose fix would change a Section 12.x answer needs the plan owner, not a code patch. |

## Severity scale (defined at MT-6.1-01; all slices use it)

| Severity | Definition |
|---|---|
| **critical** | Exploitable now with no preconditions: auth bypass, arbitrary read/write, secret exposure leading to account takeover. WP-6.1 cannot close with one open. |
| **high** | Exploitable with limited/common preconditions, or a core Section 12.2/12.3 guarantee (matrix cell, scoping, traversal, revocation) demonstrably broken. WP-6.1 cannot close with one open. |
| **medium** | Real gap in a defense layer or its verification, with compensating controls in place and no known exploit path today. |
| **low** | Hygiene, documentation, or deployment-readiness observation; closed-loop or trivially fixable. |

Ecosystem advisory severities (MT-6.1-05) map: CVSS 9.0–10.0 → critical; 7.0–8.9 → high;
4.0–6.9 → medium; < 4.0 → low — adjusted by exploitability/context and recorded.

**Statuses:** `Fixed` (closed in this WP) · `Open` (active; follow-up named) ·
`Accepted risk` (owner-approved, justification + revisit recorded) · `Deferred` (blocked; blocker named).

---

## Findings

| ID | Severity | Status | Finding | Slice |
|---|---|---|---|---|
| F-01 | medium | Open (blocked on plan owner — OQ-16) | Section 12.5 audit trail has **no login/token events**: the Section 9.6 catalog defines no `token.*`/`login.*`/`auth.*` type, so logins, token issuance and revocation write no Event row. Raised as OQ-16 in M1 and still undecided; catalog-first discipline (Section 20.4 item 5) forbids inventing a type — the fix is a plan decision, not a code patch. | MT-6.1-01 |
| F-02 | low | Fixed (this slice) | Section 12.5 "the audit viewer is read-only" had **no automated assertion** — nothing pinned the absence of a mutation path on `/api/v1/events`(+`/stream`) or that unsafe methods leave the trail untouched. Closed by `backend/tests/test_security_authorization_review.py` (URLConf pins the two read routes; no mutation handler; POST/PUT/PATCH/DELETE refuse through the catalog envelope with zero rows written). | MT-6.1-01 |
| F-03 | medium | Open (operator-pending — same blocker class as MT-5.2-01/MT-5.2-04) | The **live edge layers are not yet applied** at the Cloudflare zone (Access policy, tunnel route allowlist, edge rate limits incl. E1 30/min/IP on `/api/v1/auth/`): configuration is code (`infra/cloudflare/access-policy.md`, `route-allowlist.md`, `rate-limits.md`) and the local checklist half ran 96/96, but this host has no Cloudflare account, so a tunnel-exposed deployment currently relies on Django-layer controls alone — which deliberately leave Owner auth unthrottled (FR-SEC-05 scope; pinned by `test_owner_session_endpoints_are_not_throttled`). Compensating controls: every non-health route requires Django auth; API-layer throttles cover all agent/device routes; the auth-failure burst alert (Section 17 rules, `test_alerts.py`) fires on stuffing attempts. Owner: operator. Revisit: first live-tunnel bring-up (MT-6.6 rehearsal). | MT-6.1-01 |
| F-04 | low | Accepted risk (plan-recorded deferral; drift-guarded) | `POST /api/v1/tasks/{id}/transition` (Section 9.2 owner publish/unpublish/archive) **does not exist** in the API or `schemas/openapi.yaml`; the Section 12.2 "Publish tasks" row therefore runs on a probe mounting the real `CanPublishTasks` class, and the endpoint's absence is asserted by `DEFERRED_ENDPOINTS` (`test_authorization_matrix.py`, `test_route_allowlist_coverage.py`) — deny-by-absence, no security exposure. Tracked in the WP-1.5 / WP-4.4 / WP-4.5 changelogs as an endpoint gap awaiting the plan owner's routing decision. Owner: plan owner. Revisit: WP-6.6 release-readiness pass. | MT-6.1-01 |
| F-05 | low | Open (cosmetic hardening; follow-up: attachment-intake hardening pass) | `strip_filename` (WP-1.11) accepts a name whose final component is the literal label `..` (e.g. `../..` normalizes to `..` and is stored as the row's display filename). Not a path anywhere — storage is content-addressed, nothing joins the label into a filesystem path (asserted: `test_upload_abuse.py::test_traversal_only_filename_is_an_inert_label_not_a_path`) — so no escape is possible; recorded rather than silently "fixed" in another WP's validation. | MT-6.1-02 |
| F-06 | high → **Fixed** (this slice) | Fixed (upgrade/override applied; web green) | Three **high** js-yaml DoS advisories (GHSA-52cp-r559-cp3m, GHSA-5p4m-2wfm-xmqj, GHSA-2883-xcg3-v3hh — quadratic CPU on merge-key/omap parsing) reached `web` through the dev chain `@hey-api/openapi-ts` → `@hey-api/json-schema-ref-parser` → `js-yaml@4.2.0`. npm's offered "fix" was a **downgrade** of openapi-ts to 0.97.0 (semver-major; rejected). Remediated via the documented exception process step 1/3 — a **scoped npm override** pinning the unaffected fixed release: `web/package.json` → `"overrides": { "@hey-api/json-schema-ref-parser": { "js-yaml": "^4.3.2" } }`; resolution verified (`npm ls js-yaml` → 4.3.2); web `tsc --noEmit`, `eslint`, and the full **442**-test suite green after regeneration. | MT-6.1-05 |
| F-07 | high | Accepted risk (mirrors the recorded CI waiver; time-bounded) | The **braces chain** (root advisory GHSA-vfj7-8cjw-p6xm — stack-exhaustion DoS through deeply nested patterns, CVSS 7.5) propagates through `micromatch` → `fast-glob` → `@next/eslint-plugin-next` → `eslint-config-next` (5 npm entries, one root cause). **Dev-only lint tooling** — never shipped to users, never parses untrusted input in this repo. No fixed braces release exists (OSV: affected ≤ 3.0.3; upstream micromatch/braces#70), so no upgrade/pin/override can clear it; `npm audit fix --force` would downgrade eslint-config-next to 14.x (breaking — rejected). Owner: repository maintainer. Revisit: when braces ships a fixed release, or at the WP-6.6 release-readiness pass. Identical justification already recorded next to the CI threshold in `.github/workflows/security.yaml`. | MT-6.1-05 |
| F-08 | low | Open (recorded follow-up — tooling out of MT scope) | **Container image CVE scanning is not wired** (the security.yaml header records it as an M6 item; no scanner exists in the CI gate, and adding one is explicitly out of MT-6.1-05 scope). Infra images are version-pinned but not digest-pinned (`postgres:16-alpine`, `redis:7.4-alpine`, `cloudflare/cloudflared:2026.10.0`, `mailhog/mailhog:v1.0.1` + locally built backend/web). Mobile (pub) advisory scanning likewise remains the MT-0.3-04 recorded out-of-scope note (no `pub audit` CLI exists). Owner: release. Revisit: WP-6.6 release-readiness pass. | MT-6.1-05 |

**Slice exit checks:** MT-6.1-01 — open critical: **0**; open high: **0** (two medium —
both blocked on decisions this WP may not make unilaterally; one low fixed; one low
accepted with owner and revisit recorded). MT-6.1-02 — open critical/high from this
slice: **0** (one low, F-05). MT-6.1-03 — no new findings. MT-6.1-04 — no new
findings. MT-6.1-05 — **zero open unaddressed critical/high**: one high fixed
(F-06), one high accepted with explicit justification/owner/revisit (F-07, the
pre-existing CI waiver), one low recorded (F-08). WP-6.1 acceptance — "no open high
or critical findings" — **met**.

---

## Review record — MT-6.1-01 checks performed (evidence)

* **Matrix parity:** all 60 printed cells (10 capabilities × 6 actors) plus the anonymous
  column asserted — `ROW_GRANTS` parity (`test_permission_classes.py`) and the running-API
  walk (`test_authorization_matrix.py`), including negative cells, cross-project denial,
  kind separation, and the deferred-cell drift guards. No disagreement with Section 12.2
  found (the matrix is the contract — nothing was "fixed" to change an answer).
* **Section 12.5:** actor + correlation id on API writes (new test), service-path emissions
  (`test_event_writes.py`), viewer read-only (new tests — F-02), trigger-guarded DB role
  (`test_insert_only_permissions.py`). Login/token events: F-01.
* **FR-SEC-05:** every agent/device Section 9.2 route throttle-pinned
  (`test_rate_limiting.py`); both halves re-observed end-to-end inside the WP-6.1 review
  command (`test_security_authorization_review.py`).
* **Edge by pointer (MT-6.1-01 out of scope):** MT-5.2-01/02/03/04 artifacts exist and are
  linked from the mapping; live application → F-03.
* **Test command:** `pytest backend/tests/ -k authorization -v` — 60 passed
  (45 standing + 15 from this slice).

## Review record — MT-6.1-02 checks performed (evidence)

* **Traversal (Section 12.3 / WP-6.1 "traversal tests in CI"):** raw `../` names,
  percent-encoded traversal, absolute POSIX and Windows paths, symlink-style labels —
  normalized to a bare basename at the service layer and content-keyed at storage;
  the wire path (multipart) asserts the same boundary; names normalizing to nothing
  (`/`, empty, whitespace) refuse with the canonical `VALIDATION_ERROR`; every case
  proves zero writes outside the isolated media root (recursive no-symlink,
  resolves-inside assertions). Cosmetic `..` label → F-05.
* **Oversized:** beyond `ATTACHMENT_MAX_FILE_BYTES` → 400 `VALIDATION_ERROR`, no row,
  no partial artifact, no worker hand-off; empty/zero-byte bodies refuse the same way.
* **Spoofed MIME:** ELF bytes as `.png`/octet-stream and PNG bytes as `.pdf` → 415
  `ATTACHMENT_UNSUPPORTED_FORMAT` from content sniffing; a truthful upload under a
  generic declaration takes the **sniffed** type (client header never trusted).
* **Worker separation (Section 12.1):** the web request stores and hands off only —
  row stays `uploaded`, exactly one seam invocation with the stored id, zero pipeline
  Event rows written inline; the seam's real target is the Celery job
  `attachments.process_attachment` (wired by `AttachmentsConfig.ready()`). OS-level
  sandboxing remains the 12.3 post-v1 limitation (mapping L2); optional AV absent by
  plan (L3).
* **Test command:** `pytest backend/tests/ -k upload_abuse -v` → **15 passed**;
  fixtures inert/synthetic (Section 20.4 item 3 spirit). Zero open critical/high
  from this slice (F-05 low).

## Review record — MT-6.1-03 checks performed (evidence)

* **Scoping (FR-SEC-01/ADR-004):** an agent token reaches its own project's `/work`
  and is refused `AUTH_FORBIDDEN_PROJECT` (403) on a foreign one — including with a
  crafted body `project_id` (URL+token win, Section 9.3 step 1).
* **Expiry (Section 12.2):** agent, device and owner-session rows each reject on the
  very next request after their configured lifetime (`AUTH_REQUIRED`, catalog-closed).
  Configured values recorded and pinned: owner session **12 h**, agent **720 h**,
  device **90 days** (`ORCHESTRATOR_TOKEN_LIFETIME_*`) — the audit is tied to real
  settings, not hypotheticals (MT risk note).
* **Revocation:** agent token revocation via `DELETE /tokens/{id}` and device
  revocation via `DELETE /devices/{id}` both kill the credential on its next call;
  the device's SSE stream-reconnect rejection rides the standing
  `test_device_revocation.py` (Section 19 WP-5.3 acceptance re-verified).
  Revocation/login **audit events**: the OQ-16 catalog gap — pinned by
  `::test_token_audit_events_stay_pinned_to_the_oq16_catalog_gap` (F-01), never faked.
* **Hashing at rest:** after real issuance of all three kinds, no plaintext value
  appears in any `ApiToken` column; the stored form is a derived 64-hex digest
  (property asserted, not a schema pin — MT risk note).
* **Kind separation (FR-SEC-02):** the kind enum stays closed at three; owner cookie
  on an agent-only route, agent bearer on Owner routes, and device bearer on an
  Owner-only mutation each answer `ROLE_NOT_PERMITTED` — never data.
* **Edge layer (15.3, by pointer):** Access-style identity headers alone
  authenticate nothing, on both an events route and an agent route.
* **Biometric release:** client-side by design (ADR-006) — the backend asserts the
  release contract (bound credential, dies without a live device row); the app
  unlock half is `mobile/test/security/auth_gate_test.dart` + `lock_gate_test.dart`.
  Recorded honestly rather than claimed as a backend guarantee (MT risk note).
* **Rate limiting (FR-SEC-05):** already asserted in MT-6.1-01's slice and
  `test_rate_limiting.py` — asserted once there, cited here (MT scope note).
* **Test command:** `pytest backend/tests/ -k token_lifecycle -v` → **15 passed**.
  Zero findings new to this slice (F-01/F-03 remain as recorded).

## Review record — MT-6.1-04 checks performed (evidence)

* **Log scrubbing (Sections 12.4/17; RISK-14):** nine backend cases drive the
  sensitive flows (login success **and** failure, token issuance, device
  registration, agent bearer request, attachment upload, a crashing view) through
  the real middleware/views while the root logger is captured through the
  production `JsonFormatter` at DEBUG — no password, issued token, push token,
  header value or upload bytes/filename appears in any line; exception tracebacks
  arrive scrubbed (`[REDACTED]`) with the correlation id intact; long
  attachment-derived text truncates at DEBUG; the request-line shape cannot hold a
  header or body field. Assertions build probes from the **runtime redactor's own
  registered key names** (`apps/core/scrub.py`) — no drifting pattern copy (MT
  risk note).
* **Bridge counterpart:** four `redaction`-selected cases in
  `bridge/tests/test_logging.py` — every registered secret key/suffix, every log
  level including DEBUG, exception tracebacks, and correlation-id survival.
* **Repository scan (Section 18 gate; FR-SEC-04):** the exact CI machinery —
  `uvx pre-commit run detect-secrets --all-files` — **passed** over the whole
  worktree; the WP's new files were scanned with `--files` (they are untracked
  until commit) and pass after two markdown rows gained the standard
  `pragma: allowlist secret` for keyword-shaped prose. Zero unreviewed hits.
* **Config review:** one formatter (`JsonFormatter`) with scrubbing at the single
  redaction point serves every logger (root handler in `LOGGING`); the request
  middleware logs method/path/status/duration/correlation only; the error
  envelope scrubs `details` (standing `test_logging.py`).
* **Test command:** `pytest backend/tests/ -k log_scrubbing -v` → **9 passed**;
  `uv run --directory bridge pytest tests/ -k redaction -v` → **4 passed**.
  Zero findings from this slice.

## Review record — MT-6.1-05 checks performed (evidence)

* **Backend (Python):** `uvx pip-audit --path backend/.venv` (the CI gate command,
  any-severity threshold) → **no known vulnerabilities found**.
* **Bridge (Python/uv):** `uvx pip-audit --path bridge/.venv` → **no known
  vulnerabilities found**.
* **Web (npm):** `npm audit --audit-level=critical` (the CI gate command) passes;
  the full tree carried 9 high entries at audit start. Root causes: (a) three
  js-yaml DoS advisories via the `@hey-api/openapi-ts` chain → **fixed** by the
  scoped override (F-06); (b) the braces chain → **accepted risk** with the
  recorded waiver text (F-07). After remediation: **5 high entries, one chain,
  zero critical** — exactly the logged accepted risk. Regeneration +
  Section 20.4 item 2 battery re-run: `tsc --noEmit` clean, `eslint` clean,
  `vitest` **442 passed (55 files)**.
* **Contract stability (NFR-11):** generation from the current canonical
  `schemas/openapi.yaml` succeeds with the override in place. Note recorded
  honestly: `npm run check:api` exits 1 **in this worktree** because it diffs the
  generated client against the last commit and batch 11 carries an **uncommitted**
  schema delta (notification-preferences endpoints) whose regenerated client
  cannot be committed from this task — the same failure reproduces with the
  override removed (baseline experiment), so it is a worktree-commit condition,
  not a toolchain or advisory regression. The regenerated client was left in
  sync with the schema (the gate's own remedy) — typecheck/tests green over it.
* **Infra images:** version pins inventoried (`postgres:16-alpine`,
  `redis:7.4-alpine`, `cloudflared:2026.10.0`, `mailhog:v1.0.1` + local
  backend/web builds); no image CVE scanner exists in the gate and wiring one is
  out of this MT's scope → F-08. **Mobile (pub):** no `pub audit` CLI exists;
  remains the MT-0.3-04 recorded out-of-scope note (F-08).
* **Test command:** CI dependency-scan job commands run clean above with only the
  logged accepted risk (F-07) remaining.
