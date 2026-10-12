# WP-2.1 — Bridge package skeleton: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of
WP-2.1 (Bridge package skeleton).

## 2026-10-12 — MT-2.1-01: Bridge package layout

* `bridge/` is an independently configurable package: own `pyproject.toml`
  (Appendix A), src layout `bridge/src/orchestrator_bridge/`, uv-driven tooling
  from the package root. **Standalone, not a uv workspace** — no repo-root
  workspace exists (MT risk note answered; recorded here as required).
* Dependencies landed with WP-2.1: `mcp>=2.3.0` (official MCP Python SDK —
  Section 6.6 technology decisions; installed 2.3.0) and dev tools
  `ruff==0.17.0`, `mypy==2.4.0`, `pytest>=9.1.1` (MT-0.1-02 pins kept).
* Section 10.1 seams seeded docstring-only, each pointing at its plan section:
  `config.py`, `logging.py`, `manifest.py`, `capabilities.py`, `credentials.py`,
  `resume_cache.py`, `tools/` (empty `TOOLS` registry — WP-2.1 acceptance:
  empty tool set). Transport/entry points arrive as stubs in MT-2.1-04.
  Observation (MT risk note): Appendix A's tree names `prompts/git helper/
  executor` files while the MT's seed list names the seven above — the MT's
  explicit seed list was followed; prompts/git-helper/executor modules land
  with their own WPs rather than as premature interfaces.
* Boundary guard: `tests/test_layout.py` statically asserts no `bridge/` file
  imports `backend` or `web` (independent deployables), plus smoke imports and
  the empty-registry check. `uv run --directory bridge ruff check .` and
  `uv run --directory bridge pytest -q` pass.
* Observation: the MT cites "ADR-004 (Python bridge) / ADR-008 (independent
  deployables)"; the published ADR set has ADR-004 = project-scoped agent
  tokens and ADR-008 = host-side merge executor. The Python/`uv`/official-SDK
  decision is parent plan Section 6.6 and the independence rule is Appendix A —
  implementation follows the plan (Section 0: plan wins), no ADR edited.

## 2026-10-12 — MT-2.1-02: Configuration layering

* Loader (`orchestrator_bridge.config`) resolves **environment variables >
  user-level config file > built-in defaults** into one frozen `Settings`
  object. Precedence arrow recorded here per MT: the plan's "environment or
  user-level config" (Sections 10.3/10.11) is read as env-over-file so CI and
  containers can override, matching 12-factor practice and the backend's
  env-driven settings (Section 9.10).
* Key list (file key = attribute name; env names canonical per
  `docs/plan/conventions/configuration.md`):

  | Settings key | Environment variable | Default |
  |---|---|---|
  | `api_base_url` | `ORCHESTRATOR_API_BASE_URL` (existing canonical) | `http://localhost:8000/api/v1` |
  | `agent_token` (secret) | `ORCHESTRATOR_AGENT_TOKEN` (existing canonical) | unset |
  | `manifest_path` | `ORCHESTRATOR_BRIDGE_MANIFEST_PATH` | unset (test/passthrough hook, WP-2.2) |
  | `log_level` | `ORCHESTRATOR_LOG_LEVEL` (existing canonical) | `INFO` |
  | `log_format` | `ORCHESTRATOR_LOG_FORMAT` | `json` |
  | `mode` | `ORCHESTRATOR_BRIDGE_MODE` | `stdio` |
  | `timeout_seconds` | `ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS` | `30` |
  | `merge_repo_paths` | `ORCHESTRATOR_MERGE_REPO_PATHS` | unset/empty |

* User-level file fixed on the read side (MT risk note answered): **TOML** at
  `%APPDATA%\orchestrator\bridge.toml` (Windows) /
  `${XDG_CONFIG_HOME:-~/.config}/orchestrator/bridge.toml` (POSIX) — profile-
  anchored, never cwd-relative, never in a repo. `orchestrator init`
  (WP-2.12 / MT-2.12-02) is the write side and uses the dedicated
  `agent_token` key. The loader never reads the manifest, a repo-tracked file
  or a cwd `.env` (FR-SEC-04); an exported-but-empty env value counts as unset.
