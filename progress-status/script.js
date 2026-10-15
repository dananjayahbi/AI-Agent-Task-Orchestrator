/**
 * Progress data for the AI Agent Task Orchestrator plan series.
 *
 * Update this file at the end of each wave (or whenever micro-documents
 * land). Counts must match plan-doc-series/overview.md — the single source
 * of truth is ai_agent_task_orchestrator_architecture_plan.md; if context
 * of the plan is lost, re-read it before editing this data.
 */

const TOTAL_DOCS = 330; // +MT-1.6-09 (sessions), +MT-1.15-06 (dashboard endpoint)

const waves = [
  { id: 1, name: "Foundations",            total: 22, done: 22, status: "done" },
  { id: 2, name: "Backend foundation",     total: 23, done: 23, status: "done" },
  { id: 3, name: "State machine & leases", total: 28, done: 27, status: "active" },
  { id: 4, name: "Events, attachments",    total: 32, done: 32, status: "done" },
  { id: 5, name: "Bridge skeleton & web",  total: 33, done: 33, status: "done" },
  { id: 6, name: "Bridge core tools",      total: 36, done: 36, status: "done" },
  { id: 7, name: "Policy core & Kanban",   total: 34, done: 34, status: "done" },
  { id: 8, name: "Agent loop completion",  total: 42, done: 42, status: "done" },
  { id: 9, name: "Merge & review UIs",     total: 40, done: 40, status: "done" },
  { id: 10, name: "Release & hardening",   total: 40, done: 24, status: "active" },
];

/** Timeline of execution (append newest at the bottom; mark status). */
const timeline = [
  {
    date: "2026-10-11",
    status: "done",
    event: "Plan document series completed",
    detail: "overview.md index, 328 micro-documents, roadmap.md with 10 one-directional waves.",
  },
  {
    date: "2026-10-12",
    status: "done",
    event: "Wave 1 complete — Foundations (22/22)",
    detail:
      "Monorepo scaffolding + tooling, 8-service Compose stack (healthy, data survives restart), " +
      "4 CI workflows, ADR-001..013, OQ-01..14 table, conventions docs with ORCHESTRATOR_* env naming. " +
      "All lint/type commands green; committed as wave gate.",
  },
  {
    date: "2026-10-12",
    status: "done",
    event: "Wave 2 complete — Backend foundation (23/23) · committed 4efc49c",
    detail:
      "Full gate: 377 backend tests + web 53 + bridge 55 + flutter 27, all lint/type/format green; " +
      "all five exit criteria live-proven under Compose (AUTH_FORBIDDEN_PROJECT, manifest schema " +
      "validation, 100 unique concurrent ids, VERSION_CONFLICT, health + OpenAPI served). " +
      "ErrorEnvelope contract reconciled to nested 9.2 wire shape.",
  },
  {
    date: "2026-10-14",
    status: "active",
    event: "Batch 7 complete — 219/330 micro-docs (66%); Wave 5 DONE",
    detail:
      "Landed: wp-3.4 policy engine (R1-R9 deterministic, table-driven combos, invariant-4 wiring), " +
      "wp-1.15 finish (9.2 authz suite + coverage gates: SM 97.1%, leases 94.3%), wp-2.5 attachment " +
      "tool + wp-3.5 verdict schema/evidence (inspector = 9 tools, bridge 684), wp-4.6 task detail " +
      "(live checkpoint feed, attachment viewer; web 234). Gates: backend 1388 + PG, all clients synced.",
  },
  {
    date: "2026-10-14",
    status: "active",
    event: "Batch 8 complete — 253/330 micro-docs (76.7%)",
    detail:
      "Landed: wp-4.7 diff viewer (client patch parser, virtualized unified/split views, file tree, " +
      "large-diff fallback), wp-5.7 mobile task detail (checkpoint feed, attachments, untrusted-content " +
      "banner), wp-2.8 MCP prompts + MT-3.8-02 draft-task tool, wp-6.2 backup drill (restore drill PASS " +
      "over 15 phases after fixing a drill-check stdout-banner flaw), wp-3.6+3.8-01+3.9 review decisions, " +
      "decomposer permissions and escalation payloads. Gates: backend 1467 + 27 PG, bridge 711 + live, " +
      "web 287, mobile 199; web OpenAPI client regenerated to match schemas/openapi.yaml.",
  },
  {
    date: "2026-10-14",
    status: "active",
    event: "Batch 9 complete — 284/330 micro-docs (86.1%)",
    detail:
      "Parallel implementation (6 agents) + power-cut recovery (3 fresh finishers) + first parallel gate (backend/bridge/web/mobile/hygiene). " +
      "Landed: merge executor wp-3.7 (strategies, journal/recovery, live e2e) + mt-3.8-03, bridge conformance harness mt-2.11-01, " +
      "auditor-flow mt-3.5-03/04, metrics scaffold mt-6.4-01, web review dialogs/queue/optimistic + agents/audit/policy panels (362 tests), " +
      "mobile review sheet + audit log + release signing (243 tests). Gates: backend 1512 + 27 PG, bridge 834 incl. live, web 362, " +
      "mobile 243; OpenAPI regenerated (+405 lines).",
  },
  {
    date: "2026-10-14",
    status: "active",
    event: "Batch 10 complete — 298/330 micro-docs (90.3%)",
    detail:
      "Escalation reason-coverage mt-3.9-03 closed wp-3.9; push-sender foundation mt-5.4-01..04 (FCM behind transport protocol, dedupe, delivery tracking); review panel mt-4.8-02..04 closed wp-4.8; web a11y+perf mt-4.11-01..04 (responsive, keyboard, contrast audit, 500-card perf report; 442 web tests); alert rules mt-6.4-02 + ops dashboard mt-6.4-03 closed wp-6.4. Mobile release mt-5.10-02/04 deferred (WP-5.4/5.9 chain). Gates parallel x5: backend 1597 + 27 PG, bridge 822, web 442, mobile 243, hygiene/clients green.",
  },
  {
    date: "2026-10-15",
    status: "active",
    event: "Batch 11 complete — 313/330 micro-docs (94.8%)",
    detail:
      "Notify chain mt-5.9-01..03 + mt-5.4-05 closed wp-5.4/wp-5.9 (cycle ruling recorded); mobile release mt-5.10-02/04 (signed prod APK built+verified; 5.10-05 checklist-deferred); perf suite mt-6.3-01..03 (honest: claim p95 MISS escalated after worker tuning cut it 77%); security review mt-6.1-01..05 (freeze ruling verified, 8 findings, 0 open critical/high, js-yaml remediated); operator setup guide mt-6.5-01 (real compose dry-run). Gates parallel x5: backend 1670 + 27 PG, bridge 826/837 live, web 442, mobile 268, hygiene green.",
  },
  { date: "next", status: "pending", event: "Wave 3 — State machine, leases, tunnel start (27 docs)", detail: "wp-1.5 → wp-1.6 → wp-1.8 → wp-1.7; wp-5.1 in parallel." },
  { date: "next", status: "pending", event: "Wave 4 — Events, realtime, attachments, edge (32 docs)", detail: "Event log + SSE, attachment pipeline, edge policies, device auth." },
  { date: "next", status: "pending", event: "Wave 5 — Bridge skeleton, hardening, web start (32 docs)", detail: "MCP bridge boots and binds; M1 hardening; web shell with login." },
  { date: "next", status: "pending", event: "Wave 6 — Bridge core tools, web projects, mobile skeleton (36 docs)", detail: "Tool-only contract: availability/claim/release/details/context tools." },
  { date: "next", status: "pending", event: "Wave 7 — Policy core, submission, Kanban (34 docs)", detail: "Deterministic Policy Engine R1–R9, auditor API, live boards." },
  { date: "next", status: "pending", event: "Wave 8 — Agent loop completion (42 docs)", detail: "Checkpoint/submit tools, review decisions, escalation, push, backups." },
  { date: "next", status: "pending", event: "Wave 9 — Merge executor & review UIs (40 docs)", detail: "Host-side merge, diff viewer, review panels, mobile review sheets." },
  { date: "next", status: "pending", event: "Wave 10 — Compatibility, release, hardening (40 docs)", detail: "Client matrix, a11y/perf, observability, VPS rehearsal, tag v1." },
];

