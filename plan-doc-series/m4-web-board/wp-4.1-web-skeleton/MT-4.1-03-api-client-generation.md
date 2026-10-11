# MT-4.1-03 — Generate the Typed API Client in CI (Schema-Drift Gate)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.1-03 |
| Title | Generate the typed API client in CI (schema-drift gate) |
| Parent WP | WP-4.1 — Web app skeleton (Milestone M4) |
| Requirements | NFR-11 (typed client from OpenAPI), FR-WEB-01 |
| Priority | M |
| Dependencies | MT-4.1-01 (web scaffold with reserved seam), MT-1.1-04 (canonical OpenAPI document + CI diff discipline), MT-1.4-01 (schema versioning conventions) |
| Parent sections | 6.6, 13.1 (typed client), 19.1 (WP-4.1 acceptance), 19.6, 23 (ADR-006), 20.4 (items 2, 4), 20.5; Appendix B (B-01) |

## Context
NFR-11 is the requirement: "Web/mobile clients generate typed API clients from the
OpenAPI document (NFR-11)" — no hand-written request/response types, one contract.
WP-4.1's acceptance makes drift a **CI failure**: "client regeneration fails CI when
schema drifts." Two failure modes are covered: (a) the API changes and the committed
client is stale — regeneration produces a diff; (b) someone hand-edits the generated
client — regeneration overwrites/detects it. MT-1.1-04 established the backend half
(openapi.json generated, diffed, drift fails CI); this task is the web half:
generate `web/`'s client from that same canonical document in CI, fail when the
committed output differs from a fresh generation, and keep MT-4.1-01/02 consuming
only the generated surface. Appendix B B-01 (contract versioning) and MT-1.4-01's
schema-version work bound the compatibility story — this gate detects drift; it does
not decide version policy.

## Inputs / Prerequisites
* MT-4.1-01 — `web/` with the reserved typed-client import seam and npm scripts.
* MT-1.1-04 — the canonical `openapi.json` (or its published path/URL) and the
  existing diff-gate pattern to mirror; its Section 1.1.1 schema conventions.
* MT-1.4-01 — schema versioning conventions (what a breaking change means for the
  gate — a major-version bump still regenerates; the gate's job is freshness, not
  compatibility judgment).
* Parent plan NFR-11 — generation-from-OpenAPI mandate; Section 13.1 — the web app
  consumes the typed client; Section 19.6 — one implementation, no hand-written
  duplicate types.
* ADR-006 — web talks to backend only through the contract.

## Scope (in)
* Configure a client generator (choose one mainstream TypeScript generator consistent
  with the Section 6.6 stack — record the choice and version in the changelog; the
  plan does not name a specific tool) producing typed fetch-based client code from
  the canonical OpenAPI document into `web/`'s reserved directory.
* A `generate` npm script (e.g. `npm --prefix web run generate:api`) deterministic
  enough that two runs on the same document produce identical output (needed for the
  drift gate; disable nondeterministic headers/timestamps the tool emits).
* CI job step: regenerate → `git diff --exit-code` on the client directory → fail on
  any difference, with a message telling the developer to run the generate script
  and commit (mirror MT-1.1-04's drift-gate UX so both halves read the same).
* Wire MT-4.1-01/02's code to import types/functions from the generated package
  only — assert with a lint rule or test that no hand-written API types/fetch
  wrappers exist in `web/` (Section 19.6; NFR-11); allowlist any legitimate
  non-API helpers.
* Generator pinning: exact tool version committed (no floating latest) so CI and
  local runs agree; upgrading the generator is an explicit diff-reviewed change.
* OpenAPI document sourced exactly as MT-1.1-04 publishes it (same artifact the
  backend gate diffs) — one document, two consumers (Section 19.6).
* Tests: deterministic regeneration (run twice, no diff); drift simulation (mutate
  the document → CI step fails); hand-edit detection (edit generated file → fails);
  import-boundary test; changelog note (Section 20.4 item 7).

## Out of scope
* Producing or validating the OpenAPI document — MT-1.1-04 (backend).
* Contract versioning policy (semver, compatibility ranges) — Appendix B B-01's
  fast-follow ADR; MT-1.4-01's version fields.
* Mobile client generation (same NFR-11 mandate, WP-5.x) — this task establishes the
  pattern; the mobile WP reuses the script rather than re-choosing a generator.
* Runtime API behavior, retry/caching layers — Section 13.3/13.4 feature WPs.
* Generating non-TypeScript clients (docs, SDKs) — not required by NFR-11.

## Target paths
* `web/` — generator config, `generate:api` script in `package.json`, committed
  generated client directory (reserved by MT-4.1-01)
* CI workflow — generate + diff step beside MT-1.1-04's OpenAPI gate
* `web/` lint config — import-boundary rule (generated-only API access)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] `web/`'s API client is generated from the canonical OpenAPI document — no
  hand-written endpoint/types; import-boundary test enforces it (NFR-11; Section
  19.6).
- [ ] CI regenerates and fails on any diff between committed client and fresh output
  — WP-4.1 acceptance verbatim, "client regeneration fails CI when schema drifts"
  (Section 20.4 item 2).
- [ ] Regeneration is deterministic (two runs, zero diff) with the generator pinned
  to an exact version (reproducibility; recorded in the changelog).
- [ ] The OpenAPI document consumed is the same artifact MT-1.1-04's backend gate
  uses (one source of truth — Section 19.6; Section 20.4 item 4).
- [ ] The generation + drift step runs green on a clean tree and fails on a simulated
  schema change (both directions proven in tests/CI evidence).
- [ ] Changelog note added (Section 20.4 item 7); no secrets or environment-specific
  paths committed (item 3).

## Test command
`npm --prefix web run generate:api` twice with `git diff --exit-code web/<client-dir>`
clean between runs (determinism), then the mutation test: temporarily alter a schema
field → regeneration produces a diff → CI step fails as expected; plus
`npm --prefix web run lint` green with the import-boundary rule active.

## Attachments
* [NFR-11 — Typed API client generation](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-4.1 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 13.1 — Web client structure](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Generator choice is left open by the plan — pick a maintained TypeScript generator
  that supports App Router/React output, and record the decision + version in the
  changelog; a later ADR-style reversal would touch every consumer, so note the
  choice prominently (mobile WP-5.x will inherit it).
* Drift gates annoy developers when the fix is non-obvious — the CI failure message
  must contain the exact local command (`npm --prefix web run generate:api`) and
  remind that the OpenAPI change itself needs Section 20.4 item 4 review; a failing
  gate without a remedy breeds bypasses.
* If the backend OpenAPI document is only available from a running service (rather
  than a committed artifact per MT-1.1-04), CI ordering must fetch/build it first —
  confirm MT-1.1-04 publishes a committed snapshot; if not, raise the ordering
  question as a new OQ (`OQ-15+`) instead of generating from a live URL.
