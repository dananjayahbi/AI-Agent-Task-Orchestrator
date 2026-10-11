# MT-4.7-01 — Implement the unified patch parser for the viewer

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.7-01 |
| Title | Implement the unified patch parser for the viewer |
| Parent WP | WP-4.7 — Diff viewer (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.6-01 to MT-4.6-04 (task detail shell); WP-3.2 complete (patch artifacts uploaded and stored) |
| Parent sections | 9.7 (Patch artifacts), 9.2 (`GET /resolutions/{id}/patch`), 7.2 (Task Artifact), 13.2 (Diff viewer), 19 (WP-4.7), 20.3, 20.4, 20.5 |

## Context
Section 9.7 fixes the artifact contract: at submission the bridge uploads a unified
patch (branch vs. default branch merge-base); the backend stores it and computes the
authoritative stats and changed-file list used by the Policy Engine; the patch is
fetched via `GET /resolutions/{id}/patch` (Section 9.2) and lives as a Task Artifact
of kind `patch` (Section 7.2), with a 5 MB default size cap after which only stats and
the file list are stored. This micro-task builds the viewer-side parser that turns the
unified patch text into per-file, per-hunk structures — the data layer for
MT-4.7-02 (views), MT-4.7-03 (tree) and MT-4.7-04 (fallback). Parsing is for
rendering only: it must never re-derive the stats or changed files the backend
authored (Section 9.7).

## Inputs / Prerequisites
* Parent plan Section 9.7 — artifact shape, stats authority, 5 MB cap and the
  "diff too large" marker contract.
* Parent plan Section 9.2 — `GET /resolutions/{id}/patch`.
* Parent plan Section 7.2 — Task Resolution `diff_summary` / `changed_files` (already
  computed server-side) and Task Artifact `kind` = `patch`.
* Parent plan Section 13.2 — what the Diff viewer component needs (tree, toggles,
  collapse, flags) — downstream consumers of this parser.
* WP-3.2 — implemented patch storage and stats computation.

## Scope (in)
* A pure parser module consuming the unified patch text and producing a structure of
  files → hunks → lines (context/added/removed), including file headers, rename/new/
  delete file markers, and hunk ranges.
* Handling of the oversize representation: when the backend returns only stats and a
  file list (no patch body, Section 9.7), the parser represents this explicitly so
  MT-4.7-04 can render the "diff too large" marker — never a crash or empty diff
  masquerade.
* Robustness against real-world patch quirks: `\ No newline at end of file`, empty
  diffs (no changed files), binary file entries, CRLF content (RISK-15).
* No stats re-derivation: any figures shown come from the backend's `diff_summary`
  (Section 9.7) — the parser exposes structure only; this is asserted in tests.
* Parser unit tests against fixture patches: single-file, multi-file, rename, new
  file, delete, binary, no-newline marker, empty patch, oversize/stats-only payload.
* A WP changelog note.

## Out of scope
* Rendering (unified/split, highlighting, collapsing) — MT-4.7-02.
* File tree UI — MT-4.7-03.
* Large-diff fallback UI — MT-4.7-04.
* Rule-flag markers — MT-4.7-05.
* Backend patch parsing for stats (the authoritative one) — WP-3.2; this parser is
  deliberately separate and non-authoritative.
* Fetching logic/caching — belongs to the views (Section 13.3).

## Target paths
* `web/` (patch parser module for the diff viewer)
* `web/` tests (parser fixture tests)
* WP changelog entry

## Acceptance criteria
- [ ] The parser converts a unified patch into files/hunks/lines structures covering
  add, remove, context, hunk headers, and new/delete/rename/binary file cases.
- [ ] Stats-only payloads (Section 9.7 oversize representation) parse to an explicit
  "no body" result that MT-4.7-04 can turn into the "diff too large" marker.
- [ ] The parser reports no statistics of its own — displayed stats remain the
  backend's authoritative `diff_summary` (Section 9.7; Section 20.5: no re-derived
  contract).
- [ ] Empty patches and `\ No newline at end of file` markers are handled without
  errors; CRLF content parses correctly (RISK-15).
- [ ] Parsing 5,000-line patches completes fast enough for the WP acceptance
  (Section 19 WP-4.7: 5,000-line patch renders responsively — parser budget is part
  of it).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the parser (for example `npm test -- -t patch`) and
confirm all fixture cases parse to the expected structures, stats-only payloads yield
the explicit no-body result, and a 5,000-line fixture parses within the test's timing
budget; then the full web suite stays green.

## Attachments
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.2 — Key components (Diff viewer)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* There are two patch parsers in the system (backend authoritative, Section 9.7 /
  WP-3.2, and this viewer-side one) — they may drift; keep fixtures derived from the
  same sample artifacts and note the duplication as a maintenance cost, not a reason
  to let the client compute stats (that would violate Section 9.7's authority rule).
* Parser timing on very large patches contributes to RISK-13 — if 5,000 lines parse
  too slowly, chunk the parse rather than changing the contract; the 5 MB cap
  (Section 9.7) bounds the worst case.
* Unified-diff edge cases (combined diffs, submodules) are not specified — treat
  unparseable regions as opaque text blocks instead of failing the whole render.
