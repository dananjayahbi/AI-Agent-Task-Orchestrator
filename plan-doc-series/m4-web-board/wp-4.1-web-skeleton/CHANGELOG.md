# WP-4.1 — Web app skeleton, auth and generated API client: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-4.1-01** — Next.js scaffold + route structure (Sections 6.6, 13.1;
  FR-WEB-01, NFR-11; ADR-006/007/013). `web/` is now a full App Router
  application: **versions recorded** (MT risk note) — `next@16.4.0` (ADR-007
  major, current stable; Turbopack), `react@19.3`, `typescript@5.9`,
  `tailwindcss@4.3` + `@tailwindcss/postcss`, `eslint@10` flat config,
  `prettier@3.9`; shadcn/ui installed via its CLI (`components.json`, style
  `new-york`) with only the five primitives MT-4.1-04 will theme — `button`,
  `card`, `input`, `label`, `alert` (plus `cn`/`radix-ui`/
  `class-variance-authority`/`clsx`/`tailwind-merge`/`lucide-react`); **fork
  boundary**: the generated component files are committed under
  `components/ui/` and are now owned by this repo — upgrades are explicit,
  diff-reviewed changes (Section 19.7 discipline). **Segment structure
  (recorded per risk note):** `(auth)/` holds the only public route
  (`/login`), `(app)/` holds every Section 13.1 page behind one layout, so
  MT-4.1-02's gate wraps the segments without URL reshuffles. Route map
  (Section 13.1 → App Router): Overview/board landing → `/`, Projects →
  `/projects`, project index → `/projects/[pid]` (redirects to the board),
  Project board → `/projects/[pid]/board`, Task detail →
  `/projects/[pid]/tasks/[taskId]`, Project settings →
  `/projects/[pid]/settings`, Review queue → `/review`, Agents → `/agents`,
  Audit log → `/audit-log`, Account settings → `/settings`, Login →
  `/login`. Every route renders a title/placeholder only — feature WPs fill
  them (Section 19.6 spirit). Scripts: `dev`, `build`, `start`, `test`,
  `lint`, `typecheck`, `format`, `format:check` — all runnable from the repo
  root via `npm --prefix web …` (the commands CI's `lint-type.yaml` already
  calls; no workflow edit was needed and none was made — workflow files are
  outside this WP's ownership). **API base URL seam (Section 20.4 item 3):**
  no hardcoded URL — `next.config.ts` reads `ORCHESTRATOR_API_BASE_URL`
  (configuration.md group `API_`, documented default
  `http://localhost:8000/api/v1`, fail-fast on a non-http(s) value) and
  rewrites same-origin `/api/v1/*` to it; `web/.env.example` documents the
  variable. Same-origin proxying was chosen because `backend` has **no CORS
  middleware wired yet** (`base.py` MIDDLEWARE) — proxying keeps the
  HTTP-only session cookie and `Origin`/CSRF checks byte-identical between
  dev and prod. Typed-client import seam reserved: `lib/api/` (barrel
  `lib/api/index.ts`), nothing outside it performs HTTP. Verified:
  `npm --prefix web run lint|typecheck|format:check` and `npm --prefix web
  run build` all green — build output lists all 13 routes plus `ƒ Proxy`.

- **MT-4.1-02** — Login and protected routes (Sections 12.2, 13.1/13.2,
  9.2; FR-WEB-01, FR-SEC-01/02; G-07; ADR-001/ADR-012). **Session strategy
  (chosen and recorded per the MT):** `MT-1.2-01` exposes no whoami/me
  endpoint, so the app gates routes on *session-cookie presence* in
  `proxy.ts` (Next 16 renamed `middleware` → `proxy`; the old filename is
  deprecated — recorded here per the stack-version risk note) and treats any
  API response with canonical `AUTH_REQUIRED` as the session-expired signal,
  driving a silent redirect to `/login?next=<path+query>`; the backend
  remains authoritative (every API call re-verifies the live token row).
  Unauthenticated visits to every Section 13.1 route bounce to login with
  the return path; authenticated `/login` bounces to the Board (`/`);
  `/api/*` is never gated (a missing session there must surface as the
  backend's `AUTH_REQUIRED` envelope, not an HTML redirect). Login page
  (`app/(auth)/login`) posts username/password through the API seam — the
  response's HTTP-only `sessionid` cookie is the credential and the
  response's plaintext `token` binding is **deliberately discarded** (the
  app stores only `{id, username}` in localStorage; a test asserts no token
  ever reaches client state — Section 12.2 web model, FR-SEC-01). CSRF per
  MT-1.2-01: every mutation duplicates the `csrftoken` cookie into the
  `X-CSRFToken` header; `credentials: 'include'`. Logout
  (`SessionControls` → `performSignOut`) revokes server-side, clears local
  identity and lands on `/login` even when the revoke reports
  `AUTH_REQUIRED` (idempotent). 401-mid-session clears state and redirects
  silently with the current path as `next`; 403 `AUTH_FORBIDDEN_PROJECT`
  renders the friendly denial state without internal detail (G-07);
  `VALIDATION_ERROR` renders inline — routing behaviour lives here,
  presentation copy is MT-4.1-04's shared mapping (wired both ways).
  Role-aware affordances are deferred to feature WPs that own actions
  (nothing to hide yet); server-side enforcement stays MT-1.2-07's.
  **Sequence note (MT risk note):** MT-4.1-03's dependency has not landed,
  so the interim HTTP surface is the explicitly-sanctioned *narrow temporary
  call* — `lib/api/client.ts` (envelope parsing + 401 handler only, marked
  TEMPORARY) and `lib/api/auth.ts` (login/logout payloads typed straight
  from `schemas/openapi.yaml`) — to be replaced wholesale by the generated
  client when MT-4.1-03 runs in this same WP; no other hand-written API
  types exist. Tests (stubbed backend, per the MT test command):
  `npm --prefix web run test -- auth` → 3 files / 41 tests green — full
  redirect matrix for every Section 13.1 route incl. query-preserving return
  paths and API passthrough, login happy path + no-token-in-state, logout
  CSRF header, idempotent sign-out, silent 401 handler (and that failed
  login credentials never trigger it), envelope parsing (nested + flat).
  The integration assertion "direct API access without a session answers
  `AUTH_REQUIRED`" is covered by the backend's own suite
  (`backend/tests/test_owner_session_auth.py` — backend territory, read-only
  here). Live smoke of the built app confirmed the gate end-to-end:
  `307 /login?next=…` for `/`, `/review?sort=age`, `/settings`,
  `/projects/[pid]/board` without a cookie; `200` with one; `/login` `307 →
  /` when a session exists; `/api/v1/*` proxied upstream.

- **MT-4.1-04** — Theming, layout and error-code mapping (Sections 9.2,
  13.3/13.4; FR-WEB-01, NFR-04, NFR-11). **Theme:** `app/globals.css`
  centralizes every design token (light in `:root`, dark under `.dark`,
  oklch, mapped to Tailwind through `@theme inline`) — components consume
  tokens only, no one-off hex values in pages; dark/light exists because
  Section 13.4 asks for both, delivered with `next-themes@0.4.6`
  (`attribute="class"`, `defaultTheme="system"`) and a hydration-stable
  `ThemeToggle` whose icon swap is pure CSS (no render-cycle state — the
  new `react-hooks/set-state-in-effect` lint rule forced this and it is the
  better pattern). **Layout:** the `(app)` shell now carries navigation for
  all Section 13.1 routes (`AppNav`), session controls, theme toggle and
  consistent max-width page headers; shared patterns feature WPs reuse:
  `LoadingState` (+ `app/(app)/loading.tsx`), `EmptyState`, `ErrorState`.
  Navigation covers the six top-level Section 13.1 routes statically; the
  three project-scoped routes (board, task detail, project settings) hang
  off the dynamic `/projects/[pid]` segment — the switcher that lists them
  is WP-4.2's, so the shell links them only once real project data exists
  (no fabricated links in the skeleton).
  **Error mapping (single source, Section 19.6):** `lib/errors/catalog.ts`
  maps **all 19 Section 9.2 codes** to `{title, message, presentation}` —
  `Record<ErrorCode, …>` makes completeness a compile error, and
  `tests/errors/catalog.test.ts` parses the *published* `CodeEnum` out of
  `schemas/openapi.yaml` and fails when the two lists diverge (the UI
  counterpart of Section 20.4 item 5; `yaml` added as a devDependency for
  this). `resolveError()` never reads the envelope's `message`; unknown
  codes degrade to generic copy plus the envelope's `correlation_id`
  shown as "Reference ID" (the MT's "`request_id`" — the envelope field is
  `correlation_id` per Section 9.2/error-envelope.md, recorded as this
  task's interpretation). **Presentation matrix (recorded per the risk
  note — interpretation, not plan text):** `AUTH_REQUIRED` → `redirect`
  (silent; its message only ever shows on the login form, where it reads
  as credential guidance); form/attachment/auditor codes → `inline`;
  operational conflicts/limits/`RATE_LIMITED`/`VERSION_CONFLICT` → `toast`;
  denials, not-found, scope/policy/role blocks and `SERVER_ERROR` → `state`
  (full in-page component). Feature WPs may re-place a message without
  touching the copy table. `app/(app)/error.tsx` → `ApiErrorView` →
  `resolveError` → `ErrorState` wires the mapping into MT-4.1-02's routing;
  login inline errors go through the same resolver. Tests:
  `npm --prefix web run test -- errors` → 2 files / 12 tests green
  (catalog parity with OpenAPI, distinct copy per code, unknown-code
  fallback + request id, raw-string guard for every catalog code,
  `AUTH_FORBIDDEN_PROJECT` denial renders without leaking `details`, raw
  non-API error messages never render). Full suite: 5 files / 53 tests.

- **MT-4.1-03** — DEFERRED (roadmap 4a rule 1): its dependency
  (schema-versioning conventions, cited as MT-1.4-01) has not landed — no
  schema-versioning convention exists under `docs/plan/conventions/` or
  `schemas/` as of 2026-10-12, and `MT-1.4-01` in the series is the task
  model doc — so the generated-client + drift-gate slice runs when those
  conventions publish.

## WP notes, deviations and open questions

- **Deviation (contract bug, recorded not fixed — `schemas/` is read-only
  here):** the wire error body is nested (`{"error": {code, message,
  retryable, details, correlation_id}}` — parent plan Section 9.2 example,
  `backend/apps/core/errors.py::build_error_envelope`), but the
  `ErrorEnvelope` component in `schemas/openapi.yaml` declares the five
  fields *flat*. The web parser accepts both (nested first — plan
  authoritative); **MT-4.1-03 must not generate from the document until the
  schema serializer and the wire agree**, or generated types will misparse
  every error. Flagged for the backend/schema owner.
- **Open question (configuration):** the proxy upstream reuses the
  documented `ORCHESTRATOR_API_BASE_URL` (manifest-binding semantics; both
  are the same backend origin in dev). If production wants an *internal*
  upstream distinct from the public manifest URL, configuration.md needs a
  new canonical row (single-owner doc — not edited by this WP).
- **Doc staleness (outside `web/`):** CONTRIBUTING's web unit-test row says
  "script + runner arrive with WP-4.11" — the runner (Vitest 5, recorded
  choice: jsdom + @testing-library/react + @vitejs/plugin-react) landed here
  per MT-4.1-02/04's test commands; `test.yaml` needs no change (it already
  runs `npm --prefix web run test` whenever `web/` test files exist).
- **Plan-numbering mismatch (recorded, plan untouched):** the MTs cite
  "Section 13.2 client behavior / 13.3 error states / 13.4 component
  guidance / 19.6", while the current plan heads §13.1–13.4 as Information
  architecture / Key components / Data and state handling / Non-functional
  targets and has no §19.6 heading; behaviour was taken from the cited
  content (13.3's "all errors mapped from canonical error codes to friendly
  messages", 13.4's dark/light + responsive targets).
- **Security posture:** no secrets or environment-specific paths committed
  (`.env.example` carries only the documented default); `npm audit` reports
  the pre-existing 5 high braces/micromatch advisories via
  `eslint-config-next` — documented in CONTRIBUTING as unfixable-without-
  downgrade and gated at `critical`, so intentionally untouched.
- **Verification (2026-10-12, all green):** `npm --prefix web run lint`,
  `npm --prefix web run typecheck`, `npm --prefix web run format:check`,
  `npm --prefix web run test` (5 files / 53 tests), `npm --prefix web run
  test -- auth` (41) and `-- errors` (12), `npm --prefix web run build`
  (all routes + `ƒ Proxy`), plus the live route-gate smoke above. Nothing
  was committed (no `git add`/`git commit` by this WP).
