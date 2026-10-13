# WP-3.5 — Bridge audit tools

`submit_audit_verdict` in the MCP bridge: the Section 10.5 verdict schema
registered as a tool contract, and bridge-boundary validation of the
evidence payload before the endpoint call (MT-3.5-01 and MT-3.5-02).

## Delivered

### MT-3.5-01 — verdict schema (registered tool spec)

`tools/schemas.py` registers `submit_audit_verdict` with Section 10.5's
auditor verdict shape **field for field** — `task_id`, `verdict`
(enum `pass|flag_risk|fail`), `confidence` (1–5), `notes`, `evidence`
(required `commands` of `{label, command, exit_code, summary?}` plus
`lint_clean`), `acceptance_criteria_results` (`{criterion, met}` items) —
and the plan's required list (`task_id, verdict, confidence, evidence`).
Nothing added, removed or renamed versus the plan. Reading (recorded): the
top level is strict (`additionalProperties: false`, per the bridge's tool
conventions and the no-smuggling design rule), while nested evidence stays
**open** so auditor-supplied keys survive verbatim (FR-AUD-02; the
backend stores evidence as supplied). Snapshot-pinned by
`tests/test_audit_verdict_tool.py::test_schema_is_the_section_10_5_verdict_shape`;
catalog-order and key-input pins updated (`test_tool_schemas.py`,
`test_layout.py`).

### MT-3.5-02 — evidence validation (bridge boundary)

Two layers before the wire: the declared schema (validated by
`registration.BridgeTool` before the handler runs) covers types, enum,
bounds and required keys; `tools/audit_verdict.py::validate_verdict_payload`
adds the semantics JSON Schema cannot express — at least one command
entry, non-empty `label`/`command`/`criterion` strings, integer
`exit_code`. Every rejection is a `VALIDATION_ERROR` whose
`hint`/`next_action`/`details.field` name the exact offending field
(`evidence.commands[1].exit_code`). Valid payloads pass through
**unchanged** — `evidence` is forwarded verbatim, extras included, with
the ADR-012 fencing pair (`session_id` + `lease_generation`, 0 when this
session never claimed) and an auto-minted `Idempotency-Key` (headers.md).
Backend rejections (`TASK_NOT_FOUND`, `TASK_STATE_CONFLICT`,
`LEASE_EXPIRED`, `LEASE_NOT_OWNED`, `ROLE_NOT_PERMITTED`,
`AUDITOR_SAME_AS_CODER`) pass through the translator verbatim. The
endpoint catalog gains `audit_verdict` (`POST /api/v1/tasks/{id}/
audit-verdict`, in the OpenAPI document via WP-3.3 — no pending flag) and
the contract suite gains its request sample.

Scope note: the MT's target list also mentioned backend/tests validation —
that half is **not** this WP's ownership (the backend audit/policy agent
owns it) and the server-side mirror already exists via WP-3.3's live
endpoint; this WP delivers the bridge-side gate.

## Deferred (roadmap 4a)

* **MT-3.5-03 (auditor flow)** — deferred: needs WP-2.8's
  `orchestrator:audit` prompt and WP-3.4's policy engine landing
  concurrently.
* **MT-3.5-04 (auditor tests)** — deferred: depends on MT-3.5-03 and
  WP-3.4.

## Files

`src/orchestrator_bridge/tools/audit_verdict.py` (new),
`tools/schemas.py`, `tools/registration.py`, `endpoints.py`; tests:
`tests/test_audit_verdict_tool.py` (new), plus pinned-test updates
(`test_tool_schemas.py`, `test_layout.py`, `test_openapi_contract.py`).

## Follow-ups

* Backend evidence-validation mirror parity is owned by the concurrent
  backend audit/policy agent (WP-3.3 already enforces server-side); a
  cross-check belongs in MT-3.5-04's deferred suite.
* Live-gated run against a real backend once an auditor session can claim
  a `to_be_audited` task end-to-end.

### Convergence gate (2026-10-14)

- Bridge suite at convergence: **684 passed, 7 skipped**; `test_openapi_contract` 13/13 green against the authoritative regen (`4026FFCA…`).
