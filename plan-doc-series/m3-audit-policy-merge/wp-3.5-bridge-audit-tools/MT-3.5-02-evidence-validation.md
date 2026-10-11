# MT-3.5-02 — Implement structured evidence validation (commands, exit codes, criteria)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.5-02 |
| Title | Implement structured evidence validation (commands, exit codes, criteria) |
| Parent WP | WP-3.5 — Bridge audit tools (Milestone M3) |
| Requirements | FR-AUD-02 |
| Priority | M |
| Dependencies | MT-3.5-01 (registered verdict schema), WP-3.3 (auditor authorization on the endpoint), WP-0.5 (error envelope conventions) |
| Parent sections | 10.5, 9.4, 9.2, 19 (WP-3.5), 20.4, 20.5 |

## Context
WP-3.5's acceptance requires that "invalid evidence [is] rejected with guidance".
The verdict's `evidence` is what the Policy Engine consumes: R1 tests fail on
non-zero exit codes or missing test evidence, R7 uses `confidence`, R8 uses the
`verdict` (Section 9.4) — so structurally invalid evidence (missing commands, absent
exit codes, confidence out of range) must be rejected before it reaches the engine,
with a message that tells the auditing model exactly what to fix. Section 10.5's tool
design rules fix the shape of that guidance: stable code, human-readable hint, next
action.

## Inputs / Prerequisites
* Parent plan Section 10.5 — verdict input shape and its `required` constraints
  (top-level and nested), plus tool error rules.
* Parent plan Section 9.4 — how evidence feeds R1/R7/R8 (why each field matters).
* Parent plan Section 9.2 — `POST /tasks/{id}/audit-verdict` and the canonical code
  catalog (`VALIDATION_ERROR` among them).
* MT-3.5-01 — the registered schema that mirrors this contract.
* WP-3.3 — role/lease gating on the endpoint (this task validates payload content,
  not who may call).

## Scope (in)
* Validation of the verdict payload at the bridge boundary and (contract-wise) the
  backend endpoint's mirror checks: required fields present; `verdict` in
  {`pass`, `flag_risk`, `fail`}; `confidence` integer within 1–5; `evidence.commands`
  a non-empty array whose entries each carry `label`, `command` and integer
  `exit_code` (`summary` optional); `acceptance_criteria_results`, when present,
  pairing `criterion` with boolean `met`.
* Rejection responses that carry the canonical error code plus a hint and a next
  action naming the missing/invalid field — "guidance" per WP-3.5's acceptance, not
  a bare 400.
* Consistency: the bridge rejects malformed payloads before sending, and the backend
  enforces the same rules server-side (defense in depth — never trust the bridge
  alone, Section 12.1 posture).
* Tests: each malformed shape (missing `evidence`, missing `exit_code`, confidence 0
  and 6, unknown verdict, empty `commands`, criterion without `met`) rejected with
  catalog code + guidance; every valid shape accepted and forwarded unchanged.

## Out of scope
* The schema definition itself — MT-3.5-01.
* Semantic audit checks (running tests, verifying claims) — MT-3.5-03 and the
  auditor's own workflow; the Policy Engine judges content, this task judges shape.
* Authorization/lease checks — WP-3.3.
* Policy Engine rule evaluation — WP-3.4.

## Target paths
* `bridge/` — verdict payload validation and error guidance
* `backend/` — endpoint-side mirror validation contract (per WP-3.3's endpoint)
* `bridge/tests/`, `backend/tests/` — validation tests
* WP changelog entry

## Acceptance criteria
- [ ] Every Section 10.5 constraint is enforced: required top-level keys, verdict
  enum, confidence 1–5, `commands` entries with `label`/`command`/`exit_code`,
  criterion/met pairing (FR-AUD-02).
- [ ] Each rejection carries a Section 9.2 catalog code plus a human-readable hint
  and a next action identifying the offending field (Section 10.5 tool rules,
  Section 19 WP-3.5 acceptance: "invalid evidence rejected with guidance").
- [ ] The backend endpoint enforces the same rules independently of the bridge
  (Section 12.1 posture: no single gate).
- [ ] Valid payloads pass through unchanged — validation never rewrites evidence
  (R1/R7/R8 consume what the auditor submitted).
- [ ] Only catalog codes used (Section 20.4 item 5); lint/type/tests green (item 2);
  changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k verdict_validation -q` and
`pytest backend/tests -k audit_verdict_validation -q` — run the malformed-payload
matrix on both sides, asserting catalog code, hint and next action each time; full
suites stay green.

## Attachments
* [Section 9.4 — Policy Engine (rule table)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Over-strict validation can block honest audits (e.g. rejecting a `notes`-less but
  fully evidenced verdict the schema does not require) — enforce exactly the
  Section 10.5 `required` lists, no more.
* Double validation drift: bridge and backend rules must stay one contract — derive
  both from the Section 10.5 shape and cover divergence in a shared contract test.
* Error guidance must not echo sensitive payload content (log scrubbing,
  Section 12.4) — name fields, not values.
