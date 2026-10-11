# MT-6.6-04 — Run the Smoke Test Suite on the VPS

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.6-04 |
| Title | Run the smoke test suite on the VPS |
| Parent WP | WP-6.6 — VPS migration rehearsal and v1 release (Milestone M6) |
| Requirements | NFR-04, NFR-06 |
| Priority | M |
| Dependencies | MT-6.6-01 (provisioned), MT-6.6-02 (restored), MT-6.6-03 (reconnected); Section 18 e2e scenario suite |
| Parent sections | 1.4 (success criterion 5), 5.2 (NFR-04, NFR-06), 16.4 (VPS checklist, step 6), 18 (End-to-end row), 19 (WP-6.6 acceptance), 20.4, 20.5 |

## Context
Section 16.4 step 6: "Verify with the smoke test suite (Section 18)." WP-6.2's
acceptance already set the pattern — "a fresh host restored from backups passes the
smoke tests" — and Section 19 (WP-6.6) makes the whole WP's acceptance success
criterion 5: the full stack moved from laptop to VPS by environment configuration
only. This slice runs the Section 18 end-to-end scenarios against the migrated VPS:
happy path, crashed agent, high-risk escalation, merge conflict, text-only model with
screenshot, cross-project access attempt. A green local CI proves the code; a green
VPS smoke run proves the *migration*.

## Inputs / Prerequisites
* MT-6.6-01/02/03 — provisioned, restored, reconnected VPS stack (all three
  checklist phases complete before this step).
* Parent plan Section 18 End-to-end row — the six scenario scripts, run in CI
  against Compose; the suite definition this task reuses unchanged.
* Parent plan Section 18 Chaos row expectations — no lost state on restarts
  (NFR-04) informs restart-tolerant checks during the run.
* Parent plan Section 16.1 — service health as the pre-flight gate before scenarios.
* The e2e suite's documented invocation under `e2e/` (Appendix A) — same entry
  points as local; running a *different* suite would prove nothing about NFR-06.
* MT-6.2-04 — how a smoke pass was recorded in the drill, for a consistent
  rehearsal-log format.

## Scope (in)
* Pre-flight: all Section 16.1 services healthy, readiness green, and the reconnect
  verifications from MT-6.6-03 confirmed — the suite starts from a known-good stack.
* Execute the Section 18 smoke/e2e suite against the VPS environment using the
  documented entry points — no scenario edits, no exclusions; if a scenario cannot
  run on the VPS (e.g. needs LAN-only access), that is a finding, not an exclusion
  (record and escalate).
* Capture per-scenario results with evidence (pass/fail, output artifacts) in the
  rehearsal log, plus total duration and environment facts (Section 19 WP-6.6
  "rehearsal log").
* Triage failures: environment/config fixes are this WP's "fixes" deliverable and
  may be applied (still config-only); product defects or suite gaps are logged for
  the owning WP — re-run after each fix and record until green or honestly
  escalated (Section 20.4 item 1).
* Changelog note (Section 20.4 item 7).

## Out of scope
* Writing or modifying the smoke scenarios — Section 18 suite is the contract;
  editing it to pass would invalidate WP-6.2's and this WP's acceptance.
* The full performance suite (WP-6.3 scenarios at 10k tasks) — Section 16.4 step 6
  says the smoke suite; perf validation has its own WP.
* Security suite execution (WP-6.1) and load tests — out of this checklist step.
* Release notes/tagging — MT-6.6-05 (this task's green result is their input).
* Fixing code defects found — log with follow-up ids; code changes during a
  config-only rehearsal break criterion 5 (they become post-rehearsal fixes for the
  owning WP, recorded as such).

## Target paths
* `e2e/` — invocation only (no new or edited scenarios)
* `docs/plan/` — rehearsal log (appended: pre-flight, per-scenario results,
  duration, findings and fixes)
* WP changelog entry

## Acceptance criteria
- [ ] All Section 18 End-to-end scenarios ran against the VPS stack and passed:
  happy path, crashed agent, high-risk escalation, merge conflict, text-only with
  screenshot, cross-project access attempt (Section 16.4 step 6; Section 19 WP-6.6
  acceptance input).
- [ ] The suite used is the same one CI runs locally — no scenario edits or
  exclusions (NFR-06 identical-stack proof; Section 20.4 item 1).
- [ ] Per-scenario results with evidence recorded in the rehearsal log, including
  pre-flight health state and duration (Section 19 WP-6.6 deliverable).
- [ ] Any failure was fixed at the environment level or logged as a finding and
  re-run; nothing was silently skipped (Section 20.4 item 1).
- [ ] No tracked files modified during the run (Section 1.4 criterion 5);
  no secrets in captured output (item 3); changelog note added (item 7).

## Test command
Run the documented e2e suite entry point (under `e2e/`) against the VPS environment
exactly as CI runs it locally; confirm all six Section 18 scenario scripts report
pass, the rehearsal log records the results, and `git status` on the checkout shows
no tracked-file modifications.

## Attachments
* [Section 18 — Testing strategy (End-to-end row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.4 — VPS migration checklist (step 6)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.6 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Green-by-omission is the danger: skipped scenarios, stale fixtures or a suite
  pointed at the wrong base URL can all produce a false pass — verify the suite
  actually exercised the VPS host (addresses, logs) before recording success
  (Section 20.4 item 1).
* Some scenarios need side effects (merge executor on a host, push delivery) — on
  the VPS the topology differs from the laptop; where a leg depends on external
  services (FCM), record what was observed vs assumed rather than marking it green
  by intent (same honesty rule as MT-5.10-05's push notes).
* If scenarios fail only on the VPS, the likely cause is configuration — but
  "obviously just config" is where code edits sneak in; fix within the environment
  envelope or log the finding (Section 1.4 criterion 5 is binary).
* Suite runtime on a smaller VPS CPU may exceed local timings — record duration;
  timeouts adjusted for the environment are config, but any suite-file edit is a
  finding (the suite must stay shared with CI).
