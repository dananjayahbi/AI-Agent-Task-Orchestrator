# MT-3.5-03 — Implement the auditor flow with auditor rules integration

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.5-03 |
| Title | Implement the auditor flow with auditor rules integration |
| Parent WP | WP-3.5 — Bridge audit tools (Milestone M3) |
| Requirements | FR-AUD-01, FR-AUD-02; ADR-009 |
| Priority | M |
| Dependencies | MT-3.5-01, MT-3.5-02 (tool contract and validation), WP-3.3 (auditor role gating and independence), WP-2.4 (list/claim with `role=auditor`), WP-2.10 (read-only checkout helpers), WP-2.7 (rules delivery), WP-2.8 (`orchestrator:audit` prompt), WP-3.4 (Policy Engine decides outcome) |
| Parent sections | 11.2, 10.5, 10.6, 10.8, 8.2 (T11, T12, T13, T14), 9.4, 19 (WP-3.5), 20.4, 20.5 |

## Context
Section 11.2 fixes the auditor workflow: an independent session lists `to_be_audited`
tasks and claims one; checks out the branch (read-only intent); runs the project's
full test and lint commands; inspects the diff against acceptance criteria and scope;
submits a structured verdict with evidence and confidence, never editing code; and
"the backend decides the outcome" (Section 9.4, ADR-009 — the engine, not the
auditor, sets the outcome). WP-3.5's goal adds "read-only branch checkout helpers"
and acceptance "auditor session end to end: list, claim, verify, verdict". The
transitions: T11 (auditor claim — auditor session differs from coder), T12 (audit
lease expiry), T13 (verdict + all rules pass → merge pending, emit `audit.passed`),
T14 (verdict + any rule fails → `in_human_review` with enumerated `review_reason`,
push).

## Inputs / Prerequisites
* Parent plan Section 11.2 — the five workflow steps (verbatim).
* Parent plan Section 10.6 — auditor rules text (full test/lint matrix, verify each
  acceptance criterion, never modify the branch, honest confidence; project rules
  appended).
* Parent plan Section 10.8 — Git helper read-only guarantees (never pushes,
  force-resets or deletes).
* Parent plan Section 8.2 — T11/T12/T13/T14 guards and side effects; Section 9.4 —
  Policy Engine output.
* WP-3.3 — auditor role gating (`ROLE_NOT_PERMITTED`, `AUDITOR_SAME_AS_CODER`) and
  audit-lease endpoints.
* WP-2.4 — `get_available_tasks`/`claim_task` with `role` (`auditor` sees
  `to_be_audited`); WP-2.7 rules delivery; WP-2.8 `orchestrator:audit` prompt.

## Scope (in)
* End-to-end auditor session support in the bridge: list with `role=auditor`
  (only `to_be_audited`), claim (T11 through WP-3.3's endpoint), read-only checkout
  of the task branch via the Git helper, running the project's test/lint matrix,
  diff inspection against criteria and scope, then `submit_audit_verdict`
  (MT-3.5-01/02).
* Read-only branch checkout helper wiring: checkout for inspection with the helper's
  guarantee of read-only operations (Section 10.8) — the auditor never mutates the
  branch or working state beyond checkout.
* Auditor rules integration: the Section 10.6 auditor rules delivered through the
  claim response and initialize instructions (consuming WP-2.7's templates and
  delivery), and the `orchestrator:audit` prompt content aligned with the same flow
  (consuming WP-2.8).
* Outcome honesty: the tool reports what was submitted; final state (T13 merge-pending
  + `audit.passed`, T14 `in_human_review` + reason + push) comes from the backend
  Policy Engine (Section 9.4) — never simulated in the bridge.
* Lease expiry handling: T12 audit-lease expiry surfaces as a structured error
  telling the auditor to stop and re-claim, mirroring the coder lease discipline.

## Out of scope
* Verdict schema and evidence validation — MT-3.5-01/02.
* Backend role gating, independence rule, audit-lease endpoints — WP-3.3.
* Policy Engine rules R1–R9 and outcome computation — WP-3.4.
* Rules templates and prompt texts as deliverables — WP-2.7, WP-2.8 (this task
  consumes and wires them).
* Merge execution after approval — WP-3.7.

## Target paths
* `bridge/` — auditor session flow, checkout wiring, rules/prompt integration
* `bridge/tests/` — auditor flow tests
* WP changelog entry

## Acceptance criteria
- [ ] An auditor session completes list → claim → verify → verdict end to end
  against the real backend (WP-3.5 acceptance, FR-AUD-01/02).
- [ ] `get_available_tasks` with `role=auditor` shows only `to_be_audited`; claim
  enforces auditor independence via WP-3.3 (`AUDITOR_SAME_AS_CODER`) (Section 10.5).
- [ ] Branch checkout uses the helper's read-only operations; nothing is pushed,
  reset or deleted (Section 10.8).
- [ ] The Section 10.6 auditor rules are visible in the auditor's claim response and
  initialize instructions, and `orchestrator:audit` describes the same flow
  (Sections 10.6, 10.7).
- [ ] The final state is backend-decided (T13/T14 via Section 9.4) — the bridge never
  marks outcomes itself (ADR-009).
- [ ] Only catalog error codes used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k auditor_flow -q` — drive an auditor session against
the integration environment: list (auditor role), claim a `to_be_audited` task,
read-only checkout, submit a valid verdict, and assert the backend-produced outcome
(T13 or T14) plus rules delivery in the claim response; full bridge suite stays
green.

## Attachments
* [Section 11.2 — Auditor workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T11–T14)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The coder and auditor sessions for one attempt must never be the same (Section 8.3
  invariant 3) — this flow depends on WP-3.3's rule; do not re-implement a weaker
  check here.
* "Read-only intent" is not "read-only": wire checkout exclusively through the
  Section 10.8 helper so its no-push/no-reset/no-delete guarantee actually applies.
* If WP-2.7/WP-2.8 are incomplete, the flow still works tool-only (ADR-011) — mark
  those as dependencies rather than hard-coding rules text into this task.
