# WP-2.11 — Client compatibility and MCP conformance script

## Unreleased

**MT-2.11-01 — Build the MCP conformance script (done).**
The plan's Section 18 "scripted client" now exists as a reusable measuring
instrument under `bridge/tests/conformance/`: stdio and streamable-HTTP MCP
client connections (`connection.py`), the individual conformance checks
(`checks.py` — catalog + schemas, rules block at initialize and claim per
FR-MCP-05, prompt surfacing/rendering, Section 9.2 catalog membership), the
three role scenarios (`scenarios.py` — coder orient/list/claim/details/
attachment/checkpoint/submit plus release on a second task and the
TASK_ALREADY_CLAIMED / TASK_NOT_FOUND / ATTACHMENT_UNSUPPORTED_FORMAT error
paths; auditor list/claim/verdict; decomposer draft), the Section 10.9 report
model (`report.py` — the four matrix columns verbatim, per-check pass/fail,
exit 0/1 contract) and the orchestration + standalone CLI (`runner.py`).
Prompt absence is *reported*, never failed (NFR-08); a broken tool response
(non-JSON payload or unexpected structured error) fails the run; error-path
checks assert only `api_errors.ErrorCode` catalog members; attachment checks
cover both Section 10.4 packagings and the untrusted banner (vision run and
text-only run both exercised). Invocation shape (risk-note decision):
**standalone entry point** — `uv run --directory bridge python -m
tests.conformance.runner --manifest ... --repo ... --coder-token ...`; the
pytest self-tests call `run_conformance()` directly. `docs/agent-guides/
compatibility-matrix.md` created with all six Section 10.9 client rows
verbatim and "To verify" cells plus the MT-2.11-07 fill procedure.
Evidence: `uv run --directory bridge pytest tests/ -k conformance -q` — 9
passed, 1 skipped (the live test skips without its env gate); the 9 include
two full stdio runs against a scripted loopback stub backend (all ten
Section 10.5 tools exercised, all four prompts recorded, matrix columns
exact), broken-backend-claim detection, broken non-JSON client response
detection, prompt-absence-reported, catalog-membership rejection of an
invented code, and the Section 10.9 column pin. Live Compose run:
`ORCHESTRATOR_BRIDGE_LIVE_TESTS=1 uv run pytest tests/test_conformance_live.py`
— **1 passed**: the full coder/auditor/decomposer flow against the real
backend (claim, details, banner-exactly-once text packaging, checkpoint,
submit to `to_be_audited`, release, auditor verdict, draft creation,
TASK_ALREADY_CLAIMED/TASK_NOT_FOUND error paths) with a report artifact
whose matrix row matches Section 10.9. `uv run ruff check .`, `uv run
ruff format --check .`, `uv run mypy .` — clean for all new/changed files
(the new live test self-seeds its task + attachment via its own
`manage.py shell` invocation and pre-cleans a known duplicate patch
artifact so the shared live DB re-seeds reliably).

### Deferred

**MT-2.11-02 — Claude Code CLI verification (deferred).** Blocked: the
environment has the `claude` CLI but no authenticated Claude account
(logged-out; no Anthropic credentials), and the reference-client matrix
cells may only be filled from a passing authenticated run.

**MT-2.11-03 — VS Code Copilot / IDE verification (deferred).** Blocked:
requires a Copilot-authenticated IDE session driving the bridge over
HTTP/SSE; no Copilot credentials in this environment.

**MT-2.11-04 — OpenCode verification (deferred).** Blocked: OpenCode
(1.15.13) is installed but no provider API key is configured, so it cannot
complete an MCP-driven task flow to record tool/prompt/image cells.

**MT-2.11-05 — Aider verification (deferred).** Blocked: `aider` is not
installed in this environment and no provider API key is available.

**MT-2.11-06 — DeepSeek-based harness verification (deferred).** Blocked:
no DeepSeek API key in the environment; the OCR-fallback cells need a
real harness run.

**MT-2.11-07 — Custom-agent template and matrix update (deferred).** Blocked
on MT-2.11-02 … 06: the matrix may only be filled from verified client runs.
The runner, the matrix skeleton and the per-run fill procedure are already
in place (MT-2.11-01), so this MT reduces to recording verified rows and
the custom-agent instruction template once authenticated clients exist.
