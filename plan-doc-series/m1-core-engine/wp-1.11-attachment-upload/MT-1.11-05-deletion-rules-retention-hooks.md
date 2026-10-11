# MT-1.11-05 — Implement Deletion Rules and Retention Hooks

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.11-05 |
| Title | Implement deletion rules and retention hooks |
| Parent WP | WP-1.11 — Attachment storage and upload API (Milestone M1) |
| Requirements | FR-ATT-01 |
| Priority | M |
| Dependencies | MT-1.11-04 (descriptor listing) |
| Parent sections | 9.2, 9.5, 12.4, 16.3, 9.9, 19.1 (WP-1.11), OQ-10, 20.4, 20.5 |

## Context
Section 9.2 exposes `DELETE /attachments/{id}`. Section 9.5: originals are retained,
derived data is re-creatable. Section 12.4: attachments are retained until the task
is archived plus a configurable grace period. Section 16.3: deletion is by retention
job, never by user action on completed tasks. Section 9.9: the daily retention
cleanup job applies retention to orphaned files. OQ-10 default: attachments until
archive plus 30 days. This task encodes those rules at the API and provides the
retention hook the background job will call.

## Inputs / Prerequisites
* MT-1.11-04 — descriptor listing and attachment records.
* MT-1.11-01 — storage abstraction delete operation (content-addressed keys; deleting
  a key must not break a de-duplicated reference — see risk notes).
* Parent plan Sections 9.2, 9.5, 12.4, 16.3, 9.9 — the rule sources.
* WP-1.4 soft-archive semantics for tasks (completed/archived states).
* Retention cleanup job scheduling belongs to WP-1.7/beat (Section 9.9) — this task
  provides the hook it will call.

## Scope (in)
* `DELETE /attachments/{id}` implementing the API rules: Owner only; rejected on
  completed/archived tasks (per Section 16.3 the user never hard-deletes there —
  response explains the retention path); allowed before completion, marking the
  record deleted and removing the stored object when no other record references the
  same content key.
* A retention hook function callable by the daily retention cleanup job (Section
  9.9): given an archived task older than the grace period (configurable, OQ-10
  default 30 days), removes attachment records and orphaned stored objects.
* Derived data (chunks, OCR text, summaries) is treated as re-creatable (Section 9.5):
  it may be dropped even when an original is retained.
* Tests: deletion rules per task state, de-duplicated key reference counting, hook
  behavior on archived vs. active tasks, grace-period boundary.

## Out of scope
* Scheduling the retention job — WP-1.7 (beat schedule, Section 9.9).
* Choosing final retention periods — OQ-10 (decision recorded in the plan; M6
  applies it). Use the documented default, do not re-decide.
* Backup/restore interactions — Section 16.5 / WP-6.2.
* Patch/checkpoint retention — separate artifacts (OQ-10), their own WPs.

## Target paths
* `backend/apps/attachments/views.py` (DELETE route)
* `backend/apps/attachments/retention.py` (hook)
* `backend/tests/attachments/test_deletion_rules.py`
* WP changelog entry

## Acceptance criteria
- [ ] `DELETE /attachments/{id}` enforces Section 16.3: no user hard-delete of
  completed/archived task attachments; allowed earlier with the record marked
  deleted (Section 9.2 endpoint present and rule-tested).
- [ ] Deleting an attachment never removes stored bytes still referenced by another
  de-duplicated record (content-key reference safety).
- [ ] The retention hook applies the archive-plus-grace-period rule (Section 12.4,
  OQ-10 default 30 days, configurable) and cleans orphaned objects (Section 9.9).
- [ ] Derived data removal is permitted independently of original retention
  (Section 9.5 "derived data re-creatable").
- [ ] Canonical error codes only (Section 20.4 item 5); no environment-specific paths
  (item 3); changelog note added (item 7).

## Test command
`pytest backend/tests/attachments/test_deletion_rules.py -v` — rule matrix by task
state, shared-key reference counting, and grace-period boundary of the retention
hook.

## Attachments
* [Section 9.5 — Attachment processing (retention intent)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 12.4 — Data protection (retention periods)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.3 — Storage (deletion by retention job)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Content-addressed de-duplication plus deletion is the sharp edge: naive delete of
  the key corrupts other attachments sharing the bytes. Reference counting (or an
  equivalent orphan check) must be reviewed before merge.
* Section 9.2's `DELETE` vs. Section 16.3's "never by user action on completed
  tasks" is a tension this task resolves conservatively (reject on
  completed/archived); if product wants hard delete anywhere, that is a parent-plan
  amendment, not an implementation choice — raise a new OQ (`OQ-15+`) if requested.
