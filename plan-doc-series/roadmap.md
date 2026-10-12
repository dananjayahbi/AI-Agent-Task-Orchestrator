# AI Agent Task Orchestrator — Series Roadmap (10 Waves)

| Field | Value |
|---|---|
| Document type | Execution roadmap — groups all 328 micro-documents in this series into 10 one-directional waves |
| Parent document | `../ai_agent_task_orchestrator_architecture_plan.md` (Architecture & Implementation Plan v1.0) |
| Series index | [`overview.md`](./overview.md) |
| Audience | The project owner and the AI agents that will execute the waves |
| Version | 1.0 |
| Date | 2026-10-11 |

---

## 0. Context-Loss Rule (applies to this whole series)

**If you lose the context of the parent plan `../ai_agent_task_orchestrator_architecture_plan.md`
while reading this roadmap, planning a wave, or executing any micro-document — STOP and re-read
the parent plan (and `overview.md`) before continuing.** Never execute a wave from memory of
the plan; always re-read: Section 19 (work package definitions), Section 20 (micro-task rules),
and the design sections cited by the micro-documents in that wave.

---

## 1. How the waves work

* **One-directional:** a wave may depend only on equal-or-earlier waves. No wave ever waits on a
  later wave. This makes execution strictly forward-moving for AI agents.
* **Complexity-based sizing:** wave sizes range from 22 to 42 micro-documents. Early waves are
  smaller (foundation work is high-risk and needs tighter review); middle waves grow as parallel
  streams multiply; later waves batch integration and hardening work.
* **Within a wave:** work packages (WPs) may run **in parallel** unless §2 lists an explicit
  *order* for that wave. Ordered items must complete in sequence inside the wave.
* **Entry rule for an agent:** before executing a micro-document, re-read its Context sections
  (parent plan) and its Dependencies (earlier MT IDs).
* **Exit rule for a wave:** every micro-document's acceptance criteria passes the global
  definition of done (parent plan Section 20.4), then the wave is marked complete before the
  next wave starts.
* **Scope rule:** a wave contains entire work packages (folders), never partial WPs — a WP is
  the atomic unit of this series (parent plan Section 20.1).

```text
Wave 1 ──> Wave 2 ──> Wave 3 ──> Wave 4 ──> Wave 5 ──> Wave 6 ──> Wave 7 ──> Wave 8 ──> Wave 9 ──> Wave 10
 (M0)      (M1a)      (M1b+5.1)  (M1c+5.2/5.3) (M1d+M2a+4.1) (M2b+4.2+5.5) (M3a+4.3+5.6) (M2c+M3b+M4a+5.4+6.2) (M3c+M4b+M5c) (M2d+M4c+M5d+M6)
```

---

## 2. The 10 waves

### Wave 1 — Foundations (22 documents)

| | |
|---|---|
| Goal | Repository, Compose skeleton, CI gates, recorded decisions, shared conventions — everything later waves assume. |
| Folders | `m0-foundations/` → `wp-0.1-monorepo-scaffolding` (6), `wp-0.2-compose-skeleton` (4), `wp-0.3-ci-pipeline` (5), `wp-0.4-decision-records` (3), `wp-0.5-config-error-conventions` (4) |
| Depends on | Nothing (entry point of the series). |
| Order inside wave | `wp-0.1` → `wp-0.2` → `wp-0.3`; `wp-0.4` must finish before `wp-0.5`. `wp-0.2`/`wp-0.4` may run in parallel with each other. |
| Exit criteria | Fresh clone runs every package's lint/type check with one documented command; the stack starts healthy with data surviving restart; ADR-001..013 recorded; OQ-01..OQ-06 decided; conventions document published and referenced by all packages. |

### Wave 2 — Backend foundation: domain, auth, tasks (23 documents)

