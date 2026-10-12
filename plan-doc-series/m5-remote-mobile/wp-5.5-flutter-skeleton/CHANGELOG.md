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
- **MT-5.5-04 — complete** (deps met: WP-5.3 landed). Secure token storage +
  biometric gate (ADR-006 layer 3; Sections 12.2/14.2; release contract
  `docs/mobile/device-auth-release-contract.md`). `SecureTokenStore` seam
  over `flutter_secure_storage` (Keychain/Keystore); the device token is
  written there by exactly one call site —
  `AuthGateNotifier.storeToken` — and never appears in logs, widget state,
  or `AuthGateState`. `AuthGateNotifier` (Riverpod): cold-start probe lands
  LOCKED when a credential exists, `noCredential` when not, `storageError`
  honestly when the store is unreadable (retry affordance, never a silent
  bypass); `unlock()` runs `local_auth` 3.x with OS-passcode fallback and
  returns true only on real success; `releaseToken()` returns the token to
  the request layer **only while unlocked** (a locked app sends no
  Authorization header at all — Section 14.2); inactivity re-lock with a
  documented default of **5 minutes** (`lockTimeoutProvider` — plan leaves
  the value unspecified, so 9.10 discipline records the default; overridable
  per environment later). `AuthTokenInterceptor` injects the token only
  when released, and a 401 on an injected request fires `discardCredential`
  (delete + `noCredential` + onboarding re-entry per the release contract's
  "Rejection and recovery"). `LockGate` replaces the whole navigator while
  locked (`LockedView`: unlock, honest enrollment guidance, honest
  unsupported-device limitation, storage-retry). Platform wiring:
  Android `USE_BIOMETRIC` + `FlutterFragmentActivity` (local_auth
  requirement), iOS `NSFaceIDUsageDescription`. 18 security tests green.
  **Device-matrix decision (recorded per MT-04):** both-platform manual
  verification (real Keychain/Keystore, real biometric prompt) is pending a
  physical device run — the Windows host cannot execute it; automated tests
  cover the gate logic with scripted store/authenticator seams. Recorded as
  the remaining WP-5.5 device-matrix item alongside MT-02's iOS build.
- **MT-5.5-05 — complete** (dependency WP-1.10 landed — `/events/stream`
  exists; implemented fully against it). SSE resume client
  (`lib/core/realtime/`). `OrchestratorEvent`: the typed 7-key envelope
  (Section 9.6) with tolerant `tryParse` (malformed frames are skipped with
  a warning, never crash the stream). `SseParser`: incremental
  UTF-8+LineSplitter framing (`id:`/`data:`/comment heartbeats; chunk- and
  multi-byte-split safe — tested). `SseClient`: start/pause/resume/dispose
  over a `SseTransport` seam; **resume** sends the last processed id as
  `Last-Event-ID` (header per WP-1.10's dual contract), "processed" =
  emitted-then-persisted so a kill between emit and persist replays the
  event (at-least-once to the app, exactly-once per subscriber via the
  broadcast stream); exponential backoff + jitter with a cap; a heartbeat
  **watchdog timer** (not `Stream.timeout` — verified experimentally that
  `timeout()` does not fire over an `async*` generator) closes a silent
  connection and reconnects; on stream failures it falls back to polling
  `GET /events` with a base64url `cursorForId` (re-encoding the id exactly
  like the server's `encode_cursor`; round-trip tested against the server
  algorithm) and probes the stream back before returning to it; 401 stops
  the client (the gate's discard rule takes over) instead of storming.
  `SseLifecycleBinder` ties start/pause to gate-unlocked + app-resumed
  (Section 14.2 foreground-only streaming). `main()` persists the resume
  id via SharedPreferences (not a secret — Section 9.6). **NFR-11 note:**
  the events endpoints are not in the `schemas/openapi.yaml` snapshot yet
  (WP-1.10 lag), so the SSE transport and history cursor are hand-written
  against the documented wire contract — consistent with NFR-11's "typed
  where the contract exists" and noted as a schema follow-up below. 28
  realtime tests green.
- **MT-5.5-06 — complete** (deps met: MT-01..05 + WP-5.3). Onboarding flow
  (`lib/features/onboarding/`) with the four Section 14.1 screens in order,
  driven by `OnboardingFlowNotifier` (single flow-state source, Section
  14.3) and resumable: step + confirmed URL + completion persist in plain
  preferences (`OnboardingProgressStore` — no token material ever); resume
  is honest about what still needs an API call (URL step → itself;
  login/registration → login since the owner session was in-memory;
  enrollment → straight there because the device token is already stored).
  (1) URL entry pre-fills from flavor config, accepts the tunnel hostname,
  validates against the server's `GET /health/live` (the documented ops
  endpoint — root-level per `backend/config/urls.py`, Section 9.2; no OQ
  needed) before proceeding; a confirmed URL overrides the flavor default
  for every consumer (`main()` seed — MT-02 precedence decision honored),
  with a cheap startup re-validation so a corrupted preference falls back
  to the flavor default. (2) Login via `POST /auth/login` through the
  generated client; failures map Section 9.2 catalog codes to friendly
  copy at one point (`onboarding_messages.dart`) — no credential echo, no
  raw server text (Section 12.4; tested including password-absence and
  raw-message-absence assertions). (3) Device registration `POST /devices`
  (owner-session bearer, `Idempotency-Key` stable per logical attempt and
  rotated on fresh login — NFR-12) whose response token is handed
  directly to `gate.storeToken` in one statement chain — it never enters
  app state, widgets, or logs (MT risk note reviewed line-by-line; the
  flow test asserts `state.toString()` contains neither token). (4)
  Biometric enrollment guides arming the MT-04 gate with the real
  `local_auth` prompt; skip is honest — `finish()` claims nothing, the
  app stays locked until a real unlock (Section 14.2; tested both paths
  incl. cancelled-prompt-leaves-unfinished). Completion hands off through
  the gate's own state (unlock → shell, skip → lock view). App-level
  routing: `onboardingRequiredProvider` (seeded by `main()` from
  persisted progress; also set by `discardCredential` for post-revocation
  re-entry) makes `LockGate` render onboarding instead of shell/lock-view
  while it needs screen time. `GeneratedOnboardingApi` rebuilds a bare
  (gate-free, ADR-006 pre-auth) client per URL — the only production
  call site — with an adapter seam for the mocked-backend integration
  test. Verified: 32 onboarding tests (flow unit, widget per screen,
  full-flow mocked-backend integration asserting exactly the three
  documented calls and token placement), `flutter analyze` clean, `dart
  format --set-exit-if-changed mobile/` exit 0, all 108 `flutter test`
  green, OpenAPI drift gate in sync (client regenerated after the
  concurrent events-schema land). **Both-platform manual verification**
  (login → register → enroll on real iOS/Android) shares the MT-04
  device-matrix pending item.
- **WP-5.5 follow-ups (reported, not worked around):** (a) the events
  endpoints (`GET /events/stream`, `GET /events`) are absent from the
  `schemas/openapi.yaml` snapshot — the hand-written MT-05 transport
  should be folded into the generated client once the schema owner adds
  them (schema diff review, Section 20.4 item 4); (b) device registration
  sends `push_token: "pending-wp-5.4"` (required non-blank backend field,
  stored sensitive-at-rest and never returned) until WP-5.4 registers
  APNs/FCM; (c) tunnel request/response buffering for the SSE stream is
  a WP-5.1 (infra) verification item; (d) both-platform manual device
  matrix (real Keychain/Keystore + biometric prompt, iOS build) pending
  a physical device/macOS run.
