# MT-5.4-02 — Define minimal push payloads (ids and short title only)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.4-02 |
| Title | Define minimal push payloads (ids and short title only) |
| Parent WP | WP-5.4 — Push notifications (FCM) (Milestone M5) |
| Requirements | FR-MOB-04; NFR-03 |
| Priority | M |
| Dependencies | MT-5.4-01 (sender), WP-3.9 (`review.requested` payload), WP-5.9 (deep-link routing) |
| Parent sections | 9.8, 14.2, 12.4, 19 (WP-5.4), 20.4, 20.5 |

## Context
Section 9.8 (push payload minimization): "Payload contains only ids and a short
title; sensitive text is fetched in-app after unlock." Section 14.2: tapping a
notification deep-links to the task's review sheet **after unlock** — so the payload
never needs content, only routing data. Section 12.4: attachments may contain
sensitive designs; logs and pushes must not become a leak channel. The task title is
the one piece of display text allowed ("short title") so the OS notification banner
is meaningful without exposing notes, feedback, diffs or evidence.

## Inputs / Prerequisites
* Parent plan Section 9.8 — payload minimization rule (verbatim) and triggers.
* Parent plan Section 14.2 — deep-link-after-unlock behavior; Section 14.1 —
  Notifications screen.
* Parent plan Section 9.6 — source event envelope (event type, `project_id`,
  `task_id`, `task_version` in `data`).
* MT-5.4-01 — the sender this payload feeds; MT-5.4-03 — dedupe needs the state
  version from the same payload.
* WP-5.9 — deep-link routing consuming the payload on the client.

## Scope (in)
* A push payload builder producing, from an event: the event type, `project_id`,
  `task_id`, `task_version` (state version), and the short task title — the
  routing-ids + short-title set Section 9.8 fixes, with nothing else.
* An explicit exclusion list enforced in code and tests: no `execution_summary`, no
  `latest_feedback`, no notes, no evidence/commands, no diff or attachment text, no
  free-text event content (Section 9.8; Section 12.4 posture).
* Deep-link affordance data only to the extent the ids above provide (the client
  routes to the task's review sheet after unlock, Section 14.2) — no URL with
  embedded content.
* Payload-size sanity: the builder produces a small message (OS banner limits) —
  title truncation policy stated (truncate for display, never substitute content).
* Tests: payload snapshot per trigger type; assertion that excluded fields never
  appear even when the source event carries them (events may include rule details —
  those stay server-side/in-app per Section 9.8).

## Out of scope
* Sender mechanics, retries — MT-5.4-01; dedupe — MT-5.4-03; tracking/pruning —
  MT-5.4-04; preferences — MT-5.4-05.
* The source event's full payload (rule details) — WP-3.9 (rich data stays on the
  event stream for in-app use).
* Client rendering, banners, history — WP-5.9.
* Encrypting payloads — device/OS transport security per FCM; no custom crypto
  invented here.

## Target paths
* `backend/` — push payload builder
* `backend/tests/` — payload minimization tests
* WP changelog entry

## Acceptance criteria
- [ ] Push payloads contain only ids (event type, `project_id`, `task_id`,
  `task_version`) and the short task title — Section 9.8 verbatim.
- [ ] No sensitive text (summaries, feedback, notes, evidence, diff/attachment
  content) can appear, even when present on the source event — enforced by an
  allowlist builder and asserted by tests (Sections 9.8, 12.4).
- [ ] The payload carries what MT-5.4-03's dedupe key needs (`event type`, `task id`,
  `state version`) and what WP-5.9's deep link needs (`task_id`) — no more.
- [ ] Payloads stay within OS banner size limits with a documented truncation policy
  for the title (truncate display, never add content).
- [ ] Lint/type/tests green (Section 20.4 item 2); changelog note added (item 7).

## Test command
`pytest backend/tests -k push_payload -q` — assert the allowlisted field set per
trigger, absence of every excluded sensitive field even when the source event
includes it, dedupe-key fields present, and size/truncation behavior; then
`pytest backend/tests -q` stays green.

## Attachments
* [Section 9.8 — Notifications](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.2 — Mobile-specific behaviors (push, deep link)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Event payloads grow over time (rule details from WP-3.9) — an allowlist builder
  (copy only named fields) is the only robust defense; a blocklist ("omit
  evidence") will rot as events gain fields.
* The short title is user-authored task text rendered by the OS — keep it plain
  text; do not interpret markup in push rendering.
* If a future trigger needs more context, that is a plan change (Section 9.8 is the
  contract) — raise it rather than quietly widening the payload.
