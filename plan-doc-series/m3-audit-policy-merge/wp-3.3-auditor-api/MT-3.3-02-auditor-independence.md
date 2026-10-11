# MT-3.3-02 — Implement auditor independence rule (AUDITOR_SAME_AS_CODER)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.3-02 |
| Title | Implement auditor independence rule (AUDITOR_SAME_AS_CODER) |
| Parent WP | WP-3.3 — Auditor claim and verdict API (Milestone M3) |
| Requirements | FR-AUD-01, G-20 |
| Priority | M |
| Dependencies | MT-3.3-01 (auditor claim path exists) |
| Parent sections | 10.5 (claim errors), 8.3 (invariant 3), 12.1 (self-approval threat), 19 (WP-3.3), 20.4, 20.5 |

## Context
G-20 fixes the undefined auditor lease/independence problem: the backend rejects an
auditor whose session or agent label matches the coder of that task, with the canonical
error `AUDITOR_SAME_AS_CODER` (listed in Section 10.5's `claim_task` errors and the
Section 9.2 catalog). Section 8.3 invariant 3 states the coder session and the auditor
session for one attempt are never the same, and Section 12.1 lists self-approval as a
threat mitigated exactly by this rule. Section 19 WP-3.3 acceptance: "same session or
same label cannot audit."

## Inputs / Prerequisites
* MT-3.3-01 — the auditor claim path where the check is enforced.
* Parent plan Section 10.5 — `AUDITOR_SAME_AS_CODER` listed as a `claim_task` error.
* Parent plan Section 7.2 — Task fields `worker_session_id` /
  `worker_agent_id` of the coder (recorded during T4 and carried per attempt),
  `claimed_role`, `attempt_number`.
* Agent Session entity (Section 7.2) — bridge-issued unguessable session id and
  `agent_label`.

## Scope (in)
* An independence check evaluated inside the auditor claim transaction (after the
  row lock, with the other claim guards): reject when the claiming auditor session id
  equals the coder session id recorded for the current attempt, OR when the claiming
  auditor's agent label equals the coder's agent label for the current attempt.
* Rejection returns the catalog error `AUDITOR_SAME_AS_CODER` (no new codes) and
  leaves the task in `to_be_audited` with no audit lease set.
* Check is per attempt: labels/sessions are compared against the current
  `attempt_number`'s coder, not historical attempts (Section 8.3 invariant 3 wording
  "for one attempt").
* Unit tests: session match rejected, label match rejected, distinct session+label
  allowed, historical-attempt coder does not block a later independent auditor.
* Add a WP changelog note.

## Out of scope
* The claim transaction/locking itself — MT-3.3-01 / WP-1.6.
* Audit lease mechanics (T11 lease fields, T12 expiry) — MT-3.3-03.
* Bridge-side duplicate-session prevention — backend is the enforcement point
  (Section 12.1 mitigation table).
* Verdict-time recheck — verdict endpoint (MT-3.3-05) reuses this function but the
  rule's tests live here.

## Target paths
* `backend/apps/` (independence check in the claim service)
* `backend/tests/` (independence rule tests)
* WP changelog entry

## Acceptance criteria
- [ ] An auditor session identical to the coder session of the current attempt cannot
  claim — `AUDITOR_SAME_AS_CODER` (Section 19 WP-3.3 acceptance "same session …
  cannot audit"; G-20).
- [ ] An auditor whose agent label equals the current attempt's coder label cannot
  claim — `AUDITOR_SAME_AS_CODER` ("same label cannot audit"; G-20).
- [ ] The check runs inside the claim transaction so it cannot be bypassed by racing
  claims (FR-AUD-01 independence guarantee).
- [ ] The error code already exists in the Section 9.2 catalog — no new codes
  (Section 20.4 item 5).
- [ ] A genuinely different session AND label claims successfully (T11 proceeds).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k auditor_independence -q` and confirm: same-session
rejection, same-label rejection, distinct-claim success, and attempt-scoped comparison
using catalog code `AUDITOR_SAME_AS_CODER`; then `pytest backend/tests -q` stays
green.

## Attachments
* [Section 10.5 — claim_task errors (AUDITOR_SAME_AS_CODER)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.3 — Invariants (coder/auditor session separation)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Label matching can be over-strict in practice (one human running coder and auditor
  CLIs under a shared label is exactly what G-20 intends to block, but generic labels
  like "opencode" would collide). Follow G-20 verbatim — label equality blocks — and
  raise an OQ-xx if real workflows need label namespacing; do not silently relax the
  rule.
* The coder's session/label for the attempt must survive worker-field clearing at T7
  (MT-3.2-05 clears worker fields); if they are cleared before auditor claim, the
  check loses its input — verify where the attempt's coder identity is retained and
  flag the design gap as OQ-xx if nothing stores it.
