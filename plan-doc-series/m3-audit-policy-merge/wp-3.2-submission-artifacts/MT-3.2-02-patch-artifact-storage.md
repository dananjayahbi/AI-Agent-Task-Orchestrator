# MT-3.2-02 — Implement patch artifact storage with the 5 MB size cap

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-3.2-02 |
| Title | Implement patch artifact storage with the 5 MB size cap |
| Parent WP | WP-3.2 — Submission handling and artifacts (Milestone M3) |
| Requirements | FR-AUD-01, FR-TSK-03 |
| Priority | M |
| Dependencies | MT-3.2-01 (resolution rows exist); WP-2.6 (bridge uploads the patch) |
| Parent sections | 7.2 (Task Artifact), 9.7 (patch artifacts), 9.2 (patch endpoint), 19 (WP-3.2), 20.4, 20.5 |

## Context
Section 9.7 fixes the patch-artifact contract: at submission the bridge uploads a
unified patch (task branch vs. default-branch merge-base), the backend stores it, and a
5 MB size cap (default) applies — oversize patches keep stats and file list only, with a
"diff too large" marker in the viewers. Section 7.2 defines the Task Artifact entity
(`kind` = `patch`, optional `output_tail`) with `storage_key`, `size_bytes`, `sha256`.
Stored patches are the authoritative input for scope checking (MT-3.2-04), stats
(MT-3.2-03), Policy Engine rules (WP-3.4) and the web/mobile diff viewers (WP-4.7,
WP-5.8).

## Inputs / Prerequisites
* MT-3.2-01 — the resolution the artifact attaches to (`resolution_id`).
* Parent plan Section 7.2 — Task Artifact fields.
* Parent plan Section 9.7 — upload semantics, 5 MB default cap, oversize degraded path.
* Parent plan Section 9.2 — `GET /resolutions/{id}/patch` endpoint.
* Parent plan Section 9.10 — storage backend is configuration (local volume or
  S3-compatible); storage must go through the configured backend, not a hard-coded path.

## Scope (in)
* Task Artifact model per Section 7.2 (`id`, `resolution_id`, `kind`, `storage_key`,
  `size_bytes`, `sha256`) with `kind` = `patch` (and room for optional `output_tail`).
* Artifact receive path on submission: store the uploaded unified patch under a
  content-derived storage key, compute `sha256` and `size_bytes`.
* Enforce the 5 MB default size cap (Section 9.7): patches at or under the cap are
  stored fully; oversize patches are NOT rejected — store stats and file list only
  (no full patch body) and set the "diff too large" marker consumed by viewers.
* `GET /resolutions/{id}/patch` serving the stored patch, or the marker for oversize
  artifacts (Section 9.2 endpoint).
* Retention-safe storage through the configured backend (Section 9.10); no secrets or
  environment-specific paths committed (Section 20.4 item 3).
* Unit tests: normal store/serve round-trip, sha256 correctness, exact cap boundary,
  oversize degraded path.
* Add a WP changelog note.

## Out of scope
* Parsing stats/changed files out of the patch — MT-3.2-03 (runs after storage).
* The "diff too large" rendering in web/mobile viewers — WP-4.7 / WP-5.8.
* Retention cleanup of old patches — Section 9.9 job (later hardening WPs).
* Bridge-side merge-base computation — WP-2.6 (MT-2.6-03).
* Making the cap configurable beyond the Section 9.7 default — configuration work
  belongs to settings; keep the default exactly 5 MB.

## Target paths
* `backend/apps/tasks/` (Task Artifact model, artifact receive/serve handlers)
* `backend/` migrations (artifact table)
* `backend/tests/` (artifact storage tests incl. cap boundary)
* WP changelog entry

## Acceptance criteria
- [ ] Task Artifact rows match the Section 7.2 field set; `sha256` and `size_bytes`
  computed server-side from the stored bytes (Section 20.5 traceability).
- [ ] Patches up to the 5 MB default cap store fully; an oversize patch stores stats
  and file list only with the Section 9.7 "diff too large" marker — it is a degraded
  path, not an error (FR-AUD-01 support; Section 19 WP-3.2 "artifact storage").
- [ ] `GET /resolutions/{id}/patch` returns the stored patch or the marker for oversize
  artifacts (Section 9.2).
- [ ] No new error codes introduced for the oversize path (Section 20.4 item 5);
  storage failures map to existing catalog codes.
- [ ] Storage uses the configured backend with no committed environment-specific paths
  (Section 9.10; Section 20.4 item 3).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run `pytest backend/tests -k patch_artifacts -q` and confirm: round-trip store/serve
with matching sha256, exact 5 MB boundary behavior, oversize patch taking the
stats-and-file-list-only path with the marker, and marker served by the patch GET;
then `pytest backend/tests -q` stays green.

## Attachments
* [Section 9.7 — Patch artifacts](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Task Artifact entity](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Patch endpoint](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Oversize patches lose the body the Policy Engine's R5 added-line pattern scan
  (Section 9.4 note: engine recomputes R2–R6 from the stored patch) depends on — the
  plan does not say how R5 degrades when no patch body exists; coordinate with
  MT-3.4-03 and raise an OQ-xx if a rule cannot be evaluated.
* Cap semantics at exactly 5 MB (inclusive vs exclusive) are unspecified — pick the
  natural inclusive reading, document it in the tests, and do not change Section 9.7's
  default silently.
