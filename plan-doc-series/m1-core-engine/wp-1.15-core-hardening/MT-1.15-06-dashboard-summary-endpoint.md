# MT-1.15-06 — Implement the dashboard summary endpoint (`GET /dashboard/summary`)

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-1.15-06 |
| Title | Implement the dashboard summary endpoint (`GET /dashboard/summary`) |
| Parent WP | WP-1.15 — Core engine test and hardening suite (Milestone M1) |
| Requirements | FR-MOB-01 (Overview dashboard: per-project status cards, velocity, active agent counts) |
| Priority | M |
| Dependencies | WP-1.2 (auth + owner-session guard), WP-1.3 (Project registry), WP-1.4 (Task model), WP-1.5 (state machine + TaskTransition history), WP-1.6 (AgentSession lifecycle), MT-5.6-01 (mobile seam contract to reconcile against) |
| Parent sections | 9.2 (Dashboard row: `GET /dashboard/summary`, caller Owner), 7.2 (Task states — the six G-01 keys), 14.1 (Home / Overview: counts per state, velocity, active agents), 5.1 (FR-MOB-01), 12.2 / 9.1 (authorization), 20.4 (global DoD), 20.5 (traceability) |

## Context
Section 9.2 lists `GET /dashboard/summary` (caller **Owner**) in the REST catalog, and
Section 14.1 builds the mobile Home / Overview on it ("project cards: counts per state,
velocity, active agents"), yet no micro-task ever owned the endpoint: WP-5.6 found it
unowned when M5 arrived and shipped the mobile side behind the clean
`DashboardSummarySource` seam with a mocked implementation (its changelog's "Dashboard
endpoint gap" note recommends authoring a backend micro-task — MT-1.6-09 precedent for
unowned-endpoint follow-ups). This micro-task closes that gap: one read-only,
Owner-only endpoint that aggregates per-project data server-side, returning exactly the
card shape WP-5.6 documented (and the hand-authored mobile `DashboardSummary` model
tolerantly parses): `{projects: [{project_id, name, state_counts (the six canonical
G-01 keys), velocity, active_agents}]}`. The payload is authoritative — the mobile
client never computes velocity or active-agent counts itself (MT-5.6-01 risk note).

Two definitions the plan leaves open are pinned here as **documented defaults, never
plan facts** (Section 20.1 item 5 — no hidden decisions), and carried as OQs in the
risk notes:

* **velocity** = the number of tasks in the project that reached `completed` within a
  trailing **7-day** rolling window on the **server clock**, counted from the
  append-only TaskTransition log (`to_state = completed`). Conservative by design: one
  query, server time only (principle P7), no extrapolation or per-day averaging, and
  computed nowhere but the server (the payload is authoritative).
* **active agents** = AgentSession rows of the project with `ended_at IS NULL`
  (Section 7.2 lifecycle; no heartbeat freshness is invented — OQ-04 stays closed).

`state_counts` covers **non-archived** tasks only, mirroring the Board's default
visibility (T19: archived tasks are hidden from boards unless explicitly included).

## Inputs / Prerequisites
* Parent plan Section 9.2 — Dashboard row: `GET /dashboard/summary`, caller Owner; the
  standard error envelope and canonical codes (`AUTH_REQUIRED`, `ROLE_NOT_PERMITTED`).
* Parent plan Section 7.2 — Task entity, the six canonical G-01 states (draft, pending,
  in_progress, to_be_audited, in_human_review, completed; ADR-010), TaskTransition,
  AgentSession (`ended_at`).
* Parent plan Section 14.1 / FR-MOB-01 — Overview contents: per-project counts per
  state, velocity, active agents.
* `docs/plan/conventions/pagination.md` — single-resource GETs (explicitly including
  "dashboard summary") are **not** lists and carry no pagination.
* `plan-doc-series/m5-remote-mobile/wp-5.6-mobile-dashboard-board/CHANGELOG.md` — the
  "Dashboard endpoint gap" note and its recommended card payload; the mobile
  `DashboardSummary` model (`mobile/lib/features/dashboard/dashboard_summary.dart`)
  that defines the reconciliation contract.

## Scope (in)
* A read-only `DashboardSummaryView` (APIView) in `backend/apps/projects/views/`,
  guarded Owner-session-only (`apps.accounts.permissions.IsOwnerSession` — the §9.2
  Owner-caller row guard; §12.2 prints no dashboard row, so no agent/device cell
  exists). Anonymous → `AUTH_REQUIRED` (401); agent token of any role and device
  token → `ROLE_NOT_PERMITTED` (403).
* A serializer module documenting the wire shape for the generated contract (ADR-005):
  top-level `projects` array; per card `project_id`, `name`, `state_counts` (an object
  with exactly the six canonical G-01 keys, integer counts, always present), `velocity`
  (non-negative integer), `active_agents` (non-negative integer).
* A service aggregating, per project (every registered project, ordered by project id —
  the deterministic PID order of `GET /projects`):
  * `state_counts` — per-state counts of the project's non-archived tasks (T19
    default visibility; zero-filled for states with no tasks);
  * `velocity` — tasks reaching `completed` in the trailing 7-day window from the
    TaskTransition log (documented default; OQ in risk notes);
  * `active_agents` — AgentSession rows with `ended_at IS NULL`.
