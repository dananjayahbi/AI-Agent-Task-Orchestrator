# WP-2.4 — Tools: availability, details, claim, release, context: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.4.
All seven MTs completed 2026-10-12 in order; the "tool-only contract" (ADR-011,
NFR-08) now holds: the bridge's five core tools work with **no prompts** — names,
schemas and error payloads carry the workflow (prompts arrive with WP-2.8 as an
additive layer).

## 2026-10-12 — MT-2.4-01: Deterministic schemas for the five core tools

* `tools/schemas.py` — the **public contract**: `ToolSpec(name, description,
  input_schema, errors)` for exactly Section 10.5's five tools, in catalog
  order, modeled from the plan table by pointer. Strict-validation keywords
  live in the schemas themselves: `additionalProperties: false` everywhere,
  `role`/`priority_filter` enums, `limit` bounded 1–100 (the backend page
  cap), `task_id`/`agent_identifier` required. Every declared error code is a
  member of the Section 9.2 catalog (test-pinned; `claim_task` declares the
  plan's four named errors). The MT's named guard test — no `project_id`
  parameter on any tool — scans every schema property name.
* **Wire-schema seam (deviation, researched on the pinned `mcp` SDK):** the
  SDK derives each tool's advertised `inputSchema` from the handler's Python
  signature, and its argument model *ignores extra keys* (pydantic default).
  Neither satisfies "deterministic schemas" + "unknown properties rejected".
  Resolution: `tools/registration.BridgeTool` subclasses the SDK `Tool` —
  `create_server` passes instances (built by `build_tools`) to the
  `MCPServer` constructor with `parameters` **replaced by the declared
  schema** (what `tools/list` publishes, byte-for-byte — asserted in the
  handshake test and the inspector run below), while `BridgeTool.run`
  re-validates the raw arguments against the declared schema **before** the
  SDK's looser model, so strictness is the bridge's own.
* `tools/validation.py` — `jsonschema.Draft202012Validator` (same stack as
  manifest validation) per tool; failures raise `ToolFailure` carrying a
  `TranslatedError`: canonical `VALIDATION_ERROR` + hint + next action
  (FR-MCP-03), with the failing path named and messages scrubbed.
* `tools/errors.py` — `ToolFailure` + `payload_text`: every deliberate
  failure reaches the model as `ToolError("Error executing tool <name>:
  {json}")` where the JSON is the Section 9.2 fields plus
  `hint`/`next_action` (the bridge converts `ApiError`s raised by handlers
  too; genuine crashes keep the SDK's hiding behaviour).
* Tests (`tests/test_tool_schemas.py`, 20): exact names/order/inputs vs the
  plan table; no-`project_id` scan; catalog-closed errors; valid fixtures
  pass; malformed inputs (unknown keys, bad enums, bound violations, missing
  required, non-objects, `null` args) fail structured; `tools/list` ==
  declared schemas verbatim; `tools/call` with a smuggled `project_id`
  rejects with the JSON payload.

## 2026-10-12 — MT-2.4-02: get_available_tasks

* `tools/available_tasks.py` → `GET /api/v1/projects/{pid}/work` with
  `role` (default `coder`), `priority` (single value, §9.2) and
  `page_size=limit`; the project comes from the bound runtime, never an
  argument. Compact descriptors: `id, title, priority, state, depends_on`
  (+ attachment **descriptors** when a row carries them — never content;
  the backend Task row has no attachment list until WP-1.11, recorded as a
  forward enrichment for WP-2.5). Envelope adds `role`, `count` and
  `next_cursor` when set.
* **Pagination OQ (recorded per MT):** `limit` caps at the backend page
  size (100) and exactly one page is fetched; exposing tasks beyond 100
  needs a paging-input decision — no extra inputs invented.
* Backend errors (`AUTH_FORBIDDEN_PROJECT`, `VALIDATION_ERROR`,
  `ROLE_NOT_PERMITTED`, …) surface translated with hint/next-action;
  malformed envelopes become structured `SERVER_ERROR`. Tests (12).

## 2026-10-12 — MT-2.4-03: get_task_details

* `tools/task_details.py` → `GET /api/v1/tasks/{id}`; returns the backend's
  Section 7.2 row verbatim under `task` (criteria, scope, test command,
  `latest_feedback`, lease/dependency state) — nothing derived (§19.3).
  Resolution info passes through when the row carries it (MT wording: "when
  the backend returns it"); **role gating of that exposure is the backend's
  §12.2 authority** — the tool schema takes only `task_id` (pinning the
  coder/auditor split client-side would need a role input the plan does
  not give it; fixture tests cover both row shapes). Attachment
  descriptors pass; content never appears. Tests (10).

## 2026-10-12 — MT-2.4-04: claim_task

* `tools/claim.py` → `POST /tasks/{id}/claim` with the backend's
  `ClaimRequest` contract exactly: `{session_id (the bridge
  agent_session_id), worker_agent_id (the tool's agent_identifier)}` +
  `Idempotency-Key` (MT-2.3-03). **The wire body carries no `role`**: the
  OpenAPI `ClaimRequest` has no role field and strict serializers reject
  unknowns — the backend derives claimable work from the token's scopes
  (§12.2) and auditor claims are backend WP-3.3; the tool-level `role`
  input is schema-validated and re-enters the wire when the contract grows
  it (recorded; not a silent drop — the handler docstring and schema
  description both say so).
* Response assembly = the three §10.5 artifacts: compact **lease** block
  (generation, expiry, hard cap, checkpoint, failure count), the **rules
  block verbatim** from the backend (§10.6; WP-2.7's templates merge into
  the backend block at MT-2.7-03 — a forward consumer, not a blocker, as
  the assignment notes), the **branch name** derived per G-09
  (`auto_branch_prefix` + task index → `feat/PID00007-T004`; a deliberately
  minimal helper WP-2.10's branch utility will own/extend) plus the full
  task row. `lease_generation` is recorded on the runtime for the release
  fencing pair (ADR-012).
* The four named errors (`TASK_ALREADY_CLAIMED`,
  `CONCURRENCY_LIMIT_REACHED`, `DEPENDENCY_UNMET`, `AUDITOR_SAME_AS_CODER`)
  plus `TASK_NOT_FOUND`/`ROLE_NOT_PERMITTED` surface with exact codes,
  hint and next-action (the `TASK_ALREADY_CLAIMED` hint names
  `get_available_tasks` per §10.5). Tests (15).

## 2026-10-12 — MT-2.4-05: release_task

* `tools/release.py` → `POST /tasks/{id}/release` with `session_id` +
  optional `lease_generation` (from the runtime's claim record — a
  restarted bridge legitimately omits it and lets the backend answer
  `LEASE_NOT_OWNED`/`LEASE_EXPIRED` authoritatively, §19.3) + `reason`.
  **No failure/attempt field exists to send** — the no-increment contract
  (FR-LEA-06) is pinned by the guard test on the exact request body.
* Response: the task's new `state`, `released: true`, and a next-action
  hint (re-enter availability via `get_available_tasks`). The five catalog
  errors (`LEASE_NOT_OWNED`, `LEASE_EXPIRED`, `TASK_STATE_CONFLICT`,
  `TASK_NOT_FOUND`, `VALIDATION_ERROR`) surface with guidance; the
  `LEASE_EXPIRED` path is a calm next action, not a crash (MT risk note).
  Tests (10).

## 2026-10-12 — MT-2.4-06: get_project_context

* `tools/context.py` — no inputs; answers from the WP-2.2 session cache
  with **zero backend calls** (asserted: the fake transport records none;
  called twice → still none). Payload is the §10.3 set plus the bound id:
  `{project_id, project_name, rules, policy_summary}` — nothing else
  (§12.4 compactness).
* Miss path (a resumed session with an empty cache — future HTTP mode):
  fetch once via the shared client (project + policy, the MT-2.2-04
  `fetch_project_context` — one source for both channels, no rules-text
  drift), then serve cached. Backend failure → structured retryable
  `SERVER_ERROR` with hint/next-action (§10.10); `AUTH_FORBIDDEN_PROJECT`
  keeps its code.
* **Stale-cache OQ (recorded per MT risk note):** the plan specifies no
  invalidation for Owner policy edits mid-session — agents see the
  session-open snapshot until reconnect; raise an OQ if prompt propagation
  becomes a requirement. Tests (8).

## 2026-10-12 — MT-2.4-07: Core-tool tests incl. concurrent claim outcomes

* **Unit/cross layer** (`tests/test_core_tools.py`, 7): the full
  orient→list→details→claim→release chain over one scripted backend with
  the call sequence pinned (context from cache, release carrying the
  claim's fencing generation across tool calls); role-matrix wire behavior
  (auditor listing, cross-role claim rejections structured); an
  8-thread contended-claim shaping test (one structured winner, the rest
  `TASK_ALREADY_CLAIMED` — the bridge side only; the DB lock is proven
  live); every request scoped to the bound project.
* **Live layer — NFR-01 against the real claim service**
  (`tests/_live_backend.py` + `tests/test_core_tools_live.py`): opt-in
  (`ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`) harness that spawns the **real
  backend** — `manage.py migrate` + uvicorn `config.asgi:application` —
  against `wp16-pg` (`docker start wp16-pg`, port 5434; URL overridable
  via `ORCHESTRATOR_BRIDGE_LIVE_DATABASE_URL`) and the local Redis, seeds
  one project + agent tokens + pending tasks via `manage.py shell`, and
  drives everything through the bridge tools at the HTTP boundary (no
  backend imports — the ADR/Appendix A boundary holds; backend pytest is
  never run). Without the env flag or without Postgres the five tests
  **skip** with the exact start command (the default battery stays green).
* **Recorded live results (2026-10-12, wp16-pg):** `4 passed, 1 skipped` —
  * two independent bridge sessions (separate tokens) claiming one task
    concurrently: **exactly one winner, one structured
    `TASK_ALREADY_CLAIMED`** (WP-2.4 acceptance, FR-LEA-01);
  * **50 parallel claims through the MCP `tools/call` boundary: exactly
    one winner, 49 structured failures** (`TASK_ALREADY_CLAIMED`, each
    with hint + next-action; no partial lease state — the winner's lease
    released cleanly afterwards) (§18 concurrency row);
  * duplicate-claim through the MCP boundary returns the catalog code as
    the JSON `ToolError` payload (the model-facing contract);
  * the orient→…→release chain **skips on a recorded backend gate** (below).
* **Harness lesson (recorded):** the spawned uvicorn must log to a **file**,
  not an unread `PIPE` — the wedged-server timeouts observed mid-suite
  disappeared once the pipe was replaced (the file doubles as failure
  diagnostics).
* **Inspector acceptance (Section 19.1; WP-2.4 verbatim) — recorded
  invocation and result:**

  ```
  npx -y @modelcontextprotocol/inspector@latest --cli \
    <bridge>/.venv/Scripts/orchestrator-bridge-stdio.exe --method tools/list \
    --cwd <bridge> -e ORCHESTRATOR_BRIDGE_MANIFEST_PATH=... -e ORCHESTRATOR_AGENT_TOKEN=...
  → {"tools": [ get_available_tasks, get_task_details, claim_task,
                release_task, get_project_context ]}   (exactly the five
                core tools; inputSchema == the MT-2.4-01 declared schemas;
                startup log shows session_opened + context cache; clean
                shutdown with the best-effort session end 200)
  ```

  The same handshake runs automatically as
  `tests/test_entrypoints.py::test_stdio_process_handshake_lists_core_tools`
  (real stdio subprocess against the loopback stub backend), so CI pins the
  tool surface without Node tooling.

## 2026-10-12 — Gate follow-ups and open questions (recorded, not blocking)

* **Backend agent read-only activation (gate):** `GET /api/v1/projects/{pid}`,
  `.../policy` and `GET /api/v1/tasks/{id}` currently answer
  `ROLE_NOT_PERMITTED` ("Only the owner…") to agent tokens — the views
  document that agent read-only access for the token's own project
  "activates in WP-2.x". The bridge implements the plan contract (§9.2:
  "agents read-only for own project") and unit-tests it at the HTTP seam;
  the live chain test **skips with the gate named** until the backend
  activation lands (then it should pass unchanged). The live claim/release
  proof is unaffected (those endpoints are agent-facing today).
* **CI integration-job path (gate, `.github/workflows/test.yaml` — not in
  the bridge agent's file protocol):** the bridge integration step runs
  `uv run --directory bridge pytest bridge/tests/integration`, and uv's
  `--directory` makes cwd `bridge/`, so the path resolves to
  `bridge/bridge/tests/integration` (verified locally: exit 4, "file or
  directory not found"). The command is dormant only while no test file
  exists under `bridge/tests/integration/` (the allow-empty detection). The
  live suite therefore sits **flat in `bridge/tests/`** (self-skipping) and
  the fix — either `pytest tests/integration` or moving the suite — is a
  one-line follow-up for the CI owner.
* **Pending-endpoint cleanup:** `endpoints.PENDING_BACKEND` still lists the
  checkpoint/resolution/attachment endpoints; WP-1.8's checkpoint rows are
  landing concurrently — the MT-2.3-05 contract test auto-validates them
  the moment they appear (re-run after the regen settles, then drop the
  pending entries).
* **OQ (from MT-2.4-02):** paging input for >100 available tasks.
* **OQ (from MT-2.4-06):** cache invalidation when an Owner edits policy
  mid-session.

## 2026-10-12 — WP-2.4 complete

Verification battery green: `uv run --directory bridge ruff check .`,
`ruff format --check .`, `mypy .` (strict), `pytest -q` → **313 passed,
5 skipped** (the opt-in live suite; 4 of its 5 tests pass against the real
backend when enabled, per the recorded run above). No secrets committed
(the live-harness dev password is the compose container's documented local,
allowlist-registered; the seeded tokens are runtime-generated).