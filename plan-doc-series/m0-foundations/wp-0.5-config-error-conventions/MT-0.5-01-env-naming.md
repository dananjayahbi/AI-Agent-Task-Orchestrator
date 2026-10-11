# MT-0.5-01 — Define Environment Variable Naming and Grouping Conventions

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.5-01 |
| Title | Define environment variable naming and grouping conventions per parent plan 9.10 |
| Parent WP | WP-0.5 — Configuration, secrets and error conventions (Milestone M0) |
| Requirements | NFR-11, NFR-12 (shared conventions); NFR-06 (same names everywhere) |
| Priority | M |
| Dependencies | MT-0.4-01, MT-0.4-02, MT-0.4-03 (WP-0.4 complete) |
| Parent sections | 9.10, 16.2, 19.1 (WP-0.5), 20.4, 22 (decided OQs affecting defaults) |

## Context
WP-0.5's goal is to fix shared conventions before code spreads, and its first slice is
environment naming. Section 9.10 enumerates the configuration groups and requires every
setting to have a documented default plus fail-fast startup validation; Section 16.2
requires the same variable names to be used everywhere (Compose, VPS secrets, backend,
bridge). Capturing this as one conventions document now prevents rename churn once the
backend, bridge, web and mobile packages start reading configuration.

## Inputs / Prerequisites
* Parent plan Section 9.10 — configuration groups: database and cache URLs, secret keys,
  allowed hosts and CORS/CSRF origins, storage backend, token lifetimes, rate limits,
  OCR engine, description provider, FCM credentials, Cloudflare tunnel token, feature
  flags.
* Parent plan Section 16.2 — one documented template, real values outside Git,
  host-secret mechanism or Compose secrets with identical variable names.
* `infra/compose/.env.example` from MT-0.2-03 — existing variables to reconcile.
* Decisions from WP-0.4 (e.g. OQ-07 description provider default) and the accepted
  ADR records.
* WP-0.5 conventions document location under `docs/plan/` (created by this task if the
  WP-level file does not exist yet).

## Scope (in)
* Publish the configuration-conventions section of the WP-0.5 conventions document:
  naming pattern for all environment variables, grouping by the 9.10 groups, casing and
  prefix rules, and separation of secrets from ordinary settings.
* Require, per the convention, a documented default and a validation note for every
  setting, with fail-fast startup validation for missing/required values (9.10) and
  weak/missing-secret refusal in `prod` (16.2).
* Reconcile the naming rules against `infra/compose/.env.example` so Compose-consumed
  variables already follow the convention (renaming now is cheap; later is not).
* State the "same names everywhere" rule: Compose template, host secret mechanism,
  backend settings, bridge configuration all share one vocabulary (NFR-06).
* Reference the conventions document from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
* Add a WP changelog note.

## Out of scope
* Error envelope and error-code catalog — MT-0.5-02.
* Correlation and idempotency header conventions — MT-0.5-03.
* Pagination conventions — MT-0.5-04.
* Backend settings implementation and startup validation code — WP-1.1.
* Deciding new configuration semantics not present in 9.10 — raise as an open question.

## Target paths
* `docs/plan/conventions/configuration.md` (naming and grouping conventions section of
  the WP-0.5 conventions document)
* `infra/compose/.env.example` (reconciled to the naming rules, if any rename is needed)
* `backend/`, `bridge/`, `web/`, `mobile/` package docs or configs (reference added)
* WP changelog entry

## Acceptance criteria
- [ ] A conventions document exists covering all 9.10 groups with a naming pattern,
  grouping rule, and secret-handling rule (Section 19 WP-0.5 deliverable derived
  from Sections 9.2 and 9.10).
- [ ] Every setting is required to carry a documented default and a validation note;
  required-in-prod variables are marked (9.10, 16.2).
- [ ] `infra/compose/.env.example` conforms to the naming rules (no divergent names).
- [ ] The document is referenced from backend, bridge, web and mobile package docs
  (WP-0.5 acceptance).
- [ ] No real secrets or environment-specific values committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Re-read `docs/plan/conventions/configuration.md` against Section 9.10 and confirm every
group appears; run the Compose render check `docker compose -f infra/compose/compose.yaml --env-file infra/compose/.env.example config` to confirm reconciled names still resolve; grep the four package docs for the conventions reference.

## Attachments
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.2 — Configuration and secrets](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Renaming MT-0.2-03 variables late breaks the Compose README examples — do the
  reconciliation before M1 code reads any variable (WP-0.5 depends on WP-0.4 precisely
  so this happens before code spreads).
* Defaults for settings tied to open questions (OQ-07, OQ-09) must reflect the
  WP-0.4 decisions, not remembered defaults — re-read Section 22 after MT-0.4-03.
