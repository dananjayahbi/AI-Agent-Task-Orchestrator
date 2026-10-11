# MT-2.10-02 — Implement branch naming derivation (prefix + task index, G-09)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-02 |
| Title | Implement branch naming derivation (prefix + task index, G-09) |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07; gap G-09 (canonical branch naming) |
| Priority | M |
| Dependencies | MT-2.10-01 (repository identity), WP-2.2 (manifest with `auto_branch_prefix`) |
| Parent sections | 10.3 (manifest keys), 10.5 (`claim_task` branch name), 10.6 (rule 1), 19 (WP-2.10), 20.4, 20.5 |

## Context
Gap G-09 settles a spec conflict: the canonical branch name is the manifest's
`auto_branch_prefix` plus the task index part — for example `feat/PID00007-T004` —
with the manifest prefix winning over the spec's bare `feat/<task-id>` form and a
default prefix of `feat/{PID}-`. Section 10.6 rule 1 tells agents to work only on the
assigned (derived) branch, `claim_task` returns the branch name (Section 10.5), and
the `orchestrator:start_work` prompt has the agent create or switch to it
(Section 10.7). This slice is the single derivation function plus the branch
create-or-switch operation, all inside Section 10.8's read-plus-branch-creation
allowlist.

## Inputs / Prerequisites
* Parent plan gap G-09 — canonical rule with example `feat/PID00007-T004`.
* Parent plan Section 10.3 — manifest keys `auto_branch_prefix` (extended manifest)
  and `default_branch`; policy default `branch_prefix` of `feat/{PID}-`
  (Section on project policy fields).
* Parent plan Section 10.5 — `claim_task` returns the branch name; MT-2.4-04 is the
  consumer.
* MT-2.10-01 — identity checks and the invocation guard.
* Task id format from Section 9.2 examples (`PID00007-T004`) — the index part is the
  `-Txxxx` segment.

## Scope (in)
* A pure derivation function: given the manifest prefix (falling back to the
  documented default `feat/{PID}-` pattern when the key is absent) and a task id,
  produce the canonical branch name — prefix + task index part, exactly per G-09.
* Validation of inputs: reject task ids that do not parse to an index part and
  prefixes that would produce an invalid ref (structured error with hint — never
  silently "sanitize" into a different branch than G-09 specifies).
* Create-or-switch operation: if the branch exists, switch to it; if not, create it
  from the configured `default_branch` — the only mutating Git capability besides
  reads (Section 10.8), executed through the MT-2.10-01 guard.
* Clean-state precondition: refuse to switch/create on a dirty working tree with a
  clear structured error, so agent work is never mixed with pre-existing changes.
* Unit tests: derivation matrix (default prefix, manifest prefix, example from G-09
  producing `feat/PID00007-T004`), invalid inputs, create-new vs switch-existing,
  dirty-tree refusal.

## Out of scope
* Pushing, deleting, force operations — forbidden by Section 10.8, enforced by
  MT-2.10-01's guard.
* Submit-time branch/sha verification — WP-2.6 (MT-2.6-02).
* The `claim_task` response wiring — MT-2.4-04 calls this derivation (note the
  shared function as the contract).
* Merge-base diff — MT-2.10-03.
* Policy `branch_prefix` storage/backend — WP-1.3; this task consumes the manifest
  value.

## Target paths
* `bridge/src/` (branch naming/creation functions in the Git helper)
* `bridge/tests/` (derivation and creation tests with fixture repositories)
* WP changelog entry

## Acceptance criteria
- [ ] The G-09 example holds exactly: manifest prefix `feat/PID00007-` plus task
  `PID00007-T004` yields `feat/PID00007-T004` (Section 20.5 traceability).
- [ ] Manifest `auto_branch_prefix` always wins over defaults; absent key falls back
  to the documented `feat/{PID}-` default.
- [ ] Create-or-switch works for new and existing branches and refuses dirty trees
  with a structured error and hint (Section 10.8, Section 10.6 rule 1).
- [ ] Only reads and branch creation are used — the MT-2.10-01 guard is exercised;
  no push/reset/delete (WP-2.10 acceptance).
- [ ] Tests pass in CI on the dev platform; OS matrix covered by MT-2.10-06
  (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the branch derivation tests, e.g. `uv run pytest bridge/tests/ -k branch_naming`;
assert the G-09 example output, prefix precedence, create/switch behavior and
dirty-tree refusal.

## Attachments
* [Gap G-09 — Branch naming](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.8 — Local Git helper](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Branch names appear in the claim response, rules (rule 1) and submission evidence;
  three consumers must agree — the derivation function is the only source, and its
  output is what `claim_task` returns (per Section 10.5).
* Task ids containing unusual characters could yield invalid refs — reject with a
  structured error rather than inventing a transformation the plan does not define.
