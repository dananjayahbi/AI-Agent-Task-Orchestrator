# MT-5.8-03 — Implement the lazy per-file diff renderer with highlighting

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-03 |
| Title | Implement the lazy per-file diff renderer with highlighting |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.8-01 (sheet diff region); WP-3.2 complete (patch artifacts); WP-4.7 conventions ("diff too large" marker wording) |
| Parent sections | 14.2 (Diff rendering), 9.7 (patch artifacts and marker), 9.2 (`GET /resolutions/{id}/patch`), 7.2 (changed_files, diff_summary), 19 (WP-5.8), 20.3, 20.4, 20.5 |

## Context
Section 14.2 fixes mobile diff rendering: "lazy-loaded per file, size-capped,
monospace with horizontal scroll, syntax highlighting by file extension." FR-MOB-05
requires a "syntax-highlighted diff" in the review sheet. The source is the stored
unified patch from `GET /resolutions/{id}/patch` (Section 9.2), capped at 5 MB with
oversize payloads storing stats and file list only plus a "diff too large" marker
"in the viewers" (Section 9.7 — the marker phrase is shared with web MT-4.7-04).
Authoritative stats come from the backend `diff_summary` / `changed_files`
(Sections 9.7, 7.2) — the mobile renderer never recomputes them.

## Inputs / Prerequisites
* Parent plan Section 14.2 — the four rendering rules (lazy per file, size-capped,
  monospace + horizontal scroll, highlighting by extension).
* Parent plan Section 9.7 — patch contract, cap, marker.
* Parent plan Section 9.2 — patch endpoint; Section 7.2 — `changed_files`,
  `diff_summary`, Task Artifact `kind` = `patch`.
* Web MT-4.7-01/04 — parse/fallback conventions to stay consistent with (marker
  wording, stats-only representation).

## Scope (in)
* A diff renderer for the sheet's diff region: fetch the patch once, parse into
  per-file sections (consistent with the web parser's semantics — same marker and
  stats-only representation), and render **lazily per file** as the user scrolls
  (only visible/near-visible files built — Section 14.2).
* Size-capped rendering: honor the server's stats-only representation by showing the
  shared "diff too large" marker (Section 9.7, exact phrase) with authoritative
  stats and the file list; plus a client guard so a pathological file never builds
  unbounded widgets (cap per file, collapse remainder behind "show more" — Section
  14.2 "size-capped").
* Monospace rendering with horizontal scroll per file (no page-level horizontal
  scroll), add/remove/context visual styling, and syntax highlighting by file
  extension with plain fallback for unknown extensions (Section 14.2).
* Header per file with backend-authoritative stats (Section 9.7) and file navigation
  (next/previous file) for large changesets.
* States: loading, parse failure → marker/summary-only fallback (never fabricate
  content, Section 9.7), empty diff distinct from oversize.
* Widget/perf tests: multi-file fixture lazily builds only visible files, marker on
  stats-only payload, per-file cap enforced, highlighting applied for known
  extension with fallback, horizontal scroll containment, 5,000-line fixture
  performance sanity (Section 19 WP-4.7's bar applied to mobile as guidance).
* A WP changelog note.

## Out of scope
* Web diff viewer — WP-4.7.
* Rule flags on files — surfaced via MT-5.8-02's rule table; file-level flag markers
  on mobile are not a Section 14.2 requirement (do not invent).
* Backend patch storage/cap — WP-3.2 / Section 9.7.
* Approve confirmation contents — MT-5.8-04 (consumes diff stats from the backend).

## Target paths
* `mobile/` (diff renderer widget in the review sheet)
* `mobile/` tests (renderer widget/perf tests)
* WP changelog entry

## Acceptance criteria
- [ ] Diffs render per Section 14.2: lazy per file, size-capped, monospace with
  horizontal scroll, syntax highlighting by extension (plain fallback for unknown).
- [ ] Stats-only/oversize payloads show the Section 9.7 "diff too large" marker with
  authoritative stats and file list — same phrase as web (Section 9.7; Section 20.5).
- [ ] Per-file stats are the backend's `diff_summary`/`changed_files` — no
  client-side recomputation (Section 9.7 authority).
- [ ] A pathological file cannot break rendering: per-file cap with expand
  (Section 14.2 size cap; RISK-13 discipline).
- [ ] Loading, parse-failure and empty states handled without fabricated content
  (Sections 20.3, 9.7); catalog-only error codes (Section 20.4 item 5).
- [ ] Widget/perf tests green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to the diff renderer (for example
`flutter test --dart-define=test_filter=diff` or the project's equivalent) and
confirm lazy building, marker on stats-only payloads, per-file caps, highlighting
fallback, and scroll containment; then the full mobile suite stays green.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (Diff rendering)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.8 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Mobile highlighting grammars are heavier than web — keep the extension map minimal
  and rely on plain fallback; adding grammars is a dependency decision to record,
  not an implicit scope expansion (RISK-13/09 discipline).
* Two renderers (web/mobile) parsing the same patch can drift — keep fixture patches
  shared across suites so both agree on the "diff too large" case (Section 9.7's
  "viewers" plural).
* Very long lines plus monospace can overflow indicators — per-file horizontal
  scroll only; if a single line exceeds the cap, truncate with visual continuation
  rather than expanding widgets unboundedly (record the truncation threshold).
