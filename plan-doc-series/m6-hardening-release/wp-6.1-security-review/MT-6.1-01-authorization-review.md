# MT-6.1-01 — Run the Authorization Review Against the Section 12.2 Matrix

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.1-01 |
| Title | Run the authorization review against the Section 12.2 matrix |
| Parent WP | WP-6.1 — Security review (Milestone M6) |
| Requirements | NFR-07, FR-SEC-01, FR-SEC-02, FR-SEC-03, FR-SEC-05 |
| Priority | M |
| Dependencies | MT-1.2-07 (authorization matrix tests exist), MT-1.9-04 (insert-only audit permissions), WP-5.2 (edge policies), WP-5.3 (device auth) complete; M1–M5 features under review (Section 19 WP-6.1 dependency) |
| Parent sections | 12.1 (threat model), 12.2 (authorization matrix), 12.5 (audit trail), 18 (Security row), 19 (WP-6.1 goal, deliverables, acceptance), 20.4, 20.5; ADR-004, ADR-006 |

## Context
Section 19 (WP-6.1): goal "verify Section 12.1 mitigations with tests and a
checklist review; fix findings", deliverables "threat-to-test mapping, findings log,
fixes", acceptance "no open high or critical findings; token scoping and traversal
tests in CI". This first slice builds the mapping and runs the authorization half of
the review: every cell of the Section 12.2 matrix (10 capabilities × 6 actors:
Owner, Agent coder, Agent auditor, Decomposer, Merge Executor, Device) must map to a
test, and the Section 12.1 threats whose mitigation is access control must map to
tests too. NFR-07 (OWASP ASVS Level 1) is the baseline; FR-SEC-01/02/03/05 are the
specific guarantees under verification.

## Inputs / Prerequisites
* Parent plan Section 12.1 — twelve threats with mitigations; each becomes a mapping
  row (covered by test / covered by review / explicitly out of system scope per
  12.3's honest limitations).
* Parent plan Section 12.2 — the authorization matrix to verify cell by cell.
* Parent plan Section 12.5 — append-only audit trail properties (Event rows with
  actor and correlation id; viewer read-only; DB role cannot update/delete).
* MT-1.2-07 — existing authorization matrix tests; extend rather than duplicate.
* Section 18 Security row — "Authorization matrix tests; … Section 12.1 mapped to
  tests" — the discipline this task implements.
* Local Compose stack with fixtures for all six actor types (owner session, coder
  token, auditor token, decomposer token, merge executor service token, device
  token).

## Scope (in)
* Create the threat-to-test mapping (`docs/plan/security-threat-test-mapping.md`):
  one row per Section 12.1 threat, naming the test(s) or review step that verifies
  its mitigation, plus the Section 12.3 limitations row marked as audit-time
  detection (not prevention).
* Run the authorization review: for each matrix cell, execute an existing or new
  test asserting the exact yes/no answer from Section 12.2 — including negative
  cases (each actor denied the capabilities marked No; cross-project denial for
  agent tokens, FR-SEC-01; distinct token kinds rejected where they must not mix,
  FR-SEC-02).
* Verify Section 12.5: state-changing actions write Event rows with actor and
  correlation id; the audit viewer surfaces no mutation path; the application DB
  role cannot UPDATE/DELETE audit rows (the MT-1.9-04 permission still enforced).
* Verify FR-SEC-05: rate limiting active on agent and device endpoints (Section
  12.2's "rate limited" token note).
* Log every finding in the findings log (`docs/plan/security-findings-log.md`)
  with severity (critical/high/medium/low), status and follow-up task ids; fix
  high/critical findings within this task where the fix is small, otherwise file
  follow-ups (WP-6.1 acceptance: no open high or critical).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Upload abuse tests — MT-6.1-02; token lifecycle — MT-6.1-03; secrets/log
  scrubbing — MT-6.1-04; dependency audit — MT-6.1-05 (each appends to the same
  findings log).
* Edge-policy execution testing — MT-5.2-04 (verify it exists and link it; the
  Section 15.2/15.3 layers are reviewed by pointer here).
* External penetration testing or formal ASVS certification — the plan requires the
  baseline and internal review (Section 19 WP-6.1).
* Fixing findings from other slices — those slices own their fixes.

## Target paths
* `docs/plan/security-threat-test-mapping.md` (WP-6.1 deliverable)
* `docs/plan/security-findings-log.md` (WP-6.1 deliverable; created here, appended
  by MT-6.1-02 … 05)
* `backend/tests/` — authorization review tests (matrix cells, audit-trail
  properties, rate limiting) added where MT-1.2-07 has gaps
* WP changelog entry

## Acceptance criteria
- [ ] The threat-to-test mapping covers every Section 12.1 threat and the 12.3
  limitations with a named test or review step (Section 19 WP-6.1 deliverable;
  Section 18 Security row).
- [ ] Every Section 12.2 matrix cell is asserted by a test — 10 capabilities × 6
  actors, exact yes/no parity (FR-SEC-01/02; ADR-004/ADR-006).
- [ ] Section 12.5 properties verified: Event rows written with actor/correlation id,
  viewer read-only, DB role cannot update/delete audit rows (FR-SEC-03).
- [ ] FR-SEC-05 rate limiting verified on agent and device endpoints.
- [ ] Findings log exists with all findings from this slice, each with severity;
  zero open critical/high (Section 19 WP-6.1 acceptance).
- [ ] Authorization tests run in CI (Section 19 WP-6.1 acceptance; Section 20.4
  item 2); changelog note added (item 7).

## Test command
`pytest backend/tests/ -k authorization -v` — all Section 12.2 cell assertions,
audit-trail property tests and rate-limit checks pass; then review
`docs/plan/security-threat-test-mapping.md` for full Section 12.1 coverage and
`docs/plan/security-findings-log.md` for zero open critical/high entries from this
slice.

## Attachments
* [Section 12.1 — Threat model summary](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication and authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.1 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The matrix is the contract: if a test disagrees with a Section 12.2 cell, the
  matrix wins — a code "fix" that changes the answer is a regression, and a plan
  change is the plan owner's call, not this task's.
* Severity classification for findings is judgment — define the scale (what counts
  as critical/high) at the top of the findings log so later slices classify
  consistently; WP acceptance hinges on it.
* Appendix A reserves no `docs/security/` directory — findings and mapping live
  under `docs/plan/` with the other process artifacts; record the choice in the
  changelog instead of inventing a top-level docs area.
