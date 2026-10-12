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

## 2026-10-12 — Deferral notes (roadmap §4a rule 1)

* **MT-2.2-04 (backend session open/end with project context caching)** —
  deferred: blocked on the backend `POST /agent-sessions` endpoint (being
  traced); finish when it lands.
* **MT-2.2-05 (project-mismatch abort with a clear startup error)** —
  deferred with MT-2.2-04: its startup abort compares the session-open
  response's project context against the bound manifest, i.e. the same
  not-yet-landed endpoint; both complete together.
