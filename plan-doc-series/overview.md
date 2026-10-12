# AI Agent Task Orchestrator — Micro-Document Series Overview

| Field | Value |
|---|---|
| Document type | Series index (overview) — master list of every micro-document in `plan-doc-series/` |
| Parent document | `../ai_agent_task_orchestrator_architecture_plan.md` (Architecture & Implementation Plan v1.0) |
| Series purpose | Distribute the implementation complexity of the parent plan across ~328 small, independently executable micro-documents |
| Template | Each micro-document follows the micro-task template in parent plan Section 20.2 |
| Version | 1.0 |
| Date | 2026-10-11 |

---

## 0. Context-Loss Rule (applies to this whole series)

**This series is a derivative of the parent architecture plan. If at any point you lose the
context of `ai_agent_task_orchestrator_architecture_plan.md` — while creating, editing, or
executing any document in this series — STOP and re-read the parent plan before continuing.**

Specifically:

1. Before writing or editing any micro-document in this folder, re-read the parent plan
   sections that the micro-document cites (Section 19 work package definition, plus the
   design sections listed in its Context field).
2. Before executing any micro-document as a task, re-read the parent plan Sections 8
   (state machine), 9 (backend), 10 (bridge), and 20 (micro-task rules) as needed.
3. Every micro-document in this series carries the same re-read reminder in its header —
   if that reminder is missing, restore it.
4. `roadmap.md` carries the same reminder. Any future document added to this series must
   carry it too.

Never rely on memory or summary of the parent plan. The parent plan is the single source
of truth for identifiers (G-, FR-, NFR-, ADR-, WP-, MT-, RISK-, OQ-), canonical state
names, error codes, and policy rules.

---

## 1. Series Conventions

### 1.1 Identifier scheme
* Micro-document ID: `MT-{WP number}-{two-digit sequence}` (parent plan Section 20.2), e.g. `MT-1.6-01`.
* File name: `{MT-ID}-{kebab-case-title}.md`, e.g. `MT-1.6-01-atomic-claim-transaction.md`.
* Folder: one folder per work package: `{milestone-folder}/wp-{WP-number}-{kebab-title}/`.
* Milestone folders: `m0-foundations`, `m1-core-engine`, `m2-mcp-bridge`, `m3-audit-policy-merge`,
  `m4-web-board`, `m5-remote-mobile`, `m6-hardening-release`.

### 1.2 Content rules (mandatory for every micro-document)
* **No code snippets.** JSON appears only when a wire contract or configuration shape must be
  fixed precisely (e.g. manifest example, auditor verdict schema) — copy it by reference to the
  parent plan section rather than re-deriving it.
* Each document must be completable in one focused session (30–90 minutes, parent plan 20.1).
* Each document must be independently verifiable — it names exactly how to prove completion.
* No hidden decisions: anything not decided by the parent plan becomes an open question (OQ)
  first.
* Every micro-document includes the **Context-Loss Rule** header from Section 0 above.

### 1.3 Micro-document template fields (from parent plan Section 20.2)
ID · Title · Parent WP and requirements · Context · Inputs / prerequisites · Scope (in) ·
Out of scope · Target paths · Acceptance criteria · Test command · Attachments · Priority ·
Dependencies · Risk notes.

### 1.4 Global definition of done
See parent plan Section 20.4. Every micro-document's acceptance criteria must be consistent
with it (tests green, contracts updated, canonical error codes, events emitted, changelog note).

### 1.5 Wave planning
All micro-documents are grouped into **10 one-directional waves** in [`roadmap.md`](./roadmap.md).
A wave may only depend on earlier waves — never the reverse.

**Scheduling amendment (2026-10-12, owner-approved):** execution uses **dependency-based
scheduling** — a WP/MT starts as soon as its own `Dependencies` row is satisfied, without
waiting for the previous wave's exit criteria (see `roadmap.md` Section 4a for the full
rules: MT-level dependency checks, single-owner files, commits at WP boundaries, tests at WP
completion and wave exit). The wave grouping, sizing, and exit criteria remain unchanged.

---

## 2. Micro-Document Index

Legend for Priority: **M** = Must have, **S** = Should have, **C** = Could have (parent plan 0.3).

### Milestone M0 — Foundations (`m0-foundations/`)

#### WP-0.1 Monorepo scaffolding and tooling — `m0-foundations/wp-0.1-monorepo-scaffolding/`
Goal: One repository layout with consistent tooling for backend, bridge, web, mobile, infra, docs (ADR-001). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-0.1-01 | Define the monorepo root layout and package boundaries per parent plan Appendix A |
| MT-0.1-02 | Configure Python tooling (formatter, linter, type checker) for backend and bridge |
| MT-0.1-03 | Configure web tooling and package scripts for the Next.js app |
| MT-0.1-04 | Configure mobile tooling and package scripts for the Flutter app |
| MT-0.1-05 | Add pre-commit hooks enforcing format, lint, and secret scans |
| MT-0.1-06 | Create the documentation skeleton (docs/plan, docs/adr, docs/runbooks, docs/agent-guides) |

#### WP-0.2 Compose skeleton and environment template — `m0-foundations/wp-0.2-compose-skeleton/`
Goal: postgres, redis, placeholder backend/web start healthy under Compose with profiles (NFR-06). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-0.2-01 | Define the Compose services per parent plan Section 16.1 with correct dependencies |
| MT-0.2-02 | Configure the internal network and dev/prod profiles |
| MT-0.2-03 | Create the environment template with documented defaults and validation notes |
| MT-0.2-04 | Add health checks and prove data survives a restart |

