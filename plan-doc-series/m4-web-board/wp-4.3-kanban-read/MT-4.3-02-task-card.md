# MT-4.3-02 — Implement the task card component (id, priority, worker, progress)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.3-02 |
| Title | Implement the task card component (id, priority, worker, progress) |
| Parent WP | WP-4.3 — Kanban board (read) with realtime (Milestone M4) |
| Requirements | FR-WEB-01, FR-WEB-05 |
| Priority | M |
| Dependencies | MT-4.3-01 (board columns host the cards); WP-4.1 complete (theming MT-4.1-04) |
| Parent sections | 13.2 (card contents), 8.6 (stalled indicator), 7.2 (Task fields), 19 (WP-4.3), 20.3, 20.4, 20.5 |

## Context
Section 13.2 fixes what a board card shows: "id, title, priority chip, worker badge
with lease countdown, percent bar, attachment count, and a stalled/escalation
marker." Section 7.2 supplies the fields (priority enum `urgent`/`high`/`medium`/
`low`, `worker_agent_id`, lease timestamps, checkpoint percent, `archived_at`,
`review_reason`), and Section 8.6 defines "stalled" precisely: no `progress`
checkpoint within `stalled_after_minutes` while the lease is still valid — a
UI-only indicator. This micro-task is the presentational card each column renders.

## Inputs / Prerequisites
* MT-4.3-01 — the column component that maps tasks to cards.
* Parent plan Section 13.2 — exact card content list.
* Parent plan Section 7.2 — Task fields backing each element.
* Parent plan Section 8.6 — stalled definition (`stalled_after_minutes` from Project
  Policy, default 20) and lease fields for the countdown.
* WP-4.1 theming (MT-4.1-04) — priority chips and status markers use theme tokens.

## Scope (in)
* A `TaskCard` component rendering exactly the Section 13.2 list: task id, title,
  priority chip, worker badge with live lease countdown, percent bar (from latest
  checkpoint percent when present), attachment count, and a stalled/escalation
  marker.
* Lease countdown derived from `lease_expires_at` (ticking client-side; display-only).
* Stalled marker computed per Section 8.6 (no progress checkpoint within
  `stalled_after_minutes` while lease valid); escalation marker shown for
  `in_human_review` (review reason surfaced accessibly via title/aria — full reason
  panel is WP-4.8).
* Priority chip per the four Section 7.2 values with theme-consistent styling
  (MT-4.1-04); unclaimed tasks show no worker badge; percent bar omitted or empty
  when no percent reported.
* Component tests: each element renders from fixture data, stalled vs. not-stalled,
  claimed vs. unclaimed, priority variants.
* Add a WP changelog note.

## Out of scope
* Card click-through / task detail — WP-4.6.
* Drag-and-drop affordances — WP-4.4.
* Virtualization of many cards — MT-4.3-06.
* Live updates patching the card data — MT-4.3-05 (this task renders whatever data
  the cache holds).
* Review reason detail rendering — WP-4.8 review panel.
* Accessibility audit — WP-4.11 (keep semantic markup, but the a11y pass is later).

## Target paths
* `web/` (TaskCard component and styles within the board module)
* `web/` tests (card rendering tests)
* WP changelog entry

## Acceptance criteria
- [ ] The card shows all seven Section 13.2 elements: id, title, priority chip,
  worker badge with lease countdown, percent bar, attachment count,
  stalled/escalation marker (FR-WEB-01; Section 13.2 verbatim list).
- [ ] Stalled marker follows the Section 8.6 definition (`stalled_after_minutes`,
  policy-driven) — not a second, ad-hoc heuristic (Section 20.5 traceability).
- [ ] Priority chip covers exactly the Section 7.2 values (`urgent`, `high`,
  `medium`, `low`) using theme tokens from MT-4.1-04.
- [ ] Unclaimed and percent-less tasks render gracefully (no broken badge/bar).
- [ ] Card data flows from the board cache — no separate network fetch inside the
  card (Section 13.3 cache discipline).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the card (for example `npm test -- -t TaskCard`)
and confirm: all seven elements from fixture data, stalled/escalation variants,
claimed/unclaimed variants, and priority chips; then the full web suite stays green.

## Attachments
* [Section 13.2 — Key components (card contents)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.6 — Lease semantics (stalled indicator)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Task fields](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The lease countdown ticking every second across 500 cards interacts with MT-4.3-06
  virtualization — drive ticking from a shared timer/throttled update so re-renders
  stay bounded; the plan's "stays responsive" target (Section 13.4) applies.
* "Percent" source (checkpoint `percent` 0–100) is nullable — decide the visual for
  "unknown progress" explicitly; do not render 0 % as if the agent reported zero.