/* ---- rendering (no dependencies) ---- */

function renderOverall() {
  const done = waves.reduce((sum, w) => sum + w.done, 0);
  const pct = Math.round((done / TOTAL_DOCS) * 1000) / 10;
  document.getElementById("overall-percent").textContent = pct + "%";
  document.getElementById("overall-bar").style.width = pct + "%";
  document.getElementById("overall-detail").textContent =
    done + " of " + TOTAL_DOCS + " micro-documents implemented (" +
    waves.filter((w) => w.status === "done").length + " of 10 waves complete)";
}

function renderWaves() {
  const container = document.getElementById("wave-bars");
  container.innerHTML = "";
  waves.forEach((w) => {
    const pct = Math.round((w.done / w.total) * 100);
    const row = document.createElement("div");
    row.className = "wave-row";

    const name = document.createElement("div");
    name.className = "name";
    name.textContent = "Wave " + w.id + " · " + w.name;
    const badge = document.createElement("span");
    badge.className = "badge " + w.status;
    badge.textContent = w.status === "active" ? "IN PROGRESS" : w.status.toUpperCase();
    name.appendChild(badge);

    const track = document.createElement("div");
    track.className = "track";
    const fill = document.createElement("div");
    fill.className = "fill" + (w.status === "active" ? " active" : "");
    fill.style.width = pct + "%";
    track.appendChild(fill);

    const count = document.createElement("div");
    count.className = "count";
    count.textContent = w.done + "/" + w.total;

    row.append(name, track, count);
    container.appendChild(row);
  });
}

function renderTimeline() {
  const list = document.getElementById("timeline");
  list.innerHTML = "";
  timeline.forEach((t) => {
    const li = document.createElement("li");
    li.className = t.status;

    const date = document.createElement("div");
    date.className = "date";
    date.textContent = t.date === "next" ? "upcoming" : t.date;

    const event = document.createElement("div");
    event.className = "event";
    event.textContent = t.event;

    const detail = document.createElement("div");
    detail.className = "detail";
    detail.textContent = t.detail;

    li.append(date, event, detail);
    list.appendChild(li);
  });
}

renderOverall();
renderWaves();
renderTimeline();
