# MT-1.3-05 — Create the orchestrator.json Manifest Schema and Renderer

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.3-05 |
| Title | Create the orchestrator.json manifest schema and renderer |
| Parent WP | WP-1.3 — Project registry, policy and manifest (Milestone M1) |
| Requirements | FR-PRJ-03, FR-SEC-04; G-09; ADR-007 |
| Priority | M |
| Dependencies | MT-1.3-02 (project + policy values), MT-1.3-03 (project routes), MT-1.1-04 (schema publication pattern), MT-1.2-05 (endpoint permissions) |
| Parent sections | 9.2 (`GET /projects/{pid}/manifest`), 10.3, 7.2, 12.4, 19.1 (WP-1.3 acceptance), 20.4 (item 4), 20.5 |

## Context
FR-PRJ-03 requires a downloadable `orchestrator.json` for a project; WP-1.3's
acceptance adds "generated manifest passes schema validation". Section 10.3 fixes the
manifest wire contract exactly (JSON below is the plan's own contract — reproduce by
reference, not re-derive): `schema_version`, `project_id`, `project_name`,
`orchestrator_api`, `default_branch`, `auto_branch_prefix`, `audit_required_default`,
`agent_hints`. The manifest holds no secrets and is safe to commit (FR-SEC-04,
Section 10.3), the bridge validates against a published schema (Section 10.3 step 2,
WP-2.2), and the backend never touches repositories (ADR-007) — the manifest is how
project context reaches a repo without the backend seeing it. G-09: `auto_branch_prefix`
is the canonical branch prefix (`feat/{PID}-` default from Section 7.2).

## Inputs / Prerequisites
* Parent plan Section 10.3 — the extended manifest JSON example (the authoritative
  contract; the `$schema` URL shown there is what the schema file must satisfy).
* Parent plan Section 7.2 — source values: project name, default_branch, branch_prefix
  → `auto_branch_prefix`, audit_required_default.
* Parent plan Section 9.2 — `GET /projects/{pid}/manifest` (caller Owner; agents read
  their own project's manifest through the bridge's local file, not this endpoint).
* Parent plan FR-SEC-04 — secrets never in the manifest; manifest safe to commit.
* Parent plan Appendix A — `schemas/` directory holds the manifest schema file.
* MT-0.5-04 — not directly required (manifest is a single document, not a list) —
  confirm no pagination applies.
* WP-2.2 will consume the schema — its validation rules must be testable now.

## Scope (in)
* Publish the manifest JSON Schema file under `schemas/` (Appendix A) satisfying the
  Section 10.3 contract: required keys, types, `schema_version: 1`, `project_id`
  matching `PID[0-9]{5}`. Copy the contract by reference to Section 10.3 — do not
  invent additional required keys.
* Implement the renderer: given a project (and its policy), produce the manifest JSON
  with `project_id`, `project_name`, `orchestrator_api` (from Section 9.10 settings —
  the API base URL; not from user input), `default_branch`, `auto_branch_prefix`
  (policy `branch_prefix` per G-09), `audit_required_default` (policy), and
  `agent_hints` defaults per Section 10.3 (all `agent_hints` keys optional).
* Implement `GET /projects/{pid}/manifest` returning the document as a downloadable
  file, Owner-only (Section 9.2 caller; permission from MT-1.2-05).
* Guarantee no secret material can appear in the render: the renderer reads only the
  Section 7.2/10.3 fields — a test asserts a fixed allowlist of keys (FR-SEC-04).
* Validate every rendered document against the published schema in tests (WP-1.3
  acceptance: "generated manifest passes schema validation").
* Document the endpoint in the OpenAPI snapshot (Section 20.4 item 4).
* Add a WP changelog note (Section 20.4 item 7).

## Out of scope
* Bridge-side discovery, walking up to Git root, version-compatibility check,
  session binding — WP-2.2 (Section 10.3 steps 1–5).
* The `orchestrator init` command writing the manifest — FR-MCP-08, WP-2.x.
* Secrets/token embedding — forbidden by FR-SEC-04; the token comes from environment
  or user-level config (Section 10.3 step 3).
* Updating the schema when the bridge adds keys — later WPs must extend the schema in
  `schemas/` with schema diff review (Section 20.4 item 4).

## Target paths
* `schemas/manifest.v1.json` (or repository-standard manifest schema filename —
  record choice) — published schema (Appendix A)
* `backend/apps/projects/` — manifest renderer + `GET /projects/{pid}/manifest`
* `backend/tests/` — renderer + schema-validation + no-secrets tests
* `schemas/` / `backend/` — OpenAPI snapshot updated with the endpoint
* WP changelog entry

## Acceptance criteria
- [ ] A manifest schema file is published under `schemas/` and matches the Section
  10.3 contract key-for-key (nothing required beyond it; Section 20.5 traceability
  against FR-PRJ-03).
- [ ] `GET /projects/{pid}/manifest` returns a document that passes validation against
  the published schema (WP-1.3 acceptance).
- [ ] Rendered values come from the plan's sources: `auto_branch_prefix` from policy
  (G-09/Section 7.2 default `feat/{PID}-`), `orchestrator_api` from Section 9.10
  settings, `audit_required_default` from policy.
- [ ] A test asserts the output contains only the allowlisted Section 10.3 keys —
  no secrets possible (FR-SEC-04; Section 10.3 "safe to commit").
- [ ] Endpoint is Owner-only; catalog codes only for failures
  (Section 20.4 item 5).
- [ ] OpenAPI snapshot updated (item 4); tests/lint green (item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/test_manifest.py` asserting: every generated manifest for a
fresh and a customized project validates against `schemas/` manifest schema; key set
equals the Section 10.3 allowlist; `auto_branch_prefix` reflects the policy value; the
endpoint requires Owner authentication.

## Attachments
* [Section 10.3 — Manifest discovery and binding (wire contract)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — REST API surface (manifest endpoint)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19.1 — WP-1.3 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The schema filename and the `$schema` URL host (`https://orchestrator.local/...` in
  the example) are placeholders in the plan — pick the repository-local schema
  reference for validation, keep the example's URL as-is in generated documents only
  if WP-2.2 expects it, and record the decision; mismatch here breaks bridge
  validation (WP-2.2 acceptance).
* `orchestrator_api` differs between local Compose and tunnel deployments (Section
  15) — it must come from configuration (Section 9.10), never be baked into code
  (NFR-06: env-only configuration).
