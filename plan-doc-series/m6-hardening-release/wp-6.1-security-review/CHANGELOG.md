# WP-6.1 — Security review: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

### Freeze ruling for MT-6.1-01 (M1–M5 readiness; recorded verbatim per the batch directive)

MT-6.1-01's Dependencies row, verbatim: "MT-1.2-07 (authorization matrix tests exist),
MT-1.9-04 (insert-only audit permissions), WP-5.2 (edge policies), WP-5.3 (device auth)
complete; M1–M5 features under review (Section 19 WP-6.1 dependency)". Parent plan
Section 19 (WP-6.1), verbatim: "Depends on: M1 to M5. Requirements: NFR-07, FR-SEC-01
to FR-SEC-05."

Ruling: the wording depends on the M1–M5 **feature sets being under review** — not on
every MT checkbox reading (done). Verified against the WP changelogs that every
remaining M1–M5 gap is operator-excluded or execution-blocked on operator resources:
MT-2.11-02…07 (deferred — no authenticated client/credentials in this environment),
MT-5.1-04 (code artifacts complete; through-tunnel 30-min run operator-pending, OQ-11),
MT-5.10-03 (deferred — no Apple Developer account; `xcodebuild` not on Windows),
MT-5.10-05 (checklist authored at `mobile/docs/release-checklist.md`; execution blocked
— no real device, no FCM client transport, no iOS). Freeze dependency **satisfied**;
WP-6.1 proceeds. Recorded also for honesty: the Section 9.2
`POST /tasks/{id}/transition` remains a plan-recorded endpoint deferral
(deny-by-absence, drift-guarded by `DEFERRED_ENDPOINTS`) — findings log F-04.

