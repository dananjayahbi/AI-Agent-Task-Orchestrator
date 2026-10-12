# WP-2.2 — Manifest discovery and session binding: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.2.

- **2026-10-12 — PAUSED at MT-2.2-01/02/03 (implementation written, unverified):** remaining: targeted tests (`tests/test_manifest_discovery.py`, `tests/test_manifest_validation.py`, `tests/test_token_loading.py`), `tests/test_entrypoints.py` updates for startup binding, `uv lock` after the `jsonschema` dependency add + wheel force-include build check, `ruff check`/`ruff format --check`/`mypy` + targeted pytest verification, per-MT changelog entries, and the one-line MT-2.2-04/MT-2.2-05 deferral notes. *(All remaining items completed same day — see entries below.)*

## 2026-10-12 — MT-2.2-01: Implement upward manifest discovery to the Git root

* `orchestrator_bridge.manifest_discovery.discover_manifest(start, *, override=None)`
  walks from `start` (default: cwd) upward; **per directory the manifest
  candidate is checked before the `.git` ceiling**, so a manifest sitting at
  the Git root always wins over a closer repository marker (Section 10.1 —
  first-found-wins from the nearest directory; also covers the
  parent-repo-`.git`-first layout). `.git` as a directory *or* a file
  (linked worktree) stops the walk; a start with no `.git` anywhere walks to
  the filesystem root and raises with distinct "no Git root" wording so the
  terminal case is diagnosable.