| | |
|---|---|
| Goal | Django skeleton, owner/agent/device tokens, project registry, task CRUD — the data model everything else consumes. |
| Folders | `m1-core-engine/` → `wp-1.1-django-skeleton` (5), `wp-1.2-accounts-tokens` (7), `wp-1.3-project-registry` (5), `wp-1.4-task-crud` (6) |
| Depends on | Wave 1 (Compose/env conventions, CI, decisions). |
| Order inside wave | Strict sequence: `wp-1.1` → `wp-1.2` → `wp-1.3` → `wp-1.4`. |
| Exit criteria | Backend healthy under Compose with OpenAPI served; agent token for PID00001 gets `AUTH_FORBIDDEN_PROJECT` on PID00002 resources; generated manifest passes schema validation; 100 concurrent task creations yield unique ids; stale-version updates return `VERSION_CONFLICT`. |

### Wave 3 — State machine, leases, tunnel start (27 documents)

| | |
|---|---|
| Goal | The concurrency core: state machine service, atomic claims, sweeper/retry policy, checkpoints — plus the outbound tunnel service. |
| Folders | `m1-core-engine/` → `wp-1.5-state-machine` (6), `wp-1.6-lease-claim` (8), `wp-1.7-lease-sweeper` (5), `wp-1.8-checkpoints` (4); `m5-remote-mobile/` → `wp-5.1-tunnel-service` (4) |
| Depends on | Wave 2 (task model, tokens). |
| Order inside wave | `wp-1.5` → `wp-1.6` → {`wp-1.8`, `wp-1.9`(wave 4)} … within this wave: `wp-1.5` → `wp-1.6` → `wp-1.8` → `wp-1.7`; `wp-5.1` is independent (parallel with all M1 work). |
| Exit criteria | Every legal transition passes and every illegal pair returns `TASK_STATE_CONFLICT`; 50 concurrent claims produce exactly one winner (NFR-01); a simulated dead worker's task returns to `pending` within lease + 60 s; after `max_retries` the task is `in_human_review` with `retry_exhausted`; `cloudflared` starts with no inbound ports. |

### Wave 4 — Events, realtime, attachments, edge & devices (32 documents)

| | |
|---|---|
| Goal | Append-only event log + SSE realtime; full attachment storage/pipeline; edge access policy and device authentication. |
| Folders | `m1-core-engine/` → `wp-1.9-event-log` (5), `wp-1.10-realtime-sse` (6), `wp-1.11-attachment-upload` (5), `wp-1.12-attachment-pipeline` (8); `m5-remote-mobile/` → `wp-5.2-edge-policies` (4), `wp-5.3-device-auth` (4) |
| Depends on | Wave 3 (lease events, tunnel service in `wp-5.1`); Wave 2 (tokens for device auth). |
| Order inside wave | `wp-1.9` → `wp-1.10`; `wp-1.11` → `wp-1.12`; `wp-5.2` after `wp-5.1` (wave 3); `wp-5.3`, `wp-1.9` groups run in parallel. |
| Exit criteria | Every transition/token action emits exactly one event; SSE reconnect with last id shows no gaps/duplicates with p95 under 2 s; sample corpus (screenshot, scanned PDF, text PDF, DOCX, Markdown) all reaches `ready` or a clear `failed`; blocked routes are denied on the tunnel hostname but succeed on LAN; a revoked device is rejected on its next request. |

### Wave 5 — Bridge skeleton, attachment serving, core hardening, web start (32 documents)

| | |
|---|---|
| Goal | MCP bridge boots and binds to projects; attachment retrieval for agents; M1 hardening suite; web app shell with login. |
| Folders | `m1-core-engine/` → `wp-1.13-description-provider` (5), `wp-1.14-attachment-retrieval` (5), `wp-1.15-core-hardening` (5); `m2-mcp-bridge/` → `wp-2.1-bridge-skeleton` (4), `wp-2.2-manifest-binding` (5), `wp-2.12-init-command` (4); `m4-web-board/` → `wp-4.1-web-skeleton` (4) |
| Depends on | Wave 4 (attachment pipeline, events); Wave 2/3 (claim service for tool contracts). |
| Order inside wave | `wp-1.13` → `wp-1.14` → `wp-1.15`; `wp-2.1` → `wp-2.2` → `wp-2.12`; `wp-4.1` independent. The three groups run in parallel. |
| Exit criteria | Vision session receives an image block and text-only session receives OCR + description with untrusted banner; core test suite green in CI with coverage gates; bridge starts under an MCP inspector; a token mismatch aborts with a clear message; new repo usable via `init` in under 2 minutes; login works and client regeneration fails CI on schema drift. |

