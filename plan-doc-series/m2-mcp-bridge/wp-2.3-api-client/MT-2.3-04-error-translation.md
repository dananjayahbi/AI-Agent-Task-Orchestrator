# MT-2.3-04 — Implement error translation to code + hint + next-action

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.3-04 |
| Title | Implement error translation to code + hint + next-action |
| Parent WP | WP-2.3 — Backend API client (Milestone M2) |
| Requirements | NFR-04, NFR-12 |
| Priority | M |
| Dependencies | MT-2.3-01 (typed envelope parsing), MT-2.3-02 (retry classification) |
| Parent sections | 9.2, 10.5, 19 (WP-2.3), 20.4 (item 5), 20.5 |

## Context
Section 10.5's tool design rules require that every tool error carries a stable code,
a human-readable hint, and a "next action" suggestion for the model. The WP-2.3
deliverable is an "error translator giving code, hint, next action", and its acceptance
criterion is that errors surface as structured tool errors. This slice is the bridge
between the backend's Section 9.2 envelope and what the model actually sees: the
canonical code passes through unchanged, while the hint and next action are derived
from a translation table so agents can self-correct (for example on
`TASK_ALREADY_CLAIMED`, suggest re-listing available tasks).

## Inputs / Prerequisites
* Parent plan Section 9.2 — canonical error codes (19) and envelope fields; messages
  are human-readable and not parsed by clients.
* Parent plan Section 10.5 — tool error rule: stable code + hint + next action;
  design rule that no tool takes a project id.
* Parent plan Section 20.4 item 5 — global DoD: error codes used must exist in the
  catalog; the WP-0.5 conventions document is the published catalog.
* MT-2.3-01/02 — parsed envelope and retry classification feeding the translator.

## Scope (in)
* A translation module mapping each relevant Section 9.2 code to a model-facing hint
  and a concrete next action (for example: `LEASE_EXPIRED` → stop work and re-claim
  via `claim_task`; `TASK_ALREADY_CLAIMED` → call `get_available_tasks` again;
  `CONCURRENCY_LIMIT_REACHED` → wait or release a held task; `AUTH_REQUIRED` →
  verify token configuration; `RATE_LIMITED`/`SERVER_ERROR` → retryable, wait and
  retry).
* Passthrough guarantees: the canonical `code`, `details`, and `correlation_id` from
  the envelope are preserved verbatim; only hint/next-action are added locally.
* A documented default branch for codes with no specific entry that still names the
  canonical code (never invents a new one).
* Deterministic unit tests asserting the code → hint/next-action mapping and that no
  out-of-catalog code can be emitted.

## Out of scope
* MCP tool schemas and the five tool handlers that will call this translator —
  WP-2.4.
* Web/mobile friendly-message mapping (13.3) — WP-4.x.
* Adding any new error codes — forbidden; codes are added to the Section 9.2 catalog
  first (Section 20.4 item 5).
* Retry/backoff execution — MT-2.3-02.

## Target paths
* `bridge/src/` (error translator module)
* `bridge/tests/` (translation table tests)
* WP changelog entry

## Acceptance criteria
- [ ] Every translation entry keys on a code from the Section 9.2 catalog; a test
  rejects any code not in the catalog (Section 20.4 item 5).
- [ ] Translated errors reaching a tool handler carry all three parts — stable
  `code`, human-readable `hint`, actionable `next action` — plus the original
  `correlation_id` (Section 10.5, WP-2.3 deliverable).
- [ ] No canonical code, message or detail is rewritten or dropped by translation
  (Section 20.5 traceability: nothing beyond the plan).
- [ ] Retryable codes (`SERVER_ERROR`, `RATE_LIMITED`, timeout-class failures)
  retain their retryable classification through translation.
- [ ] Unit tests cover at least the claim-, lease-, auth- and server-class codes
  plus the default branch, and pass in CI (Section 20.4 item 2).
- [ ] Changelog note added (Section 20.4 item 7).

## Test command
Run the translator tests, e.g. `uv run pytest bridge/tests/ -k error_translation`;
assert each catalog code maps to a non-empty hint and next action and that unknown
codes are rejected.

## Attachments
* [Section 9.2 — Error envelope and canonical codes](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 10.5 — Tool catalog and tool design rules](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Hint/next-action text is agent-facing behavior: vague advice degrades agent
  recovery. Review wording for the claim/lease codes carefully — they carry the
  RISK-02 mitigation path (checkpoint/re-claim guidance).
* Translation must not become a second error catalog; the default branch keeps the
  canonical code visible so drift is detectable.
