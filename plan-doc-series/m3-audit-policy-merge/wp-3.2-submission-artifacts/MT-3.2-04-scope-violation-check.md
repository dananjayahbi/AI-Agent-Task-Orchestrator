# MT-3.2-04 — Implement scope violation check against target_scope

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.2-04 |
| Title | Implement scope violation check against target_scope |
| Parent WP | WP-3.2 — Submission handling and artifacts (Milestone M3) |
| Requirements | FR-AUD-01, FR-TSK-03 |
| Priority | M |
| Dependencies | MT-3.2-03 (authoritative changed_files); MT-3.2-01 (resolution row) |
| Parent sections | 9.7, 12.3 (path and scope enforcement), 7.2 (target_scope), 8.2 (T8), 8.4, 19 (WP-3.2), 20.4, 20.5 |

## Context
Section 12.3 defines honest scope enforcement: submissions and audits compare changed
files to `target_scope`, paths are normalized and rejected if they escape the repo root,
and violations escalate to mandatory human review (G-06). Section 19 WP-3.2's acceptance
is explicit — an out-of-scope patch lands in `in_human_review` with `scope_violation`.
This micro-task implements the comparison itself against the authoritative
`changed_files` from MT-3.2-03, producing the flag that drives transition T8
(MT-3.2-05) and Policy Engine rule R2 (WP-3.4).

## Inputs / Prerequisites
* MT-3.2-03 — authoritative `changed_files` derived from the stored patch.
* MT-3.2-01 — the resolution/submission the check runs for; Task `target_scope`
  (Section 7.2: list of path globs relative to the repo root).
* Parent plan Section 12.3 — normalization rules; what is and is not enforceable.
* Canonical error code `SCOPE_VIOLATION` (Section 9.2 catalog) — already exists for
  scope failures.
* The single shared glob matcher agreed with MT-3.1-03 / WP-3.4.

## Scope (in)
* A pure check: given `target_scope` globs and the authoritative `changed_files`,
  determine whether any changed file lies outside every scope glob.
* Path normalization consistent with Section 12.3 (repo-root-relative; traversal,
  absolute and symlink-escape inputs rejected rather than matched).
* Record the outcome on the submission path (violating file list captured) so both the
  T8 transition (MT-3.2-05) and rule R2 (MT-3.4-02) read one computed result instead of
  recomputing divergently — the Section 9.4 note still lets the engine recompute from
  the stored patch; keep both paths on the same matcher and semantics.
* Unit tests: in-scope patch clean; one out-of-scope file flagged; empty scope list
  behavior; glob edge cases (directory prefix, extension match); traversal input
  rejected.
* Add a WP changelog note.

## Out of scope
* Firing T8 or setting `review_reason` — MT-3.2-05.
* Rule R2 evaluation and its `test_failure`/`scope_violation` decision wiring —
  WP-3.4 (MT-3.4-02).
* Enforcing scope in the agent's local file tools — explicitly not enforceable
  (Section 12.3); this is detection at submission/audit time.
* Validating `target_scope` at task creation — WP-1.4 owns task fields.

## Target paths
* `backend/apps/tasks/` (scope check module wired into the submission path)
* `backend/tests/` (scope check tests)
* WP changelog entry

## Acceptance criteria
- [ ] Any changed file outside every `target_scope` glob is flagged on the submission,
  with the offending paths captured (Section 19 WP-3.2 acceptance: out-of-scope patch
  is detectable and drives `scope_violation` — FR-AUD-01).
- [ ] Path handling follows Section 12.3: inputs normalized, repo-root escapes
  rejected, no absolute-path matching.
- [ ] The check uses the authoritative `changed_files` from the stored patch, never
  agent- or auditor-supplied claims (Section 9.7; Section 9.4 design note).
- [ ] A single shared glob matcher is used (same semantics as MT-3.1-03 validation and
  WP-3.4 rules) — no second matcher introduced.
- [ ] Where the check result is surfaced as an error, the code is `SCOPE_VIOLATION`
  from the catalog (Section 20.4 item 5); no new codes.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k scope_check -q` and confirm: clean in-scope submission,
single out-of-scope file flagged with its path, traversal/absolute path rejected, and
empty-`target_scope` behavior documented; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 12.3 — Path and scope enforcement (G-06)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine rule R2 inputs](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.2 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Empty `target_scope` semantics (does an empty list mean "everything is out of
  scope" or "unrestricted"?) are not stated in the plan — decide explicitly, document
  it in the test, and raise OQ-xx if either reading materially changes escalation.
* The engine (Section 9.4) recomputes R2 from the stored patch; keep this check and
  the engine's reconfiguration on identical matcher semantics or submissions could
  pass here and fail at rule time (or vice versa).
