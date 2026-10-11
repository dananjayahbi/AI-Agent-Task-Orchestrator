# MT-4.8-01 — Implement the cross-project review queue page

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.8-01 |
| Title | Implement the cross-project review queue page |
| Parent WP | WP-4.8 — Human review panel and queue (Milestone M4) |
| Requirements | FR-WEB-06 |
| Priority | M |
| Dependencies | WP-4.3 complete (board, stream hook MT-4.3-04/05); WP-3.6 complete (review decisions); WP-4.1 complete (auth, API client) |
| Parent sections | 13.1 (Review queue route), 9.2 (tasks/events endpoints), 9.6 (`review.requested`), 8.1 (`in_human_review`), 19 (WP-4.8), 20.3, 20.4, 20.5 |

## Context
Section 13.1 reserves the Review queue route for "All `in_human_review` tasks across
projects, sorted by age and priority." Section 19 WP-4.8 lists the review queue page
as its first slice; the escalation itself is signaled by `review.requested` events
(Section 9.6 catalog) emitted on every entry to `in_human_review` (Section 9.8
triggers), each carrying rule details (WP-3.9). This task is queue-page only: list,
sort, navigate — the panel, actions and merge status are MT-4.8-02…04.

## Inputs / Prerequisites
* Parent plan Section 13.1 — queue scope (all projects), sort keys (age, priority).
* Parent plan Section 8.1/8.4 — the canonical `in_human_review` state and the review
  reasons a row may surface.
* Parent plan Section 9.6 — `review.requested` for live queue updates through the
  WP-4.3 hook; `task.transitioned` for removals when a decision resolves the row.
* Parent plan Section 9.2 — task/history endpoints available for listing.
* Section 7.2 — Task fields shown per row: id, title, priority, `review_reason`,
  `created_at`/update timestamps for age, project id.

## Scope (in)
* The Review queue route/page listing every task in `in_human_review` across all
  projects, sorted by age and priority per Section 13.1.
* Row content: project, task id, title, priority chip, review reason (canonical
  Section 8.4 value displayed with a friendly label), age since escalation, and an
  entry action opening the review panel (MT-4.8-02) or task detail (WP-4.6).
* Live maintenance through SSE: `review.requested` adds/updates rows;
  `task.transitioned` out of `in_human_review` removes them (Sections 9.6, 13.3 cache
  patching); graceful handling when the stream is down (visible status per
  Section 13.3).
* Data-source wiring to whatever listing the backend exposes for cross-project
  `in_human_review` tasks (see Risk notes) with loading/empty/error states
  (Section 20.3) and catalog-only error mapping (Section 20.4 item 5).
* Component tests: fixture queue render, age/priority sort, live add/remove on
  events, empty state, error state.
* A WP changelog note.

## Out of scope
* The review panel contents (reasons detail, rule table, evidence, diff) — MT-4.8-02.
* The three actions and confirmations — MT-4.8-03.
* Merge-status display — MT-4.8-04.
* Producing `review.requested` events — WP-3.9 / state machine (Section 9.8).
* Per-project board columns — WP-4.3.

## Target paths
* `web/` (review queue route/page and row component)
* `web/` tests (queue tests with fixture events)
* WP changelog entry

## Acceptance criteria
- [ ] The queue lists `in_human_review` tasks from all projects — not one project —
  sorted by age then priority (Section 13.1).
- [ ] Each row shows project, task id, title, priority, canonical `review_reason` and
  age; reason values come verbatim from Section 8.4 (Sections 20.4 item 5, 20.5).
- [ ] The queue updates live: `review.requested` adds rows, resolution transitions
  remove them, via the WP-4.3 stream hook and cache patching (Sections 9.6, 13.3).
- [ ] Rows navigate to the review panel/task detail entry points (MT-4.8-02 /
  WP-4.6 contracts).
- [ ] Loading, empty ("nothing to review") and error states handled
  (Section 20.3); catalog-only error codes (Section 20.4 item 5).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the web test suite filtered to the review queue (for example `npm test -- -t
"review queue"`) and confirm cross-project listing, sort order, live add/remove on
fixture events, row navigation, and empty/error states; then the full web suite stays
green.

## Attachments
* [Section 13.1 — Information architecture (Review queue row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.4 — Review reasons (canonical enum)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.8 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Section 9.2 exposes `GET /projects/{pid}/tasks` (per project) but no documented
  cross-project task query — a true cross-project queue needs either a filtered
  endpoint, `GET /events` history, or a backend addition. Confirm what WP-4.3/WP-1.10
  shipped; if an endpoint must be added, treat it as an OpenAPI contract change
  (Section 20.4 item 4) rather than client fan-out over N projects (N-project
  fan-out violates the responsiveness target, Section 13.4).
* "Age" definition (since escalation vs since creation) is not spelled out —
  Section 13.1 says "sorted by age and priority"; use time in `in_human_review`
  (the escalation timestamp from the transition/event) and record the choice.
* Priority sorting across mixed states (urgent rows buried under old medium rows)
  needs a documented ordering rule — the plan gives two keys without precedence;
  implement age-first as written and note it.
