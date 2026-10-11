# MT-2.10-03 — Implement merge-base diff computation with stats and changed files

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.10-03 |
| Title | Implement merge-base diff computation with stats and changed files |
| Parent WP | WP-2.10 — Local Git helper (Milestone M2) |
| Requirements | FR-MCP-07 (Git evidence: patch, changed files) |
| Priority | M |
| Dependencies | MT-2.10-01 (repo identity and guard), MT-2.10-02 (branch derivation); WP-1.6/WP-3.4 context for downstream consumers |
| Parent sections | 9.7, 10.8, 19 (WP-2.10), 20.4, 20.5 |

## Context
Section 10.8 lists "compute merge-base diff, stats and changed-file list" among the
helper's capabilities, and Section 9.7 fixes what submission uploads: a unified patch
of the branch versus the default branch merge-base, with the backend computing
authoritative stats from it (5 MB cap; oversize patches store stats and file list
only). WP-2.6's submission flow (MT-2.6-03) and the Policy Engine's R2/R3/R4/R5/R6
rules all consume this evidence — R2 (scope), R3 (critical paths), R4 (migrations)
and R6 (diff size) need the changed-file list and stats this slice produces. Getting
the merge-base semantics right here is what makes every downstream rule honest.

## Inputs / Prerequisites
* Parent plan Section 10.8 — merge-base diff, stats and changed-file list capability.
* Parent plan Section 9.7 — patch artifact definition (branch vs default-branch
  merge-base), 5 MB cap behavior at upload time.
* Parent plan Section 9.4 — Policy Engine rules R2-R6 consuming changed files/stats
  from the stored patch (backend recomputes; bridge supplies the patch).
* Manifest `default_branch` (Section 10.3) — the merge-base target.
* MT-2.10-01/02 — identity, guard and branch derivation.

## Scope (in)
* Merge-base resolution: compute the merge-base of the task branch and the manifest's
  `default_branch`, failing with a structured error when either ref is missing or
  unrelated histories are detected (hint: fetch/update default branch or report the
  situation).
* Unified diff generation from the merge-base to the task branch HEAD, returned as a
  single patch payload plus a size in bytes so callers can apply the Section 9.7
  5 MB cap decision (oversize handling itself is the upload path's job, WP-2.6).
* Stats computation: insertions, deletions, and per-file changed list (paths as
  repository-relative, forward-slash normalized — Section 12.3's traversal rules and
  cross-platform consistency).
* Structured result shape: merge-base sha, head sha, patch, stats, changed files —
  the evidence bundle Section 9.7/10.8 describe, consumed by WP-2.6 and, indirectly,
  Policy Engine inputs.
* Unit tests on fixture repositories: clean feature branch vs default, no-op branch
  (empty diff), merge-base ahead/behind cases, missing default branch, large-diff
  size reporting, path normalization.

## Out of scope
* Uploading the patch and backend-side authoritative recomputation — WP-2.6/WP-3.4
  (Section 9.7: the backend computes authoritative stats from the stored patch).
* Branch/sha verification before submission — WP-2.6 (MT-2.6-02).
* Applying/merging/rebasing anything — Section 10.8 forbids destructive operations.
* Secret scanning of the diff — MT-2.10-04.
* The 5 MB cap enforcement point — the submission upload path (WP-2.6), which reads
  the size this task reports.

## Target paths
* `bridge/src/` (diff/stats functions in the Git helper)
* `bridge/tests/` (diff tests with fixture repositories)
* WP changelog entry

## Acceptance criteria
- [ ] Diff is computed against the merge-base of task branch and manifest
  `default_branch` — not a naive branch-vs-HEAD or worktree diff — asserted by a
  fixture where they differ (Section 9.7, 10.8).
- [ ] Result includes merge-base sha, head sha, unified patch, insertions/deletions
  and the changed-file list with repository-relative, forward-slash paths.
- [ ] Missing/unrelated default branch produces a structured error with a catalog
  code and actionable hint (Section 10.5 error rules; Section 20.4 item 5).
- [ ] Patch size in bytes is reported for the Section 9.7 cap decision; the helper
  itself does not truncate (truncation is defined at upload).
- [ ] Only read-only Git operations used (MT-2.10-01 guard; Section 10.8).
- [ ] Tests pass in CI (Section 20.4 item 2); changelog note added (item 7).

## Test command
Run the diff tests, e.g. `uv run pytest bridge/tests/ -k merge_base_diff`; assert
merge-base semantics, stats accuracy, changed-file normalization, and the
missing-default-branch error path.

## Attachments
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.8 — Local Git helper](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Computing against the wrong base silently poisons every Policy Engine rule fed by
  the patch (R2-R6) — the divergent-base fixture test is the essential guard.
* Renamed/deleted files and binary files change stats semantics; define behavior
  from Git's own output and document it rather than approximating.
