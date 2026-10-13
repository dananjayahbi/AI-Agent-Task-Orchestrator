# WP-2.12 — Init command: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.12.
All four MTs completed 2026-10-13 in order; `orchestrator init` now bootstraps a
repository end-to-end (FR-MCP-08 verbatim): schema-valid manifest at the Git root,
agent token in user-level config, a real session-open self-test, then per-client
MCP registration snippets. The recorded real run (below) completes in **1.11
seconds** — far inside WP-2.12's "under 2 minutes" acceptance.

## 2026-10-13 — MT-2.12-01: Manifest write (`orchestrator init` duty 1)

* `bridge/src/orchestrator_bridge/init/manifest_write.py` —
  `find_git_root()` (MT-2.2-01's ceiling rule: `.git` directory *or*
  worktree pointer file; no Git → clear error, "at the repository root"
  is never guessed); `fetch_project_inputs()` reads the **project row and
  policy row** through the existing catalog endpoints
  (`GET /projects/{pid}`, `GET /projects/{pid}/policy` — agent-readable
  for the token's own project per §9.2), so the id, name, default branch,
  branch prefix and audit default all come from the backend (§19.3: no
  client-side derivation; the MT's risk note about a missing
  project-create call for anonymous init is answered by *select-and-
  verify* with the agent credential the user already has — project
  creation stays in the web UI where §12.2 puts Owner powers);
  `compose_manifest()` projects exactly the shared schema's allowlisted
  keys (FR-SEC-04: no secret or absolute path can fit — asserted), with
  the §10.3 example's `$schema` URL and `agent_hints` defaults, mirroring
  the backend renderer's `{PID}` prefix resolution (G-09);
  `write_manifest()` runs every candidate through MT-2.2-02's validator
  *before* a byte lands (writer/validator drift fails here, not at the
  next startup).
* Overwrite safety: an existing `orchestrator.json` is never clobbered —
  decline (or a non-TTY stdin) fails with the `--force` remedy; `--force`
  bypasses the question; an equal document short-circuits to "unchanged"
  (no write, no prompt — re-init is safe).
* No timestamps: the schema (FR-SEC-04 allowlist, `additionalProperties:
  false`) has no created-timestamp key, so the manifest stays hermetic and
  byte-comparable across re-runs (the MT's non-hermetic risk note does
  not apply to the frozen field set).
* CLI: `orchestrator` console script (`bridge/pyproject.toml`) + `python
  -m orchestrator_bridge.init` module entry, `init` subcommand with
  `--project-id`, `--api`, `--force`, `--self-test`. Failure posture
  mirrors the run-mode entry points: one scrubbed stderr line, no
  traceback, exit 1; stdout stays reserved for the flow's own output.
* Tests (`tests/test_init_manifest.py`, 22): root write from a
  subdirectory with a discovery+validator round-trip, worktree-pointer
  root, overwrite/force/unchanged matrix, secret scan of the written
  file, backend-row projection, wrong-project/unreachable/shape-drift/
  malformed-id failures, and the orchestrated `run_init` flow (duties
  chained over the send seam) plus `main()` rendering and the standalone
  `--self-test` exit codes against the loopback stub.

## 2026-10-13 — MT-2.12-02: Agent token storage (duty 2)

* `bridge/src/orchestrator_bridge/init/token_store.py` — the write side
  of MT-2.1-02's contract: `acquire_token()` takes the token from
  `ORCHESTRATOR_AGENT_TOKEN` (headless/CI) or a **hidden** `getpass`
  prompt (never argv, never echoed, header-safety checked on both paths
  without revealing the value); `store_agent_token()` merges the
  `agent_token` key into the user-level TOML by line edit — other keys
  *and comments* survive a re-init, duplicates collapse, and the merged
  text is re-parsed (tomllib) plus checked with the loader's own key
  validation before writing, so init can neither persist nor leave a file
  the loader rejects.
* FR-SEC-04 hard guard: a config path resolving *inside* the repository
  is refused outright (a cwd-relative "user config" would leak the secret
  by construction); the loader round-trip (what this writes,
  MT-2.2-03's loader reads) and env-over-file precedence are cross-tested.
* Permissions: POSIX gets `0600` on the file and `0700` on the
  `…/orchestrator/` directory after a successful write. **Windows has no
  POSIX permission bits** — recorded here as the MT requires: the file
  lands in `%APPDATA%\orchestrator\bridge.toml`, whose user-profile
  directory is ACL-protected by default; the code applies no chmod there
  rather than claiming POSIX guarantees.
* Tests (`tests/test_init_token_storage.py`, 13): write outside the repo
  + loader round-trip, merge preserving keys/comments, re-init replacing
  only the token, repo-internal refusal, POSIX permission bits (skipped
  on Windows with the reason), profile-anchored default path (APPDATA/
  XDG, never cwd), env-over-prompt preference, hidden-prompt trim, empty/
  unsafe/cancelled input, headless failure naming the env var, and
  no-echo assertions on success and error paths.

## 2026-10-13 — MT-2.12-03: Connectivity self-test (duty 3)

* `bridge/src/orchestrator_bridge/init/selftest.py` — three checks in
  FR-MCP-08 order: (1) manifest present + schema-valid (MT-2.2-01/02
  reused, honoring the `ORCHESTRATOR_BRIDGE_MANIFEST_PATH` override);
  (2) token resolvable via MT-2.2-03's loader — the verdict names the
  *source* (environment or user config path), never the value;
  (3) the real probe: MT-2.2-04's `open_session` (credential + binding +
  reachability in one call — not an unauthenticated ping) then
  `close_session`, so no session is left dangling.
* Verdicts: one PASS/FAIL/SKIP line per check with remedy text; a failed
  prerequisite makes the probe SKIP with the earlier remedy (duty order
  enforced, tested); exit code is the caller's (`main` returns 1 on any
  non-pass). A wrong-project token lands on MT-2.2-05's
  `ProjectMismatchError` message verbatim (same clear-message path).
