# Mobile (`mobile/`)

The Flutter mobile client — monitoring, approvals, and push handling (parent plan
Section 14). It is an API-only client of the backend; authentication follows the
layered model in ADR-006.

* Package boundaries and tooling commands:
  [CONTRIBUTING.md — Mobile (Flutter)](../CONTRIBUTING.md#mobile-flutter)

## Architecture (WP-5.5)

**Feature-first structure** (parent plan Section 14.3) with one folder per
Section 14.1 screen area and a shared core layer beneath them:

```
lib/
  main.dart                  # startup: resolve build config (fail fast), runApp
  app/                       # app root, route table (AppArea = Section 14.1),
                             # navigation shell (bottom tabs)
  core/
    config/                  # resolved build-time configuration (AppConfig)
    theme/                   # theme baseline (light/dark)
    api/                     # OrchestratorClient wrapper: error mapping,
                             # correlation id, idempotency helpers, Riverpod
                             # apiClientProvider
    widgets/                 # shared widgets (honest empty placeholder view)
  features/
    onboarding/              # Section 14.1 — Onboarding (MT-5.5-06)
    home/                    # Section 14.1 — Home / Overview (WP-5.6)
    board/                   # Section 14.1 — Board (WP-5.6)
    task_detail/             # Section 14.1 — Task detail (WP-5.7)
    review/                  # Section 14.1 — Review sheet (WP-5.8)
    notifications/           # Section 14.1 — Notifications (WP-5.9)
    audit_log/               # Section 14.1 — Audit log (WP-5.9)
    settings/                # Section 14.1 — Settings (later mobile WPs)
  orchestrator_mobile.dart   # GENERATED barrel — do not edit (see below)
  src/                       # GENERATED API client — do not edit (see below)
tool/
  openapi_client.dart        # regen/check for the generated client
env/
  dev.json                   # dev flavor dart-defines (LAN default)
  prod.json                  # prod flavor dart-defines (no URL committed)
```

Placeholder screens are honest empty states: they render an explicit
"not implemented yet — lands in WP-x" message and never fake business data
(parent plan Section 20.3).

**State management (WP-5.5 decision): Riverpod** — parent plan Section 6.6
names "Riverpod for state", and it satisfies Section 14.3's "single predictable
pattern": one provider graph (`appConfigProvider`, `apiClientProvider`,
`shellIndexProvider`), no mix of setState/event-bus/inherited-widget styles.
Changing it later would be a cross-cutting refactor, so every feature WP
(5.6–5.10) must keep using providers.

**Routing:** `AppArea` in `lib/app/routes.dart` is the single source of truth
for the eight Section 14.1 areas and their named routes; the shell hosts the
four tab areas (Home, Board, Notifications, Settings) and flow/modal areas are
pushed (`/onboarding`, `/task-detail`, `/review`, `/audit-log`).

## Environment flavors (MT-5.5-02)

Two flavors install side by side (distinct application ids and display names —
parent plan Section 14.3, Section 15.1):

| Flavor | Application id (Android / iOS bundle id) | Display name | Backend URL source |
|---|---|---|---|
| `dev` | `…orchestrator_mobile.dev` | Orchestrator Dev | `env/dev.json` → `ORCHESTRATOR_API_BASE_URL` default `http://10.0.2.2:8000/api/v1` (Android-emulator → LAN host pattern; override per device, see below) |
| `prod` | `…orchestrator_mobile` | Orchestrator | **Not committed.** Build-time `ORCHESTRATOR_API_BASE_URL`, or derived as `https://<tunnel>/api/v1` from `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME` |

The URL reaches Dart only as a `--dart-define` (build configuration — no
endpoint literal in `lib/` source; parent plan Section 20.4 item 3).
`AppConfig.resolveFromEnvironment()` runs in `main()` before the first frame
and fails fast with a message naming the missing define (Sections 9.10/16.2).

**Run dev (Android emulator or iOS simulator):**

```powershell
flutter run --flavor dev --dart-define-from-file=env/dev.json
```

* iOS simulator: the committed `10.0.2.2` default does not apply — add a
  machine-local file (git-ignored pattern `env/*.local.json`), e.g.
  `{"ORCHESTRATOR_API_BASE_URL": "http://127.0.0.1:8000/api/v1"}` and pass a
  second `--dart-define-from-file=env/dev.local.json` (later files override
  earlier keys).