### Wave 6 — Bridge core tools, rules, transport, git helper; web projects; mobile skeleton (36 documents)

| | |
|---|---|
| Goal | The tool-only contract delivered: availability/claim/release/details/context tools, rules injection, HTTP transport, git helper; project UI; Flutter skeleton. |
| Folders | `m2-mcp-bridge/` → `wp-2.3-api-client` (5), `wp-2.4-core-tools` (7), `wp-2.7-rules-injection` (4), `wp-2.9-http-transport` (4), `wp-2.10-git-helper` (6); `m4-web-board/` → `wp-4.2-project-ui` (4); `m5-remote-mobile/` → `wp-5.5-flutter-skeleton` (6) |
| Depends on | Wave 5 (`wp-2.1`/`wp-2.2`, `wp-4.1`); Wave 3 (claim service); Wave 4 (device auth for `wp-5.5`). |
| Order inside wave | `wp-2.3` → `wp-2.4` → `wp-2.7`; `wp-2.9` after `wp-2.2`; `wp-2.10` after `wp-2.1`; `wp-4.2` after `wp-4.1`; `wp-5.5` after `wp-5.3`. Otherwise parallel. |
| Exit criteria | Two concurrent `claim_task` calls yield one success + one `TASK_ALREADY_CLAIMED`; rules appear in claim response and initialize instructions; two simultaneous connections for different projects never share state; git helper never pushes or deletes (OS matrix green); manifest can be downloaded and used by `init` in one flow; login, device registration, and biometric enrolment work on both mobile platforms. |

### Wave 7 — Policy core, submission, auditor, policy engine; web board; mobile board (34 documents)

| | |
|---|---|
| Goal | The deterministic quality gate: submission handling with patch artifacts, auditor independence, Policy Engine R1–R9, decomposer; live Kanban on web and mobile. |
| Folders | `m3-audit-policy-merge/` → `wp-3.1-policy-model` (3), `wp-3.2-submission-artifacts` (5), `wp-3.3-auditor-api` (5), `wp-3.4-policy-engine` (7), `wp-3.8-decomposer` (3); `m4-web-board/` → `wp-4.3-kanban-read` (6); `m5-remote-mobile/` → `wp-5.6-mobile-dashboard-board` (5) |
| Depends on | Wave 6 (claim tooling for auditor role, git helper); Wave 3 (state machine, leases); Wave 4/5 (events for realtime views). |
| Order inside wave | `wp-3.1` → `wp-3.2` → `wp-3.3` → `wp-3.4`; `wp-3.8` after `wp-3.2` (task model) and Wave 6 (tools); `wp-4.3` and `wp-5.6` independent of M3 — parallel. |
| Exit criteria | Out-of-scope patch lands in `in_human_review` with `scope_violation`; self-flagged submission lands with `self_flagged`; same session or label cannot audit (`AUDITOR_SAME_AS_CODER`); table-driven rule tests cover each of R1–R9 pass/fail and combinations; decomposer cannot publish or claim; an agent's transition appears on the web board within 2 s without refresh; mobile board resumes with no gaps after suspension. |

### Wave 8 — Bridge audit/submit tools, review decisions, escalation, web editing, push, backups (42 documents)

