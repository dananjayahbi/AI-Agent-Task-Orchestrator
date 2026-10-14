# WP-4.10 — Audit log viewer and policy editor: changelog

## Unreleased

- **MT-4.10-01 — audit log viewer (done).**
  `web/app/(app)/audit-log/page.tsx` replaces the placeholder with
  `web/components/audit/audit-log-view.tsx` (query + separated
  loading/empty/error states) and `audit-event-entry.tsx` (one
  read-only entry). Data is a pure REST read of the published
  `GET /events` history through the generated client (`lib/queries/audit-events.ts`,
  NFR-11) — no SSE subscription (stream-down cannot affect a history
  view), no write path anywhere (Section 12.5; the only interactive
  control is the payload expander). Each entry renders the server UTC
  instant verbatim, the actor (`actor_type · actor_ref`, plain text —
  never enriched, per the P10-adjacent risk note), project/task links
  when the envelope carries them, and the monotonic event id.
  **ADR-010:** the friendly label and the canonical type string render
  together — `lib/audit/event-labels.ts` is an exhaustive
  `Record<EventEnvelopeTypeEnum, string>` (a future catalog type is a
  compile error until labelled) and types outside the catalog render
  raw without crashing (20.4 item 6). **Recorded contract gap:** the
  AC's "correlation id" has no wire field — the Section 9.6 envelope
  carries only the monotonic `id`, so the viewer displays that id
  (`#n`) instead of inventing a correlation id. **Cursor discipline
  (RISK-13):** pages follow the Section 9.2 cursor through the shared
  bounded helper (100-page defensive cap + repeated-cursor guard),
  presented newest-first (the endpoint pages oldest → newest — the
  MT-4.6-03 recorded reading of this endpoint); payloads are
  collapsed by default and rendered only on expand, so large JSON
  never burdens the default render. Filters are a view prop keyed
  per set (`queryKeys.auditEvents`) — MT-4.10-02 wires the controls.
  Tests: `web/tests/audit/audit-log-view.test.tsx` (7 — full-field
  fixture render + raw unknown type, payload expansion, two-page
  cursor follow, read-only guarantee, contract-only filter params,
  empty state, catalog-only error copy).
