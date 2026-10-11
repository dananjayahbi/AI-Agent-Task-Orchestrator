# MT-3.3-01 — Add auditor role gating to work listing and claim

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.3-01 |
| Title | Add auditor role gating to work listing and claim |
| Parent WP | WP-3.3 — Auditor claim and verdict API (Milestone M3) |
| Requirements | FR-AUD-01, FR-AUD-02, G-03 |
| Priority | M |
| Dependencies | MT-3.2-01 (submissions produce `to_be_audited` work); MT-2.4-02 (`role` parameter on `get_available_tasks`); WP-1.6 complete (claim transaction) |
| Parent sections | 9.2 (work/claim endpoints), 10.5 (role parameter), 12.2 (authorization matrix), 8.2 (T11), 19 (WP-3.3), 20.4, 20.5 |

## Context
G-03 records that the original spec defines an Auditor but gives it no tools; Section
10.5 closes the gap by giving `get_available_tasks` and `claim_task` a `role`
parameter (coder default, `auditor`), with auditors seeing `to_be_audited` work.
Section 12.2's authorization matrix is unambiguous: claim `pending` is coder-only,
claim `to_be_audited` is auditor-only. FR-AUD-01 requires submitted tasks be claimable
only by an independent auditor session. This micro-task adds role-aware gating to the
backend work listing and claim so T11 (auditor claim) can exist at all.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `GET /projects/{pid}/work` (available tasks, `role`,
  filters) and `POST /tasks/{id}/claim` (Agent).
* Parent plan Section 10.5 — `role` values (`coder` default, `auditor`) and the
  `AUDITOR_SAME_AS_CODER` claim error (independence itself is MT-3.3-02).
* Parent plan Section 12.2 — authorization matrix rows "Claim `pending`" and
  "Claim `to_be_audited`".
* MT-3.2-01 — submissions that populate `to_be_audited` (T7 from MT-3.2-05).
* WP-1.6 claim transaction (row lock, skip-locked, concurrency guards).

## Scope (in)
* Accept and validate `role` on `GET /projects/{pid}/work`: `coder` (default) lists
  `pending` unblocked tasks; `auditor` lists `to_be_audited` tasks — never a mixed or
  wrong-state listing (Section 10.5 behavior).
* Accept and validate `role` on `POST /tasks/{id}/claim`: `coder` claims only from
  `pending` (existing T4 path unchanged); `auditor` claims only from `to_be_audited`
  and executes the **T11** guards from Section 8.2 (auditor session differs from
  coder, audit lease available) as the audit-claim half of the transition.
* Reject role/state mismatches with catalog codes (`ROLE_NOT_PERMITTED` where the
  caller's role may not act, `TASK_STATE_CONFLICT` where the state forbids it) — no
  invented codes.
* Mirror the same gating behind the bridge tool surfaces that call these endpoints
  (`get_available_tasks`, `claim_task` with `role`) — contract-level tests only here;
  bridge-side plumbing already exists via MT-2.4-02 / MT-2.4-04.
* Unit/integration tests: role-filtered listings, coder-vs-claim matrix from
  Section 12.2, invalid role values.
* Add a WP changelog note.

## Out of scope
* The independence check `AUDITOR_SAME_AS_CODER` — MT-3.3-02.
* Audit lease expiry/sweep semantics (T12) — MT-3.3-03.
* Audit Report persistence and verdict endpoint — MT-3.3-04 / MT-3.3-05.
* Bridge tool schemas — WP-2.4 already defined the `role` parameter.
* Changing the coder claim path (T4) — WP-1.6.

## Target paths
* `backend/apps/` (work listing and claim endpoints: role parameter handling,
  T11 guard wiring)
* `backend/tests/` (role gating tests)
* WP changelog entry

## Acceptance criteria
- [ ] `GET /projects/{pid}/work` with `role=auditor` returns only `to_be_audited`
  tasks; with `role=coder` (or omitted) it returns only unblocked `pending` tasks
  (Section 10.5; FR-AUD-01).
- [ ] `POST /tasks/{id}/claim` with `role=auditor` only succeeds on `to_be_audited`
  and applies the T11 guards (Section 8.2); coder claims on `to_be_audited` and
  auditor claims on `pending` are rejected per the Section 12.2 matrix.
- [ ] Invalid `role` values and role/state mismatches return catalog codes
  (`ROLE_NOT_PERMITTED` / `TASK_STATE_CONFLICT`) — Section 20.4 item 5.
- [ ] A successful auditor claim records `claimed_role` = `auditor` with auditor lease
  fields per Section 7.2 (claim side of T11).
- [ ] Existing coder behavior (T4) unchanged — regression tests stay green.
- [ ] OpenAPI updated for the `role` parameter with schema diff reviewed
  (Section 20.4 item 4); tests green in CI; changelog note added
  (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k auditor_role_gating -q` and confirm: role-filtered
work listings for both roles, claim matrix rejections with catalog codes, auditor
claim setting `claimed_role` on `to_be_audited` only, and coder-path regressions;
then `pytest backend/tests -q` stays green.

## Attachments
* [Section 10.5 — Tool catalog (role parameter)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authorization matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T11)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Role source of truth: Section 10.5 makes `role` a caller-supplied parameter while
  Section 12.2 treats coder/auditor as distinct capabilities — the backend must treat
  the parameter as a request intent validated against state/session, never as trust;
  independence (MT-3.3-02) is the real gate.
* An "auditor" listing must not leak full task content beyond descriptors (Section
  10.5: listings return descriptors); keep the serializer shared with the coder path.
