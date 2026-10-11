# MT-4.5-03 — Implement acceptance-criteria and target-scope glob editors

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-4.5-03 |
| Title | Implement acceptance-criteria and target-scope glob editors |
| Parent WP | WP-4.5 — Task creation/edit modal and attachment uploader (Milestone M4) |
| Requirements | FR-WEB-03 |
| Priority | M |
| Dependencies | MT-4.5-01 (modal scaffold), WP-1.4 (task CRUD, glob validation rules) |
| Parent sections | 13.2, 12.3, 8.2 (T2), 19 (WP-4.5), 20.4, 20.5 |

## Context
Section 13.2's modal includes an "acceptance criteria list editor" and a
"target-scope editor with glob validation". These two fields carry most of a task's
contract: criteria are what the auditor verifies (Section 10.6 auditor rules,
Section 11.2 step 3) and the Policy Engine's context; `target_scope` globs are the
R2 scope rule's input (Section 9.4) and are "validated on creation" per Section 12.3
(path and scope enforcement). T2 (publish) requires "Required fields valid" —
including these.

## Inputs / Prerequisites
* Parent plan Section 13.2 — the two editors (verbatim).
* Parent plan Section 12.3 — `target_scope` globs validated on creation; payload
  paths normalized/rejected on escape (server side).
* Parent plan Section 9.4 — R2 Scope rule consumes `target_scope`.
* WP-1.4 — backend field rules and glob validation the client mirrors.
* MT-4.5-01 — modal scaffold; shared validation schemas (Section 13.3).

## Scope (in)
* Acceptance-criteria list editor: add, edit, remove ordered criteria; each criterion
  is one structured line/entry as WP-1.4 models it; empty list handled per backend
  rules (criteria are the audit checklist — enforce the backend's required/optional
  stance, do not invent one).
* Target-scope glob editor: add/remove glob patterns with **client-side glob
  validation** (syntax check mirroring WP-1.4's validator) plus inline feedback;
  clearly displays the current scope set since it bounds agent edits (RISK-04 overlap
  hints: scope globs are overlap hints — Section 21).
* Shared-schema validation integrated with the modal (Section 13.3); server
  `VALIDATION_ERROR` responses mapped to field-level messages, keeping the modal
  open for correction.
* Component tests: criteria add/edit/remove round trip; glob syntax acceptance and
  rejection with messages; server-rejection mapping; save→reload fidelity for both
  fields.

## Out of scope
* Markdown description — MT-4.5-02; dependencies — MT-4.5-04; other fields —
  MT-4.5-01.
* Server-side glob validation and path normalization — WP-1.4 (the gate) and
  WP-3.2 (submission-time scope comparison).
* The Policy Engine's R2 evaluation — WP-3.4.
* Scope-overlap visualization across tasks — not specified in the plan; out of
  scope here.

## Target paths
* `web/` — criteria list editor and target-scope glob editor components
* `web/tests/` — editor component tests
* WP changelog entry

## Acceptance criteria
- [ ] Acceptance criteria are managed as a list (add/edit/remove) and round-trip
  through save and reload unchanged (Section 13.2).
- [ ] Target scope accepts glob patterns with client-side syntax validation and
  inline feedback; invalid globs cannot be submitted without correction
  (Section 13.2, Section 12.3 "validated on creation").
- [ ] Server `VALIDATION_ERROR` on either field maps to a field-level friendly
  message with the modal staying open (Section 13.3).
- [ ] The displayed scope set always matches what is saved — the operator sees
  exactly the globs that bound the agent (R2/RISK-04 context).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`npm test -- -t criteria-scope-editors` — assert criteria round trip, glob
accept/reject cases with messages, server-error mapping to fields, and
save→reload fidelity; then the full web suite stays green.

## Attachments
* [Section 12.3 — Path and scope enforcement](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.4 — Policy Engine (R2 Scope)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Client glob validation must mirror, not reinvent, WP-1.4's semantics — two glob
  dialects would let the UI accept what the server rejects (or, worse, the reverse);
  share the pattern rules or test both against one fixture set.
* Scope globs drive audit escalations (R2) — an over-broad default added "for
  convenience" silently invites `scope_violation` storms; never pre-fill scope with
  patterns the operator did not type.
* The plan does not specify whether criteria are required for publish — check
  WP-1.4's T2-required-fields implementation and mirror it; flag any gap as an open
  question rather than choosing.
