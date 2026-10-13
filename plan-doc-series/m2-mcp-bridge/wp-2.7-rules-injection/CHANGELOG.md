# WP-2.7 — Rules injection: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.7.
All four MTs completed 2026-10-13 in order; the Section 10.6 rules block now
reaches agents through every gap G-08 channel the bridge owns — initialize-time
server `instructions`, the mandatory `rules` block of every `claim_task`
response, and `get_project_context`'s `rules` field — all rendered from one
source, plus per-client fallback snippets for clients that ignore server
instructions. The WP-2.4 forward note on `claim_task` ("merged in at
MT-2.7-03") is resolved.

## 2026-10-13 — MT-2.7-01: Coder and auditor rules templates per Section 10.6

* `bridge/src/orchestrator_bridge/rules.py` — `CODER_RULES`: the eight
  Section 10.6 standard rules, numbered, in plan order, transcribed without
  rewording the obligations (Section 20.5 traceability — tests pin each
  rule's operative phrase and count, so a dropped/reordered/reworded rule
  fails CI). `AUDITOR_RULES`: the four auditor obligations the plan names
  (full test+lint matrix, verify each criterion, never modify the branch,
  honest confidence) — "the rules *instead* cover", so no coder rule leaks
  into an auditor render (pinned).
* Parameterized slots are exactly the three the plan names: the assigned
  branch (G-09 derivation), the task's test command, and rule 5's N
  **derived from the lease** — `checkpoint_interval_minutes()` = lease
  window ÷ 3 (floor 1 minute), never hardcoded (RISK-02 mitigation);
  `lease_minutes()` parses the Section 8.6 lease record and falls back to
  the policy/Section 7.2 default on missing/garbage input rather than
  fabricating a cadence. Connect-time channels render the generic
  phrasings ("the branch returned by claim_task", "the task's test
  command") since no task exists yet — role is chosen at claim time
  (MT-2.7-03 risk note).
* One shared `render_rules()` so MT-2.7-02/03/04 cannot fork the content.
  Tests (`tests/test_rules_templates.py`, 12): rule count/order/obligation
  phrases for both roles, slot substitution, lease-derived interval math,
  fallback parsing, "no invented rules" (every rendered numbered line
  traces to a template modulo slot substitution), no env-specific paths or
  secret-shaped content in templates (Section 20.4 item 3).

## 2026-10-13 — MT-2.7-02: Project-specific rules merging from `system_prompt_rules`

* `render_rules(..., project_rules=...)` appends the owner's
  `system_prompt_rules` (from the Section 10.3 step-5 cached context) after
  the standard/auditor rules under a `Project rules:` header — the Section
 10.6 ordering, asserted by index tests; missing/empty/whitespace-only
  rules render the standard block with **no empty-section artifact**.
* Normalization is deliberately minimal (MT risk note): control characters
  (C0/C1/DEL, except newline/tab) stripped, length capped at
  `PROJECT_RULES_MAX_CHARS = 8000` (documented default; visible truncation
  marker). The owner's wording is otherwise preserved **verbatim** — no
  paraphrase, no interpretation; braces/template syntax survive literally
  (rules are data, never interpolated — tested).
* Consistency guarantee: `render_session_rules()` (connect-time: policy
  lease → checkpoint interval) and the claim-time `render_rules()` share
  one path; tests assert byte-identical output for equal inputs and that
  the cached-context refresh (fetch-on-refresh, no invalidation invented)
  surfaces an Owner edit exactly once then serves the cache.
  **Propagation OQ (per MT risk note):** sessions opened before an Owner
  edit keep the old text until reconnect; the plan specifies no live
  invalidation — raise an OQ if prompt propagation becomes a requirement.
  Tests (`tests/test_rules_merge.py`, 12).

## 2026-10-13 — MT-2.7-03: Rules delivered through initialize instructions and claim responses

* **Initialize channel (G-08 #1):** `server.create_server` now passes
  `instructions=` to the MCP SDK server when a bound runtime exists —
  the merged coder block (generic slots, checkpoint interval from the
  cached policy's `lease_duration_minutes`, project rules appended). The
  unbound skeleton server still advertises no instructions. Wired through
  the real stdio handshake: the subprocess test asserts the
  `initialize` response's `instructions` carry rule 8 plus the stub
  project's appended rule, on the wire.
* **Claim channel (G-08 #3, mandatory):** `claim_task`'s response
  `rules` field is now `{role, text}` where `text` is the bridge's own
  Section 10.6 render for the claiming role — coder or auditor per the
  tool's `role` input — parameterized with **this** claim's G-09 branch,
  the task's own `test_command` from the returned row, and the checkpoint
  interval derived from **this** lease (a re-claim with a shorter lease
  re-delivers a tighter cadence — tested). Project rules come from the
  session cache; a cache miss fetches through the client and a failure
  surfaces translated, never a crash. The backend's wire `rules_block`
  remains shape-checked (Section 9.3 step 6 / OpenAPI contract) but the
  bridge's templates are the delivery source of truth (Section 10.6 is a
  bridge-owned block; MT-2.4-04's forward note resolved — the old
  `{standard_rules, project_rules}` pass-through shape is replaced).
* **`get_project_context` channel:** the `rules` field now returns the
  merged Section 10.6 block (was: the raw `system_prompt_rules` string) —
  byte-identical to the initialize instructions for the same session
  inputs (asserted). Payload keys unchanged.
* Tool descriptions already name the rules block (WP-2.4 `claim_task`
  description: "Returns the lease record, the Section 10.6 rules block…");
  G-08 channel #2 is textually satisfied and rides the templates.
  Tests (`tests/test_rules_delivery.py`, 9; plus updated claim/context/
  live-suite assertions and the handshake instructions proof).

## 2026-10-13 — MT-2.7-04: Per-client fallback instruction snippets (G-08)

* `docs/agent-guides/rules-fallback-snippets.md` — **one snippet per
  Section 10.9 matrix row** (Claude Code CLI, VS Code Copilot / IDE,
  OpenCode, Aider, DeepSeek-based harness, Custom agent), each carrying
  all eight coder rules **generated from the render source**
  (`rules.render_client_snippet`) — no hand-retyped copy (Section 20.5).
  Text-only clients (Aider, DeepSeek harness per the matrix's "likely /
  expected text-only" rows) get the rule-6 OCR/untrusted-text variant
  note.
* Each snippet and the file header state the fallback posture explicitly:
  tools + the claim `rules` block remain authoritative and sufficient
  (NFR-08); project rules ride the claim channel, with a note on
  per-project instruction files. No client config syntax is asserted as
  verified — the guide says verification and setup pages are WP-2.11's
  (per the MT risk note; "To verify" status stays visible).
* Generation seam: `bridge/scripts/generate_rules_snippets.py` renders
  the whole guide; `tests/test_rules_snippets.py` (7) pins the committed
  file to that generation byte-for-byte (drift in either direction fails
  CI), plus per-snippet rule presence, matrix completeness, text-only
  variants, and the fallback/NFR-08 wording.

## 2026-10-13 — WP-2.7 complete

* Acceptance met: rules appear in the claim response and in initialize
  instructions (wire-proven by the stdio handshake test); project rules
  appended correctly after the standard rules in every channel (ordering
  asserted); auditor claims get the auditor obligations; snippets exist
  for every matrix row, generated from the single source.
* Targeted battery green: `uv run --directory bridge pytest tests/ -k
  "rules"` → 35 passed; the affected tool suites (claim, context,
  core-tools, release, entrypoints handshake) green.
* Inspector evidence (assignment requirement): the stdio handshake test
  asserts `tools/list` still advertises exactly the five WP-2.4 tools and
  the `initialize` response now carries the composed rules in
  `instructions`; a claim over the tool boundary returns the composed
  `{role, text}` block (see `tests/test_rules_delivery.py`).
* Deferred/forward: prompt-based workflows (WP-2.8); per-client
  verification and setup pages (WP-2.11 — owns the matrix fill and
  publishes the snippets in its guides); auditor claim role wiring on the
  wire (backend WP-3.3 — the tool `role` input already selects the
  template client-side).

## 2026-10-13 — Verification finisher note

* Bridge finisher re-verified all four MT acceptance sets against code and tests (no gaps found in WP-2.7): final battery green — `ruff check .` / `ruff format --check .` / `mypy .` clean, `pytest -q` → **415 passed, 6 skipped** (5 live-backend opt-in, 1 POSIX-permission-on-Windows) — and a fresh documented inspector CLI run (`npx -y @modelcontextprotocol/inspector@latest --cli … --method tools/list` against a loopback stub) records exactly the five core tools, with `--method initialize` showing the eight-rule §10.6 coder block + appended project rules in `instructions`; the one mid-run `test_openapi_contract` failure was the backend agent's attachment-sample regen landing mid-flight and passed on re-run (attachment-only, no rules/init entries involved).