* `settings.manifest_path` (`ORCHESTRATOR_BRIDGE_MANIFEST_PATH`, WP-2.1's
  documented test/passthrough hook) bypasses the walk entirely; a relative
  override resolves against the start directory. Returns
  `DiscoveredManifest(path, document)` with the **raw** parsed JSON — reading
  and validation stay separate gates (validation is MT-2.2-02's).
* Failures are actionable and leak-free: not-found names the fix
  (`orchestrator init`, `errors.INIT_COMMAND`); unreadable / non-UTF-8 /
  invalid-JSON documents raise `ManifestParseError` carrying the path and the
  parser detail — scrubbed on the way out by the logging layer and the stdio
  entrypoint's stderr line (`scrub_text`), as with every binding message.
* Startup wiring: `manifest.bind_startup(settings)` runs discovery →
  validation → token in that order; the stdio entrypoint **fail-fasts** on
  binding failure — exit 1, one structured `binding_failed` event naming the
  error class (no traceback), no partial MCP handshake.
* Tests (`tests/test_manifest_discovery.py`, 17): subfolder → root, nearest
  manifest wins, `.git` ceiling (directory and worktree file) never reads
  past the root, override precedence + relative resolution, no-`.git`
  filesystem-root edge, missing / non-object / non-UTF-8 / invalid-JSON
  documents, `orchestrator init` present in the not-found message.
  `tests/test_entrypoints.py` reconciled with the new fail-fast: the three
  WP-2.1 startup-contract tests now bind a minimal temp manifest (empty-tools
  handshake asserted *with* real binding; subprocess variant passes manifest +
  token via env), and two new tests assert the documented no-manifest
  behaviour in-process and via subprocess (exit 1, `binding_failed`,
  `ManifestNotFoundError`, message names `orchestrator init`, no traceback).
  The handshake itself was hardened while reconciling: `input=` closes stdin
  immediately, and EOF is the SDK's shutdown trigger, so an in-flight
  `tools/list` could be cancelled under load (observed flake). The test now
  holds stdin open until the `tools/list` response is seen — then EOF, so the
  clean-shutdown path stays asserted — with a kill watchdog bounding a hung
  server (9 consecutive full-suite runs green after the fix).

## 2026-10-12 — MT-2.2-02: Implement manifest schema validation and version compatibility check

* Two discrete, distinguishable gates that run before any credential work
  (FR-SEC-01 hygiene — an invalid manifest never gets near a token):
  unsupported `schema_version` → `ManifestVersionError` ("upgrade the
  bridge"); structurally invalid document → `ManifestValidationError`.
  Version rule fixed here (MT risk note answered): **integer generation,
  exact match** — `SUPPORTED_SCHEMA_VERSIONS = {1}`, checked as its own step
  with an int/bool guard; the schema file itself is the version
  (`manifest.v1.json`), versions are not semver, unknown generations fail
  closed rather than guessing compatibility. Appendix B's B-01
  fast-follow ADR supersedes this rule when it lands; the Section 10.11 API
  version header is a backend HTTP exchange with no canonical header name yet
  and joins WP-2.3.
* Structural validation via `jsonschema.Draft202012Validator` (schema
  meta-checked on load) against the published `schemas/manifest.v1.json` —
  the same single file the backend renderer was keyed to in MT-1.3-05 (one
  schema, two consumers; Section 20.4 item 4). Loaded from disk, **never
  fetched over the network** (out of scope per MT): a repo checkout reads the
  canonical file first, an installed package reads
  `orchestrator_bridge/schemas/manifest.v1.json`. `jsonschema>=4.23` is a
  direct dependency (already transitive via `mcp`; declared because the
  bridge imports it) with `types-jsonschema` in the dev group (`uv lock`
  re-run). Error text highlights the failing key (`best_match`) and carries
  the source path; messages run through `scrub_text`.
* **Packaging deviation (recorded here per Section 20.4):** the parked static
  `[tool.hatch.build.targets.wheel.force-include]` with
  `../schemas/manifest.v1.json` **cannot build** — `uv build` constructs the
  wheel from the *extracted sdist*, where that relative path resolves into
  uv's temp dir and raises `FileNotFoundError` (observed). Replaced by a
  custom hatchling build hook, `bridge/hatch_build.py`
  (`[tool.hatch.build.hooks.custom]`): the **sdist** pass force-includes the
  canonical file as `schemas/manifest.v1.json` (hatchling's defaults already
  ship `hatch_build.py` itself in the sdist, so the hook re-runs when the
  wheel is built from it); the **wheel** pass resolves the first existing
  candidate — `<root>/schemas/` (extracted sdist) then `<root>/../schemas/`
  (source checkout) — force-including to
  `orchestrator_bridge/schemas/manifest.v1.json`, and fails the build with
  both searched paths when neither exists (an artifact can never ship
  without its schema). Verified after the fix: wheel entry byte-identical
  (SHA-256) to the canonical file, sdist carries `hatch_build.py` + the
  schema, and `packages = ["src/orchestrator_bridge"]` keeps any stray root
  `schemas/` out of the wheel. Hook file carries targeted
  `type: ignore[import-not-found]`/`[misc]` (hatchling is build-system-only,
  absent from the dev env); mypy config itself untouched.
* Belt-and-braces proven by test: an invalid manifest carrying a planted
  `agent_token` is rejected before token work and the value never appears in
  the error message (schema cannot smuggle credentials past FR-SEC-04).
* Tests (`tests/test_manifest_validation.py`, 18): valid Section 10.3
  PID00007 example; unsupported version → `ManifestVersionError` even when
  the rest of the document is also malformed (discrete check proven); non-int
  / bool versions fall through to schema → `ManifestValidationError`;
  malformed shapes (`null`, array, string, number, missing/wrong-typed keys,
  `additionalProperties` violation, bad `project_id`/`project_name`/URI/
  branch prefix); source path in the message; schema source resolution
  (repo-first → packaged fallback → clear not-found).
* Observation (flagged to WP-2.2 by WP-1.3 MT-1.3-05): `$id` keeps the plan
  example's placeholder host `https://orchestrator.local/schemas/manifest.v1.json`.
  Confirmed safe for now — validation loads the schema from disk and never
  dereferences `$id`, and no canonical hosted URL exists yet (schemas are
  repo-local), so the placeholder stays and the hosting confirmation carries
  forward to schema-publication/OpenAPI time (WP-2.3+), not resolved here.

## 2026-10-12 — MT-2.2-03: Implement agent token loading from environment or user-level config

* `credentials.require_agent_token(settings)` — step 3 of `bind_startup`,
  reached only after discovery and validation succeed: **environment
  (`ORCHESTRATOR_AGENT_TOKEN`) > user-level config file** (TOML, WP-2.1's
  configuration-layering arrow read explicitly for the token per Section
  10.3 step 3); otherwise `TokenError` naming both sources and
  `orchestrator init`. The resolved value stays inside `Settings` — no
  second copy in globals or a separate structure; the logging layer's
  scrubbing plus the header-safety gate are the leak defences.
* Header safety (FR-SEC-01): the value must be a plausible bearer —
  non-empty (the loader already collapses empty/whitespace-only to `None`)
  and free of whitespace or ASCII control characters that would break or
  inject into the header line. Rejection messages describe the *shape*, never
  the content; server-side validation of the token against the backend is
  out of scope here and arrives with the session-open exchange (MT-2.2-04+).
* Tests (`tests/test_token_loading.py`, 13): env-only, file-only,
  env-over-file precedence; absent-both failure names `ORCHESTRATOR_AGENT_TOKEN`
  and `orchestrator init`; header-unsafe values (embedded newline, space,
  control byte) rejected with the value absent from `str(exc)`; fixture
  token absent from every raised binding error; `bind_startup` end-to-end
  with a temp manifest + fixture token.

## 2026-10-12 — MT-2.2-04: Open and end agent sessions with a cached project context

* New `orchestrator_bridge.session` — Section 10.3 steps 4–5, run by the
  stdio entry point immediately after `bind_startup` (steps 1–3), sharing
  one `ApiClient` with the tool runtime:
  * **Step 4 open.** `POST /api/v1/agent-sessions` with a bridge-minted,
    unguessable id (`uuid4().hex`, G-18 — the backend *issues* nothing; the
    open body is exactly `{id, client_name, capability, transport}` and
    never a `project_id`, ADR-004: the backend derives the project from the
    token, which is the server-verified binding of FR-SEC-01). The returned
    id becomes the process's `agent_session_id` (deliberately *not* named
    "session" bare — MCP protocol handshake vs. backend session is the MT's
    named integration-bug risk; logged and threaded under the distinct
    name). `transport` maps Section 10.2 run modes onto the backend's
    `TransportEnum` (`stdio|http`).
  * **Step 5 cache.** `fetch_project_context` reads
    `GET /api/v1/projects/{pid}` (name + `system_prompt_rules`) **and**
    `GET /api/v1/projects/{pid}/policy` (the structured policy summary) —
    no single endpoint returns the Section 10.3 triple today, so two reads
    feed one immutable `ProjectContext{project_id, name, rules,
    policy_summary}`; only the Section 10.3 set is cached (MT risk note:
    extra fields invite client-side policy drift, §19.3), in process memory
    only, never on disk (asserted). `endpoints.py` gains the
    `project_policy` catalog entry (already in the OpenAPI document; the
    MT-2.3-05 contract test validates it, with a `ProjectPolicy` response
    sample added).
  * **End.** `close_session` posts `/agent-sessions/{id}/end` with a
    **2-second timeout and a single attempt** (`dataclasses.replace` on the
    settings — stdio teardown must never hang; §10.10); failure logs
    `session_end_failed` and returns `False` without raising. A crashed
    bridge never ends the session — the **backend's stale-session sweep is
    the safety net** (dependency recorded: M1 owns it; the end call is
    idempotent per the OpenAPI description, so a replayed best-effort end
    is safe).
* **Error mapping.** Backend rejections at open/context-fetch become
  `SessionOpenError` (new `BindingError` subclass, `errors.py`) naming the
  canonical code; `AUTH_FORBIDDEN_PROJECT` becomes `ProjectMismatchError`
  (MT-2.2-05). Transient failures ride the WP-2.3 bounded retry (observed:
  one 5xx → retried → open succeeds); exhaustion aborts clearly. Messages
  run through `scrub_text`; tests assert the fixture token never appears.
* **Entry-point wiring.** `stdio.run` now serves only a fully-bound session
  (open before `create_server`, tools registered against the bound runtime
  with MT-2.4 — the five core tools land here later), ends the session
  best-effort after `server.run` returns; the startup log carries
  `agent_session_id`. HTTP/executor entry points are unchanged stubs (their
  session work is WP-2.9/WP-3.7).
* **Tests** (`tests/test_session_lifecycle.py`, 14; plus entry-point
  reconciliation): open body/headers/idempotency/read-only cache/no-disk;
  context shape is exactly the §10.3 set fetched once per open; retry-then-
  open and retry-then-abort; `AUTH_REQUIRED`/`RATE_LIMITED`/`SERVER_ERROR`/
  `VALIDATION_ERROR` map distinguishably, token never leaks; end called
  with the session id, bounded, one attempt, failure logged not raised.
  `test_entrypoints.py` gains the loopback `StubHttpBackend` (conftest) so
  the in-process and real-subprocess stdio tests bind through a real
  socket; the subprocess handshake test now asserts the WP-2.4 tool set
  (MT-2.4-07's inspector-equivalent proof) plus open+end over the wire.
* **Deviation notes:** (a) the MT named a single "Project Context
  endpoint" — the backend exposes project + policy reads, so the cache
  composes two calls (no contract invented); (b) end-call timeout is a
  session-module constant (2 s), stricter than `settings.timeout_seconds`,
  per the MT's "aggressively bounded" risk note.

## 2026-10-12 — MT-2.2-05: Abort on project mismatch with a clear message

* `ProjectMismatchError(SessionOpenError)` with
  `canonical_code = "AUTH_FORBIDDEN_PROJECT"` — one abort vocabulary for
  both detection paths. The backend's 403 at session open (the
  server-verified half, FR-SEC-01) maps to a message that names: the
  manifest's project id (repo-visible, safe), the canonical code, and both
  remedies (`ORCHESTRATOR_AGENT_TOKEN`/user-config pointed at this
  project's token, or `orchestrator init` in the right repository), plus
  the backend's scrubbed message. Never the token or anything derived from
  it (asserted against the fixture string).
* **No local token decoding** (§12.2 opaque bearer): the optional early
  pre-check was conditioned on MT-2.12-02 recording the token's issued
  project — that metadata does not exist yet, so every mismatch costs the
  one authoritative network round trip. Recorded here so WP-2.12 does not
  assume a local pre-check exists; add one only if MT-2.12-02 ships the
  metadata.
* **Entry-point abort path:** stdio exit 1 (`EXIT_CONFIG_ERROR`), one
  scrubbed `bridge startup error:` stderr line, empty stdout, a
  `binding_failed` log record with `error_type=ProjectMismatchError`, and
  no server built; the matching-project control starts, serves and ends
  its session (stub backend). Message/log redaction asserted end to end.
* Tests: `tests/test_project_mismatch.py` (7).

## 2026-10-12 — WP-2.2 complete

All five MTs done (deferral notes from earlier today superseded — the
backend `POST /agent-sessions` + `/{id}/end` pair landed as MT-1.6-09, unblocking
MT-2.2-04/05 the same day). Verification battery green:
`uv run --directory bridge ruff check .`, `ruff format --check .`, `mypy .`,
`pytest -q` — **313 passed, 5 skipped** (the skips are WP-2.4's opt-in live
suite, not WP-2.2's).
