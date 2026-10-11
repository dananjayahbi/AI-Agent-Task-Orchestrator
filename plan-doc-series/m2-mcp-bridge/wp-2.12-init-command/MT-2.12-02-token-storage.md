# MT-2.12-02 — Store the Agent Token in User-Level Config

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.12-02 |
| Title | Store the agent token in user-level config |
| Parent WP | WP-2.12 — Init command (Milestone M2) |
| Requirements | FR-MCP-08, FR-SEC-04 (secrets never in repo-tracked config), FR-SEC-01 |
| Priority | M |
| Dependencies | MT-2.12-01 (manifest written first), MT-2.1-02 (config schema/format), MT-2.2-03 (reader contract: env over file) |
| Parent sections | 10.11 (init duty 2), 10.3 (step 3 — never from manifest), 12.2 (token auth), 19.1 (WP-2.12 second slice), 20.4, 20.5 |

## Context
FR-MCP-08's second duty: init "stores the agent's token in user-level config."
Section 10.11 repeats it; Section 10.3 step 3 is the complementary read rule the
bridge already implements (MT-2.2-03: environment **or** user-level config, never the
manifest). FR-SEC-04 is the invariant this task exists to protect: the token must
never land in a repo-tracked file — the manifest at the repo root is exactly the file
an uninitiated user might paste it into, so init provides the safe destination
instead. Section 12.2 fixes the credential family (PAT-style bearer token; rotation
policy notes 90 days — storage must support straightforward replacement). The file
format and path were fixed by MT-2.1-02's read side; this task is the write side of
that same contract: one file, one key, permissions-restricted, overwritable on
re-init, never echoed to the terminal.

## Inputs / Prerequisites
* MT-2.1-02 — the user-level config file's path/format/key table (single contract;
  this writer must produce exactly what that reader accepts).
* MT-2.12-01 — init sequence: manifest first, then token storage (FR-MCP-08 duty
  order).
* MT-2.2-03 — the reader's precedence (env still wins at runtime; this file is the
  fallback) and its expectation of an init-produced file.
* Parent plan Section 12.2 — bearer token handling, rotation; Section 10.11 — init's
  storage duty; FR-SEC-04 — never repo-tracked.
* Parent plan Section 17 / FR-SEC-01 — no secret in logs; MT-2.1-03 redaction.

## Scope (in)
* Token input handling in init: take the token from an interactive prompt (hidden
  input — never argv, which leaks via process lists and shell history) or from an
  environment variable the user already exports (CI/headless init); never prompt-
  echo, never print the value back.
* Writing it to the user-level config file at the path/format MT-2.1-02 fixed, under
  the dedicated token key — outside the repository tree, with owner-only file
  permissions where the platform supports it (`0600` POSIX; user-profile location on
  Windows — the expectation MT-2.2-03's risk note paired with this task).
* Merge semantics: update the token key without destroying other keys already in the
  file (re-init must not wipe unrelated config); create the file with a minimal
  structure if absent.
* Verification short of decoding: non-empty, trimmed, plausible bearer shape
  (Section 12.2) — real validation is the self-test's job (MT-2.12-03) and the
  backend's (FR-SEC-01).
* Round-trip proof: what this writes, MT-2.2-03's loader reads (cross-test in the
  bridge suite); file path asserted to be outside the repo (guard against a
  misconfigured "user config" that points inside the working tree).
* No-secrets discipline: the value never appears in init's stdout, structured logs
  (MT-2.1-03), or exception messages; tests assert with a fixture token; the file
  itself is git-ignored by location (outside the repo), and a repo-scan assertion
  confirms no token-shaped content was written under the working tree
  (Section 20.4 item 3).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Reading the token at runtime — MT-2.2-03 (cross round-trip test only here).
* Writing the manifest — MT-2.12-01; self-test connectivity — MT-2.12-03.
* Token issuance, rotation UI, revocation — backend (Section 12.2's 90-day policy is
  server-side); this task only makes replacement (re-init) clean.
* Keychain/credential-manager integration (OS secure storage) — the plan says
  "user-level config" (Section 10.11), not an OS vault; do not add one (raise
  `OQ-15+` if a security review demands it later).
* OIDC device/browser flows — WP-1.3 (init stores the token it is given; an OIDC
  future may change what "token" means — flag, do not build).

## Target paths
* `bridge/` init command module — token-storage step (MT-2.12-01's command file or
  an adjacent init substep, keeping duties separated)
* `bridge/` config module — shared path/key definitions from MT-2.1-02 (writer and
  reader import the same constants)
* `bridge/tests/` (write/merge/permissions/path/redaction tests; round-trip with
  MT-2.2-03's loader)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] Init stores the agent token in the user-level config file — FR-MCP-08 second
  duty verbatim; Section 10.11 (WP-2.12 second slice).
- [ ] The file lives outside the repository; a test asserts the resolved path is not
  under the repo root and that no token-shaped content exists anywhere in the
  working tree after init (FR-SEC-04; Section 20.4 item 3).
- [ ] The value is never echoed to the terminal, argv, stdout or logs (Section 12.2
  bearer hygiene; MT-2.1-03) — fixture-token non-leak assertions.
- [ ] Owner-only permissions applied where supported; re-init updates only the token
  key, preserving other config keys (merge test).
- [ ] Round-trip: MT-2.2-03's loader reads this file with env-var override still
  winning (Section 10.3 step 3 precedence intact).
- [ ] Tests, lint and type check green in CI (item 2); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_init_token_storage.py -v` — write
creates file outside repo with correct permissions, merge preserves keys, hidden
prompt path, redaction, loader round-trip with precedence; `uv run --directory bridge
ruff check .` green.

## Attachments
* [FR-MCP-08 — Init command duties](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-SEC-04 — Secrets never repo-tracked](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Token authentication](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Path resolution for "user-level config" must not depend on the cwd (init may run
  inside the repo) — anchor to the user profile/config dir; a cwd-relative path
  would put the secret in the repo and violate FR-SEC-04 by construction; test from
  a repo subdirectory explicitly.
* Hidden interactive prompts do not translate to all terminals/CI — provide the
  env-var input path (documented in the init output) so headless init works without
  falling back to argv.
* Windows permission semantics differ from `0600`; apply the platform-appropriate
  restriction and record what was done in the changelog rather than claiming POSIX
  guarantees everywhere.