* Physical device: use the Compose host's LAN address
  (`ORCHESTRATOR_BIND_ADDR`-style host IP) plus `ORCHESTRATOR_PORT_BACKEND`
  (default 8000) in that local file.

**Build prod (tunnel hostname supplied at build time):**

```powershell
flutter build apk --flavor prod --dart-define-from-file=env/prod.json `
  --dart-define=ORCHESTRATOR_API_BASE_URL=https://<tunnel-hostname>/api/v1
```

…or supply `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME=<tunnel-hostname>` instead
and the URL is derived. `env/prod.json` deliberately contains only the flavor
key — no environment-specific hostname or URL is committed
(Section 20.4 item 3). On iOS/macOS the same flags apply; the `Dev`/`Prod`
schemes in `ios/Runner.xcodeproj/xcshareddata/xcschemes/` select the matching
`Debug-Dev`/`Profile-Dev`/`Release-Dev` (and `-Prod`) build configurations
(verify with a macOS build — not possible from the Windows dev host).

**Precedence (WP-5.5 decision):** a server URL the user enters during
onboarding (MT-5.5-06) overrides the flavor default; this build-time config is
always the fallback. The resolved `AppConfig` is the single source of the base
URL for every consumer — the generated client and (later) onboarding —
asserted by `test/flavor_config_test.dart`.

## Generated API client (MT-5.5-03)

The typed client is **generated from `schemas/openapi.yaml`** (the ADR-005
contract snapshot — NFR-11) with a pinned OpenAPI Generator
(`dart-dio`, jar 7.26.0, SHA-256 verified on first download). Regeneration:

```powershell
dart run tool/openapi_client.dart regen   # regenerate lib/orchestrator_mobile.dart + lib/src/
dart run tool/openapi_client.dart check   # regenerate and exit 1 on drift (CI contract gate)
```

* Output is owned by the tool: `lib/orchestrator_mobile.dart` and `lib/src/**`
  (sources, `*.g.dart` built_value parts) — hand-written code never lives
  there. The generator runs fully offline against the committed snapshot after
  the one-time jar download.
* The regen pipeline is deterministic: generate → `build_runner` → per-file
  `ignore_for_file` style-lint stamps → `dart format`.
* Hand-written wrapper: `OrchestratorClient.fromConfig(AppConfig)` builds the
  base URL from `appConfigProvider` (never a committed endpoint), registers
  the **single** Section 9.2 error mapping point
  (`ErrorMappingInterceptor` → `OrchestratorApiException` with `code`,
  `message`, `retryable`, `details`, `correlation_id`), generates
  `X-Correlation-ID` per exchange, and lets the mutation layer attach
  `Idempotency-Key` via `idempotencyHeaders(...)` (Sections 9.2, NFR-12;
  `docs/plan/conventions/headers.md`).
* Token storage/biometrics (MT-5.5-04) attach at the dio interceptor seam;
  SSE (MT-5.5-05) is a separate transport.

## Tests

```powershell
flutter analyze            # from mobile/
flutter test               # navigation, flavor config and API client suites
dart format --set-exit-if-changed mobile/   # from repo root (CI gate)
```

CI runs format, analyze and `flutter test` for `mobile/`
(`.github/workflows/lint-type.yaml`, `test.yaml`).

## Shared conventions (WP-0.5)

Every configuration value this package reads follows the shared conventions:

* [Configuration conventions](../docs/plan/conventions/configuration.md) —
  environment variable naming, grouping and secret handling (parent plan
  Sections 9.10, 16.2)
* [Error conventions](../docs/plan/conventions/error-envelope.md) — canonical
  error envelope and the 19-code catalog (parent plan Section 9.2)
* [Header conventions](../docs/plan/conventions/headers.md) — correlation id and
  idempotency key headers (parent plan Sections 9.2, 9.6, 17; ADR-012)
* [Pagination conventions](../docs/plan/conventions/pagination.md) — cursor-based
  lists for every list endpoint, plus the Section 9.5 attachment `content`
  exception (parent plan Sections 9.2, 9.5)
