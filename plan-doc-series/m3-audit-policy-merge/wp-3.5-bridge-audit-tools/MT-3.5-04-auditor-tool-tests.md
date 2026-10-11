# MT-3.5-04 — Write auditor tool tests incl. invalid evidence guidance

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.5-04 |
| Title | Write auditor tool tests incl. invalid evidence guidance |
| Parent WP | WP-3.5 — Bridge audit tools (Milestone M3) |
| Requirements | FR-AUD-01, FR-AUD-02 |
| Priority | M |
| Dependencies | MT-3.5-01..03 (the full WP-3.5 implementation), WP-3.3 (independence rules under test), WP-3.4 (policy outcomes), WP-0.3 (CI) |
| Parent sections | 11.2, 10.5, 9.4, 19 (WP-3.5), 18, 20.4, 20.5 |

## Context
WP-3.5's acceptance is behavioral: "auditor session end to end: list, claim, verify,
verdict; invalid evidence rejected with guidance." Section 18's integration and
contract rows define how this is proven (API with database and Redis; MCP tool
schemas). This final slice writes the cross-cutting suite: the full auditor chain
against the real backend, plus a malformed-evidence matrix asserting that every
rejection carries a catalog code, a hint and a next action — the "guidance" the
acceptance demands.

## Inputs / Prerequisites
* MT-3.5-01..03 — schema, validation, flow.
* Parent plan Section 10.5 — verdict shape and error rules under test; Section 9.4 —
  expected T13/T14 outcomes for valid verdicts.
* WP-3.3 — `AUDITOR_SAME_AS_CODER` / `ROLE_NOT_PERMITTED` behaviors exercised
  end-to-end (their unit tests live in WP-3.3; this suite asserts the tool-level
  experience).
* WP-3.4 — Policy Engine outcomes the chain must produce on valid verdicts.
* WP-0.3 — CI pipeline running the suite.

## Scope (in)
* An end-to-end auditor chain test against the integration environment: independent
  auditor session lists `to_be_audited`, claims (T11), read-only checkout, submits a
  well-formed verdict with evidence, and the backend produces the correct outcome —
  all-rules-pass → merge pending + `audit.passed` (T13); any rule fails →
  `in_human_review` with the enumerated `review_reason` (T14).
* A malformed-evidence matrix: missing `evidence`; empty `commands`; command missing
  `label`/`command`/`exit_code`; `confidence` 0 and 6; verdict outside
  `pass`/`flag_risk`/`fail`; criterion without `met` — each asserted to produce a
  Section 9.2 catalog code with a hint and a next action naming the offending field
  (guidance, not a bare rejection).
* Cross-role rejections at the tool level: coder session claiming/verifying fails
  (`ROLE_NOT_PERMITTED`), same-session coder-auditor rejected
  (`AUDITOR_SAME_AS_CODER`), non-lease-owner verdict rejected.
* Audit-lease expiry (T12) surfacing as a stop-and-re-claim error.
* Schema contract check reusing MT-3.5-01's snapshot (Section 18 contract row).
* CI wiring so the suite runs with the bridge/integration jobs (Section 20.4 item 2).

## Out of scope
* Re-writing per-slice unit tests — they stay with MT-3.5-01..03.
* Backend-only Policy Engine rule-unit tests — WP-3.4.
* Authorization matrix unit tests — WP-3.3.
* MCP conformance across real clients — WP-2.11.

## Target paths
* `bridge/tests/` — auditor chain and guidance-matrix suite
* CI pipeline config (suite invocation)
* WP changelog entry

## Acceptance criteria
- [ ] The list → claim → verify → verdict chain passes end to end against the real
  backend (WP-3.5 acceptance, FR-AUD-01/02).
- [ ] Each malformed evidence payload is rejected with a Section 9.2 catalog code
  plus hint and next action identifying the problem (WP-3.5 acceptance: "invalid
  evidence rejected with guidance"; Section 10.5 tool rules).
- [ ] T13 and T14 outcomes appear correctly for pass and rule-fail verdicts
  (Section 9.4, Section 8.2).
- [ ] Cross-role and lease-owner rejections behave per Sections 10.5 and 12.2, using
  only catalog codes (Section 20.4 item 5).
- [ ] Schema snapshot matches Section 10.5 (Section 18 contract row); suite green in
  CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k audit_tools -q` — run the auditor chain plus the
malformed-evidence matrix against the integration environment; then the full bridge
suite stays green.

## Attachments
* [Section 11.2 — Auditor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 18 — Testing and Quality Strategy](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Asserting only "some error" for invalid evidence would pass while the required
  guidance (hint + next action) is missing — check all three elements of the error
  contract on every rejection case.
* The chain test must use a real backend and database (Section 18 integration row);
  mocking the verdict endpoint would not prove T13/T14.
* If WP-3.4's rules are still moving, anchor expected outcomes to the Section 9.4
  rule table rather than to a snapshot of current engine output, so the suite tracks
  the plan, not an accident.
