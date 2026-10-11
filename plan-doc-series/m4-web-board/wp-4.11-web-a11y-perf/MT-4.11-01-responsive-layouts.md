# MT-4.11-01 — Implement Responsive Layouts Incl. Phone-Browser Fallback

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.11-01 |
| Title | Implement responsive layouts incl. phone-browser fallback |
| Parent WP | WP-4.11 — Responsive, accessibility and performance pass (Milestone M4) |
| Requirements | NFR-13 |
| Priority | M |
| Dependencies | MT-4.3-01 … MT-4.3-06 (board exists), WP-4.4 … WP-4.10 complete (review queue, task detail, review panel, audit log, editors all landed) |
| Parent sections | 13.1 (routes), 13.2 (components), 13.4 (responsive/phone-browser fallback), 19 (WP-4.11 first slice), 20.4, 20.5; 21 (RISK-09, RISK-11) |

## Context
Section 13.4 requires "responsive layouts that remain usable on a phone browser as a
fallback review channel" — the web board is the interim remote-review path until
mobile ships (RISK-11) and stays the safety net afterwards (RISK-09: "responsive web
as mobile fallback"). This first WP-4.11 slice lays the layout groundwork the
keyboard, contrast and performance slices build on: the core flows from Section 13.1
(board, task detail, review queue, review panel, audit log, settings) must be
operable on a phone-sized viewport without horizontal-trap or unreachable actions.
NFR-13 is the WP's requirement; the phone-fallback wording is this slice's specific
target.

## Inputs / Prerequisites
* WP-4.3 to WP-4.10 — all screens and components exist to be made responsive
  (board, filters, task modal, checkpoint feed, diff viewer, review panel, audit log
  viewer, policy/rules editors).
* Parent plan Section 13.1 — the route map; core flows to preserve: view board,
  open task, review (approve/request changes/reassign), read audit log.
* Parent plan Section 13.2 — component inventory (Board columns, Task modal, Review
  panel, Attachment viewer).
* Parent plan Section 13.4 — the target wording and the dark/light theme requirement
  already satisfied by MT-4.1-04.
* Existing theme tokens (MT-4.1-04) — responsive work reuses them; no new palette.

## Scope (in)
* Responsive layout rules (breakpoints and container behavior) for the core routes:
  project board (six columns), task detail, review queue, review panel, audit log and
  settings — at phone viewport widths the layout stacks/reflows so every core-flow
  control is reachable and operable.
* Review channel specifically: the approve / request-changes / reassign actions and
  the diff viewer must remain usable on a phone browser (this is the fallback channel
  RISK-09/RISK-11 depend on).
* Consistent behavior of loading, empty and error states across viewports (Section
  20.3: UI tasks keep states explicit).
* Reuse of existing theme tokens so dark and light themes keep working at all
  viewports (Section 13.4).
* Component/layout tests asserting the core screens at representative phone and
  desktop viewports, plus notes on any flow intentionally simplified on small screens.
* Changelog note (Section 20.4 item 7).

## Out of scope
* Keyboard navigation — MT-4.11-02; contrast/label fixes — MT-4.11-03; performance
  measurement — MT-4.11-04.
* Column virtualization (already MT-4.3-06) — reuse it; do not re-implement.
* A native or PWA mobile app — M5 owns the mobile client; this is the browser
  fallback only.
* New visual design beyond responsive adaptation; drag-and-drop rules (FR-WEB-02)
  stay server-validated as built.
* Mobile dynamic text sizes (NFR-13's mobile half) — Flutter app, WP-5.x.

## Target paths
* `web/` — responsive layout/style modules and component adjustments for the core
  routes
* `web/` tests — viewport-level component tests for phone and desktop
* WP changelog entry

## Acceptance criteria
- [ ] Core flows (board → task → review decision; audit log) are usable at a phone
  browser viewport: no unreachable controls, no horizontal scroll-trap on primary
  content (Section 13.4 phone-browser fallback).
- [ ] The review actions (approve, request changes, reassign) and diff viewer work at
  phone width — the fallback review channel promised by RISK-09/RISK-11 mitigations.
- [ ] Board, detail, queue, audit and settings each reflow using shared layout rules,
  not one-off hacks per page (one coherent change — Section 20.3).
- [ ] Dark and light themes render correctly at all tested viewports (Section 13.4).
- [ ] Viewport tests green in CI (Section 20.4 items 1–2); changelog note added
  (item 7).

## Test command
`npm --prefix web test -- responsive` (or the scaffold's test selector) — component
tests for core screens at phone and desktop viewports pass; then manually load the
review panel at a phone viewport and complete an approve flow against the local
stack, confirming every control is reachable.

## Attachments
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.1 — Information architecture](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-09, RISK-11 (responsive web as fallback)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Scope creep toward a "mobile site" — Section 20.3 caps this at layout adaptation;
  anything needing new interaction patterns (beyond reflow) becomes a follow-up task.
* Phone-browser usability is the mitigation for RISK-11 (mobile arrives late) — if
  this slice slips, flag the risk explicitly in the changelog rather than silently
  shipping a desktop-only board.
* Hiding functionality on small screens is a trap: prefer stacking and progressive
  disclosure over removal, or the fallback channel cannot actually review.
