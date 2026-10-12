/**
 * Progress data for the AI Agent Task Orchestrator plan series.
 *
 * Update this file at the end of each wave (or whenever micro-documents
 * land). Counts must match plan-doc-series/overview.md — the single source
 * of truth is ai_agent_task_orchestrator_architecture_plan.md; if context
 * of the plan is lost, re-read it before editing this data.
 */

const TOTAL_DOCS = 328;

const waves = [
  { id: 1, name: "Foundations",            total: 22, done: 22, status: "done" },
  { id: 2, name: "Backend foundation",     total: 23, done: 23, status: "done" },
  { id: 3, name: "State machine & leases", total: 27, done: 3,  status: "active" },
  { id: 4, name: "Events, attachments",    total: 32, done: 0,  status: "pending" },
  { id: 5, name: "Bridge skeleton & web",  total: 32, done: 7,  status: "active" },
  { id: 6, name: "Bridge core tools",      total: 36, done: 3,  status: "active" },
  { id: 7, name: "Policy core & Kanban",   total: 34, done: 0,  status: "pending" },
  { id: 8, name: "Agent loop completion",  total: 42, done: 0,  status: "pending" },
  { id: 9, name: "Merge & review UIs",     total: 40, done: 0,  status: "pending" },
  { id: 10, name: "Release & hardening",   total: 40, done: 0,  status: "pending" },
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
    date: "2026-10-12",
    status: "active",
    event: "Max-parallel dispatch — 4 concurrent agents (58/328)",
    detail:
      "Owner directive recorded in roadmap 4a: maximize dependency-safe parallelism. Running: " +
      "wp-1.5 state machine (backend), wp-4.2 project UI + MT-4.1-03 (web), wp-5.3 device auth " +
      "(backend/accounts territory), wp-2.2 manifest binding MT-01..03 (bridge). " +
      "Deferred MTs tracked in WP changelogs (await WP-1.9/1.10, agent-sessions endpoint).",
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
