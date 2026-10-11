# MT-4.11-03 — Fix Contrast and Label Accessibility Findings

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.11-03 |
| Title | Fix contrast and label accessibility findings |
| Parent WP | WP-4.11 — Responsive, accessibility and performance pass (Milestone M4) |
| Requirements | NFR-13 |
| Priority | M |
| Dependencies | MT-4.11-01 (layout), MT-4.11-02 (keyboard navigation), MT-4.1-04 (theme tokens and error mapping) |
| Parent sections | 13.2 (components), 13.4 (themes), 18 (Web UI row: accessibility checks on core flows), 19 (WP-4.11 deliverable: accessibility audit report; third slice), 20.4, 20.5 |

## Context
NFR-13 sets the bar: "Web meets WCAG 2.1 AA for core flows." Section 19 (WP-4.11)
lists the accessibility audit report among the WP deliverables and "no critical
accessibility issues on core flows" among its acceptance. This slice is the
"contrast and labels" slice: audit the core flows, fix the contrast and labeling
findings, and publish the report that shows the audit ran and what was fixed. WCAG
contrast and label criteria are objective and testable, which keeps this task
verifiable within the global DoD (Section 20.4 item 1).

## Inputs / Prerequisites
* MT-4.11-01 and MT-4.11-02 — layout and keyboard work complete, so the audit runs
  against the final interaction model.
* Parent plan Section 13.2 — component inventory to cover: board cards (priority
  chip, worker badge, percent bar, stalled marker), task modal, review panel (rule
  table, evidence), diff viewer, audit log table, forms (policy/rules editors).
* Parent plan Section 13.4 — dark and light themes: contrast must hold in both.
* Parent plan Section 18 — Web UI row: accessibility checks on core flows (the check
  that produces findings).
* Theme token set (MT-4.1-04) — fixes belong in tokens wherever possible so both
  themes move together.

## Scope (in)
* Run an accessibility check over the core flows (board → task → review decision;
  audit log; settings forms) — automated check plus manual review of states — in both
  dark and light themes, and record every finding.
* Fix **contrast** findings: text, status chips/markers (priority, stalled,
  escalation), focus indicators and disabled states meeting WCAG 2.1 AA contrast —
  preferably by adjusting shared theme tokens (MT-4.1-04) rather than per-component
  overrides.
* Fix **label** findings: form fields have associated labels; icon-only buttons and
  controls have accessible names; the review panel's rule/evidence elements and the
  board's status markers are labelled for non-visual consumption; error messages are
  programmatically associated with their inputs (Section 13.3 error mapping).
* Publish the accessibility audit report: date, flows checked, tool/method, findings
  table with status (fixed / accepted limitation with justification), confirmation
  that no critical issues remain on core flows (Section 19 WP-4.11 acceptance).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Keyboard mechanics — MT-4.11-02 (its deferred component gaps may appear as
  findings here; fix only if they are contrast/label-class issues, else route back).
* Responsive layout — MT-4.11-01; performance — MT-4.11-04.
* Mobile app accessibility (dynamic text sizes) — NFR-13's mobile half, WP-5.x.
* Redesigning components for aesthetics — fixes are accessibility-driven; visual
  refresh is out.
* Achieving a formal third-party WCAG certification — the plan requires the baseline
  and the report, not an external audit.

## Target paths
* `web/` — theme token and component fixes for contrast/label findings
* `web/` tests — contrast/label assertions on core-flow components
* `docs/plan/` — accessibility audit report (WP-4.11 deliverable; Appendix A does
  not reserve a dedicated reports directory — see risk notes)
* WP changelog entry

## Acceptance criteria
- [ ] The audit report exists and covers all core flows in both themes, listing
  findings and their disposition (Section 19 WP-4.11 deliverable).
- [ ] No open critical contrast or label findings on core flows — Section 19 WP-4.11
  acceptance "no critical accessibility issues on core flows" (NFR-13).
- [ ] Contrast fixes applied via shared tokens where the finding spans both themes,
  verified in dark and light (Section 13.4).
- [ ] All audited form fields, icon-only controls and status markers have labels or
  accessible names (NFR-13, WCAG 2.1 AA).
- [ ] Regression tests for the fixed findings green in CI (Section 20.4 items 1–2);
  changelog note added (item 7).

## Test command
Run the web accessibility check over the core flows (e.g.
`npm --prefix web test -- a11y` for the component assertions) and confirm zero
contrast/label violations; then open `docs/plan/accessibility-audit.md` and verify
every finding is marked fixed or carries an accepted-limitation justification.

## Attachments
* [NFR-13 — Accessibility requirement](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.4 — Non-functional targets](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-4.11 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Appendix A reserves only `docs/plan/`, `docs/adr/`, `docs/runbooks/` and
  `docs/agent-guides/` — placing the audit report under `docs/plan/` keeps it with
  other process artifacts (like the decision-review notes); record the choice in the
  changelog rather than inventing a new top-level docs directory.
* "Accepted limitation" entries must be genuinely justified (e.g. a third-party
  component's known gap with an upstream link) — an over-used exception silently
  voids the Section 19 acceptance.
* Fixing contrast in shared tokens changes every screen — run the full web test
  suite, not just the a11y subset, to catch unintended palette shifts (Section 20.4
  item 2).
