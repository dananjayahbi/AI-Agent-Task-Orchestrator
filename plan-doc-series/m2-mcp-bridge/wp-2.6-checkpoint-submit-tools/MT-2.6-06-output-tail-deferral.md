# MT-2.6-06 — Document deferral of optional output-tail attachment (G-11, Could)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-2.6-06 |
| Title | Document deferral of optional output-tail attachment (G-11, Could) |
| Parent WP | WP-2.6 — Tools: checkpoint and submission with Git evidence (Milestone M2) |
| Requirements | G-11 |
| Priority | M |
| Dependencies | MT-2.6-01 (checkpoint tool as the surviving ingest path) |
| Parent sections | 4 (G-11), 10.5, 19 (WP-2.6), 20.4, 20.5 |

## Context
Gap G-11 (Section 4): "'Live Agent Terminal Feed' implies raw terminal output, but the
only ingest path is `log_task_checkpoint` (a message string)." Resolution: "v1 live
feed = checkpoint stream. Optional (Could) output-tail attachment per checkpoint is
described but deferred (WP-2.6 note)." The plan's WP-2.6 slices list "optional
output-tail (Could, G-11)" last — this micro-task discharges that slice as a
documented deferral decision, so the gap is closed on paper honestly rather than
silently skipped, and no half-built ingest path lingers.

## Inputs / Prerequisites
* Parent plan Section 4 — G-11 row and its resolution (verbatim).
* Parent plan Section 10.5 — `log_task_checkpoint` (message string) as the only v1
  ingest path.
* MT-2.6-01 — the implemented checkpoint tool that constitutes the v1 live feed.
* WP-0.4 decision records — where gap resolutions live, if this session recorded a
  G-11 entry there.
* Section 20.4 item 7 — changelog obligation.

## Scope (in)
* A WP-2.6 note (changelog/decision record entry) recording the deferral: what was
  deferred (optional output-tail attachment per checkpoint, "Could" priority), why
  (v1 live feed = checkpoint stream per G-11), what the deferred design would add
  (tail of agent output attached to a checkpoint), and what would unblock it later
  (attachment pipeline + explicit product need).
* Cross-reference both ways: the note cites G-11 and WP-2.6; the conventions/decision
  documentation points at the note so a future reader finds it from G-11.
* A repository sweep confirming no partial output-tail implementation exists in the
  bridge (no dead parameters, no stubbed endpoint) — the deferral is total.
* An optional follow-up marker (open-question/backlog reference) so the "Could" item
  is visible for post-v1 consideration, without creating a new plan ID.

## Out of scope
* Implementing any output-tail capture, upload or storage — deferred by decision.
* Changing `log_task_checkpoint`'s schema — it stays `task_id`, `message`,
  `percentage` (Section 10.5).
* Re-litigating G-11's resolution — settled in Section 4.
* The rest of the WP-2.6 changelog — that belongs to MT-2.6-01..05.

## Target paths
* WP-2.6 changelog / decision note (deferral record)
* Cross-reference entry next to the G-11 resolution (decision records, WP-0.4)
* (No runtime code paths)

## Acceptance criteria
- [ ] The WP-2.6 note states the deferral verbatim against G-11: optional output-tail
  attachment per checkpoint is deferred; v1 live feed = checkpoint stream.
- [ ] The note records why (only ingest path is `log_task_checkpoint`, a message
  string) and what would unblock the deferred item, per Section 4's resolution.
- [ ] G-11 and WP-2.6 reference each other, so neither document is a dead end.
- [ ] A repository search shows no partial output-tail implementation (no stubs, no
  unused parameters).
- [ ] Changelog note added (Section 20.4 item 7); no requirement IDs invented
  (Section 20.5 — the task traces to G-11 only).

## Test command
Grep the bridge package for output-tail references (e.g. search for `output_tail`,
`output-tail`, `tail`) and confirm zero runtime hits outside the deferral note; then
grep the plan and the note for `G-11` to confirm both cross-references exist.

## Attachments
* [Section 4 — G-11 resolution](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-2.6 slices](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Documentation-only task: its risk is being skipped as "nothing to do" — the G-11
  slice is explicitly part of WP-2.6, and skipping it leaves the gap untraceable
  (Section 20.5).
* Resist "while we're here" partial implementations (e.g. a flag that captures
  nothing) — a dead flag is worse than a clean deferral.
* If a reviewer wants the output-tail now, it changes scope from "Could" to shipped
  work: raise it as a decision first (Section 20.1, no hidden decisions) rather than
  folding it into this note.
