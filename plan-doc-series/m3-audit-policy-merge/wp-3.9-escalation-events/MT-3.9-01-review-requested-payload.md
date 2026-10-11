# MT-3.9-01 — Define the review.requested event payload with rule details

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.9-01 |
| Title | Define the review.requested event payload with rule details |
| Parent WP | WP-3.9 — Escalation notifications hook (Milestone M3) |
| Requirements | FR-MOB-04 |
| Priority | M |
| Dependencies | WP-3.4 (persisted rule results), WP-1.9 (event log and envelope conventions) |
| Parent sections | 9.6, 9.8, 8.4, 9.4, 19 (WP-3.9), 20.4, 20.5 |

## Context
Section 9.6 fixes the event envelope (`id`, `type`, `project_id`, `task_id`,
`occurred_at`, `actor`, `data`) and the event catalog, which includes
`review.requested|decided`. WP-3.9's goal: "Emit `review.requested` events with
reasons ready for push (consumed in M5)", and acceptance: "each review reason yields
one event with rule details". Section 9.8 makes `in_human_review` entry (all reasons)
a push trigger — M5's WP-5.4 dispatches from this payload. Section 9.4 persists
"every rule and its outcome … so the human reviewer sees exactly why the task was
escalated" — those persisted rule results are the "rule details" the payload carries.

## Inputs / Prerequisites
* Parent plan Section 9.6 — event envelope and catalog (verbatim).
* Parent plan Section 9.4 — Policy Engine rule table (R1–R9 → review reasons) and
  the persisted rule results this payload references.
* Parent plan Section 8.4 — canonical review-reason enum (12 values).
* Parent plan Section 9.8 — push triggers reading this payload (dedupe key needs the
  state version).
* WP-3.4 (MT-3.4-06) — persistence of rule results and engine version per audit
  report; WP-1.9 — event writing/publication machinery.

## Scope (in)
* The `data` contract for `review.requested`, built on the Section 9.6 envelope:
  the canonical `review_reason` (Section 8.4 enum), the rule details — the persisted
  rule results from the Policy Engine (Section 9.4, WP-3.4's structure: every rule
  and its outcome) — and `task_version` (needed for the Section 9.8 dedupe key
  `(event type, task id, state version)`).
* Field naming that matches WP-3.4's persisted rule-result structure exactly — one
  vocabulary, not a parallel "escalation details" shape.
* Envelope compliance: `type` = `review.requested`; `project_id`, `task_id`,
  `occurred_at`, `actor` per Section 9.6; written by the event log (WP-1.9).
* Readiness for push: nothing sensitive beyond ids, reason, rule outcomes and the
  state version — push payload minimization (Section 9.8) is applied by WP-5.4, but
  the payload must not carry free-text evidence that would tempt it to.
* A schema/contract definition plus envelope tests asserting the documented fields
  and catalog membership (Section 20.4 item 6).

## Out of scope
* Deciding *when* the event fires — MT-3.9-02.
* Reason-coverage tests — MT-3.9-03.
* The `review.decided` payload — WP-3.6's endpoint side of the catalog pair.
* Push dispatch, dedupe, preferences — WP-5.4 (consumer).
* Rule-result persistence — WP-3.4 (source).

## Target paths
* `backend/` — `review.requested` payload contract/serializer
* `backend/tests/` — envelope/contract tests
* Contract/OpenAPI or event-catalog documentation update (schema diff reviewed)
* WP changelog entry

## Acceptance criteria
- [ ] `review.requested` uses the Section 9.6 envelope with `type`
  `review.requested` and a `data` payload carrying the canonical `review_reason`,
  the persisted rule details, and `task_version` (Section 9.8 dedupe needs it).
- [ ] `review_reason` values come only from the Section 8.4 enum (12 values, none
  invented).
- [ ] Rule details reuse WP-3.4's persisted rule-result structure — no second,
  divergent shape for the same facts (Section 9.4).
- [ ] The event is registered in the Section 9.6 catalog contract
  (`review.requested|decided`) — catalog unchanged, shape documented
  (Section 20.4 item 6).
- [ ] No free-text evidence/secrets in the payload (Section 9.8 minimization posture,
  Section 12.4).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k review_requested_payload -q` — assert envelope fields,
reason-enum membership, rule-details structure equals WP-3.4's persisted shape, and
`task_version` presence; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.6 — Realtime gateway and event model](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine (rule results)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan fixes the event *type* and the requirement for rule details, but not a
  field-by-field JSON schema for `data` — derive fields from Sections 9.4, 8.4 and
  the 9.8 dedupe key only; anything else is an open question, not an invention.
* Two shapes for rule results (audit report vs event) would drift — assert
  structural equality with WP-3.4's persisted output in tests.
* Escalations without a reason (or with a non-enum reason) would break the M5 push
  mapper and the review UI — treat enum membership as a hard contract.