- **MT-4.10-02 — log filters (done; two contract-backed dimensions,
  three raised).**
  `web/components/audit/audit-log-filters.tsx` (controls + chips) and
  `audit-log.tsx` (URL-synced container) drive the viewer.
  **Contract-first mapping (AC 2 + the MT risk note, applied):** the
  generated client's `GET /events` operation publishes exactly two
  filter parameters — `project` and `task` — so those two are wired
  1:1 (the AC's "multi-select project" is recorded as a deviation:
  the parameter is single-valued; a true multi-select needs either a
  server multi-value parameter or a bounded fan-out — raised with the
  same contract change). The remaining Section 19 dimensions — actor
  (`actor_type · actor_ref`), date range on `created_at`, and event
  type — render as **disabled** controls with a visible note
  (`EVENTS_FILTER_CONTRACT_NOTE`): they are raised as an OpenAPI
  contract change (Section 20.4 item 4), never emulated with
  client-side post-filtering, which on a one-year-retention log
  (Section 12.4) behind the page cap would silently lie about
  completeness and break the cursor semantics. The type select still
  enumerates only Section 9.6 catalog values (20.4 item 6) — ready
  the moment the parameter lands. **Date semantics (risk note):**
  the disabled range inputs are labeled UTC (Section 0.4 — the query
  would be server-UTC). **URL state:** the URL is the filter state —
  `useSyncExternalStore` over `location.search` (server snapshot
  empty → no hydration mismatch), `history.replaceState` + a local
  notify for writes; only the documented parameters are written, so
  views are shareable/refreshable and a refresh reproduces the
  filters. A filter change is a new query key (cursor walk restarts
  at page one — pagination reset). Chips summarize active filters
  with individual clear + clear-all; the task draft input is keyed
  by the committed URL value so a chip clear can never leave a stale
  draft; the filtered-empty state ("No events match these
  filters" + Clear filters) is distinct from the empty log and the
  error state (Section 20.3).
  Tests: `web/tests/audit/audit-log-filters.test.tsx` (5 — project
  parameter mapping + pagination restart, project+task composition
  with URL round-trip, distinct filtered-empty + reset, catalog-only
  type options with disabled dimensions + contract note, chips with
  individual clear and clear-all).
- **MT-4.10-03 — policy editor presets & read-only (done).**
  `web/lib/projects/policy-presets.ts` is a verbatim transcription of
  `backend/apps/projects/policy_presets.py` (all three presets' 16
  fields, `PRESET_LIBRARY_VERSION` pinned to the backend constant) —
  drift is caught by a source-parsing test rather than a dynamic
  backend import (the corrector daemon's imports must not run in CI).
  The project policy form gains a preset picker: applying a preset
  populates the draft only after a mandatory confirmation when the
  draft's three path-glob lists differ from saved values, and never
  discards other in-progress edits (numbers/sliders stay as edited).
  The backend's `policy_preset` PATCH parameter is deliberately not
  sent — it is incompatible with explicit per-list globs
  (VALIDATION_ERROR on combination) and the form is populate-then-
  edit, so the client-side transcription is the honest path. The
  per-field `readOnly` threading is replaced by the Section 12.2
  native **fieldset gate** (`disabled={readOnly || save.isPending}`);
  a PATCH 403 `ROLE_NOT_PERMITTED` flips the form to read-only with
  the existing notice/banner (Recorded contract gap: no client maps
  403 yet — raised with the change). **No `version` field exists on
  the policy PATCH contract** — a conflict could never trigger the
  AC's message today; kept as defensive mapping only (recorded).
  Glob inputs (the three optional per-list fields added by this MT)
  validate against the documented backend rules (≤64 entries, ≤500
  chars each, no backslash/NUL/absolute/drive/`..` segments, balanced
  brackets, `**` only as a whole segment) with inline errors —
  `lib/forms/project-schemas.ts` mirrors `services/globs.py`; every
  hint cites the Section 7.2 defaults (retries 3, stalled 20, lease
  45, checkpoint 15).
  Tests: `web/tests/projects/policy-editor.test.tsx` (5 — preset
  replace confirmation preserving other edits, `**`/bracket glob
  errors, read-only fieldset gate + notice on ROLE_NOT_PERMITTED,
  defaults rendered, save payload carries only the three changed
  globs) and `policy-presets.test.ts` (3 — source drift pin against
  the backend file, glob validator/bracket rules, version pin).
  `npx vitest run tests/projects` → 45 passed; `tsc --noEmit`,
  `eslint`, `prettier --check` clean.
- **MT-4.10-04 — rules editor with rules-block preview (done).**
  `web/lib/projects/agent-rules.ts` is a verbatim transcription of
  the WP-2.7 single render path — `bridge/src/orchestrator_bridge/rules.py`
  (`CODER_RULES`, `AUDITOR_RULES`, connect-time generic slot phrasings,
  the one-third-of-lease checkpoint cadence, and the project-rules
  normalisation: control-char strip + 8000-char cap with the same
  visible truncation marker) — pinned by a source-parsing drift test
  so a Section 10.6 / WP-2.7 change fails here too (Section 20.5).
  `web/components/projects/rules-form.tsx` (the MT-4.2-02 editor,
  extended in place) gains the Section 13.1/19 **rules-block
  preview**: standard rules first, the live draft appended under a
  "Project rules:" separator, shown exactly as the bridge normalises
  them — inert plain text in a `<pre>` (Principle P10; never
  HTML-rendered or executed) — with a coder/auditor toggle
  (`aria-pressed`) for the Section 10.6 auditor half and an
  "applies on next connect or claim" effect-timing note (running
  sessions keep their startup context; no false instant-rewrite
  claim). Slots render at connect-time generically ("the branch
  returned by claim_task …") because no claim exists yet; the
  cadence uses the policy lease (`usePolicyQuery`, Section 7.2
  default 45 → 15 min only as fallback). Save still round-trips
  `system_prompt_rules` verbatim through `PATCH /projects/{pid}`
  with `resolveError` canonical mapping; a `ROLE_NOT_PERMITTED`
  rejection flips the Section 12.2 native fieldset gate with the
  read-only notice (same raised 403-mapping gap as MT-4.10-03).
  No client-only size cap is invented — the char counter informs,
  the server validates (risk note).
  Tests: `web/tests/projects/rules-preview.test.tsx` (5 — coder
  block + appended draft + effect timing, auditor toggle round-trip,
  live-draft preview with truncation marker over the cap, inert
  markdown rendering, read-only gate on ROLE_NOT_PERMITTED) and
  `agent-rules.test.ts` (7 — verbatim coder/auditor transcription
  against the bridge source, lease/cap constant pins, cadence math,
  normalisation parity, slot rendering). Full suite 362 passed;
  `tsc --noEmit`, `eslint`, `prettier --check` clean.
