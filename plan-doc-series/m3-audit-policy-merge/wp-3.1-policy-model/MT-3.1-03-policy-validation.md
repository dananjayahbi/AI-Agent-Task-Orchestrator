# MT-3.1-03 — Implement policy validation (glob syntax, ranges)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.1-03 |
| Title | Implement policy validation (glob syntax, ranges) |
| Parent WP | WP-3.1 — Policy model and defaults (Milestone M3) |
| Requirements | FR-PRJ-05 |
| Priority | M |
| Dependencies | MT-3.1-01 (fields persisted), MT-3.1-02 (presets must pass validation) |
| Parent sections | 7.2 (Project Policy), 12.3 (glob validation discipline), 19 (WP-3.1), 20.4, 20.5 |

## Context
Section 19 WP-3.1 acceptance requires "invalid globs rejected", and Section 12.3
establishes the discipline that globs are validated on creation and paths never escape
the repo root. The Policy Engine rules R2–R5 (Section 9.4) and the submission scope
check (MT-3.2-04) trust that policy globs are well-formed and that numeric policy values
are sane; a bad glob or a nonsense range stored silently would break escalation later.
This micro-task closes WP-3.1 by validating policy writes.

## Inputs / Prerequisites
* MT-3.1-01 — the policy fields and their Section 7.2 types/defaults.
* MT-3.1-02 — preset globs, which must always validate (regression guard).
* Parent plan Section 7.2 — explicit ranges where stated: `auditor_min_confidence`
  (1–5); integer fields with operational defaults for the rest.
* Parent plan Section 12.3 — glob/path validation expectations (repo-root-relative,
  no traversal, no absolute paths).
* Canonical error code `VALIDATION_ERROR` (Section 9.2 catalog).

## Scope (in)
* Validation on `PATCH /projects/{pid}/policy` (and project create with policy or
  preset): 
  * glob syntax checks for `critical_path_globs`, `migration_path_globs`,
    `sensitive_config_globs` — parseable by the single shared glob matcher, each entry
    repo-root-relative, rejecting absolute paths and parent-directory escapes
    (Section 12.3).
  * range checks: `auditor_min_confidence` within 1–5 (explicit in Section 7.2);
    positive-integer checks for `lease_duration_minutes`, `lease_max_total_minutes`,
    `max_retries`, `max_concurrent_tasks`, `autonomous_diff_threshold_lines`,
    `stalled_after_minutes`, with `lease_max_total_minutes` >= `lease_duration_minutes`
    (semantics implied by Section 8.6 hard-cap wording).
  * enum checks: `lease_extension_mode` and `merge_strategy` restricted to the
    Section 7.2 values.
* Rejections return `VALIDATION_ERROR` with per-field details in the Section 9.2
  envelope (no new codes).
* Unit tests: each invalid class rejected, each default accepted, each preset from
  MT-3.1-02 accepted.
* Add a WP changelog note.

## Out of scope
* Enforcing the globs against actual changed files — R2/R3/R5 (WP-3.4) and the
  submission scope check (MT-3.2-04).
* Task `target_scope` validation — task-creation work (WP-1.4) owns that; only keep
  matcher consistency in mind.
* Range policy beyond what Section 7.2/8.6 imply — stricter limits would be a new
  decision, not this task.
* Validation UI feedback in the policy editor — WP-4.10.

## Target paths
* `backend/apps/projects/` (policy serializer/endpoint validation logic)
* `backend/tests/` (policy validation tests)
* WP changelog entry

## Acceptance criteria
- [ ] Invalid glob syntax, absolute paths and parent-traversal globs in any of the
  three policy glob fields are rejected — Section 19 WP-3.1 acceptance "invalid globs
  rejected" (FR-PRJ-05).
- [ ] `auditor_min_confidence` outside 1–5 is rejected (Section 7.2 explicit range).
- [ ] Enum fields accept only Section 7.2 values; numeric fields reject non-positive
  values; `lease_max_total_minutes` < `lease_duration_minutes` is rejected.
- [ ] All rejections use `VALIDATION_ERROR` with field details (Section 9.2 catalog;
  Section 20.4 item 5) — no invented codes.
- [ ] Every preset from MT-3.1-02 and every Section 7.2 default passes validation
  (no valid input blocked).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_validation -q` and confirm: malformed glob,
absolute glob, escaping glob, out-of-range confidence and bad enums each return
`VALIDATION_ERROR`, while defaults and all three presets pass; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 7.2 — Project Policy fields and ranges](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.3 — Path and scope enforcement](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* One matcher must be shared between this validation and the Rule Engine glob
  matching (WP-3.4); two implementations would let a glob that "validates" fail to
  match at rule time — agree on the matcher before writing tests.
* Positive-integer bounds beyond `auditor_min_confidence` are inferred from Section
  7.2/8.6, not stated as ranges; if a stricter bound seems needed, record it as a new
  open question (OQ-xx) instead of silently inventing one.
