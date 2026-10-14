# WP-2.8 — MCP prompts: changelog

Short notes per parent plan Section 20.4, item 7 — one entry per micro-task of WP-2.8.
All four MTs completed 2026-10-14 in order; the Section 10.7 prompt set now lists and
renders through `prompts/list`/`prompts/get` while workflows keep working from tools
alone (NFR-08, ADR-011 — the tool surface is byte-identical with or without prompts).

## 2026-10-14 — MT-2.8-01: Prompt `orchestrator:start_work`

* `bridge/src/orchestrator_bridge/prompts/` package seeded: `start_work.py` owns the
  name (`orchestrator:start_work` exactly), the client-facing description and the
  guidance text; `__init__.py` holds the `PromptSpec` registry + `build_prompts()`
  seam (mirrors the tools' `registration.build_tools` pattern — one seam, so the
  inspector check stays honest).
* Text walks the five Section 10.7 steps in plan order: orient
  (`get_project_context`), list (`get_available_tasks`), claim (`claim_task`),
  create/switch to the branch **using the name claim_task returns** (G-09 single
  derivation — `git_helper.branch` docstring's three-way agreement), then
  `get_task_details`/`read_task_attachment` as needed. Stop-and-reorient on
  `LEASE_EXPIRED`/`TASK_STATE_CONFLICT` (Section 11.1 step 7) and the rules-block
  pointer are included; claim errors named are the Section 9.2 codes only.
* **Pure enhancement** (RISK-01): the text opens "Optional guidance … the same
  workflow is available from the tool descriptions and the claim response" — no step
  reads as a capability only the prompt provides (ADR-011; Wave-6 exit).
* No prompt arguments (the plan defines none — MT-2.8-01 risk note): the renderer is
  a zero-argument callable; `test_every_prompt_has_a_description_and_no_arguments`
  pins that against drift.
* `server.create_server` registers prompts only when a bound runtime exists — the
  WP-2.1 "empty skeleton" contract survives (`test_unbound_server_advertises_no_prompts`).
* Tests (`tests/test_prompts.py`): listing order/name pin, per-step chain order,
  vocabulary discipline (every snake-case tool-like token ∈ the Section 10.5 tool set
  or the documented field set; every SCREAMING_SNAKE token ∈ the Section 9.2 error
  catalog — Section 20.4 item 5 / 20.5), ADR-011 tool-surface identity.

## 2026-10-14 — MT-2.8-02: Prompt `orchestrator:checkpoint`

* `prompts/checkpoint.py`: the two Section 10.7 behaviors in order — **commit current
  work first, then** `log_task_checkpoint` with honest message/percentage, honoring
  the returned `next_checkpoint_due` hint (RISK-02; WP-2.6's hint is the prompt's
  anchor).
* Lease semantics restated by pointer, never invented (Section 8.6): extension only
  while the caller owns the lease, the hard-cap submit-or-release guidance matches
  the tool's own `next_action`, and `LEASE_EXPIRED` → stop and re-orient, "never
  attempt to resurrect a lost lease" (Section 11.1 step 7). No promise of extension
  beyond `lease_max_total_minutes` (MT-2.8-02 risk note).
* Three-channel alignment (RISK-02): rule 5 of the rules block, the tool description
  and this prompt carry the same cadence discipline — each names the others.

## 2026-10-14 — MT-2.8-03: Prompt `orchestrator:submit_for_audit`

* `prompts/submit_for_audit.py`: the three Section 10.7 behaviors in order — run
  verification with **real exit codes**, concise `execution_summary`, then
  `submit_task_resolution` with the assigned `git_branch`, the `commit_sha` and an
  **honest** risk flag (`requires_human_attention` + `risk_justification` — Section
  11.1 step 6; the over-optimistic-prompt risk from the MT is addressed by wording
  that names uncertainty/incompleteness as flag-worthy).
* Outcome states stay the backend's decision: the text names T7 `to_be_audited` and
  T8 `in_human_review` as what the submission "lands in per the Policy Engine" — it
  promises no particular state (Section 8.2 wording re-checked; Section 9.4).
* `LEASE_EXPIRED`/`TASK_STATE_CONFLICT` → stop and re-orient (Section 11.1 step 7).

## 2026-10-14 — MT-2.8-04: Prompt `orchestrator:audit`

* `prompts/audit.py`: the five Section 10.7 steps mirroring Section 11.2 — claim with
  `role auditor`, read-only branch inspection (never modify — Sections 11.2/10.8),
  full test+lint matrix with real exit codes, diff review against acceptance
  criteria and `target_scope`, then `submit_audit_verdict`.
* **Independence per Section 12.1** (MT-2.8-04 scope): the text states the auditor
  session must differ from the coder's and names `AUDITOR_SAME_AS_CODER` as the
  backend's rejection.
* Verdict vocabulary is exactly the Section 10.5 schema (`pass`/`flag_risk`/`fail`,
  confidence 1–5, evidence entries) — nothing invented (Section 20.5).
* "The verdict is input, not the outcome: the backend's Policy Engine decides"
  (Section 9.4; ADR-009) — auditors are never told they perform T13/T14 directly
  (MT-2.8-04 risk note).
* The Section 10.5 contract was the stable anchor while WP-3.5 shipped alongside;
  the implemented `submit_audit_verdict` schema matches the rendered text field for
  field (re-verified against `tools/schemas.py`).

## Inspector evidence (Section 19 WP-2.8 acceptance)

* Wire-level (CI-pinned, authoritative per MT-2.8-01 risk note):
  `tests/test_prompts.py::test_stdio_process_lists_and_renders_all_four_prompts`
  drives a **real stdio subprocess** through JSON-RPC `initialize` →
  `prompts/list` → four `prompts/get` calls and asserts: the exact four names in
  Section 10.7 order, descriptions verbatim from the specs, no arguments, and the
  exact registered text rendering on every `prompts/get`.
* Recorded MCP-inspector CLI run (manual, Node tooling — same posture as WP-2.4/2.7).
  The 2026 inspector CLI dropped the old `--server-command/--server-args` flags and
  its positional-target forwarding loses server args on Windows, so the recorded run
  uses **config-file mode**, which passes command/args/env explicitly
  (`bridge/scripts/inspector_evidence.py` boots the loopback stub backend, writes the
  temp manifest + token + config, and runs the three probes):

  ```text
  uv run --directory bridge python scripts/inspector_evidence.py
  # -> internally: npx -y @modelcontextprotocol/inspector@latest --cli
  #      --config <tmp>/inspector-config.json --server orchestrator-bridge
  #      --protocol-era auto --format json --method prompts/list |
  #      prompts/get --prompt-name orchestrator:start_work | tools/list
  ```

  Observed output (2026-10-14):

  ```text
  === prompts/list ===
  prompt: orchestrator:start_work — Guides the agent: orient, list tasks, claim, ...
  prompt: orchestrator:checkpoint — Commit current work and log a checkpoint ...
  prompt: orchestrator:submit_for_audit — Run verification, summarize, submit ...
  prompt: orchestrator:audit — Auditor workflow: claim, check out branch, run ...

  === prompts/get ===
  description: Guides the agent: orient, list tasks, claim, ...
  message[0] (1259 chars): Optional guidance for starting coder work in the bound
  project (Section 10.7). ... 1. Orient: call get_project_context ... 2. List work:
  call get_available_tasks (role coder) ... 3. Claim it: call claim_task ... 4.
  Create or switch to the task branch ... 5. Read the requirements ...

  === tools/list ===
  10 tools: get_available_tasks, get_task_details, claim_task,
  read_task_attachment, log_task_checkpoint, submit_task_resolution,
  release_task, submit_audit_verdict, create_draft_task, get_project_context
  ```

  (The CI stdio test above is the automated equivalent; the npx run is the
  environment-sensitive manual confirmation. The 10th tool, `create_draft_task`,
  landed with WP-3.8-02 in the same batch — the tool-surface-identity test covers
  the current count either way.)
* ADR-011 exit: `test_registered_tool_names_still_advertised_with_prompts_present`
  asserts the tool list is unchanged (`CORE_TOOL_NAMES`, still 9) whether prompts are
  advertised or not — workflows work from tools alone.

## Tooling

* `ruff check` / `ruff format --check` / `mypy --strict` clean; `pytest -q` green
  (10 new prompt tests; full suite below in the batch close-out).
