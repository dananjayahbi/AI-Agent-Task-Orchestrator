# MT-4.7-03 — Implement the file tree with jump-to-file

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.7-03 |
| Title | Implement the file tree with jump-to-file |
| Parent WP | WP-4.7 — Diff viewer (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.7-01 (parser file structures); MT-4.7-02 (view rendering); MT-4.6-03 (resolution changed_files display) |
| Parent sections | 13.2 (Diff viewer: file tree, jump to files), 9.7 (authoritative changed-file list), 7.2 (Task Resolution `changed_files`), 19 (WP-4.7), 20.3, 20.4, 20.5 |

## Context
Section 13.2 gives the diff viewer a "file tree" and "jump to files flagged by rule
results." Section 9.7 says the backend computes the authoritative changed-file list
from the stored patch — the tree must be consistent with it (the parsed patch files
are the same set, but the backend list is the contract of record, with
`changed_files` on Task Resolution as Section 7.2's field). This micro-task ships the
tree navigation itself: file list, selection, and scroll-into-view jumping;
flag-highlighting of tree entries is layered on by MT-4.7-05.

## Inputs / Prerequisites
* Parent plan Section 13.2 — file tree and jump-to-file behavior.
* Parent plan Section 9.7 / 7.2 — authoritative changed-file list and `diff_summary`.
* MT-4.7-01 — parsed per-file structures (anchors for jumping).
* MT-4.7-02 — the diff view the tree scrolls and selects within.
* Parent plan Section 13.4 — keyboard navigation expectations.

## Scope (in)
* A file tree beside the diff view listing every changed file from the patch, grouped
  by directory, with per-file status markers (new / modified / deleted / renamed as
  parsed from Section 9.7's patch headers) and per-file stat display from the
  backend's authoritative figures.
* Jump-to-file: selecting a file scrolls the diff view to that file's section (and
  vice versa — the active file updates in the tree as the diff scrolls, within
  reasonable throttling).
* Keyboard navigation: tree reachable and operable per Section 13.4 (arrow/tab
  traversal, Enter to jump).
* Consistency guard in tests: the tree's file set equals the backend's
  `changed_files` for the same resolution (Section 9.7 authority; mismatch surfaces
  as a test failure, not silent drift).
* Empty-diff and stats-only states: stats-only payloads (Section 9.7 oversize) show
  the file list without jump targets — MT-4.7-04 owns the marker; the tree degrades
  to a plain list.
* Component tests: tree render, directory grouping, jump scroll, scroll-sync,
  keyboard navigation, stats-only degradation.
* A WP changelog note.

## Out of scope
* Flag markers on tree entries — MT-4.7-05 (this task exposes the selection/anchor
  API it needs).
* Diff rendering and toggles — MT-4.7-02.
* Parsing — MT-4.7-01.
* Server-side changed-file computation — WP-3.2 / Section 9.7.

## Target paths
* `web/` (file tree component paired with the diff view)
* `web/` tests (tree, jump and keyboard tests)
* WP changelog entry

## Acceptance criteria
- [ ] The tree lists all changed files with status markers and backend-authoritative
  per-file stats (Sections 13.2, 9.7, 7.2).
- [ ] Selecting a file jumps the diff view to its section, and scroll position updates
  the active file in the tree (Section 13.2 "file tree ... jump to files").
- [ ] The tree's file set matches the resolution's authoritative `changed_files`
  (Section 9.7) — asserted in a test.
- [ ] Keyboard navigation works per Section 13.4.
- [ ] Stats-only/oversize payloads degrade to a non-jumping list without errors
  (Section 9.7; MT-4.7-04 marker rendered elsewhere).
- [ ] Only catalog error codes in error states (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the tree (for example `npm test -- -t "file
tree"`) and confirm grouping, jump/scroll-sync, keyboard traversal, changed_files
consistency, and stats-only degradation; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (Diff viewer)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Deep directory trees on large changesets can overwhelm the panel — collapse
  unexpanded directories by default (Section 13.4 responsiveness; RISK-13).
* Scroll-sync frequency affects main-thread cost on 5,000-line patches — throttle the
  active-file computation; this is a rendering concern, not a contract change.
* Renames shown as old → new paths must use the patch's rename header (Section 9.7
  parser output) — reconstructing rename detection client-side would invent data.