#### WP-0.3 CI pipeline — `m0-foundations/wp-0.3-ci-pipeline/`
Goal: Automated quality gates from parent plan Section 18. Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-0.3-01 | Add lint and type-check jobs for every package |
| MT-0.3-02 | Add unit and integration test jobs |
| MT-0.3-03 | Add container build job |
| MT-0.3-04 | Add dependency and secret scanning gates |
| MT-0.3-05 | Add build caching to keep the pipeline under 10 minutes |

#### WP-0.4 Decision confirmation and ADR records — `m0-foundations/wp-0.4-decision-records/`
Goal: Resolve parent plan Section 22 open questions blocking M1/M2 and record ADR-001..ADR-013 as accepted. Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-0.4-01 | Run the decision review session and record outcomes for OQ-01..OQ-14 |
| MT-0.4-02 | Write ADR-001 through ADR-013 as accepted decision records in docs/adr |
| MT-0.4-03 | Update the parent plan open-question table with decisions and dates |

#### WP-0.5 Configuration, secrets and error conventions — `m0-foundations/wp-0.5-config-error-conventions/`
Goal: Fix shared conventions (env naming, error envelope, correlation id, idempotency, pagination) before code spreads (NFR-11, NFR-12). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-0.5-01 | Define environment variable naming and grouping conventions per parent plan 9.10 |
| MT-0.5-02 | Publish the canonical error envelope and error-code catalog from parent plan 9.2 |
| MT-0.5-03 | Define correlation-id and idempotency header conventions |
| MT-0.5-04 | Define cursor-based pagination conventions for all list endpoints |

### Milestone M1 — Core Engine (Backend) (`m1-core-engine/`)

#### WP-1.1 Django project skeleton — `m1-core-engine/wp-1.1-django-skeleton/`
Goal: ASGI project with env-split settings, DRF, OpenAPI, health endpoints, structured logging (NFR-10, NFR-11). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.1-01 | Create the Django ASGI project with settings split by environment |
| MT-1.1-02 | Add structured JSON logging with correlation-id propagation |
| MT-1.1-03 | Implement /health/live and /health/ready endpoints |
| MT-1.1-04 | Generate and serve the OpenAPI document, validated in CI |
| MT-1.1-05 | Build the backend container image and wire it into Compose |

#### WP-1.2 Accounts, tokens and permissions — `m1-core-engine/wp-1.2-accounts-tokens/`
Goal: Owner login, project-scoped agent tokens, device tokens, hashing, revocation, permissions (ADR-004, FR-SEC-01/02/05). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.2-01 | Implement owner session authentication (login/logout/refresh) |
| MT-1.2-02 | Create the API token model with hashed storage and expiry fields |
| MT-1.2-03 | Implement project-scoped agent token issuance and revocation |
| MT-1.2-04 | Create the device token model for mobile registration |
| MT-1.2-05 | Implement permission classes enforcing the authorization matrix (Section 12.2) |
| MT-1.2-06 | Add rate limiting on agent and device endpoints |
| MT-1.2-07 | Write authorization-matrix tests incl. cross-project rejection |

#### WP-1.3 Project registry, policy and manifest — `m1-core-engine/wp-1.3-project-registry/`
Goal: Project CRUD with PID generation, Project Policy with defaults, manifest generation (FR-PRJ-01..05). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.3-01 | Implement atomic PID identifier generation (PID[0-9]{5}) |
| MT-1.3-02 | Create Project and ProjectPolicy models with migrations and defaults |
| MT-1.3-03 | Implement project CRUD endpoints with Active/Paused/Archived status |
| MT-1.3-04 | Implement policy read/patch endpoints with validation |
| MT-1.3-05 | Create the orchestrator.json manifest schema and renderer |

#### WP-1.4 Task model, id sequencing and CRUD — `m1-core-engine/wp-1.4-task-crud/`
Goal: Tasks with canonical fields, atomic id sequencing, priorities, dependencies, optimistic versioning, soft archive (FR-TSK-01/02/05/06/07/08). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.4-01 | Create the Task model with fields and check constraints for id patterns |
| MT-1.4-02 | Implement atomic per-project task counter for gap-tolerant ids |
| MT-1.4-03 | Implement task CRUD endpoints |
| MT-1.4-04 | Implement list filters and priority/FIFO ordering |
| MT-1.4-05 | Implement task dependency relation (depends_on) |
| MT-1.4-06 | Implement soft archive and read-only completed state |

#### WP-1.5 State machine service and transition history — `m1-core-engine/wp-1.5-state-machine/`
Goal: Single service implementing parent plan Section 8.2 with guards, side effects, transactional history (FR-TSK-03/04). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.5-01 | Build the transition registry and guard framework |
| MT-1.5-02 | Implement owner transitions T2 (publish), T3 (unpublish), T19 (archive) |
| MT-1.5-03 | Implement system transitions T5 (lease expired), T9 (retry exhausted) |
| MT-1.5-04 | Implement agent transition stubs T4/T6/T7/T8 for later wiring |
| MT-1.5-05 | Create the append-only Task Transition history model with insert-only permissions |
| MT-1.5-06 | Write the exhaustive transition matrix tests (legal + illegal pairs) |

#### WP-1.6 Lease and claim service — `m1-core-engine/wp-1.6-lease-claim/`
Goal: Atomic claim with skip-locked semantics, fencing, extension, release, concurrency limit (FR-LEA-01/02/03/06/08). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.6-01 | Implement the atomic claim transaction with row lock and skip-locked |
| MT-1.6-02 | Implement next-available selection ordered by priority then creation |
| MT-1.6-03 | Implement lease extension rules with hard total-age cap |
| MT-1.6-04 | Implement voluntary release without failure increment |
| MT-1.6-05 | Implement lease fencing generation on every claim |
| MT-1.6-06 | Enforce per-project max_concurrent_tasks at claim time |
| MT-1.6-07 | Implement claim and release REST endpoints |
| MT-1.6-08 | Write claim race tests (50 concurrent claimants, exactly one winner) |

