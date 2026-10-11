# MT-2.1-02 — Implement Configuration Layering (Env over User-Level File)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.1-02 |
| Title | Implement configuration layering (env over user-level file) |
| Parent WP | WP-2.1 — Bridge package skeleton (Milestone M2) |
| Requirements | FR-MCP-01; FR-SEC-04 (no secrets in repo files), NFR-10 (operability) |
| Priority | M |
| Dependencies | MT-2.1-01 (package layout), MT-0.5-01 (env var conventions), WP-2.12 (user-level config writer — later consumer) |
| Parent sections | 10.1 (config responsibility), 10.10 (resilience), 19.1 (WP-2.1 second slice), 20.4, 20.5; OQ-07 relevance |

## Context
WP-2.1's second slice is "config" and its acceptance adds "independent configuration."
The plan's layering model is stated in Section 10.3/10.11 language: the agent token
comes "from environment or user-level config" (never the manifest — FR-SEC-04), and
Section 10.10's resilience text assumes a backend base URL that can differ per
environment. Section 9.10 settings-style discipline and MT-0.5-01's env conventions
(`ORCHESTRATOR_*` naming, `.env.example`) are the Foundations-era contracts this
config module must honor. The precedence order — environment variables override the
user-level config file — follows directly from the plan's wording ("from environment
**or** user-level config") plus the operational need for CI/container overrides
(12-factor style); document that reading in the changelog since the plan does not spell
the arrow of precedence out in one sentence. Config must be resolved once at startup,
validated against known keys, and never logged (NFR-10; FR-SEC-04).

## Inputs / Prerequisites
* MT-2.1-01 — `bridge/` package and the `config` placeholder module to fill.
* MT-0.5-01 — env var naming conventions and `.env.example` discipline (apply the
  same conventions to the bridge's example file).
* Parent plan Section 10.1 — config as a bridge responsibility (input to every other
  component: transport, credentials, manifest path overrides).
* Parent plan Section 10.11 / FR-MCP-08 — the user-level config file that
  `orchestrator init` will write (WP-2.12); this task defines its read side and
  schema, WP-2.12 the write side.
* Parent plan FR-SEC-04 — "secrets never appear in repo-tracked config files."
* Parent plan Section 9.10 — settings groups pattern (backend's), as the style
  precedent for grouped, documented settings.

## Scope (in)
* A single config loader for the bridge resolving, in precedence order: environment
  variables → user-level config file (a per-user path under the user's config
  directory, never inside the repo or the manifest) → built-in defaults; merged view
  exposed as one settings object read by all other modules.
* Keys the plan's bridge needs at minimum: backend base URL, agent token (FR-SEC-04:
  environment or user-level file only), manifest path override for tests, log level/
  format, and any timeout values Section 10.10 requires — every key documented with
  its plan source in the example file.
* Validation at startup: unknown keys, missing required keys for the selected run
  mode, and malformed values fail fast with a clear message (operability, NFR-10) —
  never a stack trace through user config parsing.
* Secrets hygiene: the loader never prints or logs secret values (token redacted);
  `.env.example`/example user-config shipped with placeholder values only
  (Section 20.4 item 3; FR-SEC-04).
* Tests: precedence (env beats file beats default), file-absent defaults, malformed
  file, missing required key, redaction; changelog note (item 7) recording the
  precedence reading.

## Out of scope
* Writing the user-level file — that is `orchestrator init` (WP-2.12 / MT-2.12-02);
  this task reads it and defines the schema it will write to.
* Manifest discovery and its path resolution — WP-2.2 (a `--manifest`/override here
  is only a passthrough hook for tests).
* Credential loading from vault/KMS or any new secret store — not in the plan;
  environment or user-level config only (Section 10.3).
* Backend-side `Settings` (Section 9.10) — different package, already owned by
  WP-0.5/MT-0.5-01.
* Structured logging itself — MT-2.1-03 (config supplies its level/format keys).

## Target paths
* `bridge/` config module (the Section 10.1 config placeholder from MT-2.1-01)
* `bridge/` example config / `.env.example`-style file (MT-0.5-01 conventions)
* `bridge/tests/` (precedence, validation, redaction tests)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Environment variables override the user-level config file, which overrides
  built-in defaults — one merged settings object (documented precedence; Section
  10.3/10.11 "environment or user-level config").
- [ ] The agent token is accepted only from environment or user-level file — never
  from the manifest or repo-tracked files (FR-SEC-04) — and is redacted in all
  logging/output.
- [ ] Missing/malformed configuration fails fast at startup with a clear, non-secret-
  revealing message (NFR-10; Section 10.10 operability).
- [ ] Example config files contain placeholders only, no environment-specific paths
  or secrets (Section 20.4 item 3).
- [ ] Tests, lint and type check green in CI (item 2); changelog note documenting the
  precedence order and key list added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_config.py -v` — precedence chain,
file-absent defaults, malformed file, missing required key, token redaction;
`uv run --directory bridge ruff check .` green.

## Attachments
* [Section 10.1 — Bridge responsibilities (config)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-SEC-04 — No secrets in repo-tracked config](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.11 — Init and packaging (user-level config)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not fix the user-level config file's exact path or format (JSON vs
  TOML) in one place — Section 10.11/MT-2.12-02 will write it; choose one format
  now, state it in the changelog, and treat a later plan statement as authoritative
  if it conflicts (raise `OQ-15+` if genuinely ambiguous).
* Precedence "env over file" is an interpretation of "environment or user-level
  config" — if the plan's later sections imply the reverse for any key (e.g. init
  writing env explicitly), flag it rather than special-casing keys ad hoc.
* Do not let the loader auto-discover a `.env` from the current working directory —
  bridge entry points may run from arbitrary project directories (Section 10.3's
  upward walk is for the manifest, not config); cwd-relative secrets loading would
  violate the FR-SEC-04 intent.
