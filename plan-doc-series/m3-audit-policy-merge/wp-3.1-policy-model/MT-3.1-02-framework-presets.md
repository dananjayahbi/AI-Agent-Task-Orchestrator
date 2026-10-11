# MT-3.1-02 — Create framework preset library (Django, Next.js, Flutter glob sets)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.1-02 |
| Title | Create framework preset library (Django, Next.js, Flutter glob sets) |
| Parent WP | WP-3.1 — Policy model and defaults (Milestone M3) |
| Requirements | FR-PRJ-05 |
| Priority | M |
| Dependencies | MT-3.1-01 (policy fields persisted) |
| Parent sections | 7.2 (critical/migration/sensitive glob fields), 12.3 (glob validation), 19 (WP-3.1), 20.4, 20.5 |

## Context
Section 7.2 gives `critical_path_globs`, `migration_path_globs` and
`sensitive_config_globs` meaningful defaults ("CI/CD, root migrations, security config",
"framework-specific", "env files, key material, security rules") but leaves the actual
glob sets framework-dependent. Section 19 WP-3.1 lists the preset library — at least
Django, Next.js and Flutter — as a deliverable, with the acceptance "presets selectable
at project creation". This micro-task authors those preset glob sets and makes them
selectable so new projects get sensible escalation triggers without hand-editing policy.

## Inputs / Prerequisites
* MT-3.1-01 — persisted policy fields the presets populate.
* Parent plan Section 7.2 — the three glob fields and the meaning of each default
  category (what a preset must cover).
* Parent plan Section 12.3 — globs are repo-root-relative paths; traversal, absolute
  and symlink-escaping paths are rejected.
* Section 19 WP-3.1 acceptance — "presets selectable at project creation".

## Scope (in)
* A versioned preset library (data, not code logic) with at least three frameworks:
  Django, Next.js, Flutter; each preset supplies glob lists for all three categories
  (`critical_path_globs`, `migration_path_globs`, `sensitive_config_globs`).
* Preset glob content derived from the Section 7.2 category meanings: CI/CD files and
  root migrations and security config for critical; framework migration directories for
  migration; env files, key material and security rules for sensitive.
* An API/dto surface to list available presets and to apply a preset at project
  creation or project update (fills the three policy fields in one action).
* Tests: each preset applies cleanly, is readable by the policy read endpoint
  (MT-3.1-01), and every glob passes the validation rules of MT-3.1-03 once it lands
  (write tests to match those rules; coordinate ordering).
* Add a WP changelog note.

## Out of scope
* Glob syntax/range validation implementation — MT-3.1-03.
* Using the globs for escalation — Policy Engine rules R3/R4/R5 (WP-3.4) and the
  scope check (MT-3.2-04) consume them later.
* Per-task `target_scope` presets — tasks keep their own scope (Section 7.2 Task).
* Presets for frameworks beyond the three required — may be added later, not here.
* Web UI for preset selection — WP-4.10.

## Target paths
* `backend/apps/projects/` (preset library data module, preset-apply endpoint or
  create-time parameter)
* `backend/tests/` (preset coverage and apply tests)
* WP changelog entry

## Acceptance criteria
- [ ] At least Django, Next.js and Flutter presets exist, each covering all three glob
  categories from Section 7.2 (FR-PRJ-05; Section 19 WP-3.1 deliverable).
- [ ] A preset can be selected at project creation and writes the three policy glob
  fields (Section 19 WP-3.1 acceptance: "presets selectable at project creation").
- [ ] Every preset glob is repo-root-relative and passes policy validation
  (Section 12.3; no absolute paths, no parent-traversal escapes).
- [ ] No policy fields beyond Section 7.2 are introduced by presets
  (Section 20.5 traceability).
- [ ] Errors (unknown preset id, invalid selection) use catalog codes
  (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_presets -q` and confirm: three frameworks present,
each preset fills `critical_path_globs`, `migration_path_globs` and
`sensitive_config_globs`, all globs pass validation; then `pytest backend/tests -q`
stays green.

## Attachments
* [Section 7.2 — Project Policy glob fields](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-3.1 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.3 — Path and scope enforcement](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not enumerate the concrete glob strings — preset content is framework
  judgment. Document the derivation for each glob next to the data so reviewers can
  audit it against the Section 7.2 category meanings; the plan stays authoritative.
* Glob metacharacter escaping (`{}`, `*`, `?`) must match whatever matcher
  MT-3.1-03 / R2–R5 adopt — one matcher, shared rules, or presets will silently
  mismatch later rules.