* Fail-fast validation (NFR-10): unknown file keys, malformed TOML, and
  malformed values (level/format/mode/timeout/URL/path-list) raise `ConfigError`
  with a key-naming message and no traceback at the entry points (exit 1).
  Mode-required keys (`validate_for_mode`): only the Merge Executor requires
  startup config today — `merge_repo_paths`, grounded in Section 10.2's
  "config listing allowed repo paths"; STDIO and HTTP bind without it.
  `ORCHESTRATOR_MERGE_REPO_PATHS` is a new group (`MERGE_`), flagged for owner
  confirmation alongside the new `BRIDGE_`-group names and `ORCHESTRATOR_LOG_FORMAT`
  (Section 20.1 rule 5). Recorded in `bridge/.env.example` +
  `bridge/user-config.example.toml` (configuration.md: bridge-only settings
  live in the consumer's package docs); `docs/plan/conventions/configuration.md`
  and `infra/compose/.env.example` untouched — no Compose-consumed setting added.
* Secrets hygiene: `repr(Settings)` renders the token as `[REDACTED]`; wrong-
  type token errors never echo the value; example files carry placeholders only
  (Section 20.4 item 3). Tests: full precedence chain, file-absent defaults,
  malformed file/values, unknown key, missing mode-required key, redaction,
  planted cwd `.env`/manifest ignored, example files parse and match the key
  table (`uv run --directory bridge pytest tests/test_config.py -v`).

## 2026-10-12 — MT-2.1-03: Structured logging

* `orchestrator_bridge.logging` emits one JSON object per line with the MT's
  base fields — `st_dev`, `pid`, `level`, `timestamp` (ISO-8601 UTC ms + `Z`,
  same spelling as backend logs), `component` (`bridge.<module>`) — plus
  `message` (scrubbed/truncated), `correlation_id` (when a scope is installed),
  `exception`, and scrubbed `extra=` fields. Interpretations flagged as OQ
  candidates (MT risk notes): `st_dev` = stable host-device tag (hostname of
  the machine running the bridge); MCP JSON-RPC request ids are a separate id
  space and never appear as `correlation_id`.
* Redaction in exactly one place (`orchestrator_bridge.scrub`): bearer tokens,
  secret-shaped `key=value` text, credential field names → `[REDACTED]`; <!-- pragma: allowlist secret -->
  prompt/attachment-content field names → `[OMITTED]` (G-07); everything
  truncated at 2000 chars (Section 12.4). Paired with MT-2.1-02's structural
  rule (token is never a log field) so safety does not rest on patterns alone.
* Correlation (`orchestrator_bridge.correlation`): contextvar scope,
  canonical header constant `X-Correlation-ID` (headers.md, no aliases),
  startup bootstrap from `ORCHESTRATOR_CORRELATION_ID` with honor-or-generate
  semantics; WP-2.3 will read the same scope to send the header, WP-2.9 to
  re-scope per connection.
* Resilience events (`orchestrator_bridge.events`): one structured line per
  retry attempt (`event=retry_attempt`, attempt/max/backoff/cause) and per
  stale-session abort (`event=stale_session_abort`, session/reason) per Section
  10.10 — shapes fixed here, callers land in WP-2.3/2.9/2.2.
* **Stream deviation (MT-2.1-03 risk note → OQ candidate `OQ-15+`)**: stdio
  mode logs JSON lines to **stderr**, other modes to stdout. Verification
  method: inspected official MCP Python SDK 2.3.0 `mcp/server/stdio.py` — the
  stdio transport claims fd 1 for JSON-RPC frames and diverts fd 1 to stderr
  only *while serving*, so diagnostics emitted before/after the serving window
  would otherwise reach the wire and could corrupt framing; stderr is never
  claimed. Owner should confirm the stderr default as the standing rule.
* SDK interplay: `MCPServer` calls `logging.basicConfig` on the root logger;
  the bridge logger uses `propagate = False` so lines are emitted exactly once
  in the bridge format. MCP protocol-level `notifications/message` logging is
  out of scope (recorded follow-up if Section 10.4 negotiation needs it).
  Tests: JSON schema/base fields, redaction cases, correlation round-trip,
  level filtering, stream selection, event shapes
  (`uv run --directory bridge pytest tests/test_logging.py -v`).

## 2026-10-12 — MT-2.1-04: Entry points for stdio, HTTP and executor modes

* One construction path: `orchestrator_bridge.server.create_server(settings)`
  builds the official-SDK `MCPServer` for every mode (Section 10.11 single
  entry; Section 19.6 one implementation) with the empty tool set until WP-2.4
  wires the `tools` registry in. One bootstrap for every invocation:
  load layered config (MT-2.1-02) → configure structured logging (MT-2.1-03) →
  install correlation scope → resolve mode → dispatch. No inline defaults.
* Entry points declared in `bridge/pyproject.toml`:
  `orchestrator-bridge` (generic, `--mode`), `orchestrator-bridge-stdio`,
  `orchestrator-bridge-http`, `orchestrator-bridge-executor`, and
  `python -m orchestrator_bridge` (module invocation).
* Mode-selection precedence, documented in `bridge/.env.example` and
  `bridge/user-config.example.toml` and tested: **explicit invocation >
  config key (`ORCHESTRATOR_BRIDGE_MODE` env > `mode` file) > default stdio**.
* Stub boundaries fail fast, non-zero, naming the implementing WP: HTTP mode
  exits `2` with a WP-2.9 message (MT-2.1-04's context cites "WP-2.10", but
  parent plan Section 19.1 and `plan-doc-series/overview.md` make HTTP
  transport **WP-2.9** and WP-2.10 the Local Git helper — plan wins, doc
  inconsistency noted); Merge Executor raises `NotImplementedError` naming
  **WP-3.7** (Merge queue and Merge Executor), CLI exits `2`; configuration
  errors exit `1` with one clear line. Exit codes: 0/1/2 (success / config
  error / not implemented).
* **Inspector acceptance (Section 19.1, WP-2.1 verbatim) — recorded invocation
  and result (Section 20.4 item 1):**

  ```
  npx -y @modelcontextprotocol/inspector@latest --cli --method tools/list ... orchestrator-bridge-stdio.exe
  → {"tools": []}   (initialize handshake completed; startup/shutdown JSON
                     logs emitted; process exit code 0 — clean shutdown)
  ```

  The same handshake (initialize → notifications/initialized → tools/list over
  a real stdio subprocess) runs as `tests/test_entrypoints.py::
  test_stdio_process_handshake_lists_empty_tools` and asserts every stdout
  line is a JSON-RPC message (framing intact) with diagnostics on stderr only.
  CI gap note: the npx inspector run itself is a manual/Node-tooling step; the
  subprocess handshake is the automated stand-in.
* Smoke checks recorded: `orchestrator-bridge --help`, `python -m
  orchestrator_bridge --help`, `--mode http` → exit 2 + WP-2.9 message,
  `--mode merge-executor` → exit 2 + WP-3.7 message. Verification:
  `uv run --directory bridge ruff check .`, `ruff format --check .`, `mypy .`
  and `pytest -q` (55 tests) all green; no secrets or environment-specific
  values committed (item 3).
