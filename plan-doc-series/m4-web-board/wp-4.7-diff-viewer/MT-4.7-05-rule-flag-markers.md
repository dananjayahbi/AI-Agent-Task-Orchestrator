# MT-4.7-05 — Implement rule-flag markers on files flagged by policy results

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.7-05 |
| Title | Implement rule-flag markers on files flagged by policy results |
| Parent WP | WP-4.7 — Diff viewer (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.7-01 to MT-4.7-03 (parser, views, tree); WP-3.4 complete (`policy_rule_results` persistence); WP-4.6 complete (audit reports in detail) |
| Parent sections | 13.2 (Diff viewer: jump to files flagged by rule results), 9.4 (rule results persisted for reviewers), 7.2 (Audit Report `policy_rule_results`), 19 (WP-4.7 acceptance), 20.4, 20.5 |

## Context
Section 9.4's design note is explicit: "The result (every rule and its outcome) is
persisted so the human reviewer sees exactly why the task was escalated," and the
engine recomputes R2–R6 from the stored patch — rules R2 (scope), R3 (critical
paths), R4 (migrations) and R5 (sensitive config) are file-based: their fail
conditions are expressed as changed files matching globs (Section 9.4). Section 13.2
says the diff viewer supports "jump to files flagged by rule results," and Section 19
WP-4.7 acceptance requires "flagged files visibly marked." This task connects the
persisted `policy_rule_results` (Audit Report, Section 7.2) to markers in the tree
and the diff.

## Inputs / Prerequisites
* Parent plan Section 9.4 — rules R1–R9, file-based fail conditions for R2–R5,
  persisted per-rule results, engine versioning.
* Parent plan Section 7.2 — Audit Report `policy_rule_results` (JSON listing every
  rule and pass/fail) fetched via `GET /tasks/{id}/audit-reports` (Section 9.2).
* Parent plan Section 13.2 — "jump to files flagged by rule results" and the review
  panel's rule table (WP-4.8 renders the table; this task renders file markers).
* MT-4.7-03 — tree selection/jump API the markers ride on.
* MT-4.7-02 — the diff view that shows flagged lines/files.

## Scope (in)
* Extraction of flagged files from the audit report's `policy_rule_results` for the
  file-based rules (R2, R3, R4, R5) — mapping rule results to file paths exactly as
  the backend persisted them; no client-side glob re-evaluation (Section 9.4: the
  engine is authoritative).
* Visible markers: a distinct per-file badge in the file tree and a corresponding
  visual marker on the file's section in the diff view, naming the flagging rule id
  (R2/R3/R4/R5) so the reviewer sees why (Section 13.2 jump-to-flagged behavior:
  selecting a flagged file uses MT-4.7-03's jump).
* State handling: no audit report yet (pre-audit, Section 8.5) or no failing
  file-based rules → no markers, viewer otherwise unchanged; rules with no file
  payload (R1, R6–R9) never produce file markers — they belong to the review panel's
  rule table (WP-4.8).
* Consistency with stats-only payloads: flags still mark tree entries even when
  MT-4.7-04's marker hides the diff body.
* Component tests: fixture `policy_rule_results` with R2/R4 failures → correct files
  marked with correct rule ids; passing results → no markers; R7-style non-file rule
  ignored for markers; tree marker → jump works; stats-only + flags combination.
* A WP changelog note.

## Out of scope
* Rule evaluation itself — WP-3.4 (Section 9.4 engine).
* The review panel's rule table and reason display — WP-4.8 (MT-4.8-02).
* Mobile flag markers — WP-5.8 (MT-5.8-02/03 surface rule results there).
* Changing how results are persisted — WP-3.4.

## Target paths
* `web/` (flag extraction + tree/diff markers)
* `web/` tests (marker tests with fixture rule results)
* WP changelog entry

## Acceptance criteria
- [ ] Files flagged by file-based rules (R2, R3, R4, R5 from Section 9.4) are visibly
  marked in the file tree and the diff view — Section 19 WP-4.7 acceptance "flagged
  files visibly marked".
- [ ] Each marker names its flagging rule id exactly as persisted in
  `policy_rule_results` (Section 7.2) — no client-side rule re-evaluation or glob
  re-matching (Section 9.4 authority note; Section 20.5).
- [ ] "Jump to files flagged by rule results" works through MT-4.7-03's tree API
  (Section 13.2).
- [ ] Non-file rules (R1, R6–R9) and absent audit reports produce no markers and no
  errors (Sections 9.4, 8.5).
- [ ] Markers remain visible in the stats-only fallback state (Section 9.7
  composition with MT-4.7-04).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to rule flags (for example `npm test -- -t "rule
flag"`) and confirm: correct files marked for fixture R2/R4 failures with verbatim
rule ids, jump-to-flagged, no markers for non-file rules or missing reports, and
stats-only composition; then the full web suite stays green.

## Attachments
* [Section 9.4 — Policy Engine (persisted rule results)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Key components (Diff viewer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* `policy_rule_results` is a JSON blob whose exact file-list shape is fixed by
  WP-3.4's persistence (Section 9.4) — read the fields WP-3.4 actually writes and
  treat unknown shapes as "no markers" rather than guessing (Section 20.5).
* Multiple rules may flag the same file — design the marker to show all rule ids, not
  only the first; the reviewer needs the full "why" (Section 9.4's stated purpose).
* Marker colors/legend must not be the only signal (accessibility, Section 13.4
  keyboard/a11y expectations) — pair color with the rule-id text label.
