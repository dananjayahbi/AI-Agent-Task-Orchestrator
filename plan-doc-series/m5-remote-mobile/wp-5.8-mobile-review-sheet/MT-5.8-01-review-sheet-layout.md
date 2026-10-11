# MT-5.8-01 — Implement the review sheet layout

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-01 |
| Title | Implement the review sheet layout |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.7-01 (task detail screen/navigation); WP-3.6 complete (review endpoint); WP-5.6 complete (needs-review entry points) |
| Parent sections | 14.1 (Review sheet row), 14.2 (offline behavior, biometric gate context), 11.5 (human review workflow), 8.4 (reasons), 19 (WP-5.8), 20.3, 20.4, 20.5 |

## Context
Section 14.1's Review sheet row fixes the layout: "Reason and rule results, execution
summary, auditor notes, syntax-highlighted diff, three actions." Section 19 WP-5.8
slices it as sheet layout first, then rule results (MT-5.8-02), diff renderer
(MT-5.8-03), and the three action flows (MT-5.8-04…06). Section 14.2 adds the
session constraints the sheet lives under: the app token is biometric-gated, offline
shows a clear state with **no queued approvals** ("to avoid stale decisions"), and
mutations require connectivity. The sheet is the mobile counterpart of WP-4.8's panel
with `decided_via` `mobile` (Section 7.2).

## Inputs / Prerequisites
* Parent plan Section 14.1 — exact sheet contents and the three actions.
* Parent plan Section 14.2 — biometric-gated session, offline rules, approve-safety
  (consumed by MT-5.8-04), voice note (MT-5.8-05).
* Parent plan Section 11.5 / 8.4 — workflow semantics and canonical reasons the
  sheet displays.
* Parent plan Section 9.2 — task, audit-report, resolutions endpoints behind the
  sheet; `POST /tasks/{id}/review` for actions.
* MT-5.7-01 — navigation host; MT-4.8-02 (web) — content parity reference.

## Scope (in)
* The review sheet UI (full-height sheet/screen) presenting, in Section 14.1 order:
  escalation reason(s), rule-results region (owned detailed by MT-5.8-02), execution
  summary, auditor notes, diff region (owned by MT-5.8-03), and a fixed actions bar
  with the three actions (approve and merge, request changes, reassign — wired by
  MT-5.8-04/05/06).
* Presentation of the canonical `review_reason` values (Section 8.4) with friendly
  labels — canonical strings retained (ADR-010; Section 20.5).
* Data load through the generated API client (Section 14.3): task detail, audit
  reports, resolutions (Section 9.2); loading, empty, error and **offline** states
  with actions disabled offline per Section 14.2 (no queued mutations).
* Entry points: from board "needs review" affordances/notifications shell (deep-link
  routing itself is WP-5.9) with the biometric-gated session already established
  (Section 14.2 — gate is app-level, not per-sheet).
* Accessibility/ergonomics: actions reachable on small screens, safe-area handling,
  theming; widget tests per Section 14.3 for layout, states, and action-bar wiring
  placeholders.
* A WP changelog note.

## Out of scope
* Rule-results/evidence internals — MT-5.8-02.
* Diff rendering — MT-5.8-03.
* The three action behaviors — MT-5.8-04/05/06.
* Push deep links and biometric-gated entry — WP-5.9 / WP-5.3.
* Web review panel — WP-4.8.

## Target paths
* `mobile/` (review sheet screen/layout and state)
* `mobile/` tests (widget tests for layout and states)
* WP changelog entry

## Acceptance criteria
- [ ] The sheet renders all Section 14.1 elements: reason and rule-results region,
  execution summary, auditor notes, diff region, and the three actions in an
  accessible action bar.
- [ ] Reasons display canonical Section 8.4 values with friendly labels — no invented
  reasons (Sections 8.4, 20.5).
- [ ] Data loads via the generated API client with loading/empty/error/offline
  states; offline disables mutations with the Section 14.2 clear offline state and
  **no queued approvals**.
- [ ] The sheet is reachable from the board/notification shells by task id —
  contract stable for WP-5.9 deep links (Section 14.1).
- [ ] Layout survives small screens (actions always reachable) and follows
  Section 14.3's single state-management pattern.
- [ ] Widget tests green; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to the review sheet (for example
`flutter test --dart-define=test_filter=review_sheet` or the project's equivalent)
and confirm layout regions, reason labels, loading/empty/error/offline states, and
action-bar presence with mutations disabled offline; then the full mobile suite
stays green.

## Attachments
* [Section 14.1 — Navigation and screens (Review sheet row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.2 — Mobile-specific behaviors](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.8 slices and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Sheet-vs-screen and gesture dismiss are unspecified — a dismiss attempt with
  unsaved dictated text (MT-5.8-05) must confirm first; record the interaction
  decision in the changelog (Section 20.1 item 5).
* Content parity with the web panel (Section 13.2) is the reference, but mobile
  v1 may omit widgets (e.g. attachments) — note any intentional omission rather
  than silently diverging from Section 11.5's reviewer needs.
* The sheet depends on audit data that may be absent (Section 8.5 coder-evidence
  path) — the layout must degrade to reason + summary without collapsing (same
  discipline as MT-4.8-02).