* Mounting the route in `backend/config/urls.py` under the Section 9.2 base path
  (`/api/v1/dashboard/summary`) with a minimal edit.
* Tests in `backend/tests/test_dashboard_summary.py`: payload shape (six G-01 keys
  always present, zero-filled), per-project aggregation correctness (states, archive
  exclusion, velocity window, active vs ended sessions), and the caller matrix —
  Owner 200; coder/auditor/decomposer/merge-executor agent tokens 403
  `ROLE_NOT_PERMITTED`; device token 403; anonymous 401 — including the cross-project
  isolation proof that a project-scoped agent token never receives any project's
  counts (the denial carries only the Section 9.2 error envelope, no data).
* Retiring the `/api/v1/dashboard/summary` entry from `DEFERRED_ENDPOINTS` in
  `backend/tests/test_authorization_matrix.py` (its own drift guard instructs the
  landing micro-task to do so; the real per-caller cases live in this MT's test file).
* A WP-1.15 changelog note (Section 20.4 item 7).

## Out of scope
* Regenerating `schemas/openapi.yaml` — the audit finisher is the SOLE OpenAPI
  regenerator; this path needs a regen as a listed follow-up (Section 20.4 item 4).
* Swapping the mobile `DioDashboardSummarySource` to a generated typed client — M5
  reconciliation follow-up once the schema path lands (the WP-5.6 changelog's
  recommendation; the seam makes it a one-file change).
* Granting **device** (mobile) access to this Owner row — §9.2 names Owner and §12.2
  prints no dashboard cell; a device cell is an owner decision (OQ in risk notes),
  not a silent widening.
* A "needs review" banner field — the mobile derives it from the documented
  `in_human_review` count (no invented field, MT-5.6-01).
* Cursor pagination — dashboard summary is a single-resource GET (pagination.md
  explicitly lists it as non-list).
* Web Overview consumption (Section 13.1) — M4 work, not this endpoint's landing.
* Any event emission — GET-only; the Section 9.6 catalog has no dashboard event
  (Section 20.4 item 6 satisfied by emitting nothing).

## Target paths
* `backend/apps/projects/views/dashboard.py` (new)
* `backend/apps/projects/serializers/dashboard.py` (new)
* `backend/apps/projects/services/dashboard.py` (new)
* `backend/config/urls.py` (minimal mount line)
* `backend/tests/test_dashboard_summary.py` (new)
* `backend/tests/test_authorization_matrix.py` (retire the deferred dashboard entry)
* `plan-doc-series/m1-core-engine/wp-1.15-core-hardening/CHANGELOG.md` (note)

## Acceptance criteria
- [ ] `GET /api/v1/dashboard/summary` resolves and answers 200 for an owner session
      with one card per registered project in project-id order (Section 9.2 Dashboard
      row; FR-MOB-01).
- [ ] Every card carries exactly `project_id`, `name`, `state_counts`, `velocity`,
      `active_agents`; `state_counts` always contains all six canonical G-01 keys
      (zero-filled) and counts only non-archived tasks (Section 7.2; ADR-010; T19
      default visibility).
- [ ] `velocity` equals the project's completions in the trailing 7-day window from
      the TaskTransition log and is documented as a conservative default with the OQ
      recorded (Section 20.1 item 5); `active_agents` counts only sessions with
      `ended_at IS NULL`.
- [ ] Non-owner callers answer catalog codes with the five-field envelope: anonymous
      401 `AUTH_REQUIRED`; every agent role and a device token 403
      `ROLE_NOT_PERMITTED`; a PID-scoped agent token receives no project's counts in
      the response body (ADR-004 isolation; the denial is envelope-only).
- [ ] The response carries no pagination (single-resource GET per pagination.md).
- [ ] The MT doc pins velocity and active-agents as documented defaults with OQs —
      never as plan facts (Section 20.1 item 5).
- [ ] The deferred `/api/v1/dashboard/summary` entry is retired from
      `test_authorization_matrix.py` and this file's tests carry the real cases
      (MT-1.2-07 drift-guard contract).
- [ ] Lint, type check and the named test command green (Section 20.4 item 2); no
      secrets or environment-specific paths (item 3); changelog note added (item 7).
- [ ] Follow-ups recorded: `schemas/openapi.yaml` regen (item 4) and the mobile
      typed-client swap.

## Test command
`uv run --directory backend pytest tests/test_dashboard_summary.py -v` — then the
suite stays green alongside `tests/test_authorization_matrix.py` (deferred entry
retired) and the contract suite (`tests/test_contract.py`).

## Attachments
* [Section 9.2 — REST API surface (Dashboard row)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 7.2 — Entities and key fields (Task states G-01, TaskTransition, AgentSession)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 14.1 — Mobile Home / Overview contents](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [WP-5.6 changelog — the dashboard endpoint gap note](../../m5-remote-mobile/wp-5.6-mobile-dashboard-board/CHANGELOG.md)

## Risk notes
* **Velocity definition is an OQ.** The plan names "velocity" (FR-MOB-01, Section
  14.1) but never defines it. The 7-day rolling completion count above is a
  *documented default* chosen for conservatism (append-only transition log, server
  clock, no invented statistics). Raising the OQ lets the owner pin the window or
  definition later; the payload stays authoritative so the mobile client is never
  tempted to recompute (MT-5.6-01 risk note).
* **Device (mobile) access is a decision, not a default.** FR-MOB-01's Overview runs
  on a device token (ADR-006), but §9.2's caller cell says Owner and §12.2 prints no
  dashboard row — so devices are denied exactly like every other non-Owner caller.
  If mobile Overview must read this row, that is an owner decision to add a cell
  (the WP-1.8 checkpoints precedent: raise the cell as an OQ rather than widen
  silently); until then the mobile Overview against a real backend surfaces the
  honest `ROLE_NOT_PERMITTED` error state.
* **Aggregation cost.** Three grouped queries plus the project list per call — fine
  at NFR-09 scale (10,000 tasks) because each is one indexed query (state,
  transition timestamp, session `ended_at`), but a future cache/refresh knob should
  become an OQ, never a silent constant (Section 20.1 item 5).
* **Concurrent edits.** `config/urls.py` is a shared mount point while other backend
  finishers are active — re-read it immediately before the one-line edit, and touch
  nothing else in it.
