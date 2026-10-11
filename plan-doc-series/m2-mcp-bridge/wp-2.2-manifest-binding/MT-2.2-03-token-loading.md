# MT-2.2-03 — Load the Agent Token from Environment or User-Level Config

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.2-03 |
| Title | Load the agent token from environment or user-level config |
| Parent WP | WP-2.2 — Manifest discovery and session binding (Milestone M2) |
| Requirements | FR-SEC-01 (token verification), FR-SEC-04 (secrets never in repo-tracked config), FR-MCP-06 |
| Priority | M |
| Dependencies | MT-2.2-01 (manifest found), MT-2.2-02 (manifest valid), MT-2.1-02 (config layering loader), WP-2.12 (writes the user config this reads) |
| Parent sections | 10.3 (step 3), 10.11 (init stores token), 12.2 (authentication), 19.1 (WP-2.2 third slice), 23 (ADR-002/ADR-005), 20.4, 20.5 |

## Context
Section 10.3 step 3 is precise: "Load agent token from environment or user-level
config (never from the manifest)." FR-SEC-04 locks the negative half — "secrets never
appear in repo-tracked config files" — and the manifest is repo-tracked by
construction (MT-2.12-01 writes it into the repo). Section 10.11 gives the positive
half: init "stores the agent's token in user-level config." Section 12.2 fixes the
credential family: PAT-style **token auth** is the shipped M1 path, verified
server-side (FR-SEC-01: backend verifies signature/expiry/revocation), with OIDC as
the flag-gated alternative (WP-1.3). WP-2.2's third slice is "token loading" — the
bridge-side read and hand-off; verification is the backend's job when the session
opens (MT-2.2-04). MT-2.1-02 already defined the layered loader; this task wires the
token key through it with the plan's exact sourcing rules and redaction guarantees.

## Inputs / Prerequisites
* MT-2.1-02 — config layering (env → user-level file → defaults) and redaction;
  this task defines the token key's semantics on top of that loader.
* MT-2.2-01 / MT-2.2-02 — a discovered, valid manifest precedes token loading
  (Section 10.3 ordering: step 3 after steps 1–2).
* WP-2.12 / MT-2.12-02 — writes the user-level config file; its format is the one
  this reader consumes (coordinate via MT-2.1-02's schema note).
* Parent plan Section 12.2 — bearer token on `Authorization` header, PAT/short-lived
  tokens, OIDC behind flag; Section 10.3 step 3 and Section 10.11 for sourcing.
* FR-SEC-04 — never in repo-tracked files; FR-SEC-01 — server-side verification.

## Scope (in)
* Token resolution through MT-2.1-02's precedence: environment variable first (CI/
  containers/secret-injected sessions), then the user-level config file written by
  init; no other sources (explicitly not: manifest, repo `.env`, command-line
  arguments — argv leaks via process lists; not in the plan anyway).
* Missing-token behavior: fail fast before session open with a clear message that
  does not echo the token and points at the two legitimate sources (env var name and
  the init command) — logged through MT-2.1-03, value never logged (FR-SEC-04 spirit;
  Section 17 no-secrets rule applies to the bridge too).
* Load-time shape checks only (non-empty, plausible header form per Section 12.2's
  bearer usage) — no signature/expiry/revocation validation locally: that is
  FR-SEC-01's backend verification, exercised when MT-2.2-04 opens the session
  (do not reimplement verification in the bridge).
* Ensure the token is held in the config/settings object (single access point from
  MT-2.1-02) rather than copied into module globals — one redaction boundary.
* Tests: env wins over file; file-only succeeds; neither → error message with both
  sourcing hints and no token echo; manifest-embedded token field ignored even if a
  bad manifest smuggles one (assert it is never read — belt-and-braces for FR-SEC-04);
  redaction on all log paths; changelog note (item 7).

## Out of scope
* Backend token verification (signature/expiry/revocation), session cookies —
  FR-SEC-01 server side; MT-1.2-01 owns the backend half.
* Token issuance/rotation UI and API — backend M1/M3 WPs (Section 12.2 rotation
  policy mentions 90-day rotation — the bridge does not implement rotation).
* OIDC flows — WP-1.3 (flag `AUTH_MODE=oidc`; the bridge passes tokens it is given,
  so no change anticipated — flag this if Section 10.4 capability work later disagrees).
* Writing the user-level config — MT-2.12-02 (this task reads; that task writes).
* Authorization/permission checks — Section 12.3 (backend, MT-1.2-07).

## Target paths
* `bridge/` config/token key in the MT-2.1-02 loader (no new module unless the seam
  warrants it)
* `bridge/tests/` (sourcing precedence, missing-token message, manifest-smuggled
  token ignored, redaction)
* WP changelog entry (Section 20.4 item 7)

## Acceptance criteria
- [ ] The token is read only from environment or user-level config, in that
  precedence — Section 10.3 step 3 verbatim (FR-SEC-04).
- [ ] A token present in the manifest (or any repo-tracked file) is never read or
  used — tested by planting one in a fixture manifest (FR-SEC-04; "never from the
  manifest").
- [ ] Missing token fails fast before session open with a non-leaking message
  naming the env var and `orchestrator init` (Section 10.3 ordering; Section 10.11).
- [ ] The token never appears in logs, exceptions or test output (MT-2.1-03
  redaction; Section 17).
- [ ] Local verification is not reimplemented — shape check only; real verification
  is left to the backend (FR-SEC-01; Section 12.2) — asserted by absence of
  crypto/decode logic in the loader tests.
- [ ] Tests, lint and type check green in CI (Section 20.4 items 1–2); no secrets
  committed (item 3); changelog note added (item 7).

## Test command
`uv run --directory bridge pytest tests/test_token_loading.py -v` — env-over-file,
file-only, missing-token message, planted manifest token ignored, redaction;
`uv run --directory bridge ruff check .` green.

## Attachments
* [Section 10.3 — Token loading (step 3)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [FR-SEC-04 — Secrets never in repo-tracked config](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.2 — Authentication (token auth)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The env-var name for the token is a contract between docs, init (MT-2.12-02) and
  this loader — fix one name in MT-2.1-02's key table and reference it from
  `agent-guides/`; a mismatch here is the most likely integration failure with
  WP-2.12.
* "User-level config" file permissions are not specified by the plan — on POSIX,
  write it `0600` when init creates it (MT-2.12-02's concern; note the expectation
  here so the pair lands consistently); on Windows, restrict to the user profile
  path. Record any deviation in the changelog.
* Section 12.2's `Authorization` header and MT-0.5-03's no-extra-headers rule: the
  bridge must send exactly `Authorization: Bearer <token>` — ensure the hand-off to
  MT-2.2-04's session open does not invent additional auth headers.
