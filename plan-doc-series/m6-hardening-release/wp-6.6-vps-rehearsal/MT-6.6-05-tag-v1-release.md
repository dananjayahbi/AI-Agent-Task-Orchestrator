# MT-6.6-05 — Tag v1 Release with Release Notes

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.6-05 |
| Title | Tag v1 release with release notes |
| Parent WP | WP-6.6 — VPS migration rehearsal and v1 release (Milestone M6) |
| Requirements | NFR-06, GOAL-5 |
| Priority | M |
| Dependencies | MT-6.6-01 … MT-6.6-04 (rehearsal green), WP-6.1 … WP-6.5 complete (Section 19 WP-6.6 dependency), MT-6.3-02/03 (performance verdicts for the notes), MT-6.1-05 (security findings status) |
| Parent sections | 1.2 (GOAL-5), 1.4 (success criterion 5), 5.2 (NFR-06), 19 (WP-6.6 goal, deliverables, acceptance), 20.4, 20.5, 20.6 (execution order: M6 last); 21; 22 (open OQs status) |

## Context
Section 19 (WP-6.6) closes the delivery plan: goal "Prove GOAL-5 and tag v1",
deliverables "rehearsal log, fixes, release notes, tag", acceptance "success
criterion 5 in Section 1.4 met". Section 20.6 orders execution with M6 last — this
task is the final act of the whole plan series. "v1 works" is defined by the five
Section 1.4 success criteria, and NFR-06/GOAL-5's proof is the completed rehearsal.
The release notes are the honest, evidence-backed statement of what v1 delivers,
what was proven (with pointers to the evidence), what remains open (OQs, Could
items, known limitations), and what the operator needs to know — not marketing.

## Inputs / Prerequisites
* MT-6.6-01 … 04 — the completed rehearsal log with green smoke results and the
  fixes applied; the acceptance evidence for criterion 5.
* WP-6.1 … WP-6.5 deliverables — findings logs (security), performance report
  (WP-6.3), backup drill record (WP-6.2), docs set (WP-6.5): the status each must
  report honestly in the notes.
* Parent plan Section 1.4 — the five success criteria; v1's definition of done is
  theirs, verified by the evidence trail.
* Parent plan Section 1.3 — non-goals to restate (what v1 deliberately is not).
* Parent plan Section 22 — open-question table status: which OQs were decided
  (recorded in WP-0.4/ADRs) and which remain open at tag time.
* Section 20.4 — the global DoD must hold for this task too (changelog, no secrets).
* Section 20.6 — M6 is the last milestone; nothing after this tag is in v1.

## Scope (in)
* Assemble the release notes document: scope of v1 (goals, features by milestone),
  the five Section 1.4 success criteria each with its evidence pointer (test run,
  rehearsal log entry, drill record, report), verification summary from WP-6.1
  (no open high/critical findings), WP-6.3 (targets met), WP-6.2 (restore drill
  passed), WP-6.6 (VPS rehearsal green).
* State known limitations and open items honestly: open OQs, deferred Could items,
  documented limitations (Section 12.3 honest limitations, RISK register items that
  remain live), and anything escalated in the WP logs — RISK-09's scope discipline
  means the notes say what was *not* built too.
* Confirm the release gate before tagging: all WP-6.x acceptances met, WP changelog
  items complete, CI green on the release commit (Section 20.4 item 2), no secrets
  in the tree (item 3).
* Create the git tag for v1 per the repository's tag convention (record the exact
  tag name chosen) pointing at the release commit, and attach/publish the release
  notes with it.
* Record the tag and notes location in the WP changelog and rehearsal log
  (Section 19 WP-6.6 deliverables "release notes, tag"; Section 20.4 item 7).

## Out of scope
* Any code, docs or config changes "to make the release better" — the release is
  cut from the verified state; changes belong to post-v1 work (Section 20.6: M6 is
  last).
* Running the rehearsal or smoke suite — MT-6.6-01 … 04 (this task consumes their
  results).
* Deciding deferred features/OQs — plan owner (Section 22); the notes record
  status, they don't resolve questions.
* Publishing/distribution mechanics beyond attaching notes to the tag — MT-5.10's
  distribution path covers app builds; this tag covers the orchestrator itself.
* Version-numbering schemes beyond choosing the v1 tag name — no scheme invention
  is needed for a single v1 tag (see risk notes).

## Target paths
* `docs/` — release notes document (location recorded with the MT-6.5-01 docs
  choice, or attached to the tag — choose one and record it)
* Git tag — v1 (exact name recorded in changelog and release notes)
* `docs/plan/` — rehearsal log (final entries: gate confirmation, tag)
* WP changelog entry (final)

## Acceptance criteria
- [ ] Release notes exist and cover: v1 scope, the five Section 1.4 success criteria
  each linked to its evidence, verification status from WP-6.1/6.2/6.3/6.6, known
  limitations, open OQs and deferred items — Section 19 WP-6.6 deliverable "release
  notes" (Section 20.4 item 1; Section 1.3 non-goals restated).
- [ ] Every claim in the notes traces to a real artifact (log, report, test run) —
  no unreferenced "works" statements (Section 20.5 traceability discipline).
- [ ] The release gate is confirmed and recorded: WP-6.1 … WP-6.5 acceptances met,
  CI green on the tagged commit, no secrets in the tree (Section 20.4 items 2, 3).
- [ ] Success criterion 5 is explicitly asserted with the completed rehearsal log as
  its evidence — WP-6.6 acceptance (Section 1.4).
- [ ] A git tag exists pointing at the release commit with the notes attached/
  linked, and the tag name is recorded in the WP changelog (Section 19 WP-6.6
  deliverable "tag").
- [ ] Final changelog note added (Section 20.4 item 7).

## Test command
Confirm the gate: WP-6.x acceptance evidence present (rehearsal log green through
step 6, drill record pass, findings log with zero open critical/high, performance
report verdicts green) and CI green on HEAD; then verify the tag exists on the
intended commit (`git tag -l "v1*"` and `git rev-parse` comparison) and that the
release notes reference each of the five Section 1.4 success criteria.

## Attachments
* [Section 1.4 — Success criteria (definition of "v1 works")](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.6 goal, deliverables, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 20.6 — Execution order (M6 last)](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Tagging with a red or partially-gathered gate is the one irreversible mistake
  here — if any WP-6.x acceptance or success criterion lacks evidence, the correct
  outcome is a blocked tag with the gap recorded, not a tag with an asterisk
  (Section 20.4 item 1).
* The notes will be read as promises: every "supports X" must be backed by the
  verification that ran; conversely, do not omit documented capabilities just
  because they weren't re-verified in M6 (the evidence trail is cumulative across
  milestones).
* Open OQs at tag time are legitimate (the plan says needed-by dates, not
  guarantees) — list them as open with their recommended defaults, never resolved
  silently in prose (Section 22; Section 20.1 principle 5).
* Choose and record the exact tag string once (`v1` vs `v1.0.0` — plan says "tag
  v1"); changing tag names after publication confuses every consumer of the notes —
  make the choice in the changelog before creating it.
