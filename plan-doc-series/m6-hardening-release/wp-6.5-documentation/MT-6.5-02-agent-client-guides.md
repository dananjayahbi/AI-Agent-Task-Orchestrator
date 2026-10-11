# MT-6.5-02 — Write the Per-Client Agent Guides

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.5-02 |
| Title | Write the per-client agent guides |
| Parent WP | WP-6.5 — Documentation and runbooks (Milestone M6) |
| Requirements | all (per Section 19 WP-6.5; primarily NFR-08, FR-MCP) |
| Priority | M |
| Dependencies | MT-2.11-01 … MT-2.11-07 (conformance results, matrix, setup pages and custom-agent template), MT-2.12-04 (init config snippets), MT-6.5-01 (operator guide to link from) |
| Parent sections | 10.3 (manifest discovery), 10.9 (compatibility matrix), 10.11 (packaging/init), 11.1 (coder workflow), 19 (WP-6.5 deliverables, acceptance), 20.4, 20.5; 21 (RISK-01); Appendix A |

## Context
Section 19 (WP-6.5) counts "agent client guides" among its deliverables, and the WP
acceptance requires that someone following only the docs can "connect an agent". The
per-client setup pages already exist from WP-2.11 (MT-2.11-07 published
configuration/instruction-snippet/known-limits pages plus the compatibility matrix
and a custom-agent template, under `docs/agent-guides/`). This slice's job is to
finish those pages into operator-ready guides: each supported client walked from
zero to a claimed task — manifest placement, token/config, first connect, first
claim — grounded strictly in the verified matrix facts, so RISK-01 (client
differences) is answered by documentation rather than trial and error.

## Inputs / Prerequisites
* `docs/agent-guides/` — MT-2.11-07's setup pages, compatibility matrix
  (no "To verify" cells) and custom-agent template; MT-0.1-06's index README.
* Parent plan Section 10.9 — the client matrix (Claude Code CLI, VS Code Copilot,
  OpenCode, Aider, DeepSeek-based harness, Custom agent); names stay verbatim.
* Parent plan Section 10.3 — upward manifest discovery to the Git root, schema
  validation, mismatch aborts: the manifest chapter each guide must get right.
* Parent plan Section 10.11 / MT-2.12-04 — `init` command and its printed per-client
  config snippets, if landed; otherwise link Section 10.9 by pointer.
* Parent plan Section 11.1 — the coder workflow (orient → claim → checkpoint →
  submit) each guide ends with, so "connect an agent" means a real claimed task.
* MT-6.5-01 — the operator guide these guides hang off (bring-up assumed done).

## Scope (in)
* For each supported client in Section 10.9, write the end-to-end agent guide under
  `docs/agent-guides/`: prerequisites (stack running per MT-6.5-01, project
  onboarded), manifest creation/discovery (Section 10.3), obtaining and placing the
  project-scoped token (Section 12.2 — user-level config outside the repo, never in
  Git), client configuration (transport/registration from the MT-2.11 setup pages),
  first connection verification (orient/orientation call succeeds), and completing
  one claim → checkpoint → submit cycle (Section 11.1).
* Reuse and link MT-2.11-07's pages for configuration detail, instruction snippets
  and known limits — guides orchestrate the flow; they do not fork the facts
  (Section 20.5).
* Cover the text-only/vision capability note (Section 10.4) where it changes client
  setup, and the prompt-vs-tools framing (NFR-08, ADR-011): tools are the contract.
* Update `docs/agent-guides/README.md` index so every guide is one hop from the
  operator guide and from each other; the custom-agent template gets the same
  end-to-end framing for non-listed clients.
* Verify each guide by executing its steps against a live local stack (the "connect
  an agent" acceptance leg) and add a changelog note (Section 20.4 item 7).

## Out of scope
* Re-running conformance or changing matrix facts — MT-2.11-01 … 06 (the matrix is
  the contract; guides restate it).
* Editing the parent plan's Section 10.9 table — plan changes go through the plan
  owner (Section 0).
* The Section 17 "onboard a new agent client" runbook — MT-6.5-03 (it links here).
* Troubleshooting per failure mode — MT-6.5-04 (guides link, trees live there).
* Verifying clients beyond the Section 10.9 list — the custom template covers them
  by process (RISK-01 scope control).

## Target paths
* `docs/agent-guides/` — one end-to-end guide per supported client, custom-agent
  template updated
* `docs/agent-guides/README.md` — index updated with the guide links
* `docs/` — operator guide (MT-6.5-01) cross-link added
* WP changelog entry

## Acceptance criteria
- [ ] Every client named in Section 10.9 has a guide covering manifest, token/config,
  connect, and one full claim → checkpoint → submit cycle (Section 19 WP-6.5
  deliverable "agent client guides"; acceptance leg "connect an agent").
- [ ] Each guide's steps were executed against a live stack in order and worked as
  written (Section 20.4 item 1; Section 19 WP-6.5 acceptance).
- [ ] Guides link to MT-2.11-07's setup pages/matrix rather than restating config
  facts; client names appear verbatim as in Section 10.9 (NFR-08; RISK-01).
- [ ] Token handling matches Section 12.2: project-scoped, user-level config outside
  the repo, never committed (Section 20.4 item 3).
- [ ] The index README and MT-6.5-01 cross-link set is complete (Section 20.5).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
For one text-only and one vision-capable client from Section 10.9, follow the guide
verbatim on a running local stack and confirm a task reaches submitted state;
grep `docs/agent-guides/` for absolute host paths and secret-shaped strings (expected:
zero), and confirm every Section 10.9 client name appears as a guide link in the
README index.

## Attachments
* [Section 10.9 — Client compatibility matrix](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 11.1 — Coder workflow](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.5 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Guide/matrix drift is the standing risk (the same one MT-2.11-07 flagged): if a
  guide step and a matrix cell disagree, the matrix wins — re-verify and fix the
  guide, never "adjust" the matrix in documentation work.
* Not every client can be re-verified in this task's session — where a guide's
  execute-once check cannot run (client unavailable), mark the guide's verification
  status explicitly and log it rather than implying it ran (Section 20.4 item 1;
  RISK-01).
* Token-config instructions are the highest-risk documentation (RISK-14): one
  example showing a token inside the repo would teach the exact anti-pattern
  Section 12.2 forbids — use placeholders and user-level paths exclusively.
