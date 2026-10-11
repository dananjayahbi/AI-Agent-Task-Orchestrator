# MT-4.7-04 — Implement the large-diff fallback ("diff too large" marker)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.7-04 |
| Title | Implement the large-diff fallback ("diff too large" marker) |
| Parent WP | WP-4.7 — Diff viewer (Milestone M4) |
| Requirements | FR-WEB-04 |
| Priority | M |
| Dependencies | MT-4.7-01 (parser's explicit no-body result); MT-4.7-02 (view pass-through); MT-4.7-03 (tree degradation); WP-3.2 complete (oversize artifact behavior) |
| Parent sections | 9.7 (5 MB cap, marker), 13.2 (Diff viewer fallback), 19 (WP-4.7), 20.3, 20.4, 20.5 |

## Context
Section 9.7 fixes the oversize contract: patches are capped (default 5 MB); "oversize
patches store stats and file list only, with a 'diff too large' marker in the
viewers." The viewers (plural) means web here and mobile in WP-5.8. Section 19
WP-4.7 lists the large-diff fallback as a slice. The marker state flows from
MT-4.7-01's explicit no-body parse result — this task renders it honestly instead of
showing an empty or misleading diff.

## Inputs / Prerequisites
* Parent plan Section 9.7 — cap, stats-and-file-list-only representation, exact
  marker phrase "diff too large".
* Parent plan Section 7.2 — `diff_summary` and `changed_files` remain available on
  the resolution even when the patch body is absent.
* MT-4.7-01 — parser output distinguishing "no body" payloads.
* MT-4.7-02/03 — view and tree pass-through points.

## Scope (in)
* Fallback rendering in the diff view when the patch payload has stats and a file list
  but no body: a clear "diff too large" marker (Section 9.7's phrase, verbatim)
  explaining that only stats and the changed-file list were stored.
* The view still shows the authoritative `diff_summary` totals and the file list
  (Section 7.2), so the reviewer is not left blind — the file tree stays usable as a
  non-jumping list (MT-4.7-03 degradation).
* Same fallback trigger for a client-side guard: if fetching/decoding the patch fails
  due to size policy rather than a catalog error, show the marker instead of a broken
  viewer — never fabricate diff content.
* Consistency with mobile: the marker wording is shared so WP-5.8's renderer
  (Section 14.2 size-capped rendering) presents the same state (out of scope to
  implement there; in scope to not diverge here).
* Component tests: stats-only payload → marker + stats + file list; normal payload →
  no marker; fetch-size failure → marker without fabricated content; empty diff
  (zero changed files) is distinguishable from "diff too large".
* A WP changelog note.

## Out of scope
* Changing the backend cap or storage behavior — WP-3.2 / Section 9.7 owns it.
* Progressive/streamed patch fetching — not in the plan; would be a plan change.
* Mobile marker implementation — WP-5.8 (MT-5.8-03) consumes the same wording.
* Parser and views — MT-4.7-01 / MT-4.7-02 (this task composes with them).

## Target paths
* `web/` (large-diff fallback state in the diff view)
* `web/` tests (fallback tests)
* WP changelog entry

## Acceptance criteria
- [ ] A stats-only/oversize payload renders the "diff too large" marker exactly as
  Section 9.7 phrases it, plus the authoritative stats and file list
  (Sections 9.7, 7.2).
- [ ] Normal patches never show the marker; a genuinely empty diff is distinguishable
  from the oversize state.
- [ ] No diff content is ever fabricated client-side when the body is absent
  (Section 9.7 authority rule; Section 20.5).
- [ ] The file tree degrades to its non-jumping list in the marker state without
  errors (MT-4.7-03 contract).
- [ ] Marker wording is implementation-neutral so WP-5.8 can reuse it
  (Section 14.2 mobile size cap).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the fallback (for example `npm test -- -t "too
large"`) and confirm: marker plus stats/list on stats-only payloads, absence on
normal payloads, empty-diff distinction, and no fabricated content; then the full web
suite stays green.

## Attachments
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.7 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The cap default (5 MB, Section 9.7) is configurable — the client cannot know the
  server's cap; trigger only on the server's representation (stats/list without
  body), never on a client-side byte threshold guess (RISK-13).
* Reviewers may be frustrated by a body-less diff — the marker must point at where
  the full context lives (resolution summary and files), but must not promise content
  the backend did not store.
* Two "viewers" (web, mobile) may drift in wording — coordinate the exact marker
  string via this task's test fixture so WP-5.8 can assert the same phrase.