* Bounded retries ride the WP-2.3 transport policy (§10.10: fixed
  attempts, backoff — pinned at exactly the configured budget in tests);
  structured `selftest_check` log records accompany every verdict
  (MT-2.1-03); the run is read-only (manifest/config bytes unchanged,
  asserted) and secret-free (fixture-token non-leak asserted).
* Tests (`tests/test_init_selftest.py`, 13): all-pass naming the token
  source and closing the probe, the three failure verdicts with remedies
  and skip chaining, the 403 mismatch reuse, bounded retry count, token
  value absent from every verdict, config-file source named, no mutation,
  structured log records, manifest-override honoring.

## 2026-10-13 — MT-2.12-04: Per-client MCP registration snippets (duty 4)

* `bridge/src/orchestrator_bridge/init/snippets.py` — after a *passing*
  self-test only (safe ordering per the MT risk note; the flow exits
  non-zero before snippets otherwise), init prints one registration block
  per §10.9 matrix client — the same client list WP-2.7's fallback
  snippets use (`rules.CLIENT_MATRIX`, §19.6 single source, drift-guarded
  at render time). Each block: the stdio launch resolved for *this*
  machine (`orchestrator-bridge-stdio` on PATH, else `python -m
  orchestrator_bridge --mode stdio`), the token-source reference
  (user config path or `ORCHESTRATOR_AGENT_TOKEN` — never a value), and
  a verification pointer (`orchestrator init --self-test` or the bridge
  under MCP inspector).
* Secret-free generated text (FR-SEC-04 applies to snippets too) and
  machine-marked: output says "terminal output only, never commit these
  paths". **No `agent-guides/` file was written**: Appendix A's guide
  list shows every client page as "planned" (content lands in WP-2.11
  with the conformance script), and no client-setup guide exists to
  update in place — terminal output only, per the MT's rule.
