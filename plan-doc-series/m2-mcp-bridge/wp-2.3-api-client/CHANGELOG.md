# WP-2.3 — Backend API client: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.3.

## 2026-10-12 — MT-2.3-01: Implement the transport and authentication layer

* `orchestrator_bridge.api_errors` — the typed client error
  (`ApiError`) carrying Section 9.2's five envelope fields **verbatim**
  (`code`, `message`, `retryable`, `details`, `correlation_id`) plus
  `status_code` and an `ErrorKind` for the three parsing paths
  (`envelope`, `malformed_response`, `transport_failure`). The catalog is
  mirrored as the closed `ErrorCode` StrEnum (19 codes, published order,
  error-envelope.md): the transport can never emit an uncatalogued code
  (Section 20.4 item 5) — an envelope with an unknown code degrades to
  `SERVER_ERROR` with the upstream value preserved in
  `details.upstream_code`. `str(ApiError)` is log-safe: code, HTTP status,
  backend message — never a token or body.
* `orchestrator_bridge.transport` — `ApiClient`, the raw HTTP layer every
  tool call will pass through: stdlib-`urllib` send behind one injectable
  `SendFn` seam (tests mock at the HTTP boundary — deterministic, no live
  backend per the concurrent-agent protocol); `request()` returns the decoded
  JSON body, `exchange()` the full status/headers/body response.
  * **Headers on every request** (AC 1): `Authorization: Bearer <token>`
    resolved through WP-2.2's `require_agent_token()` *per call* — `Settings`
    stays the single holder/redaction boundary (no second copy on the client,
    no token in any URL, repr, log line or error — asserted by tests);
    `X-Correlation-ID` from the correlation scope, honor-or-generate per
    headers.md; plus the API version header below.
  * **Base URL precedence (WP-2.2's flagged deferral, resolved here):** the
    bound manifest's `orchestrator_api` wins (`ApiClient.for_binding`),
    `settings.api_base_url` is the defensive fallback when the key is absent
    (the schema requires it). Catalog paths are origin-absolute
    (`/api/v1/...`, Section 9.2 base path); a path without a leading slash
    joins relative to the base URL (path-prefixed proxy deployments).
  * **Envelope parsing (AC 2):** strict parse of the five required fields —
    anything not conforming (bad JSON, wrong nesting, missing field,
    non-boolean `retryable`) degrades to a `SERVER_ERROR`-tagged
    `malformed_response` error instead of crashing; status still drives the
    retryable guess (5xx/408/429 yes, other 4xx no — mirroring the backend's
    own rule). Connection errors/timeouts map to retryable
    `transport_failure` errors (Section 10.10). The server's `retryable` flag
    is taken verbatim, never re-guessed, when an envelope parses.
  * **Version gate (Section 10.11, AC 3):** `verify_api_version()` probes
    `GET /health/live` through the full transport; an incompatible
    (or unparseable) advertised version raises the new
    `errors.ApiVersionError` ("upgrade the bridge or the backend") — the
    entry points' existing `BindingError` handler turns that into a clean
    startup abort. Absence of the header is *not* a mismatch (logged
    `event=api_version_unverified`).
  * **Bounds (Section 9.10):** `settings.timeout_seconds` per request
    (pre-existing) and the new `ORCHESTRATOR_BRIDGE_MAX_RESPONSE_MB`
    (default `64`, documented in `bridge/.env.example`; clears a
    base64-inflated 25 MB attachment) — an oversized body raises a
    non-retryable error naming the setting, never an unbounded read.
* **OQ candidate (MT-2.3-01 risk note honored — not invented silently):**
  the API version header name/value is fixed nowhere — not in the plan, not
  by WP-1.1 (backend sends nothing yet). Proposed: `X-API-Version: 1`
  (major only, `v1`/`1.x` accepted on read). Behavior while unsettled:
  advertise on every request, warn-and-continue when the backend is silent,
  abort only on an explicit mismatch. Also proposed for
  `docs/plan/conventions/configuration.md` (docs owned elsewhere):
  `ORCHESTRATOR_BRIDGE_MAX_RESPONSE_MB`, and for MT-2.3-02
  `ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS` /
  `ORCHESTRATOR_BRIDGE_RETRY_BASE_DELAY_SECONDS`.
* **Wiring note:** `verify_api_version()` joins the session-open startup path
  with MT-2.2-04 (deferred — `POST /agent-sessions` not yet in the backend);
  until then it is exercised directly by tests, and no entrypoint performs a
  live HTTP call at startup (existing entrypoint tests stay hermetic).
* Tests: `tests/test_transport.py` (28) — success/header assembly, scope
  propagation, token-hygiene, base-URL precedence, 401 `AUTH_REQUIRED`
  envelope, verbatim flag, malformed/structural/out-of-catalog degradation,
  transport failures, size cap, version match/mismatch/unverified, log
  hygiene. `tests/test_config.py` etc. reconciled (new key documented in
  `.env.example`, which that suite asserts exhaustively).

## 2026-10-12 — MT-2.3-02: Implement retry policy with backoff for 5xx and timeouts

* `orchestrator_bridge.retry` — `RetryPolicy` + `retry_call()`, attached to
  every client call inside `transport.exchange()` (headers prepared once per
  logical call, so each attempt replays the identical request — the ADR-012
  pairing MT-2.3-03 completes with the key itself; documented in both module
  docstrings and here per the MT's AC).
  * **Flag authority (AC 3):** classification reads only
    `ApiError.retryable` — the envelope flag verbatim when one parsed, the
    5xx/408/429 status guess for malformed bodies, `True` for transport
    failures (Section 10.10). A `retryable: false` envelope (including 5xx
    statuses, `TASK_ALREADY_CLAIMED`, `TASK_STATE_CONFLICT`,
    `VALIDATION_ERROR`) surfaces after **exactly one attempt** (AC 2); a
    `retryable: true` envelope (`RATE_LIMITED`, `SERVER_ERROR`) retries even
    on 4xx (AC 3).
  * **Bounded exponential backoff + jitter (AC 1):** `base · 2ⁿ⁻¹` capped at
    30 s, times a jitter factor in `[0.5, 1.0]`; attempt count from
    `settings.retry_max_attempts` (default 3) — the final attempt's error is
    re-raised for the tool layer, so an unreachable backend can never wedge
    an agent (NFR-04). Deterministic tests: recorded sleeps (never awaited),
    seeded `random.Random`, asserted attempt counts and delay bounds.
  * **`RATE_LIMITED` server delay:** envelope
    `details.retry_after_seconds` (positive number, capped at 120 s)
    overrides the schedule; anything else falls back to backoff (MT scope
    sentence). *Detail-key name fixed here — the plan is silent; OQ note in
    the report.*
  * **Named configuration (Section 9.10):** `ORCHESTRATOR_BRIDGE_RETRY_MAX_ATTEMPTS`
    (default 3) and `ORCHESTRATOR_BRIDGE_RETRY_BASE_DELAY_SECONDS`
    (default 1), validated fail-fast in `config.py` and documented in
    `bridge/.env.example` + `user-config.example.toml`. `transport` gains
    `sleep`/`rng` injection seams (deterministic tests); `on_retry` drives the
    structured `event=api_retry` log (attempt, delay, error code — no
    headers, no keys).
  * Proposed for `docs/plan/conventions/configuration.md` (docs owned
    elsewhere, not edited here): the two `ORCHESTRATOR_BRIDGE_RETRY_*` rows.
* Tests: `tests/test_retry.py` (23) — schedule bounds/cap, server-delay
  override/cap/invalid-fallback, single-attempt non-retryable, flag
  authority against status intuition, attempt cap + final-failure logging,
  transport-failure retries, callback contract, client end-to-end
  (5xx→timeout→success with identical headers across attempts).

## 2026-10-12 — MT-2.3-03: Implement idempotency key attachment on mutating calls

* `orchestrator_bridge.idempotency` — the bridge half of ADR-012:
  * **Header name** fixed to the canonical `Idempotency-Key` spelling from
    `docs/plan/conventions/headers.md` (WP-0.5's published convention;
    asserted by a test so a rename is impossible to slip in — no
    `X-Idempotency-Key` alias, matching the backend's
    `apps/core/idempotency.py` constant). No public-contract change: the
    OpenAPI document already declares the header on mutating operations
    (checked in MT-2.3-05); nothing in `schemas/` or tool schemas changes.
  * **Coverage:** every `POST`/`PATCH`/`PUT`/`DELETE` through
    `ApiClient.exchange()` carries a key; `GET`/`HEAD`/`OPTIONS` never do
    (headers.md defines mutating exactly this way).
  * **One logical call → one key:** the transport mints the key *before the
    first attempt* and the retry loop replays the identical header dict —
    proven by a test that drives one mutating call through 2×5xx to success
    and asserts all three boundary requests carry one identical key *and*
    byte-identical header sets (the AC-1 guarantee, and the safety
    dependency MT-2.3-02's changelog entry names). Two separate calls — even
    to the same endpoint — always differ.
  * **Key shape:** `<process-nonce>-<sequence>-<verb>-<slugified path>`
    (atomic sequence + per-run `uuid4` nonce → deterministic within a run,
    distinct across operations; `[A-Za-z0-9._-]` only, ≤ 200 chars —
    header-safe, uniqueness carried by the prefix). Nothing is persisted to
    disk; keys never reach logs (tests assert the key and token are absent
    from captured log output; the logging layer would redact a `key` field
    anyway — defence in depth). An explicit `idempotency_key=` argument
    lets a caller span one logical operation across several calls.
  * OQ note: the plan fixes neither the key format nor a length bound —
    the 200-char cap is an implementation assumption recorded here (backend
    retention/dedupe semantics are WP-1.15's, out of this MT's scope).
* Tests: `tests/test_idempotency.py` (23) — canonical header name,
  verb classification, presence/absence, shape/length, uniqueness per call
  and per target, retry stability, caller-supplied verbatim key,
  key-through-final-failure, log hygiene.

## 2026-10-12 — MT-2.3-04: Implement error translation to code + hint + next-action

* `orchestrator_bridge.error_translation` — `translate_error(ApiError) ->
  TranslatedError`, the Section 10.5 tool-error rule (stable code + human
  hint + model-facing next action):
  * **Passthrough verbatim (AC 2/3):** `code`, `message`, `details`,
    `correlation_id` and `retryable` are copied unchanged; only
    `hint`/`next_action` are added locally — no field is renamed, rewritten
    or dropped (Section 20.5). Retryable classification survives translation
    for `SERVER_ERROR`/`RATE_LIMITED` and stays `false` where it was.
  * **Closed catalog (AC 1):** `translate_error` rejects any code outside
    the Section 9.2 catalog with `ValueError` (tested with a fabricated
    code); `HINTS` keys are asserted ⊆ the `ErrorCode` enum, and the
    19-code published count is pinned — the translator cannot become a
    second catalog (Section 20.4 item 5).
  * **Coverage:** all 19 codes carry specific wording (test asserts every
    catalog code has a non-empty hint *and* next action). Claim/lease
    entries carry the RISK-02 mitigation path explicitly — `LEASE_EXPIRED` →
    stop, checkpoint, re-claim via `claim_task`; `TASK_ALREADY_CLAIMED` →
    re-list via `get_available_tasks`; `CONCURRENCY_LIMIT_REACHED` →
    `release_task` or wait; `AUTH_REQUIRED` → token reconfiguration
    (`orchestrator init`); `RATE_LIMITED`/`SERVER_ERROR` → retryable, wait
    and retry.
  * **Default branch (AC 4):** a catalog code with no entry still returns
    guidance naming the canonical code (and the correlation id) — exercised
    by monkeypatching an entry out, so the branch stays honest as wording
    evolves.
* Tests: `tests/test_error_translation.py` (15).

## 2026-10-12 — MT-2.3-05: Write the contract test against the OpenAPI schema

* `orchestrator_bridge.endpoints` — the client's endpoint catalog
  (`Endpoint` id/verb/`{pid}`/`{id}` path templates mirroring Section 9.2 and
  the document's spelling 1:1; `mutating` derived from the verb per
  headers.md) plus `PENDING_BACKEND`: the ten bridge endpoints whose backend
  implementation has not reached the generated document yet, each recorded
  with its owning backend work package (sessions/work/claim/release →
  WP-1.6, checkpoints → WP-1.8, resolution → WP-3.2, attachments →
  WP-1.11/1.14). Absence is tolerated **only** for those; any other missing
  endpoint fails the suite by name, and a pending endpoint the moment it
  appears is validated automatically (the flag then goes stale and is
  cleaned up with the change that lands it). The catalog mirrors the plan,
  so backend path drift from Section 9.2 surfaces here — never a silent
  skip.
* `tests/test_openapi_contract.py` (13 tests) — read-only against
  `schemas/openapi.yaml` (never written; regenerated concurrently by backend
  agents — tests parse structure, never line numbers):
  * **Presence/loud failure:** the document must exist and parse as OpenAPI
    3.x — a missing file raises an explicit "schema missing" failure
    (risk note: no silent skips), covered by a dedicated negative test.
  * **Declared operations (5 in-document endpoints today: task details,
    project context, manifest, draft-task create, health-live):** security
    accepts `bearerAuth` or is explicitly open; every mutating operation
    declares the `Idempotency-Key` header parameter; the client's actual
    boundary requests are asserted to carry `Authorization` (bearer),
    `X-API-Version`, `X-Correlation-ID`, `Idempotency-Key` exactly on
    mutating verbs, with the URL path equal to the OpenAPI template.
  * **Shapes:** representative request (`TaskCreate`) and response
    (`Task`/`Project`/`OrchestratorManifest`/`HealthLive`) samples validate
    against the component each operation references; OpenAPI 3.0 `nullable`
    is translated to JSON Schema so nullable wire values validate
    honestly. A declared endpoint appearing *without* a registered sample
    fails loudly and names it — future endpoints cannot slip in unchecked.
  * **Error envelope (AC 2):** `AUTH_REQUIRED`, `TASK_ALREADY_CLAIMED` and
    `SERVER_ERROR` samples validate against `ErrorEnvelope`, then round-trip
    through the real client parser — same canonical code, `retryable` and
    `correlation_id` on both sides; the bridge `ErrorCode` enum is asserted
    **equal to the schema's `CodeEnum`** (19 codes) — NFR-11 drift check.
  * **Failing path (AC 4):** a deliberate mismatch (envelope missing
    `correlation_id`; fabricated undeclared endpoint) fails with a message
    naming the endpoint *and* the field — asserted by tests.
  * A `pytest.raises`-style `ContractMismatch`-free design: helpers raise
    `AssertionError` directly so failures read as normal test failures.
* **Dependency change:** `pyyaml>=6.0.3` + `types-pyyaml` added to the
  bridge **dev** group (`uv add --group dev`; `uv.lock` updated) — parsing
  the canonical YAML contract is what the test exists for; both are
  test-only, the runtime dependency set is unchanged.
* **CI wiring:** the suite already runs the whole bridge pytest
  (`.github/workflows/test.yaml`) alongside ruff/format/mypy
  (`lint-type.yaml`) — no workflow edits needed (those files are owned
  elsewhere); the contract test joins the bridge suite automatically.
* **No schema change required** by this task — the document was read only;
  observations for the schema/backend owners are in the WP-2.3 report
  (Section 20.4 item 4 discipline: raise, never edit).
* Tests: `tests/test_openapi_contract.py` (13).
* **Convergence gate (2026-10-12):** WP-1.6's landed endpoints (`session_open`, `session_end`, `work_list`, `claim`, `release`) given request/response samples and cleared from `PENDING_BACKEND` per this catalog's stale-flag rule — bridge suite 207 green against the byte-stable regen.