#### WP-1.7 Lease sweeper and retry policy — `m1-core-engine/wp-1.7-lease-sweeper/`
Goal: Celery beat job reclaiming expired leases and escalating retry exhaustion (FR-LEA-04/05/07). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.7-01 | Wire Celery worker and beat services into Compose |
| MT-1.7-02 | Implement the idempotent lease sweeper job (60 s interval) |
| MT-1.7-03 | Implement retry-exhaustion escalation to in_human_review (retry_exhausted) |
| MT-1.7-04 | Implement the lease-expiring warning event at 80% of lease |
| MT-1.7-05 | Write the sweeper chaos test (dead worker reclaim, double-sweeper safety) |

#### WP-1.8 Checkpoints and token usage — `m1-core-engine/wp-1.8-checkpoints/`
Goal: Store progress reports, extend lease, validate ownership and fencing (FR-LEA-03). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.8-01 | Create the Task Checkpoint model with kind and token_usage fields |
| MT-1.8-02 | Implement lease ownership and fencing validation for checkpoints |
| MT-1.8-03 | Implement the checkpoint endpoint returning new lease expiry |
| MT-1.8-04 | Implement checkpoint listing with pagination |

#### WP-1.9 Event log and audit trail — `m1-core-engine/wp-1.9-event-log/`
Goal: Append-only event store written in the same transaction as state changes (P8, FR-SEC-03). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.9-01 | Create the Event log model with monotonic sequence used as SSE event id |
| MT-1.9-02 | Implement the write-in-transaction event helper |
| MT-1.9-03 | Implement post-commit publish to the Redis channel |
| MT-1.9-04 | Apply insert-only database permissions to transition and event tables |
| MT-1.9-05 | Write event catalog tests covering every required emission (Section 9.6) |

#### WP-1.10 Realtime gateway (SSE) — `m1-core-engine/wp-1.10-realtime-sse/`
Goal: Authenticated stream with filters, heartbeat, lossless resume (ADR-002, FR-WEB-05, NFR-03). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.10-01 | Implement the authenticated SSE stream endpoint with filters |
| MT-1.10-02 | Implement Redis fan-out to connected stream subscribers |
| MT-1.10-03 | Implement lossless resume via last event id (no gaps, no duplicates) |
| MT-1.10-04 | Add 15-second heartbeat comments for proxy keep-alive |
| MT-1.10-05 | Implement per-connection and per-event authorization filtering |
| MT-1.10-06 | Write the SSE delivery load test (p95 under 2 s locally) |

#### WP-1.11 Attachment storage and upload API — `m1-core-engine/wp-1.11-attachment-upload/`
Goal: Validated uploads to a storage abstraction (local volume now, S3-compatible later) (FR-ATT-01). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.11-01 | Create the storage abstraction layer (local volume + S3-compatible seam) |
| MT-1.11-02 | Implement upload validation: size, MIME content sniffing, de-duplication |
| MT-1.11-03 | Implement the multipart attachment upload endpoint |
| MT-1.11-04 | Implement attachment descriptor listing (id, filename, size, status) |
| MT-1.11-05 | Implement deletion rules and retention hooks |

#### WP-1.12 Attachment pipeline: parse, OCR, chunk, tokens — `m1-core-engine/wp-1.12-attachment-pipeline/`
Goal: Async processing producing text, chunks, token estimates, summaries (FR-ATT-02/07, parent plan 9.5). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.12-01 | Implement pipeline type detection and checksum stage |
| MT-1.12-02 | Implement image normalization and OCR stage |
| MT-1.12-03 | Implement PDF text extraction with OCR fallback for scanned pages |
| MT-1.12-04 | Implement DOCX and Markdown extraction |
| MT-1.12-05 | Implement page/chunk splitting and token estimation |
| MT-1.12-06 | Implement short summary generation per document |
| MT-1.12-07 | Implement processing status transitions with retry/backoff |
| MT-1.12-08 | Write sample-corpus tests (screenshot, scanned PDF, text PDF, DOCX, Markdown) |

#### WP-1.13 Visual description provider — `m1-core-engine/wp-1.13-description-provider/`
Goal: Pluggable provider generating layout captions once and caching them (G-14, FR-ATT-02/05). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.13-01 | Define the DescriptionProvider interface (disabled / remote-vision implementations) |
| MT-1.13-02 | Implement the disabled provider (no external calls) |
| MT-1.13-03 | Implement the remote vision-model provider with configuration and cost logging |
| MT-1.13-04 | Implement permanent per-attachment description caching |
| MT-1.13-05 | Implement failure degradation to OCR-only output |

