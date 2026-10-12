# WP-1.2 — Accounts, tokens and permissions: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.2-01** — Owner session authentication (Sections 9.2 Auth row, 12.2,
  7.1/7.2, 9.10; FR-SEC-02, NFR-07; ADR-006 layer 1). `backend/apps/accounts/`
  lands as the modular slice: `models/users.py` (`User(AbstractUser)` — the
  minimal Section 7.1/7.2 owner account, Django password hashing so plaintext
  passwords never reach the database; **no TOTP fields** — OQ-09's recommended
  v1 default is "strong password plus optional TOTP", TOTP is the Section 12.2
  *Could* and no WP-0.4 decision mandates it in v1, so it stays a later
  hardening item), `models/tokens.py` (`TokenKind` three-value enum + the
  `ApiToken` row with the MT-1.2-01 slice: `kind`, `hash` (unique, the only
  secret representation), `user`, `expires_at`, `revoked_at`, `last_used_at`;
  `is_valid()` is the per-request revocation/expiry predicate — no cache, so
  revocation takes effect on the very next call), `services/tokens.py`
  (generation + hashing helpers), `services/sessions.py` (session lifecycle),
  `authentication.py` (cookie authentication bound to a live token row),
  `permissions.py` (`IsOwnerSession`, first Section 12.2 matrix class),
  `serializers/auth.py`, `views/auth.py`, `urls.py`.
  Endpoints: `POST /api/v1/auth/login` (verify credentials, start the session,
  return the plaintext binding exactly once with `expires_at` + minimal user
  summary), `POST /api/v1/auth/logout` (revoke immediately, idempotent),
  `POST /api/v1/auth/refresh` (extend a *live* session only — authentication
  rejects revoked/expired rows before the view runs, so refresh can never
  resurrect one). Failures use only the Section 9.2 catalog codes in scope:
  `AUTH_REQUIRED` (bad credentials, missing/dead session, missing CSRF) and
  `VALIDATION_ERROR` (malformed body); these endpoints are not throttled —
  FR-SEC-05 scopes rate limiting to agent/device endpoints (MT-1.2-06).
  **Storage mechanics (recorded per the MT risk note, Section 12.2 followed
  literally — no second auth path invented):** the session lives in a
  **signed-cookie** Django session (secure, HTTP-only cookie; no plaintext
  session credential in any table), and every login additionally writes one
  `owner_session` API Token row whose `hash` binds a random value stored
  inside the signed session data. The row is the revocation authority: signed
  cookies are stateless and otherwise un-revokeable, but authentication
  re-reads the row on every request (fail-closed on unbound/revoked/expired),
  so logout and expiry hit both transports at once. The binding returned as
  the response's `token` doubles as the Section 15.4 bearer credential for
  token-auth clients (web clients ignore it); the `Authorization: Bearer`
  class that consumes it lands with MT-1.2-03 — both forms hash to the same
  row. CSRF: DRF's session-auth `PermissionDenied` is re-raised as
  `AuthenticationFailed` so a missing/wrong `X-CSRFToken` answers the
  documented 401 `AUTH_REQUIRED` rather than `ROLE_NOT_PERMITTED` (Section
  20.4 item 5 — wrong-role semantics would misdescribe a request that merely
  arrived without the CSRF half of its credentials); the login response marks
  the `csrftoken` cookie for delivery. **Configuration:** one new canonical
  setting `ORCHESTRATOR_TOKEN_LIFETIME_OWNER_SESSION_HOURS` (Section 9.10
  group `TOKEN_LIFETIME_`, positive integer, default **12 hours — flagged for
  owner confirmation**) drives both the row's `expires_at` and the session
  cookie max-age; documented in configuration.md and `.env.example`.
  Settings gained a hermetic `apps/core/settings/test.py` (SQLite in-memory +
  LocMem cache, inherited from `dev`) so the CI unit job runs without service
  containers; pytest selects it via `DJANGO_SETTINGS_MODULE` (pytest-django
  added, dev group, locked). OpenAPI: the three endpoints plus a
  `sessionAuth` cookie security scheme (drf-spectacular authentication
  extension) are in the regenerated `schemas/openapi.yaml` snapshot.
  Tests (`backend/tests/test_owner_session_auth.py`) cover login cookie
  security (`HttpOnly` sessionid + csrftoken), hashed-only storage (password
  and token), immediate logout revocation including a replayed pre-logout
  session cookie (proving the row — not the cookie — is the authority),
  refresh extend/cannot-resurrect, expiry failure, lifetime from settings,
  bad credentials, validation and anonymous codes, and the CSRF-required
  mutation path. Verified: `ruff check`/`format --check`, `mypy .`,
  `manage.py check`, `makemigrations --check --dry-run` clean; migrations
  split per Section 20.3 (`0001_initial` = `User`, `0002_apitoken` = token
  row).