| | |
|---|---|
| Goal | Complete the agent loop end-to-end: checkpoint/submit with git evidence, capability-aware attachment tool, auditor verdict tool, human review decisions, escalation events, web editing, push notifications, and backup automation. |
| Folders | `m2-mcp-bridge/` → `wp-2.5-attachment-tool` (6), `wp-2.6-checkpoint-submit-tools` (6); `m3-audit-policy-merge/` → `wp-3.5-bridge-audit-tools` (4), `wp-3.6-review-decisions` (4), `wp-3.9-escalation-events` (3); `m4-web-board/` → `wp-4.4-drag-drop` (4), `wp-4.5-task-modal` (6); `m5-remote-mobile/` → `wp-5.4-push-notifications` (5); `m6-hardening-release/` → `wp-6.2-backup-drill` (4) |
| Depends on | Wave 7 (Policy Engine, review reasons, submission); Wave 6 (core tools, git helper); Wave 4 (attachment retrieval, device auth for push). |
| Order inside wave | `wp-3.9` before `wp-5.4` (escalation events feed push); `wp-4.5` after `wp-4.3`; `wp-2.6` after `wp-3.2` (patch endpoint); everything else parallel. |
| Exit criteria | Backend outage during submit does not lose the payload; invalid audit evidence is rejected with guidance; approval referencing an outdated resolution is rejected; each review reason yields exactly one escalation event; disallowed drag-and-drop moves are blocked client-side with explanation; task with three attachments reaches `pending` only when all are `ready`; escalation produces one push within 10 s without duplicates; a fresh host restored from backups passes the smoke tests. |

### Wave 9 — Prompts, merge executor, web detail/review/ops, mobile detail/review (40 documents)

| | |
|---|---|
| Goal | Finish web and mobile review experiences and deliver "completed = merged" via the host-side Merge Executor. |
| Folders | `m2-mcp-bridge/` → `wp-2.8-mcp-prompts` (4); `m3-audit-policy-merge/` → `wp-3.7-merge-executor` (7); `m4-web-board/` → `wp-4.6-task-detail` (4), `wp-4.7-diff-viewer` (5), `wp-4.8-review-panel` (4), `wp-4.9-agents-panel` (3), `wp-4.10-audit-policy-ui` (4); `m5-remote-mobile/` → `wp-5.7-mobile-task-detail` (3), `wp-5.8-mobile-review-sheet` (6) |
| Depends on | Wave 8 (review decisions, patch artifacts, submission); Wave 7 (policy results feed panels); Wave 6 (transport for prompts). |
| Order inside wave | `wp-4.6` → `wp-4.7` → `wp-4.8`; `wp-5.7` → `wp-5.8`; `wp-3.7` after `wp-3.6` (wave 8) and `wp-2.10`; `wp-2.8` after `wp-2.6` (wave 8). `wp-4.9`/`wp-4.10` parallel. |
| Exit criteria | All four prompts list and render in the inspector while workflows still work from tools alone; successful merge completes the task and conflict leaves the developer's working tree untouched escalating with `merge_conflict`; 5,000-line patch renders responsively with flagged files marked; approve triggers merge-pending visible live; stalled indicator appears after `stalled_after_minutes`; approve/request-changes/reassign work end-to-end from the phone with stale approval rejected. |

### Wave 10 — Compatibility, polish, notifications, release, hardening (40 documents)

| | |
|---|---|
| Goal | Verify every agent client, polish web, complete mobile delivery, then harden, document, rehearse the VPS migration, and tag v1. |
| Folders | `m2-mcp-bridge/` → `wp-2.11-client-compatibility` (7); `m4-web-board/` → `wp-4.11-web-a11y-perf` (4); `m5-remote-mobile/` → `wp-5.9-mobile-notifications` (4), `wp-5.10-mobile-release` (5); `m6-hardening-release/` → `wp-6.1-security-review` (5), `wp-6.3-performance-tests` (3), `wp-6.4-observability` (3), `wp-6.5-documentation` (4), `wp-6.6-vps-rehearsal` (5) |
| Depends on | Wave 9 (merge + review complete); Waves 1–9 for M6 items (6.1 needs M1–M5; 6.3 needs M1 + M4; 6.6 needs 6.1/6.3/6.5). |
| Order inside wave | `wp-5.9` after `wp-5.8`; `wp-5.10` after `wp-5.9`; then hardening tail in order: `wp-6.1`, `wp-6.3`, `wp-6.4`, `wp-6.5`, `wp-6.6` (6.6 last of the entire series). `wp-2.11`, `wp-4.11` parallel with mobile work. |
| Exit criteria | Each priority client completes the coder flow end-to-end with the matrix filled with verified facts; no critical accessibility issues and the 500-card board stays responsive; notification tap lands on the correct review sheet after unlock; installable builds pass the real-device checklist; no open high/critical security findings; performance targets met with 20 simulated agents and 10,000 tasks; each Section 17 alert triggerable in a test; someone following only the docs can stand up the stack, onboard a repo, and connect an agent; VPS rehearsal meets success criterion 5 and v1 is tagged. |

