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

*None — the two roadmap-4a items (MT-3.5-03, MT-3.5-04) were lifted on
2026-10-14 (WP-2.8's `orchestrator:audit` prompt and WP-3.4's policy
engine landed in earlier batches) and are delivered under
`## Unreleased`; no WP-3.5 item remains blocked.*

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

## Unreleased

**MT-3.5-03 — Implement the auditor flow with auditor rules integration (done).**

The bridge now carries the auditor flow end to end. The `claim_task` wire
body gained the `role` field (WP-3.3's `ClaimRequest`), so an auditor claim
reaches the backend's T11 half instead of defaulting to coder; the tool
schema description was updated to match. Connect-time rules delivery now
renders **both** Section 10.6 blocks — the coder standard rules and the
auditor obligations — via a new shared `rules.render_connect_rules` helper,
used identically by the initialize instructions (`server._initialize_instructions`)
and `get_project_context` (byte-identity preserved, G-08); the auditor rules
are therefore visible before any claim, satisfying the "initialize
instructions" acceptance. The read-only checkout requirement is exercised
through the Section 10.8 helper (`create_or_switch_branch` + the `run_git`
capability guard refusing push/reset). Outcome honesty is pinned: the verdict
tool reports the backend's own task state/`merge_status`/`review_reason`
(T13 merge-pending vs T14 `in_human_review`) and never marks outcomes itself
(ADR-009).

New `tests/test_auditor_flow.py` (`-k auditor_flow`): role-on-the-wire +
auditor-rules claim, auditor list filter, both-blocks instructions,
byte-identical context, read-only checkout refusal sentinel, verdict
fencing-pair + backend-decided outcome, T12 `LEASE_EXPIRED` stop-and-re-claim,
and a live-gated list→claim→checkout→verdict chain against the real backend
(the `_live_backend` seed gained an auditable T004 with a stored clean patch
and a media root). Test evidence: `uv run pytest tests/test_auditor_flow.py -q`
→ **8 passed** (unit; live chain gated on `ORCHESTRATOR_BRIDGE_LIVE_TESTS=1`).
Full-suite verification (2026-10-14): `uv run pytest -q` → **775 passed,
10 skipped**; every failure sits in `tests/test_merge_executor_worktree.py`
(concurrent WP-3.7 WIP, outside this WP) — zero failures in this WP's files;
scoped `ruff check`/`ruff format --check`/`mypy` clean for them.

**MT-3.5-04 — Write auditor tool tests incl. invalid evidence guidance (done).**

New `tests/test_audit_tools.py` (`-k audit_tools`) pins WP-3.5's behavioral
acceptance. A malformed-evidence matrix asserts every rejection carries the
full three-element contract — Section 9.2 `VALIDATION_ERROR` code, non-empty
hint, non-empty next action — **and names the offending field**:
missing `evidence`, empty `evidence.commands`, a command missing
`label`/`command`/`exit_code`, `confidence` 0 and 6, a verdict outside
`pass|flag_risk|fail`, a criterion without `met`, and a blank criterion
string. Cross-role and lease-owner rejections are exercised at the tool
level (`ROLE_NOT_PERMITTED` on a coder claim of a `to_be_audited` task,
`AUDITOR_SAME_AS_CODER`, `LEASE_NOT_OWNED`), plus T12's `LEASE_EXPIRED`
stop-and-re-claim guidance. T13 *and* T14 both appear: the merge-pending
report (T13) in `test_auditor_flow.py` and a rule-fail `flag_risk` verdict
reporting the backend's `in_human_review` + enumerated `review_reason`
(T14, ADR-009 — reported, never chosen). The schema contract reuses
MT-3.5-01's snapshot (re-imported and re-run) and asserts only catalog codes
are declared. Test evidence: `uv run pytest tests/test_audit_tools.py -q`
→ **18 passed**; scoped `ruff check`/`ruff format --check`/`mypy` clean
(full-suite numbers as in the MT-3.5-03 entry above).

Shared-file edits (conflict-awareness): `tools/claim.py` (role on the wire),
`tools/schemas.py` (claim role description only — the verdict schema is
untouched), `rules.py` (new `render_connect_rules`), `server.py` +
`tools/context.py` (single-line switch to the connect render),
`tests/_live_backend.py` (auditable seed + media root),
`tests/test_claim_task.py` (wire-body pin updated to include `role`).
