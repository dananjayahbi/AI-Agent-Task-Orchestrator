# MT-2.6-03 — Implement merge-base patch capture with stats and changed-file list

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-03 |
| Title | Implement merge-base patch capture with stats and changed-file list |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | FR-MCP-07 |
| Priority | M |
| Dependencies | MT-2.6-02 (branch/sha verified), WP-2.10 (merge-base diff and changed-file computation), WP-3.2 (backend patch storage) |
| Parent sections | 10.8, 9.7, 9.4, 19 (WP-2.6), 20.4, 20.5 |

## Context
FR-MCP-07 requires collecting Git evidence (branch, sha, patch, changed files) locally
during submission. Section 9.7: "At submission the bridge uploads a unified patch
(branch vs. default branch merge-base). The backend stores it, computes authoritative
stats and the changed-file list from it, and uses these for the Policy Engine. Size
cap (default 5 MB); oversize patches store stats and file list only, with a 'diff too
large' marker in the viewers." Section 10.8 gives the helper the merge-base diff, stats
and changed-file list capabilities (read-only operations). The Policy Engine (Section
9.4) recomputes R2–R6 from this stored patch, so honest capture is the foundation of
audit.

## Inputs / Prerequisites
* Parent plan Section 9.7 — patch artifact contract and 5 MB cap behavior.
* Parent plan Section 10.8 — helper capabilities (merge-base diff, stats,
  changed-file list; never pushes, force-resets or deletes).
* Parent plan Section 9.4 — Policy Engine depends on the stored patch (R2–R6).
* MT-2.6-02 — verified branch and sha (capture runs only after verification passes).
* WP-2.10 (MT-2.10-03) — merge-base diff implementation this flow consumes.
* WP-3.2 — backend endpoint that stores the patch and computes authoritative
  stats/file list from it.

## Scope (in)
* Capture step in the submission flow: compute the merge-base of the submitted branch
  and the project's default branch, then produce the unified patch (diff from
  merge-base to the submitted sha) plus the local stats and changed-file list.
* Respect the 5 MB size cap (default, configurable) per Section 9.7: for oversize
  patches, still produce stats and the changed-file list and mark the patch
  "diff too large" so the backend stores stats/file list only; the marker flows to
  viewers.
* Determinism: capture is keyed to the verified `commit_sha` — no working-tree state
  leaks into the patch.
* Use only the helper's read operations (plus branch creation already granted) —
  never push, force-reset or delete (Section 10.8).
* Tests: feature branch produces a merge-base patch; empty diff (no changes)
  handled; oversize diff yields stats + file list + marker and no full patch body;
  capture matches the verified sha even if the working tree changes afterwards.

## Out of scope
* Branch/sha verification — MT-2.6-02.
* Uploading, outcome states and idempotency — MT-2.6-04.
* Backend storage, authoritative stat recomputation, viewer marker rendering —
  WP-3.2, WP-4.7.
* Secret-like pattern detection in added lines (R5 input) — WP-2.10 (MT-2.10-04).
* Policy Engine evaluation of the patch — WP-3.4.

## Target paths
* `bridge/` — submission flow: patch capture step
* `bridge/tests/` — patch capture tests
* WP changelog entry

## Acceptance criteria
- [ ] The bridge captures a unified patch computed from the branch-vs-default-branch
  merge-base at the verified sha, with stats and a changed-file list (FR-MCP-07,
  Section 9.7).
- [ ] Oversize patches (over the 5 MB default cap) produce stats and the
  changed-file list plus the "diff too large" marker instead of a full patch body
  (Section 9.7).
- [ ] Capture is deterministic against the verified sha — a dirty or moved working
  tree cannot change what was captured.
- [ ] The helper performs read operations only (plus branch creation); nothing is
  pushed, reset or deleted (Section 10.8).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`uv run pytest bridge/tests/ -k patch_capture -q` — assert merge-base-based unified
diff correctness against a fixture repository, empty-diff handling, oversize
stats+list+marker behavior, and sha-determinism; then the full bridge suite stays
green.

## Attachments
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Wrong merge-base (e.g. capturing against the wrong default branch) silently
  poisons R2 scope checks and diff stats — pin the default branch from the manifest
  and test with a fixture where the branch has a non-trivial merge-base.
* Who enforces the 5 MB cap must match WP-3.2 exactly (bridge prepares, backend
  stores per Section 9.7) — coordinate the boundary test so neither side assumes the
  other truncates.
* Merge-base commits fetched shallowly may be missing; fail with a clear error rather
  than computing a wrong diff.
