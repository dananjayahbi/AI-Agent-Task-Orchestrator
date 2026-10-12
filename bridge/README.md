# Bridge (`bridge/`)

The MCP bridge and Merge Executor — tools, prompts, client discovery, the Git helper,
evidence upload, and host-side merges (parent plan Sections 10, 16). It reports to the
backend API and never writes backend data directly.

* Package boundaries and tooling commands:
  [CONTRIBUTING.md — Bridge (Python)](../CONTRIBUTING.md#bridge-python)

## Shared conventions (WP-0.5)

Every configuration value this package reads follows the shared conventions:

* [Configuration conventions](../docs/plan/conventions/configuration.md) —
  environment variable naming, grouping and secret handling (parent plan
  Sections 9.10, 16.2)
* [Error conventions](../docs/plan/conventions/error-envelope.md) — canonical
  error envelope and the 19-code catalog (parent plan Section 9.2)
* [Header conventions](../docs/plan/conventions/headers.md) — correlation id and
  idempotency key headers (parent plan Sections 9.2, 9.6, 17; ADR-012)
* [Pagination conventions](../docs/plan/conventions/pagination.md) — cursor-based
  lists for every list endpoint, plus the Section 9.5 attachment `content`
  exception (parent plan Sections 9.2, 9.5)

## Run modes and entry points (WP-2.1, parent plan Section 10.2)

One shared construction path (`orchestrator_bridge.server.create_server`) and one
bootstrap (config → logging → correlation → mode dispatch) behind four launchers:

| Mode | Invocation | Status |
|---|---|---|
| STDIO | `uv run orchestrator-bridge-stdio`, or `uv run python -m orchestrator_bridge` | Runnable (empty tool set until WP-2.4) |
| HTTP/SSE | `uv run orchestrator-bridge-http` / `--mode http` | Stub — exits 2, tracked by WP-2.9 |
| Merge Executor | `uv run orchestrator-bridge-executor` / `--mode merge-executor` | Stub — exits 2, tracked by WP-3.7 |
| (generic) | `uv run orchestrator-bridge [--mode …]` | Dispatches per the precedence below |

Mode-selection precedence: **explicit invocation > configuration key >
default `stdio`.**

Exit codes: `0` success, `1` configuration error, `2` mode not implemented.

## Configuration (WP-2.1, MT-2.1-02)

Layering — **environment variables > user-level config file > built-in
defaults** (documented reading of parent plan Section 10.3 "environment or
user-level config"). The loader reads only the keys below by exact name; it
never autoloads a cwd `.env` and never reads the manifest (FR-SEC-04). An
exported-but-empty environment value counts as unset.

User-level file (TOML), profile-anchored, written by `orchestrator init`
(WP-2.12): Windows `%APPDATA%\orchestrator\bridge.toml`; POSIX
`${XDG_CONFIG_HOME:-~/.config}/orchestrator/bridge.toml`.

| Settings key (file) | Environment variable | Default | Validation | Secret |
|---|---|---|---|---|
| `api_base_url` | `ORCHESTRATOR_API_BASE_URL` | `http://localhost:8000/api/v1` | `http(s)://` URL | no |
| `agent_token` | `ORCHESTRATOR_AGENT_TOKEN` | unset | non-empty string; redacted in output | **yes** |
| `manifest_path` | `ORCHESTRATOR_BRIDGE_MANIFEST_PATH` | unset | non-empty path (test override, WP-2.2) | no |
| `log_level` | `ORCHESTRATOR_LOG_LEVEL` | `INFO` | `DEBUG\|INFO\|WARNING\|ERROR\|CRITICAL` | no |
| `log_format` | `ORCHESTRATOR_LOG_FORMAT` | `json` | `json` (Section 17 contract) or `text` (local debug) | no |
| `mode` | `ORCHESTRATOR_BRIDGE_MODE` | `stdio` | `stdio\|http\|merge-executor` | no |
| `timeout_seconds` | `ORCHESTRATOR_BRIDGE_TIMEOUT_SECONDS` | `30` | number > 0 (Section 10.10) | no |
| `merge_repo_paths` | `ORCHESTRATOR_MERGE_REPO_PATHS` | unset | path list (comma-separated env) | no |

Runtime scope input (not a setting): `ORCHESTRATOR_CORRELATION_ID` — installed
into the log scope at startup (honor-or-generate, headers.md).

Example files (placeholders only, never fill in with real secrets):
[`.env.example`](./.env.example), [`user-config.example.toml`](./user-config.example.toml).

## Structured logging (WP-2.1, MT-2.1-03)

JSON lines with `st_dev + pid + level + timestamp + component` base fields,
`correlation_id` propagation (`X-Correlation-ID`), and a single redaction point
(tokens/authorization → `[REDACTED]`, prompt/attachment content → `[OMITTED]`).
In stdio mode diagnostics go to **stderr** so they cannot corrupt MCP framing
(verified against the MCP Python SDK stdio transport; see the WP changelog).
