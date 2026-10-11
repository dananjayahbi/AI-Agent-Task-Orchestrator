# ADR-009 — Deterministic Policy Engine decides escalation from stored evidence

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-009 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

After an audit verdict, some outcome must decide whether work merges or escalates to
human review. Agents can be prompt-injected or self-serving — self-approval by the
same agent is an explicit threat (Section 12.1), and the auditor is itself an LLM
agent.

## Decision

Deterministic Policy Engine decides escalation from stored evidence.

## Rationale

Prevents LLM self-approval.

## Alternatives considered

* Auditor decides directly.

## Consequences

* Escalation and auto-complete are computed by code (rules R1–R9) from evidence
  stored with the submission — patches, scans, verdicts — per principle P4
  (Sections 6.1, 9).
* Every rule gets its own micro-task and test (Section 20.3), so engine outcomes are
  deterministic, auditable and regression-tested.
* The auditor's verdict is input to the rules, never the final say; a verdict alone
  cannot push work to merge or mark it complete (Section 8.2, T13/T14).

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
