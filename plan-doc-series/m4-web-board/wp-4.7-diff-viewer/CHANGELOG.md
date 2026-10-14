# WP-4.7 — Diff viewer: changelog

## Unreleased

- **MT-4.7-01 — client-side unified patch parser (done).**
  `web/lib/diff/parse.ts` is a dependency-free TypeScript parser that
  mirrors the server's semantics (`backend/apps/tasks/services/patch_parse.py`
  — note: the parser lives under `tasks/services/`, not
  `audit/services/` as the brief stated; parity was checked against
  the actual file, but the client module is written from scratch — no
  backend code is imported). It reproduces the authoritative rules:
  `diff --git` section headers win; `---`/`+++` pairs are matched
  with lookahead so a lone `---` body line is never mistaken for a
  file header (the tricky-dashes fixture locks this); binary entries
  (`GIT binary patch` / `Binary files … differ`); `/dev/null` sides
  classify added/deleted files; renamed files derive from differing
  `a/`/`b/` sides; CRLF input strips trailing `\r` per line
  (RISK-15); and `\ No newline at end of file` annotates the line it
  follows — including after the last counted body line, where both
  hunk sides are already exhausted (git emits this; the marker check
  therefore runs before the in-hunk count gate so it never leaks into
  the opaque-prose branch). Regions no rule understands (combined
  diffs, submodule headers, index/mode lines) degrade to opaque text
  — never a crash and never an empty-diff masquerade.
  `interpretPatchPayload` is the explicit Section 9.7 interpreter: a
  string body parses; `diff_too_large` or a missing/non-string body
  yields `no-body` with the server's marker (`DIFF_TOO_LARGE_MARKER`
  = "diff too large" as constant fallback — the phrase is shared with
  WP-5.8's mobile card through this one export); an empty-string body
  is a legitimate zero-file diff, distinguishable from `no-body`.
  Per the Section 9.7 authority rule the parser produces **structure
  only — never any statistics keys** (the test suite scans every
  fixture's output for `insertions`/`deletions`/`stats`/`+`/`-`-style
  keys and finds none; all figures come from the backend row).
  Tests: `web/tests/diff/patch-parser.test.ts` (13, including a
  5,000-line fixture parsed well inside a 2s budget).
- **MT-4.7-02 — unified/split diff view (done; Wave 9 exit — a
  5,000-line patch renders responsively).**
  `web/components/diff/diff-view.tsx` renders the parsed patch through
  the board's windowing primitive (`VirtualList`, MT-4.3-06): the DOM
  stays bounded by the viewport, not the patch size — that reuse, not
  a streaming design the plan never asked for, is what makes the
  Section 13.4/19 responsiveness exit hold (test asserts a bounded
  DOM row count for a 5,000-line patch and that the full row set
  feeds the window). Rows are uniform height (`DIFF_ROW_HEIGHT = 24`)
  so one fixed-height window covers file headers, hunk headers and
  lines alike. The unified/split toggle follows Section 13.2;
  **recorded choice (MT risk note):** the preference persists via
  `localStorage` (`diff-viewer:mode`) — a view preference with no
  backend field to store it against. Files whose body exceeds
  `LARGE_FILE_LINES = 200` start collapsed to a header with an expand
  affordance (Section 13.2 "collapse large files"; MT risk note: the
  threshold is a client display rule, not a contract). Syntax
  highlighting is a small dependency-free tokenizer
  (`web/lib/diff/highlight.ts`) with an extension → grammar table
  (js/ts/tsx, py, sh, yaml/json); unknown extensions fall back to
  plain monospace. **Stats discipline (Section 9.7/20.5):** the header
  shows the backend's authoritative `diff_summary` read defensively
  and labeled "backend-computed"; per-file headers show identity,
  status and flags — per-file +/- counts are deliberately not shown
  because the backend publishes only resolution-scoped figures and
  client-recomputing them would be a second, divergent contract
  (reading recorded per the authority rule).
  Tests: `web/tests/diff/diff-view.test.tsx` (10).
