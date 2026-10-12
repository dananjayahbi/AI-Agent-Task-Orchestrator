# WP-5.5 — Flutter skeleton and API client: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-5.5-01** — The Flutter app scaffolded in `mobile/`: `flutter create`
  platform projects (Android/iOS), app entry point resolving config before the
  first frame, theme baseline (`core/theme`), and the feature-first structure
  per Section 14.1 — one folder per area (`onboarding`, `home`, `board`,
  `task_detail`, `review`, `notifications`, `audit_log`, `settings`) over a
  shared `core/` layer (config, api, theme, widgets), documented in
  `mobile/README.md`. `AppArea` in `lib/app/routes.dart` is the single source
  of truth for the eight areas and routes; the navigation shell (bottom
  NavigationBar, four tabs) hosts Home/Board/Notifications/Settings and
  flow/modal areas are pushed routes. **State-management decision (recorded
  per MT-01):** Riverpod — Section 6.6 names "Riverpod for state" and it is
  the one predictable pattern Section 14.3 requires (a single provider graph;
  no mixed setState/event-bus styles), so feature WPs 5.6–5.10 must keep it.
  Placeholders are honest empty states ("not implemented yet — lands in WP-x",
  Section 20.3) with zero fake business data. Widget tests prove navigation
  shell integrity: all four tabs reachable by tap, all eight Section 14.1
  areas render from the route table, shell index tracked by the provider.
  CI already runs `dart format --set-exit-if-changed mobile/`,
  `flutter analyze` and `flutter test` for `mobile/`
  (lint-type.yaml/test.yaml — no workflow edits needed or made); no secrets or
  env-specific paths committed. Verified: `flutter analyze` clean,
  navigation suite 18/18 green.
- **MT-5.5-02** — Environment flavors `dev`/`prod` (Section 14.3, Section
  15.1): Android `productFlavors` with `.dev` applicationId suffix and
  per-flavor display names (source-set strings), iOS `Dev`/`Prod` shared
  schemes with six new build configurations (`Debug/Profile/Release-Dev` and
  `-Prod`, cloned into project, Runner and RunnerTests configuration lists —
  the exact `<Mode>-<Scheme>` + sentence-cased scheme contract
  `flutter tools/lib/src/ios/xcodeproj.dart` resolves) and per-config
  `APP_DISPLAY_NAME` wired to `Info.plist`. Backend URL reaches Dart only via
  dart-defines: committed `env/dev.json` carries the documented LAN
  development pattern (`http://10.0.2.2:8000/api/v1`, Android-emulator →
  host), `env/prod.json` carries **no** URL — prod resolves from the
  build-time `ORCHESTRATOR_API_BASE_URL` or derives
  `https://<tunnel>/api/v1` from `ORCHESTRATOR_CLOUDFLARE_TUNNEL_HOSTNAME`
  (canonical vocabulary per configuration.md), and `env/*.local.json` is
  git-ignored for machine-local overrides. `AppConfig` (the single source of
  the base URL for every consumer) fails fast in `main()` naming the missing
  define (Sections 9.10/16.2). **Precedence decision (recorded per MT-02):**
  an onboarding-set URL (MT-5.5-06) overrides the flavor default; build-time
  config is the fallback. Verified with real builds on this host:
  `flutter build apk --debug --flavor dev --dart-define-from-file=env/dev.json`
  → `app-dev-debug.apk` (aapt: `com.aiagenttaskorchestrator.orchestrator_mobile.dev`,
  label "Orchestrator Dev"); `--flavor prod …` → `app-prod-debug.apk`
  (`com.aiagenttaskorchestrator.orchestrator_mobile`, label "Orchestrator") —
  distinct ids, side-by-side installable. Config tests (resolution per flavor,
  prod fail-fast message, tunnel derivation, native id assertions) green.
  iOS scheme/config wiring is written to the flutter-tool contract but needs a
  macOS build to execute (Windows dev host) — recorded as the remaining
  device-matrix item.
- **MT-5.5-03** — Typed API client generated from the canonical
  `schemas/openapi.yaml` snapshot (NFR-11/ADR-005). **Generator decision
  (recorded per MT-03):** OpenAPI Generator `dart-dio` v**7.26.0**, jar
  pinned by URL + SHA-256 (`1760050094…da5e35e`) and fetched once into
  git-ignored `.dart_tool/openapi-generator/`; after that generation runs
  offline against the committed schema. Regeneration and the drift gate are
  wired into the Flutter tooling as `dart run tool/openapi_client.dart
  regen` / `… check` — `check` snapshots the committed client, regenerates
  in place (generate → `build_runner` → deterministic per-file lint stamps →
  `dart format`) and exits 1 on any byte difference; proven both ways on this
  host (in-sync exit 0; injected drift → exit 1 naming the file, regenerated
  output restored). Output is generation-owned at
  `lib/orchestrator_mobile.dart` + `lib/src/**` — no hand-authored endpoint
  models anywhere else. Hand-written wrapper `OrchestratorClient` constructs
  the client from `appConfigProvider` (base URL = resolved origin, no
  committed endpoint) and installs the **single** Section 9.2 mapping point:
  `ErrorMappingInterceptor` deserializes every non-2xx body into the five
  envelope fields (`code`, `message`, `retryable`, `details`,
  `correlation_id`) as `OrchestratorApiException`; a fixture 409 proves
  `TASK_ALREADY_CLAIMED` survives intact (both documented renderings — the
  canonical nested `{"error":{…}}` and the current top-level schema shape —
  are handled at that one point; see OQ below). Mutating calls can attach
  `Idempotency-Key` via `idempotencyHeaders(...)` (NFR-12; tested), and
  `X-Correlation-ID` is generated per `headers.md` with caller-supplied
  values honored (tested). Verified: `flutter analyze` 0 issues (the
  generator's style-lint noise is silenced per generated file only, never
  package-wide, so type checking still covers every generated line) and the
  9-test API suite green; pubspec.lock updated for dio/built_value and the
  pinned toolchain.
- **OQ (report, not worked around):** the canonical wire envelope is nested —
  `{"error": {…five fields…}}` (Section 9.2, quoted verbatim in
  error-envelope.md) — while `schemas/openapi.yaml` references the
  `ErrorEnvelope` schema (top-level five fields) directly as the non-2xx
  response body. The mobile mapping point accepts both shapes so the client
  works against either, and a fixture test covers each; the contract owner
  (WP-1.1/schema owner) should reconcile the schema rendering with Section
  9.2 (schema diff review, Section 20.4 item 4).
- **CI follow-up (report):** the drift gate command exists and is documented
  (`dart run tool/openapi_client.dart check` from `mobile/`); adding it as a
  workflow step belongs to the CI pipeline owner — `.github/workflows/*` is
  outside this WP executor's file ownership, so no workflow file was touched.
- **MT-5.5-04 — deferred:** dependencies not yet met (WP-5.3 device
  registration/device-bound token backend; consumes MT-5.5-03's client) —
  deferred until WP-5.3 lands, per roadmap.md §4a (recorded 2026-10-12).
- **MT-5.5-05 — deferred:** dependency WP-1.10 (SSE realtime gateway) not yet
  met — deferred until WP-1.10 lands, per roadmap.md §4a (recorded
  2026-10-12).
- **MT-5.5-06 — deferred:** depends on MT-5.5-04 (secure storage/gate) and
  MT-5.5-05 (SSE) plus WP-5.3 backend flows — all outstanding; deferred per
  roadmap.md §4a (recorded 2026-10-12).
