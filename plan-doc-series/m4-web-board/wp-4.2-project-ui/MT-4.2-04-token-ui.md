# MT-4.2-04 — Implement agent token create/revoke UI with one-time reveal

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.2-04 |
| Title | Implement agent token create/revoke UI with one-time reveal |
| Parent WP | WP-4.2 — Project switcher, project CRUD, manifest and tokens UI (Milestone M4) |
| Requirements | FR-PRJ-01 (project management context), FR-WEB-09 (project settings surface); agent tokens per Section 12.2 |
| Priority | M |
| Dependencies | MT-4.2-01/02 (Project settings section), WP-4.1 (client), WP-1.3 (token endpoints) |
| Parent sections | 9.2 (Tokens endpoints), 12.2, 13.1 (Project settings), 19 (WP-4.2), 20.4, 20.5 |

## Context
Section 12.2 defines agent authentication: "long-lived but revocable project-scoped
bearer tokens, created per project by the Owner and stored in the host's user-level
config." The endpoints are `POST /tokens/agent` (project-scoped), `GET /tokens`, and
`DELETE /tokens/{id}` (Section 9.2, Owner caller). WP-4.2's deliverable is a "token
create/revoke UI with one-time reveal" — the token value can be shown only at
creation, because the backend stores it hashed and cannot show it again. Section
13.1 places this in Project settings alongside the manifest; the manifest itself
never carries tokens (Section 10.3 step 3), so this UI is the only place secrets
appear — and only once.

## Inputs / Prerequisites
* Parent plan Section 9.2 — `POST /tokens/agent`, `GET /tokens`, `DELETE /tokens/{id}`.
* Parent plan Section 12.2 — agent token model: project-scoped, revocable, Owner
  created; agents authenticate with them (bridge reads from env/user config,
  Section 10.3 step 3).
* Parent plan Section 12.4 — secrets never committed; logs scrub tokens.
* WP-4.1 — generated client, error mapping; MT-4.2-01/02 — Project settings
  container; WP-1.3 — backend token issuance.

## Scope (in)
* Token management section in Project settings: list of the project's agent tokens
  from `GET /tokens` showing non-secret metadata only (label/identifier, project,
  created date, last-used/revoked status as the API returns).
* Create action calling `POST /tokens/agent`: on success, a one-time reveal panel
  displaying the token value exactly once, with copy-to-clipboard and an explicit
  warning that it will not be shown again, plus the pointer to store it in the
  host's user-level config / environment (Section 12.2, Section 10.3 step 3).
* Revoke action calling `DELETE /tokens/{id}` behind a confirmation dialog stating
  impact (agents using the token lose access immediately); list refreshes after
  success.
* No secret persistence in web state: the revealed value is cleared on
  unmount/navigation, never logged, never written to localStorage
  (Section 12.4, Section 20.4 item 3).
* Component tests: create flow reveals once and clears on navigation, copy works,
  revoke confirmation gates deletion, list refresh, and error states
  (`AUTH_REQUIRED`, permission failures) map to friendly messages.

## Out of scope
* Backend token issuance, hashing, scoping and revocation — WP-1.3.
* The bridge's token storage (env or user-level config) — WP-2.2 (MT-2.2-03); this
  UI only hands the value over once.
* Manifest content — MT-4.2-03 (tokens must never be added there).
* Device tokens for mobile — ADR-006/WP-5.3 (different flow: `POST /devices`).
* Session auth for the Owner (login) — WP-4.1.

## Target paths
* `web/` (token management section under Project settings)
* `web/` tests (component tests)
* WP changelog entry

## Acceptance criteria
- [ ] Creating a project-scoped agent token via `POST /tokens/agent` reveals the
  value exactly once; reloading or navigating away discards it permanently
  (WP-4.2 deliverable: one-time reveal).
- [ ] The token list shows only non-secret metadata; the token value appears in no
  list, cache, log or storage artifact (Section 12.4, Section 20.4 item 3).
- [ ] Revocation requires confirmation, calls `DELETE /tokens/{id}`, and the list
  reflects removal (Section 12.2 revocable tokens).
- [ ] The reveal panel instructs storing the token in the user-level config or
  environment — matching Section 10.3 step 3 (never in the manifest).
- [ ] All calls use the generated client; errors map from Section 9.2 codes to
  friendly messages (Section 13.3); tests pass in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the token UI component tests in `web/` (e.g. `npm test -- agent-tokens`),
asserting one-time reveal with state clearing, no secret retention, revoke
confirmation flow, and error-state mapping.

## Attachments
* [Section 12.2 — Authentication and authorization](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Tokens endpoints](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* This is the only web surface handling a bearer secret — review carefully for
  accidental persistence (form state libraries, analytics, error reports) before
  merging (Section 20.4 item 3).
* If the backend ever returns the full token from `GET /tokens`, the UI must not
  display it; treat one-time-only display as an invariant and note any API
  divergence as an OQ-xx.
