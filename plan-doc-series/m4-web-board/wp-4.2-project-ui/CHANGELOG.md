# WP-4.2 — Project switcher, project CRUD, manifest and tokens UI: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-4.2-01** — Project list and switcher (Sections 9.2, 13.1/13.3;
  FR-PRJ-01 read half, FR-WEB-01). **Data:** `GET /projects` through the
  generated client only (`callApi(listProjects(…))`), cursor pagination
  honored by `lib/api/pagination.ts::fetchAllPages` — follows `next_cursor`
  to the last page with a repeated-cursor guard (`page_size=100`, the
  contract clamp), so the list is complete regardless of page count.
  **Query caching (Section 13.3):** `@tanstack/react-query@5.104.2` added
  as the plan's "query library" (Section 6.6 names none specifically —
  TanStack Query is the maintained mainstream choice; recorded here per the
  dependency rule); `QueryProvider` wraps the `(app)` segment, `retry: off`
  so canonical error copy shows immediately, `staleTime 30 s` for instant
  switching, and `queryKeys` (`lib/queries/keys.ts`) is the single cache
  identity so every later mutation invalidates the right entries.
  **Components:** `ProjectList` (states strictly separated per Section
  20.3: `LoadingState` / catalog-mapped `ErrorState` with retry /
  `EmptyState` whose create CTA points at `/projects/new` — MT-4.2-02's
  entry point); `ProjectCard` shows exactly what `GET /projects` returns —
  id, name, status chip from Section 8's canonical
  active/paused/archived triple (no invented statuses; the richer Overview
  fields — active agents, throughput — need `GET /dashboard/summary` and
  stay with later dashboard work, per the MT's out-of-scope note);
  `StatusBadge`. **Switcher (header level):** native `<select>` in the app
  shell; the **route is the source of truth** (MT risk note) — a
  `/projects/{pid}` segment always wins and re-mirrors into the documented
  storage key `orchestrator.web.current-project` (non-secret id only; read
  via `useSyncExternalStore`, which also keeps SSR hydration clean and
  satisfies the `react-hooks/set-state-in-effect` rule); on pages without a
  project context the stored selection preselects so a reload keeps it;
  changing the selection navigates to that project's board. **Routes:**
  `/` (Overview) and `/projects` both render the shared `ProjectList`
  (one component, one current-project notion); `/projects/new` created for
  MT-4.2-02. **Tests:** `tests/projects/project-list.test.tsx` → 10 green
  (render of id/name/status, loading state, empty CTA, catalog error copy
  without raw server text, `AUTH_REQUIRED` fires the WP-4.1 silent
  redirect, cursor paging asserts page 2 carries `cursor=…`, switcher
  route-wins + navigation + storage persistence + inert-while-loading).

- **MT-4.2-02** — Project create/edit forms, status transitions, policy and
  rules editors (Sections 9.2, 10.6, 13.1/13.3; FR-PRJ-01/04, FR-WEB-09).
  **Shared validation:** `lib/forms/project-schemas.ts` — one module for
  every project form (Section 13.3 "shared schemas"; Section 6.6 names no
  validation library, so bounds are transcribed from the published
  contract's field constraints — no new dependency). **Create**
  (`/projects/new` → `CreateProjectForm`): `POST /projects` with
  `ProjectCreate`-typed fields, required/maxLength checks before any
  request, success panel displays the **backend-assigned `PID`**
  (FR-PRJ-01 — never generated client-side) and points onward to Project
  settings (`?created=…` → the manifest step of MT-4.2-03); the list query
  is invalidated so the switcher/Overview show the project immediately.
  **Edit** (`EditProjectForm`): PATCHes **only changed fields** (partial-
  update contract); rollback discipline (Section 13.2): a rejected save —
  including the simulated `VERSION_CONFLICT` — shows the catalog copy and
  invalidates the project query, and the refetched server truth flows back
  through render-phase state adjustment (React's "adjust state when props
  change" pattern; the new `react-hooks/set-state-in-effect` rule forced
  this shape and it is the better one). **Status transitions**
  (`ProjectStatusActions`): per-status allowed set — active → Pause/
  Archive, paused → Resume/Archive, archived → Restore (the serializer
  validates the triple, backend permits any transition among the three);
  every transition goes through a confirmation dialog (`components/ui/
  dialog.tsx`, shadcn shape over the monolith `radix-ui` package — same
  stack as MT-4.1-01's kit), archive uses the destructive variant, server
  rejection keeps the dialog open with friendly copy. **Policy editor**
  (`PolicyForm`): loads current values from `GET/PATCH
  /projects/{pid}/policy` — never client-invented defaults (risk note);
  numbers validated against contract minimums (1–5 confidence, ≥0
  concurrency), glob lists edited as newline text and sent as arrays,
  enums rendered from option lists typed against the generated unions,
  save sends changed fields only; success/error feedback via catalog copy.
  **Rules editor** (`RulesForm`): `system_prompt_rules` round-trips
  **verbatim** — no trimming, no reformatting, the exact textarea bytes go
  into the PATCH (WP-2.7/Section 10.6 consumer expectation; risk note).
  **New UI primitives:** `components/ui/dialog.tsx`, `components/ui/
  textarea.tsx`, shared `FieldRow`/`FormBanner`. **Tests:**
  `tests/projects/project-forms.test.tsx` → 12 green (create posts the
  exact body + shows PID + invalidates `['projects']`; local validation
  never posts; edit PATCHes only changed fields; `VERSION_CONFLICT` shows
  catalog copy and rolls the field back to `Server Wins` after refetch;
  archived project offers only Restore; archive gated behind the dialog —
  zero requests until Confirm, then correct body + invalidations;
  rejection keeps the dialog open; policy shows server values, saves
  changed-only, rejects out-of-contract numbers pre-request; rules
  verbatim round-trip incl. whitespace, disabled button when clean,
  rejection copy without raw server text).

- **MT-4.2-03** — Manifest download and copy (Sections 9.2, 10.3, 13.1;
  FR-PRJ-03). `ManifestSection` in Project settings fetches
  `GET /projects/{pid}/manifest` with the generated client and
  **`parseAs: 'text'`** — the response bytes reach the UI untouched, so
  the downloaded file matches the endpoint **byte-for-byte** (pretty-
  printed, non-ASCII content included) with **zero client-side assembly**
  (risk note: a second source of truth would drift from the bridge's
  validator). Download creates a blob named **`orchestrator.json`** so it
  drops into a repository root unchanged (Section 10.3 discovery); Copy
  writes the same text to the clipboard with a success acknowledgement,
  and a rejected clipboard promise (non-secure origin) falls back to a
  selectable read-only text area — never a dead button (risk note). Copy
  states the safety guarantee ("contains no secrets — safe to commit;
  agent tokens are never part of it") and the documented flow: place the
  file at the repository root, run the bridge's `init` command (FR-MCP-08,
  guidance only — no invented flags). Loading/error states map through the
  catalog: `AUTH_REQUIRED` fires the silent redirect, `AUTH_FORBIDDEN_
  PROJECT` renders the denial copy, and the contract's unknown-pid answer
  (`VALIDATION_ERROR` — see deviations) renders its friendly copy. **Tests:**
  `tests/projects/manifest-download.test.tsx` → 7 green (blob name +
  exact byte equality with the endpoint response + revokeObjectURL;
  clipboard gets the identical text; failure falls back to selectable
  text; secret-free + init guidance present; 403/401/400 mapping with no
  raw server text).

- **MT-4.2-04** — Agent token create/revoke UI with one-time reveal
  (Sections 9.2, 12.2/12.4, 13.1; FR-WEB-09 context). `TokenSection` in
  Project settings lists `GET /tokens?kind=agent&project_id={pid}` (cursor
  pages collected like the project list) rendering **explicitly listed
  non-secret metadata only** — `#id`, scopes, active/revoked status, last
  used, expiry — so even an API divergence that returned more could never
  surface it (risk note; the contract's `TokenSummary` carries no hash or
  value, FR-SEC-04). **Create** (`POST /tokens/agent`) opens a one-time
  reveal panel: the plaintext lives **only in component state** — never in
  the query cache, localStorage/sessionStorage, logs or URLs — shows the
  "only time it will be shown" warning (server keeps only the hash), copy
  to clipboard with a selectable-text fallback, and the Section 10.3 step-3
  storage pointer (host user-level config or environment; never the
  manifest). The value is dropped on dismiss and on unmount/navigation
  (state dies with the section; tests prove nothing persists and a
  remount shows nothing). **Revoke** goes through a confirmation dialog
  stating the impact ("agents using this token lose access immediately"),
  calls `DELETE /tokens/{id}`, invalidates the token query so the row
  disappears, and shows friendly copy on rejection; revoked rows render
  their state and offer no further action. **Tests:**
  `tests/projects/agent-tokens.test.tsx` → 6 green (metadata-only list;
  create posts `{project_id}` and reveals exactly once with storage
  guidance, copy works, no storage artifact contains the value; unmount
  discards the reveal permanently; revoke gated behind the dialog — zero
  DELETEs until Confirm — then DELETE + invalidation + row gone; creation
  `AUTH_REQUIRED` maps + fires the silent redirect without revealing;
  list failure renders catalog copy without raw text).

## WP notes, deviations and open questions

- **Deviation (contract vs MT wording):** the project contract carries **no
  `version` field** on `PATCH /projects/{pid}` (unlike tasks), so a real
  optimistic-locking `VERSION_CONFLICT` cannot originate server-side for
  projects today. The MT-4.2-02 acceptance is still proven end-to-end at
  the error boundary — the test serves a `409 VERSION_CONFLICT` envelope
  and asserts catalog copy + rollback to refetched server truth — and the
  UI will honour the code whenever the backend gains the field. Flagged,
  not fixed outside `web/`.
- **Deviation (catalog reality):** MT-4.2-03 asks for a
  "project-not-found per catalog" mapping; the catalog has no
  `PROJECT_NOT_FOUND` and the contract answers a malformed/unknown pid
  with `VALIDATION_ERROR` (400) — the UI maps that code's friendly copy,
  and the test documents the substitution.
- **Deviation (dependency citation):** MT-4.1-03's cited "MT-1.4-01
  schema-versioning conventions" does not exist (WP-4.1 changelog records
  the resolved interpretation — the documented regen + CI diff gate is the
  discipline; see that entry). Noted here because WP-4.2's list/switcher
  consumes the client that decision produced.
- **Field-ownership note:** implementing MT-4.1-03's CI target paths
  required two files outside `web/` — `.github/workflows/lint-type.yaml`
  (the MT explicitly targets "CI workflow — generate + diff step") and
  `CONTRIBUTING.md` (that workflow's header mandates changing the
  CONTRIBUTING command table first and mirroring it verbatim). No other
  non-`web/` file was written; `schemas/openapi.yaml`, `backend/`,
  `bridge/`, `mobile/`, `infra/` and `docs/` stayed untouched.
- **Scope note (Overview cards):** Section 13.1's "active agents, tasks
  needing attention, throughput" are not part of `GET /projects`; cards
  show id/name/status and the richer metrics wait for
  `GET /dashboard/summary` (the MT's out-of-scope rule) rather than
  invented fields.
- **Open question (none blocking):** if the backend later exposes an
  `ETag`/`version` for projects or a `label` field for tokens, the forms
  and list can adopt it without rework — current UIs only render fields
  the contract defines.
- **Verification (2026-10-12, all green):** `npm --prefix web run lint`,
  `npm --prefix web run typecheck`, `npm --prefix web run format:check`,
  `npm --prefix web run test` (11 files / 96 tests total, of which this WP
  contributes 35 across `tests/projects/`), `npm --prefix web run build`
  (all routes + `ƒ Proxy`). Nothing was committed (no `git add`/`git
  commit` by this WP); no secrets or environment-specific paths committed.
