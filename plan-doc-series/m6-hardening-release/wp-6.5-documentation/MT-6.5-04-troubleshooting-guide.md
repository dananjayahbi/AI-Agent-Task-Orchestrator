# MT-6.5-04 — Write the Troubleshooting Guide

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.5-04 |
| Title | Write the troubleshooting guide |
| Parent WP | WP-6.5 — Documentation and runbooks (Milestone M6) |
| Requirements | all (per Section 19 WP-6.5; primarily NFR-10) |
| Priority | M |
| Dependencies | MT-6.5-01 (operator guide), MT-6.5-02 (agent guides), MT-6.5-03 (runbooks to route into), MT-6.4-01/02 (metrics and alerts to cite) |
| Parent sections | 9.2 (error catalog), 15.4 (tunnel failure mode), 16.5 (upgrade failures), 17 (Metrics/Alerts rows), 19 (WP-6.5 goal, acceptance), 20.4, 20.5; 21 (RISK-01, RISK-02, RISK-05, RISK-12, RISK-14, RISK-15); 22 (OQ-05) |

## Context
Section 19 (WP-6.5) slices close with "troubleshooting", and the WP acceptance tests
the docs as a whole: someone following only them can stand up the stack, onboard a
repo and connect an agent — and, implicitly, recover when any of that misbehaves.
The troubleshooting guide is the router: symptom → likely cause → the runbook,
metrics/alerts, or guide chapter that handles it. It sits above the seven runbooks
(MT-6.5-03) and the setup/client guides (MT-6.5-01/02), never duplicating their
procedures — it decides *which* one applies.

## Inputs / Prerequisites
* MT-6.5-01/02/03 — the guide's link targets; the troubleshooting guide is written
  last in the WP so every destination exists.
* MT-6.4-01/02 — metric semantics and the six alert rules: each symptom entry names
  the signal that confirms or rules out the cause (Section 17).
* Parent plan Section 9.2 — the canonical error-code catalog: API/tool errors in
  symptoms map to catalog codes, not ad-hoc paraphrases (Section 20.4 item 5).
* Parent plan Section 15.4 — tunnel-down failure mode (mobile "unreachable", LAN
  fine, push via FCM still works) as a worked triage example.
* Parent plan Section 16.5 — upgrade/rollback steps for post-upgrade symptoms
  (migrate failures, API version header warnings).
* Section 21 risks — RISK-01 (client differences), RISK-02 (expired leases),
  RISK-05 (tunnel/SSE), RISK-12 (sweeper), RISK-14 (token leakage), RISK-15 (host
  path differences) — the failure modes the guide should cover first.

## Scope (in)
* Write the troubleshooting guide under `docs/` (location recorded alongside the
  MT-6.5-01 choice — same Appendix A gap), organized symptom-first:
  * Stack/bring-up: services unhealthy, health endpoints failing, migrations
    refusing to start (startup validation, Section 9.10/16.2), profile confusion.
  * Agents/leases: agent cannot claim, task stuck, lease expiring — route to the
    stuck-lease runbook with the sweeper/lease metrics as the first check
    (RISK-02/RISK-12).
  * Connectivity: mobile unreachable, SSE drops — triage tunnel-down runbook vs
    Section 15.4's expected failure mode (RISK-05).
  * Attachments/pipeline: upload or processing failures — attachment backlog alert
    and pipeline metrics first.
  * Auth/tokens: rejected tokens, repeated auth failures — token rotation runbook,
    Section 12.2 scoping, RISK-14 if leakage suspected.
  * Upgrades: post-migrate or version-header warnings — Section 16.5 rollback
    path.
  * Client-specific quirks: route to the Section 10.9 matrix and MT-6.5-02 guides
    (RISK-01) rather than restating per-client steps.
* For each symptom: confirm-signal (metric/alert/error code), likely causes in
  order, the exact runbook/guide link to follow, and when to escalate to the plan
  owner (gaps become changelog suggestions, Section 0).
* Cross-link from the operator guide, agent guides and runbooks index
  (Section 20.5); changelog note (Section 20.4 item 7).

## Out of scope
* The procedures themselves — each lives in a Section 17 runbook (MT-6.5-03) or
  guide chapter; the troubleshooting guide routes, runbooks execute.
* New diagnostics, debugging tooling or log queries beyond what metrics/logs
  already expose (NFR-10 existing surface).
* Fixing product defects found while writing — log them as findings/suggestions
  (Section 20.1 principle 5: no hidden decisions).
* Covering failures outside the plan's scope (multi-host, multi-tenant) — Section
  1.3 non-goals.

## Target paths
* `docs/` — troubleshooting guide (location recorded with the MT-6.5-01 choice)
* `docs/` — cross-links added from operator guide, `docs/runbooks/README.md`,
  `docs/agent-guides/README.md`
* WP changelog entry

## Acceptance criteria
- [ ] The guide covers the symptom families above (stack, agents/leases,
  connectivity, attachments, auth/tokens, upgrades, client quirks), each entry
  giving confirm-signal → causes → link (Section 19 WP-6.5 slice "troubleshooting";
  Section 20.4 item 1).
- [ ] Every symptom entry links to an existing runbook, metric/alert definition, or
  guide chapter — no dead ends and no duplicated procedures (Section 20.5).
- [ ] Error references use Section 9.2 catalog codes verbatim (Section 20.4 item 5).
- [ ] Tunnel/SSE symptoms reflect Section 15.4's documented failure mode without
  contradicting it (RISK-05).
- [ ] The guide is reachable from the operator guide, runbooks index and agent
  guides index (Section 20.5; WP-6.5 acceptance coherence).
- [ ] No secrets or environment-specific host paths (Section 20.4 item 3);
  changelog note added (item 7).

## Test command
Grep the guide for every Section 17 runbook name and the six alert names — each must
appear as a link target at least once — and for Section 9.2 error codes (present,
verbatim); follow two worked symptoms end-to-end (one lease symptom, one tunnel
symptom) confirming each link resolves to a real document section.

## Attachments
* [Section 17 — Observability and Operations](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 9.2 — Error-code catalog](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.5 goal, acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* The guide rots fastest of all docs because symptoms multiply — keep entries thin
  (signal + link) so maintenance is a link check, and re-run the test command
  whenever a runbook or alert is renamed.
* Writing symptoms you haven't observed invites plausible fiction — ground each
  entry in the plan's documented failure modes (Section 15.4, the risk register)
  or a real reproduction; mark speculative entries as such (Section 20.4 item 1).
* If a symptom has no owning runbook (a genuine coverage gap), do not quietly
  create an eighth runbook — log it in the changelog for the plan owner, matching
  MT-6.5-03's seven-runbook contract.
