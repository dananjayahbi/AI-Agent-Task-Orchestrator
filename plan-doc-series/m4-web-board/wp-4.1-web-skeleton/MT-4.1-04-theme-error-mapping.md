# MT-4.1-04 — Establish Theming, Layout and Error-Code Mapping

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.1-04 |
| Title | Establish theming, layout and error-code mapping |
| Parent WP | WP-4.1 — Web app skeleton (Milestone M4) |
| Requirements | FR-WEB-01, NFR-11 (client reuse), NFR-04 (aligned errors) |
| Priority | M |
| Dependencies | MT-4.1-01 (scaffold, shadcn/ui primitives), MT-4.1-02 (401/403 routing wired), MT-0.5-02 (canonical error envelope), MT-1.1-04 (OpenAPI error codes) |
| Parent sections | 9.2 (error catalog), 13.2 (client behavior), 13.3 (error states), 13.4 (component/layout guidance), 19.1 (WP-4.1 fourth slice), 19.6, 20.4, 20.5 |

## Context
WP-4.1's fourth slice is "theme and layout." Section 13.3 is the behavioral core:
canonical error codes from the Section 9.2 catalog map to friendly, human-readable
messages in the UI — never raw server text, never a bare code — reusing the MT-0.5-02
envelope's `code` + `message` fields as the contract between API and UI. Section 13.4
gives layout/component guidance (the design principles the Board WP-4.2 will build
on); Section 6.6's shadcn/ui + Tailwind supply the themable primitives from
MT-4.1-01's scaffold. The slice closes WP-4.1's whole-WP acceptance context: login
works (MT-4.1-02), drift gates CI (MT-4.1-03), and the app has a coherent visual +
error surface before feature WPs start. The mapping table is one shared source
(Section 19.6) consumed by every future page, so error UX is consistent from the
first feature onward.

## Inputs / Prerequisites
* MT-4.1-01 — Tailwind/shadcn/ui scaffold and layout shell to theme.
* MT-4.1-02 — auth error routing (401→login, 403→denial) already distinguishes
  *routing* from *presentation*; this task owns presentation.
* MT-0.5-02 — the error envelope shape (`code`, `message`, `request_id`) the UI
  parses; MT-1.1-04 — the canonical code list published in OpenAPI (generate the
  mapping keys from it where practical so codes cannot be invented — Section 20.4
  item 5 mirrors here: UI maps only catalog codes).
* Parent plan Section 9.2 — the 19 canonical codes; Section 13.3 — friendly error
  states; Section 13.4 — layout/component guidance (read for the authoritative
  principles); Section 13.2 — client behavior.
* G-07 — denials must not leak internal detail (friendly text, no stack/server
  messages shown).

## Scope (in)
* **Theme**: Tailwind design tokens (colors, spacing, typography) and shadcn/ui
  theme configuration establishing a coherent default light/dark-capable look per
  Section 13.4's guidance — tokens defined once, components consuming tokens (no
  one-off hex values sprinkled through pages); dark-mode capability exists if
  Section 13.4 calls for it, else keep the toggle out (do not invent product
  features).
* **Layout**: the app shell from MT-4.1-01 finished to Section 13.4's structure —
  navigation for the Section 13.1 routes, consistent page headers, and a shared
  loading/empty/error-state pattern component that feature WPs (WP-4.2+) reuse.
* **Error-code mapping**: one shared module mapping every Section 9.2 catalog code →
  friendly message (and severity/presentation: toast vs. inline vs. full state) per
  Section 13.3; unknown codes fall back to a generic message plus `request_id`
  (from MT-0.5-02's envelope) for support — never render raw server strings or code
  literals as the primary text; wire the mapping into MT-4.1-02's routing behavior
  and export for future pages.
* Message text quality: plain language, actionable (Section 13.3's intent); messages
  live in the mapping module (one source — Section 19.6), locale-ready but English
  only for now (no i18n framework the plan does not specify).
* Tests: every catalog code has a mapping (list derived from the OpenAPI/envelope so
  a new backend code without a UI mapping fails the test — cross-side of Section
  19.6); unknown-code fallback shows `request_id`; theme tokens referenced (lint or
  style test as practical); no raw envelope `message` shown as primary text;
  changelog note (Section 20.4 item 7).

## Out of scope
* Feature pages and their content (Board, task detail) — WP-4.2+ (this task provides
  shell + patterns they use).
* Backend error text or code changes — Section 9.2 is fixed; UI consumes.
* MT-4.1-02's redirect/denial *routing* — already wired; only the presentation layer
  lands here.
* Accessibility certification, i18n, design-system documentation site — not plan
  deliverables for WP-4.1 (note Section 13.4 principles are followed; deep a11y
  audits belong with feature WPs).
* Mobile theming (WP-5.x) — shares the mapping idea later; not built here.

## Target paths
* `web/` — theme/token config (Tailwind + shadcn/ui), layout shell components
* `web/` — shared error-state components and the error-code mapping module
  (single source; keys aligned to Section 9.2 / OpenAPI)
* `web/tests/` (mapping completeness, fallback, no-raw-string tests)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Every Section 9.2 canonical error code has a friendly mapping, rendered
  through shared components per Section 13.3 — WP-4.1 fourth slice (NFR-04;
  Section 9.2).
- [ ] Mapping completeness is test-enforced against the published code list (OpenAPI
  from MT-1.1-04) — a new backend code fails the web test until mapped
  (Section 19.6 single source; Section 20.4 item 5's UI counterpart).
- [ ] Unknown codes degrade to a generic message + `request_id` (MT-0.5-02 envelope)
  with no raw server text or internal detail shown (G-07; Section 13.3).
- [ ] Theme tokens are centralized and consumed by shadcn/ui/Tailwind — no scattered
  one-off styles; app shell renders navigation for all Section 13.1 routes with
  consistent header/loading/empty/error patterns (Section 13.4).
- [ ] Tests, lint, typecheck green in CI (Section 20.4 item 2); no secrets committed
  (item 3); changelog note added (item 7).

## Test command
`npm --prefix web run lint && npm --prefix web run typecheck` and the web test
runner on the error-mapping suite (e.g. `npm --prefix web test -- errors`, runner
choice recorded in the changelog): catalog completeness against OpenAPI, unknown-code
fallback with `request_id`, raw-string guard; then `npm --prefix web run build`.

## Attachments
* [Section 13.3 — Error states and friendly mapping](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Canonical error catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.4 — Component and layout guidance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Catalog changes are two-sided: backend adds a code (MT-1.1-04's gate catches
  schema diffs) but the web mapping test is the only thing forcing a friendly
  message — keep both gates in the same pipeline so neither lags (Section 20.4
  items 4–5).
* Section 13.3/13.4 wording may describe states (toast vs. page) without pinning
  which codes get which presentation — choose a sensible default presentation
  matrix, record it in the changelog as this task's interpretation, and let feature
  WPs refine per-page without changing the code→message table.
* shadcn/ui theming generates editable component files — once customized they stop
  tracking upstream; pin the library version and note the fork boundary in the
  changelog so future upgrades are deliberate (Section 19.7 discipline applied to
  dependencies).
