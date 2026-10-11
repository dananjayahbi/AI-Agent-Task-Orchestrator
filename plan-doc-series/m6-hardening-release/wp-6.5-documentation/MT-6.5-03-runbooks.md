# MT-6.5-03 — Write the Runbooks from Parent Plan Section 17

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.5-03 |
| Title | Write the runbooks from parent plan Section 17 |
| Parent WP | WP-6.5 — Documentation and runbooks (Milestone M6) |
| Requirements | all (per Section 19 WP-6.5; primarily NFR-05, NFR-10) |
| Priority | M |
| Dependencies | MT-0.1-06 (seven runbook stubs), MT-6.2-04 (restore procedure and drill record), MT-6.4-01/02 (metrics and alert rules to cite), MT-6.1-03 (verified token lifecycle for rotation), MT-2.11-07 (client pages for the onboard runbook) |
| Parent sections | 16.4 (VPS checklist), 17 (Runbooks row), 19 (WP-6.5 deliverables), 20.4, 20.5; 21 (RISK-02, RISK-04, RISK-05, RISK-12, RISK-14); Appendix A |

## Context
Section 17's Runbooks row names exactly seven: stuck lease, failed merge, tunnel
down, restore from backup, rotate tokens, add a project, onboard a new agent client.
MT-0.1-06 created one stub per runbook under `docs/runbooks/`, each naming this task
as its content owner. Section 19 (WP-6.5) lists "runbooks (Section 17)" as a
deliverable. This slice fills the stubs with actionable procedures built from the
systems that already exist — and from the artifacts the sibling WPs produced (the
restore procedure from WP-6.2, verified token behavior from WP-6.1, alert rules from
WP-6.4) — so an operator hitting a problem at 2 a.m. has steps, not theory.

## Inputs / Prerequisites
* MT-0.1-06 — the seven stubs in `docs/runbooks/` with the exact Section 17 names.
* Parent plan Section 17 — the runbook list verbatim (the contract: seven runbooks,
  none renamed).
* MT-6.2-04 — restore procedure and drill record, which the "restore from backup"
  runbook must link rather than duplicate.
* MT-6.4-01/02 — metric semantics and alert rules; each runbook's "detect" step
  cites the relevant alert/metric.
* MT-6.1-03 — verified token lifecycle behavior for "rotate tokens" (that task
  explicitly reserved this runbook as its link target).
* MT-2.11-07 / MT-6.5-02 — `docs/agent-guides/` pages the "onboard a new agent
  client" runbook points at.
* Parent plan Section 16.4 — VPS checklist context for host-level steps.
* Section 20.4 item 3 — no secrets or environment-specific paths in procedures.

## Scope (in)
* Fill all seven runbooks, each with a consistent structure: symptom/trigger (how
  you know you're here, with the Section 17 alert or metric that fires), diagnosis
  steps, the procedure itself (ordered, executable), verification of recovery, and
  links to deeper docs:
  * **Stuck lease** — diagnose with active-lease/lease-expiry metrics and the
    sweeper heartbeat; reference Section 8.6 lease semantics and the sweeper's
    60 s cadence (RISK-02/RISK-12 context: don't reclaim active work by hand
    without checking fencing).
  * **Failed merge** — Section 11.4/ADR-008 flow: evidence, executor failure
    handling, requeue path, what "completed = merged" means for retries (RISK-04).
  * **Tunnel down** — Section 15.4 failure mode first (LAN and agents continue;
    this may be expected), then cloudflared service checks, token rotation pointer,
    and recovery (RISK-05).
  * **Restore from backup** — thin runbook pointing at MT-6.2-04's procedure and
    drill record, plus when to run it (linking the WP-6.2 schedule).
  * **Rotate tokens** — agent/device/edge token rotation order per Section 12.2
    and MT-6.1-03's verified revocation behavior (RISK-14).
  * **Add a project** — owner flow: create project, policy, manifest fields
    (Section 10.3), token issuance (Section 12.2).
  * **Onboard a new agent client** — pointer hub to `docs/agent-guides/` (setup
    pages, matrix, custom template) with the conformance-script verification step.
* Cross-link runbooks to the MT-6.5-01 operator guide and MT-6.5-04 troubleshooting
  guide, and update the `docs/runbooks/README.md` index (Section 20.5).
* Add a changelog note (Section 20.4 item 7).

## Out of scope
* Performing any rotation, restore, or merge recovery as part of writing — runbooks
  cite evidence produced by WP-6.1/WP-6.2; they don't re-run those programs.
* The operator setup guide — MT-6.5-01; troubleshooting decision trees —
  MT-6.5-04 (a runbook executes one procedure; the troubleshooting guide routes to
  it).
* An eighth runbook (e.g. mobile signing) — Section 17 names seven; anything else
  stays in the operator guide (per MT-5.10-01's recorded choice).
* Alert rule definitions — MT-6.4-02 (cited, not restated).

## Target paths
* `docs/runbooks/` — the seven runbook stubs filled with content
* `docs/runbooks/README.md` — index updated
* WP changelog entry

## Acceptance criteria
- [ ] All seven Section 17 runbooks are filled — stuck lease, failed merge, tunnel
  down, restore from backup, rotate tokens, add a project, onboard a new agent
  client — none added, renamed or dropped (Section 20.5; Section 19 WP-6.5
  deliverable "runbooks (Section 17)").
- [ ] Each runbook has trigger, diagnosis, procedure, verification and links
  (Section 20.4 item 1 — checkable, not hand-waving).
- [ ] "Restore from backup" links MT-6.2-04's procedure/record; "rotate tokens"
  links MT-6.1-03's verified behavior; "onboard a new agent client" links
  `docs/agent-guides/` (Section 20.5 traceability, honoring the sibling tasks'
  reserved link targets).
- [ ] Each runbook's trigger names the Section 17 alert/metric that surfaces the
  condition (WP-6.4 coupling).
- [ ] No secrets or environment-specific host paths in any procedure (Section 20.4
  item 3); changelog note added (item 7).

## Test command
Grep `docs/runbooks/` and confirm exactly seven runbook files matching the Section 17
names exist and none still contain stub text (e.g. search for "stub" or "TBD",
expected: zero matches); confirm each of the seven names appears in
`docs/runbooks/README.md` and that the restore and token runbooks contain links to
the WP-6.2 and WP-6.1 artifacts respectively.

## Attachments
* [Section 17 — Observability and Operations (Runbooks row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 16.4 — VPS migration checklist](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.5 deliverables and acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Runbooks written from memory of the plan will invent commands — every procedure
  step must trace to an existing script, endpoint or doc; if a needed command does
  not exist, that's a gap to log (Section 20.4 item 1), not a command to fabricate.
* Linking sibling artifacts creates ordering pressure: if MT-6.2-04 or MT-6.1-03 has
  not landed, write the runbook against the stub target and mark the link
  "pending <MT id>" — never inline an unverified procedure as if it were tested.
* The seven-runbook count is a fixed contract (MT-0.1-06 acceptance mirrors it);
  adding an eighth for convenience breaks both tasks' checks — route extra content
  to the operator guide instead.