---

## 3. Wave summary

| Wave | Name | Documents | Entry depends on | Milestones touched |
|---|---|---|---|---|
| 1 | Foundations | 22 | — | M0 |
| 2 | Backend foundation | 23 | 1 | M1 |
| 3 | State machine & leases | 27 | 2 | M1, M5 |
| 4 | Events, attachments, edge | 32 | 3 | M1, M5 |
| 5 | Bridge skeleton, hardening, web start | 32 | 4 | M1, M2, M4 |
| 6 | Bridge core tools, web projects, mobile skeleton | 36 | 5 | M2, M4, M5 |
| 7 | Policy core, submission, Kanban | 34 | 6 | M3, M4, M5 |
| 8 | Agent loop completion, editing, push, backups | 42 | 7 | M2, M3, M4, M5, M6 |
| 9 | Merge executor, review & detail UIs | 40 | 8 | M2, M3, M4, M5 |
| 10 | Compatibility, release, hardening | 40 | 9 | M2, M4, M5, M6 |
| **Total** | | **328** | | |

---

## 4. Rules for the executing agents

1. **Context-loss rule (repeated deliberately):** if your context of
   `../ai_agent_task_orchestrator_architecture_plan.md` is lost at any point — re-read it
   (and `overview.md`) before touching any micro-document in this series.
2. Execute waves strictly in order 1 → 10; never start wave *N+1* before wave *N*'s exit
   criteria pass.
3. Inside a wave, respect the listed intra-wave order; otherwise parallelize freely.
4. One micro-document = one focused session; if a micro-document exceeds its sizing (parent
   plan Section 20.3), split it and record the new MT id in `overview.md`.
5. No code snippets in plan documents (JSON only when a wire contract must be fixed).
6. Anything undecided becomes an open question (OQ-xx) first — no hidden decisions.
7. Update `overview.md` when an MT is added, split, or renamed; update this roadmap when a
   whole WP moves (never partially).
8. Dogfooding trigger (OQ-14): after Wave 8's minimum set (submission + audit + review +
   merge working), register the orchestrator itself as `PID00001` and manage the remaining
   waves as tasks in the orchestrator.

---

## 4a. Scheduling policy amendment (2026-10-12, owner-approved)

**Dependency-based scheduling replaces strict wave gating (option 2).** The wave structure
above remains the source of truth for *dependencies, grouping, sizing, and exit criteria*,
but a WP (or an MT inside a WP whose own `Dependencies` row is satisfied) may start as soon
as its actual dependencies are green — it does not wait for an entire previous wave's exit
criteria. Rules:

1. A micro-document may start only when its `Dependencies` row lists nothing outstanding;
   blocked MTs are deferred and finished when their dependencies land (record the deferral
   in the WP `CHANGELOG.md`).
2. Each WP is owned by exactly one executing agent at a time; parallel agents must not
   touch files owned by another agent's WP (hot shared contracts: `schemas/openapi.yaml`,
   `docs/plan/conventions/configuration.md`, `infra/compose/.env.example`, migrations —
   single-owner, re-read immediately before editing).
3. Work is committed to `main` at WP boundaries (recovery point after agent failures);
   tests still run at WP completion and wave exit as before.
4. Wave exit criteria still gate the *wave summary* in §3; a wave is reported complete when
   all its WPs are done regardless of when each started.
5. **Owner directive (2026-10-12): maximize parallel dispatch** — the AI token budget is
   effectively unlimited; the orchestrator must keep the maximum number of *dependency-safe,
   file-disjoint* agents running at all times, and proactively scan for newly unblocked WPs
   after every WP completion rather than waiting for wave boundaries.

---

## 5. Related documents

* [`overview.md`](./overview.md) — full index of all 328 micro-documents with descriptions.
* `../ai_agent_task_orchestrator_architecture_plan.md` — parent plan; **re-read whenever context is lost**.
