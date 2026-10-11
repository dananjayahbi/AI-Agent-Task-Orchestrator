# MT-2.6-02 — Implement branch and commit-sha verification before submission

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-02 |
| Title | Implement branch and commit-sha verification before submission |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | FR-MCP-07 |
| Priority | M |
| Dependencies | WP-2.10 (local Git helper: repo identity, branch/sha confirmation, branch naming), WP-2.2 (manifest binding for repo identity) |
| Parent sections | 10.5, 10.8, 11.1, 19 (WP-2.6), 20.4, 20.5 |

## Context
Section 10.5: `submit_task_resolution` takes `task_id`, `git_branch`,
`commit_sha`, `execution_summary`, `requires_human_attention`, `risk_justification`,
and "bridge verifies branch exists and sha matches" before capturing and uploading
the evidence. WP-2.6's acceptance: "submission with a non-existent sha is rejected
with a clear error". Section 10.8 gives the local Git helper the confirming
capability, and ADR-007 keeps this verification host-side — the backend never
accesses repositories. Rules block items 1 and 4 (assigned branch, commit before
submit) are what the agent is held to.

## Inputs / Prerequisites
* Parent plan Section 10.5 — submission inputs and "bridge verifies branch exists and
  sha matches".
* Parent plan Section 10.8 — Git helper capabilities (verify repository identity and
  clean state; confirm the branch and sha submitted by the agent; read operations
  plus branch creation only).
* WP-2.10 — implemented helper: repo-state checks (MT-2.10-01), branch naming
  (MT-2.10-02), merge-base diff (MT-2.10-03).
* WP-2.2 — manifest binding that establishes which repository this session is bound
  to.
* Section 9.2 catalog — the code chosen for rejection must come from it.

## Scope (in)
* Pre-upload verification in the submission flow: the session's repository identity
  matches the manifest binding; `git_branch` exists locally and is the branch derived
  for this task (manifest prefix + task id, WP-2.10 branch naming); `commit_sha`
  resolves to a real commit reachable on that branch (a non-existent sha or a sha
  from another branch/ repository fails).
* A clear rejection: structured tool error with a catalog code, human-readable
  hint and a next action telling the agent what to fix (commit on the assigned
  branch, then resubmit) — Section 10.5 tool rules; never a silent acceptance.
* Clean-state expectation per Section 10.8 consumed from WP-2.10's repo-state checks
  rather than re-implemented.
* Tests: nonexistent sha rejected with a clear error; sha on the wrong branch
  rejected; valid branch+sha accepted and handed to patch capture; wrong-repo
  rejected.

## Out of scope
* The Git helper implementation itself — WP-2.10.
* Merge-base patch capture, stats and file list — MT-2.6-03.
* The upload, outcome states and idempotency — MT-2.6-04.
* Backend-side resolution storage — WP-3.2.
* Choosing branch names — WP-2.10 (MT-2.10-02).

## Target paths
* `bridge/` — submission flow: branch/sha verification step
* `bridge/tests/` — verification tests
* WP changelog entry

## Acceptance criteria
- [ ] Submission with a non-existent `commit_sha` is rejected with a clear error
  containing a hint and next action (WP-2.6 acceptance, Section 10.5).
- [ ] A `commit_sha` not reachable on the submitted `git_branch`, or a branch that is
  not the task's assigned branch, is rejected the same way.
- [ ] Repository identity is verified against the manifest binding before any Git
  work (Section 10.8, WP-2.2).
- [ ] Verification is host-side only — the backend still never accesses repositories
  (ADR-007).
- [ ] Only catalog error codes are used (Section 20.4 item 5); lint/type/tests green
  (item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k submit_verify -q` — assert nonexistent-sha rejection
with hint/next action, wrong-branch and wrong-repo rejection, and acceptance of a
valid branch+sha feeding patch capture; then the full bridge suite stays green.

## Attachments
* [Section 10.8 — Local Git helper](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The plan does not name a dedicated catalog code for a bad branch/sha — select from
  Section 9.2 (the natural fit is `VALIDATION_ERROR`), record the choice in the
  changelog, and never invent a new code (Section 20.4 item 5).
* Verification runs against the developer's working tree, which other processes could
  touch between check and capture — chain verification and patch capture atomically
  in the flow, or re-verify at capture time.
* Submodules/shallow clones may hide commits; document the supported repository shape
  rather than loosening the check.
