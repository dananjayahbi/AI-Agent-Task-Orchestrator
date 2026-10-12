# Web (`web/`)

The Next.js (App Router) operations board UI (parent plan Section 13). It is an
API-only client of the backend over HTTP and SSE — no direct database or repository
access.

- Package boundaries and tooling commands:
  [CONTRIBUTING.md — Web (Next.js)](../CONTRIBUTING.md#web-nextjs)

## Run and verify (WP-4.1)

All commands run from the repository root (recorded in the WP changelog,
Section 20.4 item 1):

| Task                                                      | Command                                                             |
| --------------------------------------------------------- | ------------------------------------------------------------------- |
| Dev server (port 3000)                                    | `npm --prefix web run dev`                                          |
| Production build                                          | `npm --prefix web run build`                                        |
| Serve the build                                           | `npm --prefix web run start`                                        |
| Unit tests (Vitest; `- <filter>` narrows, e.g. `-- auth`) | `npm --prefix web run test`                                         |
| Lint                                                      | `npm --prefix web run lint`                                         |
| Type check                                                | `npm --prefix web run typecheck`                                    |
| Format / format check                                     | `npm --prefix web run format` / `npm --prefix web run format:check` |

Configuration: copy `.env.example` to `.env.local` for local overrides —
`ORCHESTRATOR_API_BASE_URL` (see `docs/plan/conventions/configuration.md`)
names the backend that `next.config.ts` proxies `/api/v1/*` to; the browser
only ever talks to this app's own origin, so session cookies and CSRF stay
same-origin (parent plan Section 12.2).

Structure (WP-4.1):

- `app/(auth)/` — public routes (Login only).
- `app/(app)/` — protected Section 13.1 routes; gated by `proxy.ts`.
- `proxy.ts` — session gate (Next 16's proxy convention) + `/api` passthrough.
- `lib/api/` — API seam; `lib/auth/`, `lib/session/`, `lib/errors/` — auth,
  session state and the shared canonical error mapping.
- `components/` — `ui/` (shadcn/ui primitives), `layout/`, `login/`,
  `session/`, `errors/`, `states/`.
- `tests/` — Vitest suites (auth flows, route gate, error catalog).

## Shared conventions (WP-0.5)

Every configuration value this package reads follows the shared conventions:

- [Configuration conventions](../docs/plan/conventions/configuration.md) —
  environment variable naming, grouping and secret handling (parent plan
  Sections 9.10, 16.2)
- [Error conventions](../docs/plan/conventions/error-envelope.md) — canonical
  error envelope and the 19-code catalog (parent plan Section 9.2)
- [Header conventions](../docs/plan/conventions/headers.md) — correlation id and
  idempotency key headers (parent plan Sections 9.2, 9.6, 17; ADR-012)
- [Pagination conventions](../docs/plan/conventions/pagination.md) — cursor-based
  lists for every list endpoint, plus the Section 9.5 attachment `content`
  exception (parent plan Sections 9.2, 9.5)