#### WP-1.14 Attachment retrieval API — `m1-core-engine/wp-1.14-attachment-retrieval/`
Goal: Format-aware, paginated content endpoint with untrusted banner (FR-ATT-03/04/06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.14-01 | Define the attachment descriptor payload shape for task payloads |
| MT-1.14-02 | Implement format-preference resolution (auto, image_base64, text_ocr, markdown) |
| MT-1.14-03 | Implement pagination with page_number, total_pages, and token counts |
| MT-1.14-04 | Apply the untrusted-content banner to all text outputs |
| MT-1.14-05 | Implement format errors (ATTACHMENT_NOT_READY, unsupported format) |

#### WP-1.15 Core engine test and hardening suite — `m1-core-engine/wp-1.15-core-hardening/`
Goal: Consolidated concurrency, race, and authorization tests promoted to CI (NFR-01, NFR-12). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-1.15-01 | Build the claim race test suite |
| MT-1.15-02 | Build the sweeper race test suite |
| MT-1.15-03 | Build the idempotency test suite for claim/checkpoint/submit/decision |
| MT-1.15-04 | Build the authorization test suite covering the full matrix |
| MT-1.15-05 | Add coverage gates (85% target on state machine, leases, policy engine) |

### Milestone M2 — Universal MCP Bridge (`m2-mcp-bridge/`)

#### WP-2.1 Bridge package skeleton — `m2-mcp-bridge/wp-2.1-bridge-skeleton/`
Goal: Python package launched through `uv`, MCP SDK, config layering, logging (FR-MCP-01). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.1-01 | Create the bridge package layout with src modules |
| MT-2.1-02 | Implement configuration layering (environment over user-level file) |
| MT-2.1-03 | Add structured bridge logging |
| MT-2.1-04 | Create STDIO, HTTP, and executor entry points (stubs initially) |

#### WP-2.2 Manifest discovery, schema validation and session binding — `m2-mcp-bridge/wp-2.2-manifest-binding/`
Goal: Parent plan 10.3 implemented including mismatch aborts (FR-MCP-02/06, FR-SEC-01). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.2-01 | Implement upward manifest discovery to the Git root |
| MT-2.2-02 | Implement manifest schema validation and version compatibility check |
| MT-2.2-03 | Implement agent token loading from environment or user-level config |
| MT-2.2-04 | Implement backend session open/end with project context caching |
| MT-2.2-05 | Implement project-mismatch abort with a clear startup error |

#### WP-2.3 Backend API client — `m2-mcp-bridge/wp-2.3-api-client/`
Goal: Typed client with auth, retries, idempotency keys, canonical error translation (NFR-04, NFR-12). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.3-01 | Implement the transport and authentication layer |
| MT-2.3-02 | Implement retry policy with backoff for 5xx and timeouts |
| MT-2.3-03 | Implement idempotency key attachment on mutating calls |
| MT-2.3-04 | Implement error translation to code + hint + next-action |
| MT-2.3-05 | Write the contract test against the OpenAPI schema |

#### WP-2.4 Tools: availability, details, claim, release, context — `m2-mcp-bridge/wp-2.4-core-tools/`
Goal: get_available_tasks, get_task_details, claim_task, release_task, get_project_context (FR-MCP-03, FR-LEA-01). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.4-01 | Define deterministic schemas for the five core tools |
| MT-2.4-02 | Implement get_available_tasks with role parameter and filters |
| MT-2.4-03 | Implement get_task_details with criteria, scope, feedback |
| MT-2.4-04 | Implement claim_task returning lease, rules block, branch name |
| MT-2.4-05 | Implement release_task (voluntary, no failure increment) |
| MT-2.4-06 | Implement get_project_context for cheap orientation |
| MT-2.4-07 | Write core-tool tests incl. concurrent claim outcomes |

#### WP-2.5 Tool: read_task_attachment with capability negotiation — `m2-mcp-bridge/wp-2.5-attachment-tool/`
Goal: Parent plan 10.4/9.5 behavior with MCP image blocks and text fallback (FR-ATT-04/05/06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.5-01 | Implement the capability resolver (explicit param, config, client table, default) |
| MT-2.5-02 | Create the editable client capability table file |
| MT-2.5-03 | Implement image content-block packaging for vision sessions |
| MT-2.5-04 | Implement text/OCR packaging with untrusted banner for text-only sessions |
| MT-2.5-05 | Implement attachment pagination parameters |
| MT-2.5-06 | Write capability tests for both vision and text-only paths |

#### WP-2.6 Tools: checkpoint and submission with Git evidence — `m2-mcp-bridge/wp-2.6-checkpoint-submit-tools/`
Goal: log_task_checkpoint and submit_task_resolution with local patch capture (FR-MCP-07, FR-LEA-03). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.6-01 | Implement log_task_checkpoint returning next-due hint and new expiry |
| MT-2.6-02 | Implement branch and commit-sha verification before submission |
| MT-2.6-03 | Implement merge-base patch capture with stats and changed-file list |
| MT-2.6-04 | Implement resolution upload with idempotency |
| MT-2.6-05 | Implement local payload retention and retry across backend outages |
| MT-2.6-06 | Document deferral of optional output-tail attachment (G-11, Could) |

#### WP-2.7 Rules injection — `m2-mcp-bridge/wp-2.7-rules-injection/`
Goal: Parent plan 10.6 delivered via instructions, tool descriptions, claim response (FR-MCP-05). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.7-01 | Create coder and auditor rules templates per parent plan 10.6 |
| MT-2.7-02 | Implement project-specific rules merging from system_prompt_rules |
| MT-2.7-03 | Deliver rules through initialize instructions and claim responses |
| MT-2.7-04 | Write per-client fallback instruction snippets (G-08) |

#### WP-2.8 MCP prompts — `m2-mcp-bridge/wp-2.8-mcp-prompts/`
Goal: Four prompts from parent plan 10.7 (FR-MCP-04). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.8-01 | Implement prompt orchestrator:start_work |
| MT-2.8-02 | Implement prompt orchestrator:checkpoint |
| MT-2.8-03 | Implement prompt orchestrator:submit_for_audit |
| MT-2.8-04 | Implement prompt orchestrator:audit |

#### WP-2.9 HTTP/SSE transport with per-connection binding — `m2-mcp-bridge/wp-2.9-http-transport/`
Goal: Network transport where each connection binds to a project from URL and token (FR-MCP-01/06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.9-01 | Implement the local HTTP/SSE server mode |
| MT-2.9-02 | Implement per-connection project binding from URL path and token |
| MT-2.9-03 | Implement connection lifecycle and connection limits |
| MT-2.9-04 | Write the two-connections cross-project isolation test |

#### WP-2.10 Local Git helper — `m2-mcp-bridge/wp-2.10-git-helper/`
Goal: Read-mostly Git operations, secret scan, optional worktree mode (FR-MCP-07). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.10-01 | Implement repository identity and clean-state checks |
| MT-2.10-02 | Implement branch naming derivation (prefix + task index, G-09) |
| MT-2.10-03 | Implement merge-base diff computation with stats and changed files |
| MT-2.10-04 | Implement secret-like pattern scan of added lines (feeds rule R5) |
| MT-2.10-05 | Implement optional per-task worktree helper (OQ-03) |
| MT-2.10-06 | Write OS matrix tests (Windows, macOS, Linux; paths with spaces) |

#### WP-2.11 Client compatibility verification and conformance script — `m2-mcp-bridge/wp-2.11-client-compatibility/`
Goal: Fill parent plan 10.9 matrix with verified facts and publish setup guides (NFR-08). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.11-01 | Build the MCP conformance script exercising all tools and prompts |
| MT-2.11-02 | Verify Claude Code CLI (reference client) and record results |
| MT-2.11-03 | Verify VS Code Copilot and record results |
| MT-2.11-04 | Verify OpenCode and record results |
| MT-2.11-05 | Verify Aider and record results |
| MT-2.11-06 | Verify DeepSeek-based harness (text-only path) and record results |
| MT-2.11-07 | Publish the custom-agent setup template and finalize the compatibility matrix |

#### WP-2.12 `init` command — `m2-mcp-bridge/wp-2.12-init-command/`
Goal: One-time project onboarding command (FR-MCP-08). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-2.12-01 | Implement manifest writing in the init command |
| MT-2.12-02 | Implement agent token storage in user-level config |
| MT-2.12-03 | Implement connectivity self-test against the backend |
| MT-2.12-04 | Print per-client agent configuration snippets |

### Milestone M3 — Audit, Policy and Merge (`m3-audit-policy-merge/`)

#### WP-3.1 Policy model and defaults — `m3-audit-policy-merge/wp-3.1-policy-model/`
Goal: Persist all Project Policy fields with framework presets (FR-PRJ-05). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.1-01 | Persist all Project Policy fields with defaults from parent plan 7.2 |
| MT-3.1-02 | Create framework preset library (Django, Next.js, Flutter glob sets) |
| MT-3.1-03 | Implement policy validation (glob syntax, ranges) |

#### WP-3.2 Submission handling and artifacts — `m3-audit-policy-merge/wp-3.2-submission-artifacts/`
Goal: Backend side of submission: resolution, patch artifacts, stats, scope check, T7/T8/T10 (FR-AUD-01, FR-TSK-03). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.2-01 | Create the Task Resolution model and submission endpoint |
| MT-3.2-02 | Implement patch artifact storage with the 5 MB size cap |
| MT-3.2-03 | Implement authoritative patch parsing for stats and changed-file list |
| MT-3.2-04 | Implement scope violation check against target_scope |
| MT-3.2-05 | Implement submission transitions T7, T8, T10 with review reasons |

#### WP-3.3 Auditor claim and verdict API — `m3-audit-policy-merge/wp-3.3-auditor-api/`
Goal: Role-aware claim, independence rule, verdict endpoint, audit leases (G-03, G-20, FR-AUD-01/02). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.3-01 | Add auditor role gating to work listing and claim |
| MT-3.3-02 | Implement auditor independence rule (AUDITOR_SAME_AS_CODER) |
| MT-3.3-03 | Implement audit lease handling with expiry release |
| MT-3.3-04 | Create the Audit Report model with evidence JSON and confidence |
| MT-3.3-05 | Implement the audit verdict endpoint |

#### WP-3.4 Policy Engine — `m3-audit-policy-merge/wp-3.4-policy-engine/`
Goal: Rules R1–R9, versioned, persisted rule results, deterministic decisions (ADR-009, FR-AUD-02/03/04). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.4-01 | Build the policy evaluator framework (pure, versioned, testable) |
| MT-3.4-02 | Implement R1 tests and R2 scope rules |
| MT-3.4-03 | Implement R3 critical paths, R4 migrations, R5 sensitive config rules |
| MT-3.4-04 | Implement R6 diff size and R7 confidence rules |
| MT-3.4-05 | Implement R8 auditor flag and R9 auto-complete switch rules |
| MT-3.4-06 | Persist rule results and engine version on every audit report |
| MT-3.4-07 | Integrate policy decisions with transitions T13 and T14 |

#### WP-3.5 Bridge audit tools — `m3-audit-policy-merge/wp-3.5-bridge-audit-tools/`
Goal: submit_audit_verdict with schema validation and auditor flow (FR-AUD-01/02). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.5-01 | Define the submit_audit_verdict schema per parent plan 10.5 |
| MT-3.5-02 | Implement structured evidence validation (commands, exit codes, criteria) |
| MT-3.5-03 | Implement the auditor flow with auditor rules integration |
| MT-3.5-04 | Write auditor tool tests incl. invalid evidence guidance |

#### WP-3.6 Human review decisions API — `m3-audit-policy-merge/wp-3.6-review-decisions/`
Goal: Approve, request changes, reassign with history and feedback propagation (T15, T16, FR-AUD-05). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.6-01 | Implement the review decision endpoint (approve / request_changes / reassign) |
| MT-3.6-02 | Create the Review Decision model with decided_via fields |
| MT-3.6-03 | Implement latest_feedback propagation into get_task_details |
| MT-3.6-04 | Implement stale-resolution protection on approvals |

#### WP-3.7 Merge queue and Merge Executor — `m3-audit-policy-merge/wp-3.7-merge-executor/`
Goal: Host-side executor performing merges in an isolated worktree (ADR-008, FR-AUD-06). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.7-01 | Implement the merge queue API (pending / start / result) |
| MT-3.7-02 | Implement the executor loop in the bridge package |
| MT-3.7-03 | Implement isolated temporary worktree handling (never touches dev tree) |
| MT-3.7-04 | Implement merge strategies (squash, merge_commit, fast_forward_only, manual) |
| MT-3.7-05 | Implement conflict reporting back to in_human_review (merge_conflict) |
| MT-3.7-06 | Implement crash recovery on executor restart |
| MT-3.7-07 | Write the merge end-to-end test (success + conflict paths) |

#### WP-3.8 Decomposer support — `m3-audit-policy-merge/wp-3.8-decomposer/`
Goal: create_draft_task with role restriction and dependencies (UC-10). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.8-01 | Implement the decomposer role permission (draft-only) |
| MT-3.8-02 | Implement the create_draft_task tool with depends_on |
| MT-3.8-03 | Write decomposer restriction tests (cannot publish or claim) |

#### WP-3.9 Escalation notifications hook — `m3-audit-policy-merge/wp-3.9-escalation-events/`
Goal: Emit review.requested events with reasons ready for push (FR-MOB-04). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-3.9-01 | Define the review.requested event payload with rule details |
| MT-3.9-02 | Implement escalation event emission on every in_human_review entry |
| MT-3.9-03 | Write escalation tests covering each review reason |

### Milestone M4 — Web Operations Board (`m4-web-board/`)

#### WP-4.1 Web skeleton, auth and generated API client — `m4-web-board/wp-4.1-web-skeleton/`
Goal: Next.js app with login, protected routes, typed client, theming (NFR-11, FR-WEB-01). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.1-01 | Scaffold the Next.js application (App Router) |
| MT-4.1-02 | Implement login and protected routes |
| MT-4.1-03 | Set up typed API client generation from OpenAPI in CI |
| MT-4.1-04 | Set up theming, layout, and canonical error-code mapping |

#### WP-4.2 Project switcher, project CRUD, manifest and tokens UI — `m4-web-board/wp-4.2-project-ui/`
Goal: Manage projects and agent tokens (FR-PRJ-01/03, FR-WEB-09). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.2-01 | Implement the project list and switcher |
| MT-4.2-02 | Implement project create/edit forms with status transitions |
| MT-4.2-03 | Implement manifest download and copy UI |
| MT-4.2-04 | Implement agent token create/revoke UI with one-time reveal |

#### WP-4.3 Kanban board (read) with realtime — `m4-web-board/wp-4.3-kanban-read/`
Goal: Six-column board, filters, cards, live updates via stream hook (FR-WEB-01/05). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.3-01 | Implement the six board columns mapped to canonical states |
| MT-4.3-02 | Implement the task card component (id, priority, worker, progress) |
| MT-4.3-03 | Implement board filters and search |
| MT-4.3-04 | Implement the SSE stream hook with reconnect and status |
| MT-4.3-05 | Implement query-cache patching from stream events |
| MT-4.3-06 | Add column virtualization for 500-card boards |

#### WP-4.4 Drag-and-drop with validation — `m4-web-board/wp-4.4-drag-drop/`
Goal: Move rules from parent plan 13.2 with optimistic updates (FR-WEB-02). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.4-01 | Define the allowed-move map (client-side) |
| MT-4.4-02 | Integrate drag-and-drop onto the board |
| MT-4.4-03 | Implement confirmation dialogs for approve-merge and request-changes moves |
| MT-4.4-04 | Implement optimistic update with rollback on version/state conflicts |

#### WP-4.5 Task creation/edit modal and attachment uploader — `m4-web-board/wp-4.5-task-modal/`
Goal: Full task editor with markdown, criteria, scope, dependencies, uploads (FR-WEB-03, FR-ATT-07). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.5-01 | Implement the task form modal with field validation |
| MT-4.5-02 | Integrate markdown editor with preview |
| MT-4.5-03 | Implement acceptance-criteria and target-scope glob editors |
| MT-4.5-04 | Implement the dependencies picker |
| MT-4.5-05 | Implement the attachment uploader with progress and processing status |
| MT-4.5-06 | Implement the publish action gated on attachment readiness |

#### WP-4.6 Task detail: checkpoints, resolutions, attachments — `m4-web-board/wp-4.6-task-detail/`
Goal: Detail view with live feed and attachment viewer (FR-WEB-04). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.6-01 | Implement the task detail layout (drawer or page) |
| MT-4.6-02 | Implement the live checkpoint feed |
| MT-4.6-03 | Implement resolutions and transition history views |
| MT-4.6-04 | Implement the attachment viewer with OCR/description tabs |

#### WP-4.7 Diff viewer — `m4-web-board/wp-4.7-diff-viewer/`
Goal: Patch rendering with file tree and highlighting (FR-WEB-04). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.7-01 | Implement the unified patch parser for the viewer |
| MT-4.7-02 | Implement unified and split diff views with syntax highlighting |
| MT-4.7-03 | Implement the file tree with jump-to-file |
| MT-4.7-04 | Implement the large-diff fallback ("diff too large" marker) |
| MT-4.7-05 | Implement rule-flag markers on files flagged by policy results |

#### WP-4.8 Human review panel and queue — `m4-web-board/wp-4.8-review-panel/`
Goal: Review workflow UI with rule table and three actions (FR-WEB-06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.8-01 | Implement the cross-project review queue page |
| MT-4.8-02 | Implement the review panel with reasons, rule table, and evidence |
| MT-4.8-03 | Implement approve / request-changes / reassign actions with confirmation |
| MT-4.8-04 | Implement live merge-status display (pending → merged) |

#### WP-4.9 Agents and leases panel — `m4-web-board/wp-4.9-agents-panel/`
Goal: Live view of sessions, leases, countdowns, stalled markers (FR-WEB-07). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.9-01 | Implement the live agent sessions list |
| MT-4.9-02 | Implement lease countdown displays |
| MT-4.9-03 | Implement stalled-task indicators (stalled_after_minutes) |

#### WP-4.10 Audit log viewer and policy editor — `m4-web-board/wp-4.10-audit-policy-ui/`
Goal: Event history viewer and policy/rules editing UI (FR-WEB-08/09). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.10-01 | Implement the audit log viewer |
| MT-4.10-02 | Implement log filters (project, task, actor, date, type) |
| MT-4.10-03 | Implement the policy editor form with preset selection |
| MT-4.10-04 | Implement the rules editor with rules-block preview |

#### WP-4.11 Responsive, accessibility and performance pass — `m4-web-board/wp-4.11-web-a11y-perf/`
Goal: Meet NFR-13 and parent plan 13.4 targets. Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-4.11-01 | Implement responsive layouts incl. phone-browser fallback |
| MT-4.11-02 | Implement keyboard navigation for board and dialogs |
| MT-4.11-03 | Fix contrast and label accessibility findings |
| MT-4.11-04 | Run the performance pass against the 500-card board target |

### Milestone M5 — Remote Access and Mobile (`m5-remote-mobile/`)

#### WP-5.1 `cloudflared` service and tunnel ingress — `m5-remote-mobile/wp-5.1-tunnel-service/`
Goal: Outbound-only tunnel in Compose with hostname and route mapping (FR-NET-01/02). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.1-01 | Add the cloudflared Compose service |
| MT-5.1-02 | Configure ingress mapping to web and backend |
| MT-5.1-03 | Document hostname configuration and tunnel token handling |
| MT-5.1-04 | Verify SSE stability through the tunnel (30 min idle test) |

#### WP-5.2 Edge policies and route allowlist — `m5-remote-mobile/wp-5.2-edge-policies/`
Goal: Access policy on tunnel hostname and route restrictions per parent plan 15.2 (FR-NET-01, FR-SEC-05). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.2-01 | Define the Cloudflare Access policy for the tunnel hostname |
| MT-5.2-02 | Implement the route allowlist per parent plan Section 15.2 |
| MT-5.2-03 | Add edge and API rate limits |
| MT-5.2-04 | Write the blocked-vs-allowed route verification checklist |

#### WP-5.3 Device registration and mobile authentication — `m5-remote-mobile/wp-5.3-device-auth/`
Goal: Device registration, device-bound tokens, revocation (ADR-006, FR-SEC-02, FR-MOB-06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.3-01 | Implement device registration endpoints |
| MT-5.3-02 | Implement device-bound token issuance and release after biometric success |
| MT-5.3-03 | Implement device revocation with immediate rejection |
| MT-5.3-04 | Implement device list and revoke UI in web account settings |

#### WP-5.4 Push notifications (FCM) — `m5-remote-mobile/wp-5.4-push-notifications/`
Goal: Notification dispatch with dedupe and delivery tracking (FR-MOB-04, NFR-03). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.4-01 | Configure FCM credentials and the worker-side sender |
| MT-5.4-02 | Define minimal push payloads (ids and short title only) |
| MT-5.4-03 | Implement dedupe keys (event type, task id, state version) |
| MT-5.4-04 | Implement delivery tracking and invalid-token pruning |
| MT-5.4-05 | Implement per-event-type notification preferences |

#### WP-5.5 Flutter skeleton and API client — `m5-remote-mobile/wp-5.5-flutter-skeleton/`
Goal: App shell, environment flavors, generated client, secure storage, SSE client (NFR-11). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.5-01 | Scaffold the Flutter application with feature-first structure |
| MT-5.5-02 | Configure environment flavors (dev/prod endpoints) |
| MT-5.5-03 | Generate the typed API client from the shared OpenAPI schema |
| MT-5.5-04 | Implement secure token storage and biometric gate |
| MT-5.5-05 | Implement the SSE client with resume |
| MT-5.5-06 | Implement onboarding screens (URL, login, device registration) |

#### WP-5.6 Overview dashboard and mobile Kanban — `m5-remote-mobile/wp-5.6-mobile-dashboard-board/`
Goal: FR-MOB-01 and FR-MOB-02 — project cards, velocity, paged board, live updates. Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.6-01 | Implement dashboard summary consumption and project cards |
| MT-5.6-02 | Implement the project selector |
| MT-5.6-03 | Implement the horizontally paged six-state board |
| MT-5.6-04 | Implement live updates while foregrounded |
| MT-5.6-05 | Implement resume replay from last event id after suspension |

#### WP-5.7 Task detail and live checkpoint stream — `m5-remote-mobile/wp-5.7-mobile-task-detail/`
Goal: FR-MOB-03 — detail screen, streaming feed, attachment viewing. Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.7-01 | Implement the task detail screen |
| MT-5.7-02 | Implement the live checkpoint feed surviving backgrounding |
| MT-5.7-03 | Implement attachment viewing (image, OCR, document pages) |

#### WP-5.8 Review action sheet — `m5-remote-mobile/wp-5.8-mobile-review-sheet/`
Goal: Parent plan 14.2 review flow — diff, approve safety, dictated notes (FR-MOB-05). Size L.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.8-01 | Implement the review sheet layout |
| MT-5.8-02 | Implement rule results and evidence display |
| MT-5.8-03 | Implement the lazy per-file diff renderer with highlighting |
| MT-5.8-04 | Implement approve-and-merge with resolution-bound confirmation |
| MT-5.8-05 | Implement request-changes with dictated (speech-to-text) note |
| MT-5.8-06 | Implement the reassign action |

#### WP-5.9 Push deep links, notification center and audit log — `m5-remote-mobile/wp-5.9-mobile-notifications/`
Goal: Tap-to-review, in-app notification history, read-only audit log (FR-MOB-04/07). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.9-01 | Implement deep-link routing to review sheet behind biometric gate |
| MT-5.9-02 | Implement the foreground notification banner |
| MT-5.9-03 | Implement notification history with per-type toggles |
| MT-5.9-04 | Implement the read-only audit log viewer |

#### WP-5.10 Mobile release builds and distribution — `m5-remote-mobile/wp-5.10-mobile-release/`
Goal: Signed builds and an installation path (OQ-08, FR-MOB-06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-5.10-01 | Configure release signing for Android and iOS |
| MT-5.10-02 | Produce the Android internal release build |
| MT-5.10-03 | Produce the iOS TestFlight release build |
| MT-5.10-04 | Define and document the distribution path |
| MT-5.10-05 | Run the real-device release checklist (push + biometric) |

### Milestone M6 — Hardening and Release (`m6-hardening-release/`)

#### WP-6.1 Security review — `m6-hardening-release/wp-6.1-security-review/`
Goal: Verify parent plan Section 12.1 mitigations with tests and fix findings (NFR-07, FR-SEC-01..05). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.1-01 | Run the authorization review against the Section 12.2 matrix |
| MT-6.1-02 | Test upload abuse cases (traversal, oversized, spoofed MIME) |
| MT-6.1-03 | Audit token lifecycle (scoping, expiry, revocation, hashing) |
| MT-6.1-04 | Audit secrets and log scrubbing (no tokens, no attachment text) |
| MT-6.1-05 | Run the dependency audit and remediate findings |

#### WP-6.2 Backup and restore drill — `m6-hardening-release/wp-6.2-backup-drill/`
Goal: Automate backups and prove restore (NFR-05). Size S.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.2-01 | Automate daily database backups |
| MT-6.2-02 | Automate media volume backups |
| MT-6.2-03 | Schedule backups with documented retention |
| MT-6.2-04 | Run and record a full restore drill |

#### WP-6.3 Performance and load tests — `m6-hardening-release/wp-6.3-performance-tests/`
Goal: Validate NFR-02, NFR-03, NFR-09. Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.3-01 | Write load scenario scripts (20 agents, 10k tasks, SSE fan-out) |
| MT-6.3-02 | Capture performance results against the latency targets |
| MT-6.3-03 | Apply tuning changes (indexes, pooling) for any missed targets |

#### WP-6.4 Metrics, alerts and dashboards — `m6-hardening-release/wp-6.4-observability/`
Goal: Parent plan Section 17 implemented (NFR-10). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.4-01 | Implement metrics endpoints for the Section 17 metric list |
| MT-6.4-02 | Define alert rules (sweeper, backlog, push, tunnel, auth, disk) |
| MT-6.4-03 | Build the operations dashboard view |

#### WP-6.5 Documentation and runbooks — `m6-hardening-release/wp-6.5-documentation/`
Goal: Operator and user documentation. Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.5-01 | Write the operator setup guide |
| MT-6.5-02 | Write the per-client agent guides |
| MT-6.5-03 | Write the runbooks from parent plan Section 17 |
| MT-6.5-04 | Write the troubleshooting guide |

#### WP-6.6 VPS migration rehearsal and v1 release — `m6-hardening-release/wp-6.6-vps-rehearsal/`
Goal: Prove GOAL-5 and tag v1 (NFR-06). Size M.

| MT ID | Title (one-line description) |
|---|---|
| MT-6.6-01 | Provision the VPS host with container runtime |
| MT-6.6-02 | Restore database and media backups on the VPS |
| MT-6.6-03 | Reconnect tunnel, manifests, and agent tokens |
| MT-6.6-04 | Run the smoke test suite on the VPS |
| MT-6.6-05 | Tag v1 release with release notes |

---

## 3. Series Statistics

| Milestone | Folders | Micro-documents |
|---|---|---|
| M0 Foundations | 5 | 22 |
| M1 Core Engine | 15 | 85 |
| M2 MCP Bridge | 12 | 62 |
| M3 Audit, Policy, Merge | 9 | 41 |
| M4 Web Board | 11 | 48 |
| M5 Remote and Mobile | 10 | 46 |
| M6 Hardening and Release | 6 | 24 |
| **Total** | **68** | **328** |

Plus this overview and [`roadmap.md`](./roadmap.md) = **330 documents** in the series.

---

## 4. Related Documents

* [`roadmap.md`](./roadmap.md) — 10 one-directional waves grouping all 328 micro-documents for AI-agent execution.
* `../ai_agent_task_orchestrator_architecture_plan.md` — parent plan; **re-read it whenever context is lost**.
