# Client compatibility matrix (parent plan Section 10.9)

Status: **skeleton — all client cells pending verification (MT-2.11-07).**
Created by WP-2.11 / MT-2.11-01. The rows and client names below mirror
Section 10.9 of `ai_agent_task_orchestrator_architecture_plan.md` verbatim;
every "Prompts surfaced" / "Images in tool results" cell starts as
**To verify** and is filled only from a recorded conformance run.

## How a cell gets filled (MT-2.11-07 procedure)

1. Run the conformance runner against the client being verified (one
   client per run; the runner drives the bridge as that client's MCP
   session):

   ```bash
   uv run --directory bridge python -m tests.conformance.runner \
     --manifest /path/to/repo/orchestrator.json \
     --repo /path/to/repo \
     --project-id PID00007 \
     --coder-token $TOKEN --auditor-token $TOKEN --decomposer-token $TOKEN \
     --client-label "Aider" \
     --report conformance-report-aider.json
   ```

2. The run must exit 0 with all ten Section 10.5 tools exercised and all
   four Section 10.7 prompts recorded. The JSON report's `matrix` object
   carries the four Section 10.9 cells computed from what the run actually
   observed (transport, prompt count, image-vs-text packaging, notes) —
   copy them into the row below verbatim and attach the report as evidence.
3. Record the run date, bridge version and the client version in the
   Notes cell. Never fill a cell from documentation or expectation —
   only from a passing run.

The hermetic harness self-tests (`uv run --directory bridge pytest -k
conformance`) pin the runner itself; they are not client evidence.

## The matrix

| Client | Transport | Prompts surfaced | Images in tool results | Notes |
|---|---|---|---|---|
| Claude Code CLI | STDIO | To verify | To verify | Reference client |
| VS Code Copilot / IDE | HTTP/SSE or STDIO | To verify | To verify | Check tool-approval UX |
| OpenCode | STDIO | To verify | To verify | |
| Aider | STDIO or wrapper | To verify | To verify | May need a documented instruction snippet |
| DeepSeek-based harness | Varies | To verify | To verify | Relies on OCR fallback path |
| Custom agent | Either | To verify | To verify | Must pass the conformance script |

Expected values from the plan (Claude Code: prompts/images expected yes;
Aider: likely text-only; DeepSeek harness: text-only) stay out of the
verified cells until a run proves them — the plan's expectation is the
hypothesis, the run is the evidence.

## Verified runs

_None yet — MT-2.11-02 through MT-2.11-06 verify each client in order; this
table is updated by MT-2.11-07._
