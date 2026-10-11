# MT-4.7-02 — Implement unified and split diff views with syntax highlighting

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.7-02 |
| Title | Implement unified and split diff views with syntax highlighting |
| Parent WP | WP-4.7 — Diff viewer (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.7-01 (parser); MT-4.6-01 (detail shell hosting the viewer) |
| Parent sections | 13.2 (Diff viewer bullet), 13.4 (responsiveness), 9.7 (patch contract), 19 (WP-4.7), 20.3, 20.4, 20.5 |

## Context
Section 13.2's Diff viewer bullet specifies "unified/split toggle, syntax
highlighting, collapse large files" alongside the tree and fallback. Section 19
WP-4.7 acceptance is a performance contract: "5,000-line patch renders
responsively; flagged files visibly marked." This micro-task delivers the two render
modes and highlighting on top of MT-4.7-01's parser output, hosted in the task
detail's resolution/diff region (and reused by the review panel, WP-4.8).

## Inputs / Prerequisites
* Parent plan Section 13.2 — unified/split toggle, syntax highlighting, collapsing
  large files.
* Parent plan Section 9.7 — the patch content and the backend's authoritative stats
  (header figures shown in the view come from `diff_summary`).
* MT-4.7-01 — parsed files/hunks/lines structures.
* Parent plan Section 13.4 — responsiveness target the render must meet.
* WP-4.3 conventions — component/state patterns and canonical error mapping
  (Section 13.3).

## Scope (in)
* The diff view component: renders the parsed patch in **unified** mode (default) and
  **split** mode with a persistent toggle, per Section 13.2.
* Syntax highlighting by file extension for changed lines and context (file-extension
  mapping; unknown extensions fall back to plain monospace — no errors).
* Collapsing of large files: sections/regions of big files collapse with an expand
  affordance so a 5,000-line patch renders responsively (Section 19 WP-4.7
  acceptance; Section 13.4).
* Header per file showing the backend's authoritative stats (insertions/deletions
  from `diff_summary`, Section 9.7) — never client-recomputed totals.
* Interaction states: loading, error (catalog codes only, Section 20.4 item 5),
  no-body result from the parser is passed through untouched (MT-4.7-04 renders it).
* Component tests: unified/split rendering fixture, toggle persistence, highlighting
  applied for known extension and plain fallback for unknown, large-file collapse,
  5,000-line fixture render timing.
* A WP changelog note.

## Out of scope
* The parser — MT-4.7-01.
* File tree and jump-to-file — MT-4.7-03.
* "Diff too large" fallback rendering — MT-4.7-04 (view only passes the state
  through).
* Rule-flag markers/highlighting of flagged files — MT-4.7-05.
* Review panel integration/layout — WP-4.8 (consumes this component).
* Mobile diff renderer — WP-5.8 (MT-5.8-03, Section 14.2 rules).

## Target paths
* `web/` (diff view component with unified/split modes)
* `web/` tests (view tests with parsed fixtures)
* WP changelog entry

## Acceptance criteria
- [ ] Unified and split views both render correctly from parsed fixtures with a
  working toggle (Section 13.2).
- [ ] Syntax highlighting applies by file extension with a safe plain-text fallback
  for unknown types (Section 13.2).
- [ ] Large files collapse/expand so a 5,000-line patch renders responsively
  (Section 19 WP-4.7 acceptance; Section 13.4).
- [ ] Per-file header stats are the backend's `diff_summary` values — no client-side
  recomputation (Section 9.7; Section 20.5).
- [ ] Loading and error states handled; only catalog error codes (Sections 20.3,
  20.4 item 5).
- [ ] The no-body (oversize) state passes through to MT-4.7-04's marker without
  rendering an empty diff.
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to diff views (for example `npm test -- -t diff`) and
confirm: unified and split fixtures, toggle persistence, highlighting/fallback,
large-file collapse, and the 5,000-line responsiveness assertion; then the full web
suite stays green.

## Attachments
* [Section 13.2 — Key components (Diff viewer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.7 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Full syntax highlighting of every line in a 5,000-line patch can jank the main
  thread (RISK-13) — highlight lazily per visible file/region if needed; the plan
  mandates responsiveness, not a particular library.
* Highlight grammars for exotic languages are out of scope — plain fallback must be
  the default for unmapped extensions (no invented mapping tables).
* Split mode with very long lines needs horizontal scroll behavior consistent with
  Section 13.4 keyboard navigation; do not break keyboard users when adding scroll
  containers.
