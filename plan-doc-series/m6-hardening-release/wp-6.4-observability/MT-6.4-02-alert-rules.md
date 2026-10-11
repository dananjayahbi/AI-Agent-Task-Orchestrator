# MT-6.4-02 — Define Alert Rules (Sweeper, Backlog, Push, Tunnel, Auth, Disk)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-6.4-02 |
| Title | Define alert rules (sweeper, backlog, push, tunnel, auth, disk) |
| Parent WP | WP-6.4 — Metrics, alerts and dashboards (Milestone M6) |
| Requirements | NFR-10, RISK-12 |
| Priority | M |
| Dependencies | MT-6.4-01 (metrics and heartbeat signals), MT-6.2-03 (backup schedule feeds disk/backlog context), M1 background jobs (Section 9.9), WP-5.1 (tunnel verification) |
| Parent sections | 5.2 (NFR-10), 9.9 (jobs), 15.4 (tunnel failure mode), 17 (Alerts row), 19 (WP-6.4 acceptance), 20.4, 20.5; 21 (RISK-12, RISK-05) |

## Context
Section 17's Alerts row names exactly six alerts: sweeper not running, backlog of
unprocessed attachments, push failures, tunnel down, repeated auth failures, disk
usage on media volume. Section 19 (WP-6.4) makes the acceptance bar precise: "each
listed alert can be triggered in a test." RISK-12's mitigation explicitly includes
"clear metrics and alerts" for sweeper bugs — an alert that never fires is the risk
materializing quietly. This slice turns the six names into concrete rules: the
condition, its threshold, its signal source (MT-6.4-01 metrics or health checks), and
a test that forces each one to fire.

## Inputs / Prerequisites
* Parent plan Section 17 — the six-alert list verbatim; the contract for this task.
* MT-6.4-01 — metric definitions and heartbeat signals the rules read; the metric
  semantics document is where thresholds must be expressible.
* Parent plan Section 9.9 — job schedules (sweeper every 60 s, stalled detector every
  5 min) that define "not running" (a missed heartbeat window must exceed the job's
  normal cadence, with margin).
* Parent plan Section 15.4 — tunnel failure mode (LAN and agents continue; mobile
  shows unreachable) — "tunnel down" must be detectable from the host side despite
  the tunnel being outbound-only.
* Parent plan Section 12.2/15.3 — repeated auth failures as a security signal
  (anomaly alerts on repeated auth failures, Section 15.3 layer 4).
* Section 16.3/16.1 — media volume disk usage; Section 16.5 — backups also consume
  second-location disk.

## Scope (in)
* Define, for each of the six Section 17 alerts, a concrete rule: signal source,
  threshold/window with rationale, severity, and the notification/surfacing path
  (recorded in `docs/plan/`, and implemented where the plan's operations view and
  `system.alert` events already give it a home — Section 9.9 stalled detector emits
  `system.alert` flags for the UI).
* **Sweeper not running:** heartbeat/liveness of the Section 9.9 lease sweeper beyond
  its 60 s cadence (RISK-12 mitigation).
* **Backlog of unprocessed attachments:** queue depth/oldest-item age of the
  attachment pipeline past a documented bound.
* **Push failures:** push success rate (MT-6.4-01 metric) below threshold or
  failures over a window (NFR-03's 10 s dispatch is the related contract).
* **Tunnel down:** cloudflared/tunnel status per Section 16.1 health check, with
  Section 15.4's documented failure mode as expected behavior, not a page.
* **Repeated auth failures:** failure counts per identity/IP over a window
  (Section 15.3 anomaly alerts).
* **Disk usage on media volume:** usage threshold on the Section 16.1 media volume
  (and note the second-location disk that backups consume).
* A test per alert that forces the triggering condition and asserts the alert fires
  (Section 19 WP-6.4 acceptance; Section 18 test discipline), plus a changelog note
  (Section 20.4 item 7).

## Out of scope
* The metrics endpoint itself — MT-6.4-01.
* Rendering alerts in the dashboard — MT-6.4-03 (rules must be readable by it, but
  the view is a separate slice).
* External paging/on-call integrations (email, PagerDuty, etc.) — not in the plan;
  surfacing means the plan's alert/event channels; record the chosen channel as a
  decision (see risk notes).
* Threshold tuning from production traffic — v1 has no production baseline; thresholds
  start from job cadences and documented rationale, adjustable by configuration.
* Edge-side Cloudflare alerting — out of the stack's scope; host-side detection only.

## Target paths
* `docs/plan/` — alert rules catalog (rule, signal, threshold, rationale, channel)
* `backend/` — rule evaluation/triggering logic and per-alert trigger tests
* `infra/compose/` — only if a health/status signal needs wiring
* WP changelog entry

## Acceptance criteria
- [ ] All six Section 17 alerts exist as defined rules with signal, threshold and
  rationale — none renamed, added or dropped (Section 20.5; Section 19 WP-6.4
  deliverable "alert rules").
- [ ] Each rule's threshold is derived from a plan anchor (job cadence, NFR-03 window,
  volume sizing) or explicitly marked as a configurable default needing owner
  confirmation — no invented magic numbers presented as plan values (Section 20.4
  item 1).
- [ ] A test exists per alert that triggers the condition and asserts the alert fires —
  WP-6.4 acceptance "each listed alert can be triggered in a test" — all six green
  in CI (Section 20.4 item 2).
- [ ] The sweeper alert's coverage of RISK-12 is stated in the rules catalog
  (Section 21 traceability).
- [ ] The tunnel alert respects Section 15.4: tunnel-down is surfaced without
  pretending the stack is down (LAN/agents continue).
- [ ] Alerts carry no secrets or attachment content in their payloads (Section 12.4);
  changelog note added (Section 20.4 item 7).

## Test command
Run `pytest backend/tests/ -k alert -v` — six tests, one per Section 17 alert, each
forcing its condition (stop the sweeper heartbeat, flood the pipeline, fail pushes,
drop tunnel status, burst auth failures, fill the volume threshold) and asserting the
alert fires; then confirm the rules catalog lists exactly six rules matching the
Section 17 Alerts row.

## Attachments
* [Section 17 — Observability and Operations (Alerts row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-6.4 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 21 — RISK-12 (sweeper; metrics and alerts)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 15.4 — Tunnel failure mode](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* Alert fatigue is the failure mode of six rules with loose thresholds — start from
  plan anchors (60 s sweeper cadence, NFR-03 windows), make every threshold
  configurable, and record which ones the owner should revisit after first use; a
  noisy alert trains the operator to ignore the sweeper one that matters (RISK-12).
* "Tunnel down" detection from inside the host is genuinely tricky (the tunnel is
  outbound-only by design, Section 15.1) — if status can only come from the
  cloudflared service health check, document that limitation honestly rather than
  over-claiming detection (Section 20.4 item 1).
* Forcing some trigger conditions in tests (disk full, auth bursts) can disturb a
  shared local stack — use isolated/disposable fixtures so tests don't poison other
  suites (Section 18 integration discipline).
* Where an alert fires into a channel the plan never named (log, event, UI flag,
  notification), that's a real decision — record it in the rules catalog and changelog
  instead of silently choosing one (Section 20.1 principle 5, no hidden decisions).