- **MT-1.2-02** — API token model completed with hashed storage and expiry
  fields (Sections 7.2, 7.3, 7.4; FR-SEC-01/02/04; ADR-004).
  `backend/apps/accounts/models/tokens.py` now carries exactly the Section
  7.2 field set on top of MT-1.2-01's slice — `kind` (closed three-value
  enum), `hash`, `user` (Section 7.1 N:1), **`project_id`** (new),
  **`scopes`** (new), `expires_at`, `revoked_at`, `last_used_at` — with its
  own standalone migration (`0003_apitoken_project_id_apitoken_scopes_and_more`,
  Section 20.3; forward apply **and reverse verified** on the hermetic SQLite
  test settings). **Decisions recorded per the MT risk notes:**
  *Hash algorithm:* **SHA-256, hex-encoded (64 chars)**, chosen as the fast,
  unsalted lookup hash — correct here precisely because the input is 256-bit
  `secrets.token_urlsafe` randomness, not a guessable password (salting/slow
  hashing would add cost without security for high-entropy bearer material;
  password hashing remains Django's PBKDF2 in `User.password`). The value is
  the unique lookup index authentication performs per request; consistent for
  every token kind through MT-1.2-03+. No code path may store, log or return
  the plaintext (Section 7.2; FR-SEC-04) — a test proves plaintext never
  appears in any model field, `str()`/`repr()` or API response body, and that
  `hash` itself never appears in an API representation either (risk note).
  *`project_id` representation:* the canonical Section 7.3 identifier string
  (`PID` + five digits, `validate_project_id` at API boundaries) rather than a
  foreign key — the Project registry belongs to WP-1.3 (scope guard: this
  work package does not model projects) and the string is exactly what
  ADR-004's scope comparison uses. Two database `CheckConstraint`s make a
  malformed row impossible: `kind = agent` ⇒ `project_id IS NOT NULL`, and any
  stored `project_id` matches the PID regex (7.3: validated at boundaries
  *and* by DB check); model `clean()` mirrors the agent rule so serializers
  get a field error. *`scopes` representation:* a JSON list (default `[]`)
  carrying the Section 12.2 agent role names (`coder`, `auditor`,
  `decomposer`, `merge_executor`) — the MT-1.2-05 risk-note reading recorded:
  roles ride on agent-token scopes, kinds stay closed at three (no fourth
  kind invented); scope *evaluation* lands with MT-1.2-05, this MT only
  stores/round-trips the list. *Canonical validity predicate:* `is_valid()`
  (not revoked, not expired — evaluated per request against the row, no
  cache) + `matches_project()` (ADR-004: only `agent` is project-bound;
  owner sessions/devices address any project) + `is_usable_for(project_id)`
  combining both — the single source MT-1.2-03/05 authentication checks
  call. Tests (`backend/tests/test_api_token_model.py`, `-k token`) cover
  agent-requires-project at model *and* DB level, PID format enforcement,
  all three kinds across revoked/expired/live states, cross-project
  mismatch, hashed-only storage, hash-free API bodies and scopes
  round-trip. Verified: `ruff check`/`format --check`, `mypy .`,
  `manage.py check`, `makemigrations --check --dry-run` green (tooling note:
  django-stubs still spells `CheckConstraint(condition=…)`; Django 5.1+
  renamed it `check=` — ignored with a comment, runtime signature verified
  on Django 5.2).
- **MT-1.2-03** — Project-scoped agent token issuance, listing and
  revocation (Section 9.2 Tokens row, caller Owner; FR-SEC-01/02; ADR-004,
  G-07). Endpoints: **`POST /api/v1/tokens/agent`** (201; body
  `project_id` + optional `scopes`; response carries the plaintext bearer
  token **exactly once** alongside id/kind/project_id/scopes/expires_at —
  the response contract is pinned by a test per the MT risk note, and the
  row stores only SHA-256(hash) with `kind = agent`, one `project_id`, and
  expiry from the new `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS`),
  **`GET /api/v1/tokens`** (Owner's own rows, metadata only — never `hash`
  or plaintext; filterable by `kind`/`project_id`; cursor-paginated with
  the exact pagination.md envelope `results` + `next_cursor` and canonical
  `cursor`/`page_size` parameters — default 25, documented maximum 100
  **clamped** per endpoint, declared sort: **id descending, newest first**
  because `BigAutoField` ids are monotonic, satisfying pagination.md rule 2
  without inventing a `created_at` the Section 7.2 field set does not
  have), **`DELETE /api/v1/tokens/{id}`** (sets `revoked_at` once —
  idempotent like logout — and the token fails its very next request:
  WP-1.2 acceptance "revoked tokens fail immediately", per-request row
  validation with **no cache**, recorded here per the risk note). Unknown
  and foreign token ids answer identically (`NotFound` → documented
  `VALIDATION_ERROR` mapping; no generic 404 code exists, and differing
  answers would probe token existence). **Bearer authentication:**
  `TokenBearerAuthentication` resolves `Authorization: Bearer <token>` for
  any Section 7.2 kind by hashing to the same stored representation — so
  revocation/expiry hit cookie and bearer transports simultaneously, the
  Section 15.4 token-auth transport of owner sessions works, and
  `last_used_at` (Section 7.2) is written on every successful
  authentication through the shared `mark_token_used()` primitive now used
  by both auth classes. It is registered **before** the cookie authenticator
  (explicit header beats ambient cookie) and declared in OpenAPI as the
  `bearerAuth` HTTP scheme (opaque, never JWT). Project scope is *not*
  checked in authentication — ADR-004's guard belongs to permission checks
  (MT-1.2-05, Section 9.3 step 1: resolve project from the token). Wrong
  role on Owner-only rows answers `ROLE_NOT_PERMITTED` (403); unauthenticated
  `AUTH_REQUIRED` (401); malformed input `VALIDATION_ERROR` — closed catalog
  only. **Shared plumbing:** `apps/core/pagination.py` (Section 9.1 assigns
  pagination to core) implements the one cursor mechanism — opaque urlsafe
  base64 key, first page without cursor, `next_cursor: null` exactly at
  end-of-list, page-size clamping — reusable by WP-1.3/1.4 list endpoints;
  `TokenSummarySerializer` omits `hash` by construction (risk note: a
  returned hash would leak every token — a test asserts no response body
  ever contains one). **Configuration:** `ORCHESTRATOR_TOKEN_LIFETIME_AGENT_HOURS`
  now consumed with default **720 hours / 30 days** (Section 12.2
  "long-lived but revocable" — **flagged for owner confirmation**; the
  DEVICE setting stays reserved until MT-1.2-04); configuration.md and
  `.env.example` rows updated. **Scopes vocabulary:** issuance validates
  `scopes` against the closed Section 12.2 agent roles (`coder`, `auditor`,
  `decomposer`, `merge_executor` — `AGENT_ROLE_SCOPES`, evaluation lands in
  MT-1.2-05); unknown roles are a 400, never silently dropped. **Open
  deviation (WP-1.3 seam, no hidden decision):** the MT asks issuance to
  reject a *nonexistent/non-active* project — the Project registry is
  WP-1.3's deliverable and out of this work package's scope, so issuance
  validates the Section 7.3 PID **format** only (model + serializer + DB
  check); existence/active-status joins when the registry lands (comment
  seam in `issue_agent_token`). Tests
  (`backend/tests/test_agent_token_endpoints.py`, `-k token`): one-time
  plaintext + hash-only storage, exact response/list contracts, Owner-only
  enforcement (anonymous 401 / agent 403 with catalog codes), PID and scope
  validation, lifetime from settings, bearer success updating
  `last_used_at`, revoked/expired tokens failing on the very next request,
  idempotent revoke, unknown/foreign id equivalence, cursor pagination
  (order, next_cursor/null end, clamped page_size, malformed cursor →
  VALIDATION_ERROR), filters, and unguessable minting. OpenAPI snapshot
  regenerated (0 warnings: `sessionAuth` + `bearerAuth` schemes, the three
  token operations, two-member envelope, canonical query parameters).
  Verified: `ruff check`/`format --check`, `mypy .` (70 files),
  `manage.py check`, `makemigrations --check --dry-run` clean (no model
  change in this MT — no migration).
- **MT-1.2-04** — Device token model for mobile registration (Section 9.2
  Devices row; Sections 7.1/7.2/12.2/12.4; FR-SEC-02/05; ADR-006).
  `backend/apps/accounts/models/devices.py` adds `Device` with **exactly**
  the Section 7.2 field set — `id`, `user_id` (FK to the owner account),
  `platform`, `push_token`, `token_id` (FK to the `kind = device` API
  Token), `biometric_bound`, `last_seen_at`, `revoked_at` — standalone
  migration `0004_device` (Section 20.3; forward apply **and reverse
  verified** on the hermetic SQLite settings). Endpoints:
  **`POST /api/v1/devices`** (Section 12.2 "device registration after Owner
  login" — guarded by `IsOwnerSession`, so the mobile app's owner-session
  credential works on both transports while an agent token gets
  `ROLE_NOT_PERMITTED`) creates Device + device token **in one
  transaction** (`register_device` — no credential without a device, no
  device without a credential) and returns the plaintext **once** for the
  client's platform secure storage; only the SHA-256 hash is stored, and
  the sensitive `push_token` (Section 12.4) is **never echoed** in any
  response (the log scrubber already redacts `*_token` keys — MT-1.1-02).
  **`DELETE /api/v1/devices/{id}`** revokes device **and** token together
  in one transaction (`revoke_device`, idempotent — original `revoked_at`
  preserved), so losing a phone is one action that kills both rows and the
  credential fails its very next request (lost-phone threat, Section 12.1;
  FR-SEC-02 independent revocation). Unknown/foreign device ids answer
  identically (`NotFound` → documented `VALIDATION_ERROR`) — no probing.
  **Bearer authentication** (`TokenBearerAuthentication`) gained the
  device half of ADR-006: a `kind = device` credential additionally requires
  a live, non-revoked Device row (fail closed against any partial state —
  belt beyond the paired writes) and maintains **`last_seen_at`** on every
  successful use, alongside the shared `last_used_at` marker
  (`mark_token_used`). **Distinct kind** proven by test: device tokens are
  `kind = device`, never confused with owner sessions or agent tokens
  (FR-SEC-02: each kind separately revocable). **Flagged decisions (MT
  risk note — defined minimally, recorded, not guessed twice):**
  *`platform` vocabulary* — the plan ships iOS and Android flavors but pins
  no enum, so the model fixes the closed `ios`/`android` `Platform` choices
  (rejecting anything else with `VALIDATION_ERROR`);
  *`biometric_bound` arrival* — the plan says the client releases the token
  only after biometric success but not how the flag reaches the server, so
  registration accepts it as an **optional boolean, default `false`**, and
  the server merely records it (enforcement is Flutter-side, FR-MOB-06/M5);
  *`push_token` requirement* — required in the registration payload per the
  MT scope ("payload carrying platform and push_token"). **Configuration:**
  `ORCHESTRATOR_TOKEN_LIFETIME_DEVICE_DAYS` now consumed with default
  **90 days** (**flagged for owner confirmation**; expiry is secondary to
  remote revocation as the lost-phone control) — configuration.md and
  `.env.example` rows updated; all three Section 9.10 token lifetimes now
  carry documented defaults. Tests (`backend/tests/test_device_registration.py`,
  `-k device`): one-transaction registration with hash-only storage and no
  `push_token` echo, exact response contract, Owner-only guard (401/403
  catalog codes), payload validation with biometric defaulting, lifetime
  from settings, bearer authentication updating both presence fields,
  combined revocation failing on the next request, idempotent repeat, and
  unknown/foreign id equivalence. OpenAPI snapshot regenerated (0 warnings:
  `POST /devices`, `DELETE /devices/{id}` + request/response components).
  Verified: `ruff check`/`format --check`, `mypy .` (76 files),
  `manage.py check`, `makemigrations --check --dry-run` clean.
- **Post-termination verification addendum (MT-1.2-01..04 gap closure,
  2026-10-12)** — the abrupt end of the previous session left five test
  failures behind its "verified" changelog claims; all five are closed:
  (1) `POST /auth/login` with bad credentials now raises the new
  `AuthRequired` APIException (401 `AUTH_REQUIRED`) from
  `apps/accounts/exceptions.py` — DRF coerces its built-in
  `AuthenticationFailed` down to **403** whenever a view has no
  authenticator to produce a `WWW-Authenticate` challenge, which is exactly
  the `authentication_classes = []` case of the login view; the catalog code
  is unchanged, only the built-in coercion is bypassed. (2) Generic
  `NotFound`/`MethodNotAllowed` now answer **400** with `VALIDATION_ERROR`
  (`_STATUS_BY_EXCEPTION_TYPE` in `apps/core/exceptions.py`) — the code
  mapping already existed but the status stayed 404/405 while every view's
  `extend_schema` (and therefore the OpenAPI snapshot) documents 400 for
  that mapping; status and code now match the contract as one pair.
  (3) `test_refresh_extends_session_and_cannot_resurrect_it` made
  deterministic: login and refresh a few milliseconds apart can land inside
  the same system-clock tick, producing byte-identical expiries and a flaky
  `>`; the test now shrinks the row's remaining lifetime to one hour first,
  so the extension is observable by hours. (4)
  `test_unknown_and_malformed_bearer_credentials_fail_with_auth_required`
  gained the missing `db` fixture (the 500 was pytest-django's DB-access
  block, not a product defect). (5) The cursor-pagination test pages over
  `kind=agent` rows — login's own `owner_session` row shares the table and
  legitimately spills onto page two, which would test the filter rather than
  the cursor (the unfiltered shape is still asserted). All four MT test
  files green again: 52 passed.
- **MT-1.2-05** — Permission classes enforcing the Section 12.2
  authorization matrix (Sections 12.2, 6.4, 9.2; FR-SEC-01/02, NFR-07;
  ADR-004/ADR-006, G-07). `backend/apps/accounts/permissions.py` ships one
  **named class per printed matrix row** — `CanManageProjects`,
  `CanCreateDraftTasks`, `CanPublishTasks`, `CanClaimPendingTasks`,
  `CanClaimAuditTasks`, `CanSubmitResolution`, `CanSubmitAuditVerdict`,
  `CanReviewDecisions`, `CanReadMergeQueue` + `CanOperateMergeQueue` (the
  *Merge queue* row splits because the Owner cell is *Read*: reading is
  Owner+Merge-Executor, `start`/`result` are the executor's alone),
  `CanReadEvents` (no agent branch by design — Section 9.6: agents never
  subscribe to events, whatever their scopes) — plus `IsOwnerSession` (the
  Section 9.2 Owner-caller guard for auth/token/device management; the
  matrix has no row for those, hence its own name) and `HasProjectScope`
  (ADR-004/G-07: the addressed PID comes from the **URL** under
  `project_url_kwarg` — never the body — and mismatches raise
  `AuthForbiddenProject` → `AUTH_FORBIDDEN_PROJECT`, listed first so
  Zero-Bleed outranks role errors). **Recorded readings (risk note):**
  roles ride on agent-token `scopes` — kinds stay closed at three; the
  Device `Create draft tasks: Yes (Could)` cell is **granted** (the mobile
  app already holds publish/review in the same matrix); lease-owner
  qualifiers (claim / resolution / verdict) stay coarse here — WP-1.5/1.6
  narrow them at the transition layer. **Codes:** no credential →
  `AUTH_REQUIRED`, wrong kind/role → `ROLE_NOT_PERMITTED`, cross-project →
  `AUTH_FORBIDDEN_PROJECT`, nothing invented (20.4 item 5); `/health/live`
  and `/health/ready` remain unauthenticated (MT-1.1-03). New coverage test
  `backend/tests/test_permission_classes.py` cites every §12.2 row verbatim:
  the full 10-row × 7-actor grant/deny grid (owner, coder, auditor,
  decomposer, merge_executor, device, anonymous), a traceability test that
  fails if a row or a `Can*` class goes missing or a docstring stops citing
  its row, `IsOwnerSession`, `HasProjectScope` unit cases (URL-vs-body both
  directions, non-agent pass-through, no-PID routes, overridable kwarg), the
  Section 9.6 agent-events denial, and the health smoke. Verified: 84 tests
  green (`pytest tests/test_permission_classes.py -q`), `ruff check`/
  `format --check`, `mypy .`, `manage.py check`, `makemigrations
  --check --dry-run` clean. Endpoint wiring: rows with endpoints today are
  already guarded; the capability classes are the seam WP-1.3/1.4 endpoints
  use by simply naming their row class.
- **MT-1.2-06** — Rate limiting on agent and device endpoints (Sections 9.1
  `core` responsibility, 9.10, 12.3; FR-SEC-05). New
  `backend/apps/core/throttling.py`: `TokenKeyedRateThrottle` base — budget
  keyed on the **authenticated token id** (`request.auth.pk`) with a client-
  address fallback for unauthenticated callers (Section 12.3 layering; two
  sessions/agents never share a budget, revoking a token frees its key) —
  and the two named scopes `AgentEndpointThrottle` (`agent`) and
  `DeviceEndpointThrottle` (`device`). `get_rate()` re-reads `api_settings`
  per request (the DRF base class binds rates once at import; dynamic reads
  keep `settings` overrides — pytest-django's fixture — honest). Wired
  today: both device endpoints (`POST /devices`, `DELETE /devices/{id}`)
  carry `DeviceEndpointThrottle` and document the **429 → ErrorEnvelope**
  response (regenerated snapshot: the two `429` entries are the reviewed
  schema diff, 20.4 item 4). Agent-facing endpoints join by naming
  `AgentEndpointThrottle` as WP-1.4/1.5/1.6/2.x/3.x/1.11 land — the
  endpoint-coverage test enumerates **every Section 9.2 row whose caller is
  Agent/Auditor/Bridge/Mobile** (17 deferred routes asserted still-404 until
  their owning WP flips the row *with* the throttle wired; `GET /events*`
  deliberately absent — Owner-only caller, Section 9.6). **Envelope:**
  DRF `Throttled` → catalog `RATE_LIMITED`, HTTP 429, `retryable: true`,
  `Retry-After` set — the MT-0.5-02 mapping exercised for the first time.
  **Configuration (Section 9.10; documented defaults, no magic numbers):**
  `ORCHESTRATOR_RATE_LIMIT_AGENT_PER_MINUTE=120` and
  `ORCHESTRATOR_RATE_LIMIT_DEVICE_PER_MINUTE=60` consumed via
  `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`; configuration.md gained both
  rows (defaults **flagged for owner confirmation**, Section 20.1 item 5 —
  calculation: per-token keying means the Section 18 scenario's 20 agents
  never collide; 2 checkpoints/min per agent leaves ~118/min headroom) and
  `.env.example` now sets them, with `ORCHESTRATOR_RATE_LIMIT_API_PER_MINUTE`
  re-marked reserved for WP-6.1 (an API-wide budget would widen FR-SEC-05
  onto owner endpoints — explicitly out of scope, noted rather than
  silently added). Out of scope per the MT: edge limits (WP-3.x), anomaly
  alerts (Section 17), Redis/Celery standup (LocMem in tests, existing
  cache config in dev/prod). Tests (`backend/tests/test_rate_limiting.py`,
  23 green): under-limit pass, over-limit `RATE_LIMITED` envelope
  (code/retryable/correlation-id/Retry-After), per-token budget separation
  (second login gets a fresh budget), window reset, owner-session endpoints
  unaffected (behavioral burst + static `throttle_classes` declaration
  check), the endpoint enumeration, the settings contract, and the
  token-vs-address key fallback.
- **MT-1.2-07** — Authorization-matrix tests incl. cross-project rejection
  (Sections 12.2, 18 Security layer, 19.1 WP acceptance; FR-SEC-01/02/05,
  NFR-07; ADR-004, G-07). `backend/tests/test_authorization_matrix.py`
  (37 green) is the executable proof of the whole WP:
  *data-driven grid* — `PROBES` restates every §12.2 row with its printed
  cells for all seven actors and runs each cell against the **running API
  with real credentials**: owner session (cookie), four agent bearer tokens
  issued through the real `POST /tokens/agent` with the matching scope, and
  a device bearer from the real `POST /devices`; every probe mounts the
  real permission class of MT-1.2-05 behind a test-only URLConf that is
  switched on **after* fixture traffic completes (the real `/api/v1`
  surface is included in that URLConf, so revocations in-test hit the actual
  endpoints). Assertions per cell: 200 allowed / 401 `AUTH_REQUIRED`
  anonymous / 403 `ROLE_NOT_PERMITTED` wrong role — catalog-closed.
  *WP-1.2 acceptance, explicitly:* a PID00001 decomposer token addressing
  `PID00002` receives `AUTH_FORBIDDEN_PROJECT`, and revoked agent, device
  and owner-session credentials each fail on their **very next request**
  (revoke via the real `DELETE /tokens/{id}`, `DELETE /devices/{id}` and
  logout respectively). *Body cannot widen:* a body pleading the token's own
  PID on another project's URL is rejected, and a body pleading another
  project on the token's own URL is ignored — scope = token + URL, always.
  *Rate-limit case:* a burst on the real device endpoint answers
  `RATE_LIMITED` (429, `retryable: true`). *Traceability/drift guards:*
  `test_every_matrix_row_is_exercised_for_every_actor` fails if any row/actor
  cell loses its case, and `DEFERRED_ENDPOINTS` (the 28 Section 9.2 routes
  that do not exist after WP-1.2) are asserted still-404 — the first WP to
  land one fails this suite until its probe/deferral becomes a real
  authorization case, so an untested row is never silently green (risk
  note). *Probe seam recorded (no hidden decision):* no §12.2 capability row
  has a real endpoint until WP-1.3+, so probes give the rows behavioral
  coverage now; per the MT risk note the bare PID00001/PID00002 fixtures
  switch to API-created projects the moment WP-1.3's registry lands.
  Verified: `pytest tests/test_authorization_matrix.py -q` green; runs in
  CI's unit job (Security layer) via the existing `pytest` step. Changelog
  complete — WP-1.2 slices all delivered.
