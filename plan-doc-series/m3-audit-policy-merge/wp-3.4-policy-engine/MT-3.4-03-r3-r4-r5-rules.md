# MT-3.4-03 — Implement R3 critical paths, R4 migrations, R5 sensitive config rules

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.4-03 |
| Title | Implement R3 critical paths, R4 migrations, R5 sensitive config rules |
| Parent WP | WP-3.4 — Policy Engine (Milestone M3) |
| Requirements | FR-AUD-02, FR-AUD-03, FR-AUD-04, ADR-009 |
| Priority | M |
| Dependencies | MT-3.4-01 (framework); MT-3.1-01/MT-3.1-02 (glob policy fields and presets); MT-3.2-03 (authoritative changed files and patch) |
| Parent sections | 9.4 (R3, R4, R5), 7.2 (glob fields), 8.4, 8.5, 12.1 (secrets-in-diffs), 19 (WP-3.4), 20.4, 20.5 |

## Context
Section 9.4's glob-based escalation trio: **R3 Critical paths** fails when any
changed file matches `critical_path_globs` → `critical_path_changed`. **R4
Migrations** fails when any changed file matches `migration_path_globs` →
`migration_detected`. **R5 Sensitive config** fails when any changed file matches
`sensitive_config_globs`, OR env/key patterns appear in added lines →
`sensitive_config_changed`. These are exactly the FR-AUD-03 vetoes (no critical-file
changes; no migrations or secret/config changes) and Section 12.1's "secrets in diffs"
mitigation (R5 pattern scan escalates to human review). The glob sets come from the
Project Policy persisted in WP-3.1.

## Inputs / Prerequisites
* MT-3.4-01 — rule interface, registry slots R3/R4/R5, table-driven harness.
* MT-3.1-01 / MT-3.1-02 — `critical_path_globs`, `migration_path_globs`,
  `sensitive_config_globs` values (defaults/presets from Section 7.2).
* MT-3.2-03 — authoritative `changed_files`; MT-3.2-02 — stored patch body (added
  lines) for R5's pattern scan; Section 9.7 oversize behavior (no stored body).
* Section 9.4 design note — R3–R5 are recomputed from the stored patch.

## Scope (in)
* Register **R3**: any authoritative changed file matching any `critical_path_globs`
  glob → fail with `critical_path_changed` (Section 9.4 verbatim reason).
* Register **R4**: any changed file matching any `migration_path_globs` glob → fail
  with `migration_detected`.
* Register **R5**: two fail conditions — (a) changed file matches
  `sensitive_config_globs`; (b) env/key patterns appear in the diff's added lines.
  Failure reason `sensitive_config_changed`. Use the shared glob matcher for (a) and a
  single documented pattern set for (b), consistent with the bridge's
  Section 10.8 secret-like pattern detection (one conceptual pattern list; backend
  scans the stored patch authoritatively).
* Pure functions over the MT-3.4-01 context (added lines come from the stored patch
  already in context; no I/O).
* Table-driven tests: each rule pass (no match) and fail (glob match each of the
  three fields), R5 added-line pattern fail, combined case where R3+R4+R5 all fail
  with all three reasons listed.
* Add a WP changelog note.

## Out of scope
* Transition application — MT-3.4-07 (failures reach **T14** on the audited path or
  **T10** escalation on the coder path; guarded also by **T7/T8** pre-checks at
  submission — no transition code here).
* Persisting rule results — MT-3.4-06.
* Editing policy globs/presets — WP-3.1 (already landed).
* Bridge-side secret detection helper — Section 10.8 / WP-2.10 (advisory counterpart;
  backend scan is authoritative).

## Target paths
* `backend/apps/audit/` (R3, R4, R5 rule implementations, pattern set)
* `backend/tests/` (table-driven R3/R4/R5 cases)
* WP changelog entry

## Acceptance criteria
- [ ] **R3** fails iff a changed file matches `critical_path_globs`; reason
  `critical_path_changed` (Section 9.4 verbatim).
- [ ] **R4** fails iff a changed file matches `migration_path_globs`; reason
  `migration_detected` (Section 9.4 verbatim).
- [ ] **R5** fails iff a changed file matches `sensitive_config_globs` OR env/key
  patterns appear in added lines; reason `sensitive_config_changed`
  (Section 9.4 verbatim; Section 12.1 secrets-in-diffs mitigation).
- [ ] Glob matching uses the shared matcher against policy values from Section 7.2;
  recomputation is from the stored patch, not auditor text (Section 9.4 design note).
- [ ] Failures feed FR-AUD-04 escalation via **T14** (audited) / **T10** escalation
  (Section 8.5) — this task registers reasons only, no transition logic.
- [ ] Table-driven pass/fail cases per rule plus combined case (Section 19 WP-3.4
  acceptance).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k policy_rules_r3_r4_r5 -q` and confirm each table case:
R3/R4/R5 glob matches fail with their exact reasons, clean patch passes all three,
R5 added-line pattern triggers fail, combined case lists all reasons; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.4 — Policy Engine rules R3, R4, R5](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Project Policy glob fields](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (secrets in diffs)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Oversize patches (Section 9.7) store stats and file list only — R5 condition (b)
  (added-line pattern scan) cannot be evaluated without the body. The plan is silent;
  decide explicitly (fail-closed escalate vs. recorded as not-evaluable) and raise
  OQ-xx — do not let R5 pass vacuously on missing data.
* R5's env/key pattern list is not enumerated in the plan (Section 10.8 only says
  "secret-like patterns"); document the pattern set as data next to the rule, keep it
  aligned with the bridge helper, and treat additions as a reviewed change — an
  invented pattern that escalates innocent work is as harmful as a missed one.
