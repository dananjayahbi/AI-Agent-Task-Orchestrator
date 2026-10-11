# MT-3.2-03 — Implement authoritative patch parsing for stats and changed-file list

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.2-03 |
| Title | Implement authoritative patch parsing for stats and changed-file list |
| Parent WP | WP-3.2 — Submission handling and artifacts (Milestone M3) |
| Requirements | FR-AUD-01, FR-TSK-03 |
| Priority | M |
| Dependencies | MT-3.2-02 (patch stored); MT-3.2-01 (resolution fields to populate) |
| Parent sections | 9.7 (authoritative stats and file list), 9.4 (engine recomputes from stored patch), 7.2 (diff_summary, changed_files), 19 (WP-3.2), 20.4, 20.5 |

## Context
Section 9.7 states that the backend computes authoritative stats and the changed-file
list from the stored patch and uses these for the Policy Engine — not claims made in
agent or auditor text. Section 7.2 puts `diff_summary` (files, insertions, deletions)
and `changed_files` on the Task Resolution. Section 9.4's design notes harden this: the
engine recomputes R2–R6 from the patch stored by the bridge. This micro-task implements
that single authoritative derivation, feeding the scope check (MT-3.2-04), rule R6
(diff size), and the diff viewers.

## Inputs / Prerequisites
* MT-3.2-02 — the stored unified patch (or the oversize marker path from Section 9.7).
* MT-3.2-01 — Task Resolution `diff_summary` and `changed_files` fields to fill.
* Parent plan Section 9.7 — "computes authoritative stats and the changed-file list
  from it".
* Parent plan Section 9.4 — rules R2–R6 consume these derived values (pointer only;
  rule logic is WP-3.4).

## Scope (in)
* A pure parser over the stored unified diff that derives:
  * `changed_files` — the set of repo-relative paths touched (one entry per changed
    file), and
  * `diff_summary` — `{files, insertions, deletions}` counters computed from hunk
    headers/lines.
* Wiring: on artifact store (MT-3.2-02), parse and persist both fields on the
  resolution, replacing any bridge-supplied provisional values so exactly one
  authoritative source exists.
* Deterministic behavior: parsing the same stored patch twice yields identical output
  (ADR-009 determinism discipline; no clock, no I/O beyond the stored bytes).
* Oversize artifacts (Section 9.7, no stored body): stats and file list still recorded
  from whatever Section 9.7 preserves — if the plan's degraded path leaves stats
  unavailable, record that explicitly rather than fabricating numbers (coordinate with
  MT-3.2-02).
* Unit tests: representative unified diffs (multi-file, additions-only,
  deletions-only, renames, binary files) against hand-computed expectations.
* Add a WP changelog note.

## Out of scope
* Scope comparison against `target_scope` — MT-3.2-04 (consumes `changed_files`).
* Any rule evaluation (R1–R9) — WP-3.4.
* Bridge-side patch capture and its own stats — WP-2.6 (MT-2.6-03); backend values are
  authoritative regardless.
* Rendering stats in web/mobile viewers — WP-4.7 / WP-5.8.

## Target paths
* `backend/apps/tasks/` (patch parsing module, resolution stats wiring)
* `backend/tests/` (parser unit tests)
* WP changelog entry

## Acceptance criteria
- [ ] `diff_summary` and `changed_files` on the resolution are computed from the stored
  patch server-side, per Section 9.7 — bridge/auditor claims never override them
  (Section 9.4 design note; Section 20.5 traceability).
- [ ] Parsing is pure and deterministic: same patch bytes → same stats and file list
  (ADR-009).
- [ ] `changed_files` covers every file in the diff exactly once with repo-relative
  paths; `diff_summary.files` equals the changed-file count and insertion/deletion
  totals match hunk content (feeds R2/R6 inputs).
- [ ] Oversize artifacts follow the Section 9.7 degraded path without invented numbers.
- [ ] No public-contract change beyond resolution fields already declared in
  Section 7.2 (Section 20.4 item 4).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k patch_parsing -q` and confirm parser fixtures: multi-file
diff stats, changed-file list equality with diff headers, determinism across repeated
runs, and the oversize/degraded input; then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.7 — Patch artifacts (authoritative stats)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine design notes](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Task Resolution diff_summary and changed_files](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Unified-diff edge cases (renames with similarity, binary files, mode-only changes)
  are not specified in the plan — document the chosen parsing behavior next to the
  fixtures; if a case would change escalation outcomes (e.g. rename counting), raise
  OQ-xx instead of guessing silently.
* Bridge also computes stats locally (Section 10.8 helper); the plan is explicit that
  the backend's parse is authoritative (Section 9.7) — never merge or average the two.