- **MT-6.1-01 — Run the authorization review against the Section 12.2 matrix (done).**
  Review executed against Sections 12.1/12.2/12.3/12.5/15.3/18 with the matrix as the
  contract (nothing "fixed" to change a printed answer). WP-6.1 deliverables created:
  `docs/plan/security-threat-test-mapping.md` (every Section 12.1 threat + the 12.3
  limitations mapped to named tests/review steps; 12.5 properties; FR-SEC-05; the
  Section 12.2 cell-coverage index; Section 18 Security-row crosswalk; rows
  pre-registered for MT-6.1-02…05) and `docs/plan/security-findings-log.md`
  (severity scale defined at the top per the MT risk note; findings F-01…F-04).
  Findings from this slice: **zero open critical/high** — F-01 (medium, Open:
  Section 12.5 login/token events absent, catalog-first OQ-16 blocks unilateral fix),
  F-02 (low, Fixed: viewer read-only had no automated assertion), F-03 (medium,
  Open: live Cloudflare edge layers operator-pending — MT-5.2-01/04 blocker class;
  compensating Django controls enumerated in the log), F-04 (low, Accepted:
  transition-endpoint deferral, plan-owned). New CI-enforced tests
  `backend/tests/test_security_authorization_review.py` (15): events URLConf holds
  only the two read routes; neither viewer class declares a mutation handler;
  POST/PUT/PATCH/DELETE on `/api/v1/events`(+`/stream`) refuse through the catalog
  envelope with **zero** Event rows written (F-02's fix); a real API write stores the
  session actor **and** the client-supplied `X-Correlation-ID` verbatim (Section 12.5
  API-path half); FR-SEC-05 device and agent endpoints observed tripping the
  `RATE_LIMITED` envelope end-to-end inside this WP's own selector. Matrix parity,
  cross-project denial, kind separation, revocation and insert-only audit-role claims
  re-verified from the standing suites (MT-1.2-07/MT-1.9-04/MT-5.3). Evidence:
  `pytest backend/tests/ -k authorization -v` → **60 passed** (45 standing + 15 new);
  full standing suite green at baseline before this slice (1616 passed, 4 skipped).
  Recorded choice (MT risk note): no `docs/security/` area invented — mapping and log
  live under `docs/plan/` beside the other process artifacts.
- **MT-6.1-02 — Test upload abuse cases: traversal, oversized, spoofed MIME (done).**
  New CI suite `backend/tests/attachments/test_upload_abuse.py` (15) attacks the
  WP-1.11/WP-1.12 intake per Sections 12.1/12.3/18, every case asserting a canonical
  Section 9.2 envelope and **no write outside the storage root** (recursive
  inside-root + no-symlink assertions on the isolated media root). Traversal: raw
  `../` names, percent-encoded `%2e%2e%2f`, absolute POSIX/Windows paths and
  symlink-style labels all normalize to a bare basename at the service layer and
  land only under the content key `objects/<aa>/<digest>` (the wire multipart path
  asserts the same boundary; names normalizing to nothing refuse `VALIDATION_ERROR`);
  an upload whose final component is the literal label `..` is proven inert —
  metadata only, never joined into a path — and recorded as findings-log **F-05**
  (low; cosmetic hardening belongs to WP-1.11's owner, not a silent cross-WP edit).
  Oversized: beyond `ATTACHMENT_MAX_FILE_BYTES` → 400 with **no partial artifact, no
  row, no worker hand-off**; empty/zero-byte bodies likewise. Spoofed MIME: ELF-as-`.png`
  and PNG-as-`.pdf` (and octet-stream smuggling) → 415 from **content sniffing**;
  a truthful upload under a generic declaration takes the sniffed type — the client
  header is never trusted (Section 9.5). Worker separation (Section 12.1): the web
  request stores + hands off only (row stays `uploaded`, one seam invocation, zero
  inline pipeline events); the seam's real target is the Celery job
  `attachments.process_attachment` wired by `AttachmentsConfig.ready()` — asserted
  by configuration. Section 12.3 limitations recorded in the mapping, not papered
  over: OS-level sandboxing post-v1 (L2), optional AV absent (L3). Fixtures stay
  inert/synthetic (Section 20.4 item 3 spirit). Mapping rows 10/L2/L3 and the
  Section-18 crosswalk updated; findings log appended (zero open critical/high from
  this slice). Evidence: `pytest backend/tests/ -k upload_abuse -v` → **15 passed**.
- **MT-6.1-03 — Audit token lifecycle: scoping, expiry, revocation, hashing (done).**
  New CI suite `backend/tests/test_token_lifecycle.py` (15) is the single lifecycle
  view over the three Section 12.2 kinds, extending MT-1.2-07/MT-1.2-06/MT-5.3 on
  the real routes: cross-project denial end-to-end (`AUTH_FORBIDDEN_PROJECT` on a
  foreign `/work`; a crafted body `project_id` never widens scope — Section 9.3 step
  1); expiry enforced on the very next request for agent, device **and** owner-session
  rows, with the configured lifetimes recorded and pinned per the MT risk note
  (owner 12 h / agent 720 h / device 90 d — `ORCHESTRATOR_TOKEN_LIFETIME_*`);
  revocation of agent tokens and devices (the device's SSE stream-reconnect twin
  rides `test_device_revocation.py` — Section 19 WP-5.3 re-verified); hash-at-rest
  proven across all three kinds after real issuance (no plaintext in any `ApiToken`
  column; stored form is a derived 64-hex digest — property, not schema); kind
  separation (closed three-value enum; owner cookie on agent rows, agent bearer on
  Owner routes, device bearer on Owner mutations each `ROLE_NOT_PERMITTED`); edge
  identity headers alone authenticate nothing on events and agent routes (15.3).
  Biometric release stays honestly client-side (ADR-006) — backend asserts the
  release contract; the app half is `mobile/test/security/auth_gate_test.dart` +
  `lock_gate_test.dart`. Revocation/login **audit events** remain the OQ-16 catalog
  gap — pinned by a drift-guard test, never faked (findings log F-01); rate limiting
  is asserted once in MT-6.1-01's slice and cited here (MT scope). Mapping rows 7
  and the 15.3 row updated; findings log appended (no new findings). Evidence:
  `pytest backend/tests/ -k token_lifecycle -v` → **15 passed**.
- **MT-6.1-04 — Audit secrets and log scrubbing: no tokens, no attachment text (done).**
  New CI suite `backend/tests/test_log_scrubbing.py` (9) drives the sensitive flows
  (login success **and** failure, agent-token issuance, device registration, an
  agent bearer request, attachment upload, a deliberately crashing view) through
  the real middleware/views while the root logger is captured through the
  **production** `JsonFormatter` at DEBUG: no password, issued token, push token,
  Authorization header value, upload bytes or filename reaches any line; the
  exception path logs a scrubbed traceback (`[REDACTED]`) with the correlation id
  intact (NFR-10 — scrubbing never removes the join key); long attachment-derived
  text truncates per Section 12.4 even at DEBUG; the request-completed line's
  shape cannot hold a header or body field. Per the MT risk note, assertions
  build their probes from the **runtime redactor's own registered key names**
  (`apps/core/scrub.py`) — no hardcoded pattern copy that could drift. Bridge
  counterpart: four `redaction`-selected cases appended to
  `bridge/tests/test_logging.py` (every registered secret key/suffix, every log
  level including DEBUG, exception tracebacks, correlation survival). Repository
  half: the exact CI gate executed — `uvx pre-commit run detect-secrets
  --all-files` **passed** over the whole worktree, and the WP's new files pass
  `--files` scanning (two markdown rows carry the standard
  `pragma: allowlist secret` for keyword-shaped prose — flagged and fixed, never
  silenced); zero unreviewed hits. R5 diff-pattern scan stays by pointer
  (WP-2.10/Policy Engine). Mapping Section 4 + row 11 + crosswalk updated;
  findings log appended (zero findings — zero open critical/high from this
  slice). Evidence: `pytest backend/tests/ -k log_scrubbing -v` → **9 passed**;
  bridge `-k redaction` → **4 passed**.
- **MT-6.1-05 — Run the dependency audit and remediate findings (done).**
  All four packages plus the infra-image inventory audited at full review depth
  with the CI gate's own tooling. **Backend/bridge:** `uvx pip-audit --path
  backend/.venv` and `--path bridge/.venv` (any-severity threshold) → no known
  vulnerabilities. **Web:** `npm audit --audit-level=critical` passes; the full
  tree's 9 high entries decomposed to two root causes. (1) **Fixed — findings-log
  F-06:** three high js-yaml DoS advisories (GHSA-52cp-r559-cp3m,
  GHSA-5p4m-2wfm-xmqj, GHSA-2883-xcg3-v3hh) reached the tree via
  `@hey-api/openapi-ts → @hey-api/json-schema-ref-parser → js-yaml@4.2.0`; npm's
  offered fix was a breaking **downgrade** (rejected), so the documented exception
  process applied its preferred path — a **scoped override** pinning the fixed
  release: `web/package.json` → `"overrides": { "@hey-api/json-schema-ref-parser":
  { "js-yaml": "^4.3.2" } }` (resolution verified, no other consumer forced).
  Web contract battery re-run after regeneration: `tsc --noEmit` clean, `eslint`
  clean, vitest **442 passed (55 files)**. (2) **Accepted risk — F-07:** the
  braces chain (root GHSA-vfj7-8cjw-p6xm, CVSS 7.5 dev-only DoS; 5 npm entries
  via micromatch/fast-glob/@next/eslint-plugin-next/eslint-config-next) — no fixed
  braces release exists upstream; `npm audit fix --force` would downgrade
  eslint-config-next (rejected); identical justification, owner (repository
  maintainer) and revisit already recorded next to the CI threshold in
  `.github/workflows/security.yaml`. After remediation the web tree carries
  **exactly the one logged accepted risk, zero critical**. **Contract stability
  (NFR-11):** generation from the current canonical schema succeeds with the
  override; `npm run check:api` exits 1 in this worktree only because it diffs
  against the last commit while batch 11 carries an **uncommitted**
  `schemas/openapi.yaml` delta (notification preferences) — the same failure
  reproduces with the override removed (recorded baseline experiment), so it is
  a worktree-commit condition, not a regression; the regenerated client was left
  in sync with the schema (the gate's own remedy) and is green under
  typecheck/tests for whoever commits the schema. **Infra images:** pins
  inventoried (`postgres:16-alpine`, `redis:7.4-alpine`,
  `cloudflared:2026.10.0`, `mailhog:v1.0.1`, local backend/web); image CVE
  scanning has no gate and wiring one is out of this MT's scope → **F-08**
  (low, release-owned, WP-6.6 revisit). **Mobile (pub):** no `pub audit` CLI —
  remains the MT-0.3-04 recorded out-of-scope note. Mapping dependency row +
  crosswalk updated; findings log appended. **WP-6.1 acceptance: zero open
  critical/high findings** (F-06 fixed; F-07 accepted with justification;
  F-05/F-08 low).

### WP close (verification evidence)

* Standing suites stay green: backend `pytest tests/ -q --ignore=tests/integration`
  → **1670 passed, 4 skipped** (baseline 1616 + 54 new); bridge
  `pytest -q` → **826 passed, 14 skipped** (baseline 822 + 4 new); web vitest
  → **442 passed (55 files)** with `tsc --noEmit` + `eslint` clean.
* CI-parity gates: backend/bridge `ruff check` + `ruff format --check` and
  `mypy .` → clean (423 / 166 files); detect-secrets over every tracked file
  and over this WP's new files → clean (fixture secrets carry
  `pragma: allowlist secret`).
* Per-slice selectors: `-k authorization` → 60 · `-k upload_abuse` → 15 ·
  `-k token_lifecycle` → 15 · `-k log_scrubbing` → 9 · bridge `-k redaction` → 4.
* Deliverables indexed in `docs/plan/README.md` (mapping + findings log rows).
* Findings close: 8 total — zero open critical/high; 1 high fixed (F-06),
  1 high accepted with owner+revisit (F-07), 1 fixed low (F-02),
  1 accepted low (F-04), 4 open (2 medium blocked on owner/operator decisions,
  2 low follow-ups).