- **MT-4.7-03 — file tree + jump-to-file (done).**
  `web/lib/diff/file-tree.ts` builds tree entries from the Section
  7.2 `changed_files` field as the contract of record, joined with
  the parsed patch for status/rename detail; a changed file missing
  from the parse degrades to "unknown" status without error (the
  consistency guard test locks set equality). `FileTree` groups by
  directory, renders status markers from the patch's own headers
  (never reconstructed), and supports Section 13.4 keyboard
  navigation (roving tabindex; arrows/Home/End). Jump-to-file wires
  the tree to the view: selecting a file expands it if collapsed and
  scrolls the virtualized list to its header; scrolling back syncs
  the tree's active marker through `VirtualList`'s new
  `onVisibleRangeChange` (throttled to window-boundary changes, never
  per-pixel) and `ref.scrollToIndex` — both backward-compatible
  extensions to the shared board primitive (board usage unchanged;
  its tests stay green). The jump expands by pure derivation from the
  current jump request (no setState-in-effect); a manual collapse of
  the jumped file clears the request and the user's choice wins.
  Tests: `web/tests/diff/file-tree.test.tsx` (13).
- **MT-4.7-04 — large-diff fallback (done).**
  The Section 9.7 5 MB cap is enforced **server-side**; the client's
  job is to render the degradation faithfully.
  `web/components/diff/diff-too-large.tsx` shows the verbatim
  "diff too large" marker (the server's `marker` field when present,
  the shared constant as fallback), the backend's authoritative stats
  and an explanation — no empty diff, no fabricated content, and the
  changed-file list stays visible as a plain non-jumping list. An
  empty parsed diff (zero files) renders a distinct "No changes in
  this patch" state; a non-string body after a decode anomaly takes
  the marker path, never a broken viewer; fetch errors map to
  catalog-only copy (Section 20.4 item 5) and never masquerade as
  the oversize state. Tests: `web/tests/diff/diff-fallback.test.tsx`
  (9).
- **MT-4.7-05 — rule-flag markers (done; Wave 9 exit — flagged files
  are marked and jumpable).**
  `web/lib/diff/rules.ts` lists the Section 9.4 file-based rules
  (R2–R5); `web/lib/diff/rule-flags.ts` extracts flagged files from
  the paired audit report's `policy_rule_results`, tolerant of unknown
  shapes. **Recorded reading / OQ (MT risk note applied):** the
  backend's persisted rows are currently
  `{rule, passed, review_reason}` with **no file payload**, so the
  extractor reads an optional `files: string[]` per row when present
  and otherwise yields no markers — it never guesses and never
  re-evaluates rules client-side. End-to-end flagged files therefore
  depend on the backend attaching file lists to those rows (open
  question for the backend agent; the client is forward-compatible
  and all AC cases — multiple rules per file, passing rules never
  flagging, non-file rules R1/R6–R9 never flagging, absent report →
  no markers, no crash — are covered through the extractor). Flagged
  files get markers in both the tree (with rule ids) and the diff
  view, remain jumpable, and markers survive the oversize fallback
  state. Tests: rule cases in `web/tests/diff/file-tree.test.tsx`
  (5) plus flag rendering in the diff view test.
- Composition: `web/components/diff/diff-panel.tsx` is the hosted
  entry point (fetch through the generated client per NFR-11 →
  explicit Section 9.7 interpretation → tree + view + flags
  composition), mounted per resolution by the task detail's
  resolutions section behind a "View diff" toggle (mount-on-open —
  the patch fetches only when asked). `web/lib/queries/resolution-patch.ts`
  owns the cache entry (`staleTime` 60s — immutable artifacts).
  Total: 53 new tests (287 in the web suite); lint, typecheck,
  format:check, test and build all green.
