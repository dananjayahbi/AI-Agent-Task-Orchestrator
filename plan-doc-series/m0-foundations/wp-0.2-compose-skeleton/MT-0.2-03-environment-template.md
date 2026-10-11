# MT-0.2-03 — Create the Environment Template with Documented Defaults

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-0.2-03 |
| Title | Create the environment template with documented defaults and validation notes |
| Parent WP | WP-0.2 — Compose skeleton and environment template (Milestone M0) |
| Requirements | NFR-06 |
| Priority | M |
| Dependencies | MT-0.2-01 |
| Parent sections | 9.10, 16.2, 19.1 (WP-0.2), 20.4 |

## Context
Section 16.2 requires one documented environment template with real values living outside
Git, and 9.10 requires every setting to have a documented default plus a startup
validation that fails fast on missing required values. This task creates that template
and its validation notes so the Compose stack (MT-0.2-01/02) is configured only by
environment variables — the core of NFR-06 portability. Naming of the variables is
formalized later by WP-0.5 (MT-0.5-01); this task keeps names consistent from day one.

## Inputs / Prerequisites
* MT-0.2-01 (services need variables), MT-0.2-02 (port bind address variable).
* Parent plan Section 9.10 — configuration groups: database and cache URLs, secret keys,
  allowed hosts and CORS/CSRF origins, storage backend, token lifetimes, rate limits,
  OCR engine, description provider settings, FCM credentials, Cloudflare tunnel token,
  feature flags.
* Parent plan Section 16.2 — one template, real values outside Git, startup validation
  refuses weak/missing secrets in `prod`.
* Decisions from WP-0.4 where a setting's default depends on an open question (e.g.
  description provider disabled per OQ-07).

## Scope (in)
* Create the Compose environment template file (e.g. `.env.example` under
  `infra/compose/`) covering every 9.10 group that has a Compose-level consumer now,
  with a comment per variable: purpose, default, and validation note.
* Ensure `.env` (the real values file) is git-ignored and never committed.
* Record which variables are required in `prod` (secret keys, allowed hosts) versus
  optional-with-default, per 9.10 and 16.2.
* Add a validation-notes section to the Compose README: startup validation must fail
  fast on missing/weak secrets in `prod` (backend implements this in WP-1.1; the notes
  fix the contract now).
* Keep variable names consistent with the eventual naming conventions (WP-0.5 will
  formalize them in MT-0.5-01).
* Add a WP changelog note.

## Out of scope
* The formal naming-convention document — MT-0.5-01.
* Implementing backend startup validation code — WP-1.1.
* Cloudflare tunnel token provisioning — WP-5.1.
* S3-compatible storage configuration beyond the placeholder group — WP-1.1/WP-6.2.
* FCM credentials and push settings — WP-5.4.

## Target paths
* `infra/compose/.env.example` (the documented template)
* `.gitignore` (real `.env` excluded)
* `infra/compose/README.md` (validation notes and copy-and-edit bring-up steps)
* WP changelog entry

## Acceptance criteria
- [ ] One environment template exists covering every 9.10 configuration group that the
  M0 stack consumes, each variable documented with default and validation note.
- [ ] The real environment file is git-ignored; `git status` never shows it.
- [ ] Required-in-prod variables are marked, including the weak/missing-secret refusal
  rule from 16.2.
- [ ] The Compose file renders with the template applied (`docker compose --env-file`).
- [ ] No real secrets or environment-specific values committed (Section 20.4 item 3).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Render the stack with the template: `docker compose -f infra/compose/compose.yaml --env-file infra/compose/.env.example config` must succeed. Confirm `git check-ignore` reports the real `.env` as ignored, and that no line in the template contains a real credential.

## Attachments
* [Section 9.10 — Configuration (environment-driven)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.2 — Configuration and secrets](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Not every 9.10 group has a consumer in M0 (FCM, OCR, description provider) — the
  template should mark those as reserved placeholders so WP-0.5 can reconcile them
  against the final naming conventions without renaming Compose-consumed variables.
* Defaults chosen here (token lifetimes, rate limits) become de-facto contract; flag any
  value whose default depends on an undecided OQ (e.g. OQ-07, OQ-09) and defer it to
  WP-0.4 outcomes.