* Config-shape honesty: the widely documented `mcpServers` block is shown
  for clients whose registration shape the plan can assert today; Aider
  (§10.9: "STDIO or wrapper") gets the bare wrapper command line rather
  than an invented config key; every block is flagged "verified in
  WP-2.11" (Section 10.9 is titled "to be verified in WP-2.11"). HTTP/SSE
  snippets are deferred to WP-2.10/2.11 (the VS Code row's note says so).
* Tests (`tests/test_init_snippets.py`, 10): all six matrix clients
  covered, stdio entry in every block, fixture-token absence, config
  source + self-test + inspector pointers, Aider wrapper form, ephemeral
  marking, PATH-preference and module fallback of `bridge_command()`,
  and render-touches-no-files.

## 2026-10-13 — WP-2.12 complete

* Acceptance — "new repo usable via init in under 2 minutes": **recorded
  real run, 1.11 s wall time** (`bridge/scripts/timed_init_flow.py`,
  re-runnable): fresh `git init` repo, `python -m orchestrator_bridge.init
  init --project-id PID00007 --api <live uvicorn>/api/v1` from a
  subdirectory, token from the environment, user config redirected to an
  isolated profile. Real backend (migrations + seed + uvicorn over
  `wp16-pg`): manifest written at the root, `bridge.toml` stored,
  all three self-test checks PASS (session opened *and* ended over the
  socket — the backend log shows `agent.session_started`/`ended`), six
  snippets printed, exit 0, token absent from stdout+stderr. Backend
  boot (7.3 s) reported separately — not part of the init flow.
* `orchestrator init --self-test` is the standalone re-verification the
  snippets and agent guides point at; it opens and closes a real session
  (no dangling rows; the backend's staleness handling remains the
  backstop for crashed bridges).
* Recorded boundaries: the self-test proves **binding**, not the tool
  surface (tool-level verification is WP-2.8/2.11 territory, per the MT's
  out-of-scope list); HTTP-mode client snippets are WP-2.10/2.11; project
  *creation* stays in the web UI (Owner powers, §12.2) — init selects and
  verifies with the agent token, which is what makes a two-prompt
  (or fully flagged) sub-minute flow possible.
* Gate follow-up carried from WP-2.4 (unchanged, backend-owned): agent
  read access to `GET /projects/{pid}` is required by both init's
  verification and the self-test probe. The bridge-side live tests record
  it answering `ROLE_NOT_PERMITTED` on the older backend; this WP's
  recorded run (current `main`) answered 200 for the seeded agent token,
  i.e. the read cell is active there. Both init paths map a
  `ROLE_NOT_PERMITTED` answer to a clear remedy either way; no backend
  patch was made from the bridge side.
* Final battery (2026-10-13): `ruff check .`, `ruff format --check .`,
  `mypy .`, `pytest -q` — all green (412 passed, 6 skipped; skips are the
  POSIX-permission and live-backend gates). Inspector-equivalent wire
  evidence lives in `tests/test_entrypoints.py`: the stdio handshake
  advertises the five core tools with the §10.6 rules in `initialize`
  instructions, and `tools/call claim_task` over the real JSON-RPC wire
  returns the composed rules block (G-09 branch, 45÷3=15-minute cadence,
  task test command, appended project rules; the backend's wire
  `rules_block` is shape-checked but not delivered).

## 2026-10-13 — Verification finisher note

* Bridge finisher re-verified all four MT acceptance sets, adding the two
  missing AC tests (`test_full_flow_keeps_the_token_out_of_the_working_tree`
  — MT-2.12-02's post-init working-tree token scan — and
  `test_cli_withholds_snippets_when_the_probe_fails` — MT-2.12-04's
  safe-ordering gate): final battery green — `ruff check .` /
  `ruff format --check .` / `mypy .` clean, `pytest -q` → **415 passed, 6
  skipped** (5 live-backend opt-in, 1 POSIX-permission-on-Windows); the
  timed flow record (1.11 s, `bridge/scripts/timed_init_flow.py`) stands
  for the "under 2 minutes" acceptance; documented inspector CLI run
  (`npx … --cli orchestrator-bridge-stdio.exe --method tools/list` against
  a loopback stub) records the five core tools with clean session
  open/end; one mid-run `test_openapi_contract` failure was the backend
  agent's attachment-sample regen landing mid-flight (attachment-only —
  `endpoints.py`/contract samples untouched by this WP) and passed on
  re-run; no secret-shaped content or machine paths in the changed files.
