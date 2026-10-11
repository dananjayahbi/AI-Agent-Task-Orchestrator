# MT-4.5-02 — Integrate markdown editor with preview

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-02 |
| Title | Integrate markdown editor with preview |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03 |
| Priority | M |
| Dependencies | MT-4.5-01 (modal scaffold), WP-4.1 (UI primitives, dependency decision for the editor) |
| Parent sections | 13.2, 13.3, 19 (WP-4.5), 20.4, 20.5 |

## Context
Section 13.2's task modal includes a "markdown editor with preview" — task
descriptions are authored as markdown (they flow to agents through
`get_task_details`, where they are consumed as data — P10 posture applies
downstream). This slice integrates the editing surface with a live preview into the
MT-4.5-01 scaffold, keeping Section 13.3's discipline: shared validation schemas and
canonical error mapping, no bespoke form state.

## Inputs / Prerequisites
* Parent plan Section 13.2 — "markdown editor with preview" requirement.
* Parent plan Section 13.3 — typed client, shared schemas, query cache.
* MT-4.5-01 — modal shell the editor mounts into.
* WP-4.1 — theming (dark/light) and dialog primitives the editor must match.

## Scope (in)
* A markdown editor for the task description field with a preview toggle/pane,
  mounted in the modal scaffold and bound to the same form state.
* Round-trip fidelity: markdown written in the editor saves unchanged through the
  modal's `POST`/`PATCH` path and comes back byte-identical on reload (no
  normalization surprises).
* Preview rendering that treats the markdown as data — safe rendering (no script
  execution), consistent with the P10 posture for content that reaches agents.
* Theming and keyboard support: dark/light themes (Section 13.4), keyboard-accessible
  edit/preview toggle; performance acceptable for realistically long descriptions
  (lazy preview render if needed).
* Component tests: edit→save→reload fidelity, preview shows rendered output,
  hostile markdown (raw HTML/script attempts) renders inert, keyboard toggle, theme
  application.

## Out of scope
* Other modal fields (criteria/scope editors are structured lists, not markdown) —
  MT-4.5-03; core fields — MT-4.5-01.
* Server-side markdown storage/processing — WP-1.4 (stores text as-is).
* Rendering task descriptions elsewhere (detail views, agent-facing payload) —
  WP-4.6, WP-2.4.
* Choosing/sanitizing backend content beyond safe preview rendering — security
  review WP-6.1 covers upload/content abuse.

## Target paths
* `web/` — markdown editor component and modal integration
* `web/tests/` — editor component tests
* WP changelog entry (editor dependency recorded)

## Acceptance criteria
- [ ] The description field is a markdown editor with a working preview, per
  Section 13.2.
- [ ] Content round-trips unchanged: edit → save → reload yields the identical
  markdown source.
- [ ] Preview renders markdown inertly — embedded HTML/scripts cannot execute
  (P10 posture; Section 12.1 injection row).
- [ ] Editor follows dark/light theming and is keyboard-operable (Section 13.4).
- [ ] Editor dependency choice recorded in the changelog (Section 20.4 item 7);
  lint/type/tests green (item 2).

## Test command
`npm test -- -t markdown-editor` — assert round-trip fidelity, preview rendering,
inert hostile input, keyboard toggle and theming; then the full web suite stays
green.

## Attachments
* [Section 13.2 — Key components (task modal)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.1 — Threat model (prompt injection)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Editor library choice is a real dependency decision — prefer one with no
  unsafe-by-default HTML preview; record the pick and its sanitizer behavior in the
  changelog (Section 20.1, no hidden decisions).
* WYSIWYG editors that rewrite markdown on save break the round-trip guarantee —
  test fidelity explicitly, not just "content present".
* Preview must not fetch remote resources embedded in markdown (image/link
  callbacks) without deliberate review — leaking editor sessions to third parties
  is an avoidable regression.
