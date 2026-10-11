# MT-4.1-01 — Scaffold the Next.js Web Application

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.1-01 |
| Title | Scaffold the Next.js web application |
| Parent WP | WP-4.1 — Web app skeleton (Milestone M4) |
| Requirements | FR-WEB-01 (web dashboard), NFR-11 (typed API client) |
| Priority | M |
| Dependencies | MT-0.1-01 (repo groundwork), MT-1.1-04 (OpenAPI document to generate against), ADR-006/ADR-007/ADR-013 (stack), MT-0.1-02 conventions (per-package tooling) |
| Parent sections | 6.6 (stack), 13.1 (page/route map), 23 (ADR-006, ADR-007, ADR-013), 19.1 (WP-4.1 first slice), Appendix A (`web/`), 20.3, 20.4, 20.5 |

## Context
WP-4.1's first slice is "scaffold." Section 6.6 fixes the stack in one sentence:
"Web app: Next.js (App Router) with React and Tailwind CSS, plus shadcn/ui for
components." Section 13.1 fixes the routes: Board, Task detail, Projects, Settings,
plus whatever 13.1 enumerates (read it as the authoritative page list) — the skeleton
must place these routes even if each renders a placeholder, because routing is the
layout contract later WPs fill (WP-4.2+ build Board, task detail, etc.).
ADR-007 (Next.js) and ADR-013 (frontend libraries) pin the choices; ADR-006's
frontend/backend split means the app talks to the API only through the generated
typed client (NFR-11) — so the scaffold sets up that seam from day one (generation
wiring lands in MT-4.1-03, but the scaffold must not add hand-written fetch layers).
Appendix A gives the home: top-level `web/`, independent of `backend/` (ADR-006
deployables). WP-4.1's acceptance for the whole WP — "login works; client
regeneration fails CI when schema drifts" — starts with an app that boots.

## Inputs / Prerequisites
* MT-0.1-01 — repository structure; the `web/` directory per Appendix A.
* MT-1.1-04 — the published OpenAPI document (generation target for MT-4.1-03; the
  scaffold only declares the hook).
* Parent plan Section 6.6 — stack (Next.js App Router, React, Tailwind, shadcn/ui);
  Section 13.1 — route/page map; ADR-006/007/013 — binding stack decisions.
* MT-0.1-02-style per-package tooling conventions — `web/` gets its own
  `package.json`, lint/typecheck scripts the CI can call (Section 19.7: test only
  what changed).
* Backend endpoints (Section 9.2) exist from M1 — the scaffold does not call them
  yet beyond health/placeholder wiring.

## Scope (in)
* Create `web/` as a Next.js App Router application with the Section 6.6 stack —
  TypeScript, React, Tailwind CSS, shadcn/ui installed and minimal-configured;
  own `package.json` with scripts: dev, build, lint, typecheck (naming consistent
  with how MT-0.1-02's tooling phrasing applies to npm packages).
* Route placeholders for every page Section 13.1 lists, at App Router paths that
  mirror the plan's navigation (Board as the landing view, task detail under a
  project/task segment, Projects, Settings) — each renders a title/placeholder only;
  layout shell (app chrome, nav) may be minimal until MT-4.1-04 themes it.
* Configuration seam for the API base URL (read from environment/config, never
  hardcoded — Section 20.4 item 3) and the typed-client import path reserved for
  MT-4.1-03 (no ad-hoc `fetch` calls in placeholders — keep the single-HTTP-client
  rule of NFR-11 clean from the start).
* CI/test wiring: `web` lint and typecheck scripts runnable from the repo root
  (e.g. via npm `--prefix web`), added to the pipeline the same way backend gates
  run (Section 20.4 item 2); build must pass.
* No secrets, no `.env` values committed; `.env.example`-style placeholder for the
  API base URL if the scaffold needs one (MT-0.5-01 conventions applied to the web
  package).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Login/auth UI and route protection — MT-4.1-02.
* Typed API client generation and CI drift gate — MT-4.1-03.
* Theming, layout polish, error-code mapping — MT-4.1-04.
* Real feature pages (Board columns, task flows, kanban interactions) — WP-4.2 and
  beyond (Section 19 slices for those WPs).
* Backend work, database, or API changes — ADR-006 boundary; only consume.
* Deployment/hosts (Vercel etc.) — plan's deployment story is later; scaffold must
  build anywhere Node builds.

## Target paths
* `web/` — Next.js App Router app (`app/` routes per Section 13.1, `package.json`,
  Tailwind/shadcn config, tsconfig)
* `web/.env.example`-style placeholder if needed (MT-0.5-01 conventions)
* CI workflow — web lint/typecheck/build step (follow the existing pipeline's
  structure; do not restructure it)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] `web/` builds and serves placeholder pages for every Section 13.1 route with
  the Section 6.6 stack (Next.js App Router, React, Tailwind, shadcn/ui) —
  WP-4.1 first slice; ADR-007/ADR-013 (FR-WEB-01).
- [ ] Lint, typecheck and build scripts run from the repo root and pass in CI
  (Section 20.4 item 2); the run command is recorded in the changelog (item 1
  discipline).
- [ ] The API base URL comes from configuration, not a hardcoded value; no secrets
  or environment-specific paths committed (Section 20.4 item 3).
- [ ] No hand-written HTTP layer exists — the typed-client import seam is reserved
  for MT-4.1-03, keeping NFR-11's single-client rule intact.
- [ ] `web/` remains an independent package (own manifest, no imports from
  `backend/`) per ADR-006; backend CI untouched (Section 19.7).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
`npm --prefix web run lint` and `npm --prefix web run typecheck` and
`npm --prefix web run build` — all three green (the scaffold's proof; full UI tests
arrive with feature WPs).

## Attachments
* [Section 6.6 — Frontend stack](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.1 — Web page and route map](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [ADR-006 / ADR-007 / ADR-013 — Stack decisions](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* App Router path choices become load-bearing for MT-4.1-02's route groups
  (public vs. protected segments) — lay routes out so a `middleware`/layout-based
  protection can wrap them without reshuffling URLs; note the chosen segment
  structure in the changelog.
* Scaffold templates drift from the plan quickly (create-next-app defaults evolve) —
  pin the Next.js major per ADR-007's version stance if the ADR records one, and
  record the resolved versions in the changelog; if ADR-007 does not pin a version,
  choose the current stable and note it (do not leave versions implicit).
* shadcn/ui generates components into the repo — keep only what Section 13.4's
  component guidance needs later; a bloated initial component set invites unused
  code (Section 19.6 spirit), so scaffold with the minimum themeable primitives
  MT-4.1-04 will restyle.
