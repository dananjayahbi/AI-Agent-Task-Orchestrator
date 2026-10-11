# ADR-011 — Tool-only contract; prompts and injected rules are enhancements

| Field | Value |
|---|---|
| Status | accepted |
| Decision date | 2026-10-11 |
| Parent plan | Section 23 — ADR-011 |
| Session notes | [`../plan/m0-decision-review-notes.md`](../plan/m0-decision-review-notes.md) (WP-0.4 / MT-0.4-01) |

## Context

The bridge must serve heterogeneous MCP clients with uneven support for prompts,
images and tool-approval UX (RISK-01, Section 10.9). Principle P5 requires the system
to work regardless of client features.

## Decision

Tool-only contract; prompts and injected rules are enhancements.

## Rationale

Works across heterogeneous clients.

## Alternatives considered

* Prompt-dependent workflows.

## Consequences

* All required behavior is delivered through the tool catalog (Section 10.5); the
  rules block (Section 10.6) and prompts (Section 10.7) enhance but are never
  required (P5).
* NFR-08 tool-only compatibility is verified by the conformance script and per-client
  guides (WP-2.11).
* No workflow may depend on a client supporting prompts to be correct.

## Amendments

None — MT-0.4-01 (2026-10-11) flagged no conflict with Section 23.
