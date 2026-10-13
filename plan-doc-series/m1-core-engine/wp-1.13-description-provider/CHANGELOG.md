# WP-1.13 — Visual description provider: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.13-01 (DescriptionProvider interface + selector)** —
  `apps/attachments/description.py` rewritten as the WP-1.13 seam with
  the obligations MT-1.13-02…05 own recorded in its docstring.
  Interface: `describe(*, attachment_id, image_png, ocr_text) -> str`
  — attachment identity joins the Section 9.5 stage-2 inputs so G-14's
  "per attachment" cache key has an owner; the output contract is
  caption text or the explicit **no-description** sentinel `""`
  (never `None`, never a placeholder); the failure contract is the
  **typed** `DescriptionProviderError(reason, transient=…)` — its
  `reason` is composed from identifiers/status codes/type names only
  (Section 12.4), and no other exception counts as a provider failure
  (a programming error must surface — MT-1.13-05 risk note).
  Selection stays configuration-driven (`ORCHESTRATOR_DESCRIPTION_
  PROVIDER`, Section 9.10) with **disabled** the documented fresh-
  environment default (OQ-07); `SUPPORTED_DESCRIPTION_PROVIDERS` grew
  to `{"disabled", "anthropic-vision"}` and unknown names fail fast
  naming the supported set — the Section 9.5 `local model` stays
  undelivered (no OQ asks for it; MT-1.13-01 out-of-scope). A
  `set_description_provider` override seam joins the OCR engine's
  idiom for hermetic suites. Settings gained the Section 9.10
  `DESCRIPTION_` group's remote entries (MT-1.13-03) with the
  placeholder names appended to `infra/compose/.env.example` and
  `docs/plan/conventions/configuration.md` (append-only; credentials
  env-only, Section 12.4). The image stage still routes only through
  the interface (`pipeline_images` imports no concrete class — the
  MT-1.12-02 seam honored; import-checkable). Tests:
  `tests/attachments/test_description_provider.py` (9 — interface
  contract, default resolution, override, fail-fast with the supported
  set, disabled-zero-external-calls with network+subprocess blocked,
  and the call-spy proving the caption hook is reached under default
  configuration — the MT-1.13-02 risk note made executable).
- **MT-1.13-02 (disabled provider: no external calls)** —
  `DisabledDescriptionProvider` is the OQ-07 default and the
  out-of-the-box configuration of the whole system (G-14 "can be
  disabled"): answers `""` and touches no HTTP client, subprocess or
  network endpoint — enforced by the test (socket and subprocess
  blocked for the run), not by reading the code. With default
  settings an image flows detect → normalize → OCR → caption no-op →
  persist → `ready` with no description persisted and no failure
  recorded (WP-1.13 acceptance, first half); `""` remains the
  interface's no-description sentinel and is never a *cached* value
  (MT-1.13-04). The old "configured-but-unimplemented fails fast"
  example moved to `local-model` (`anthropic-vision` is implemented
  now — `test_image_pipeline.py` updated). Also recorded: the WP-1.12
  hook's blanket `except Exception` was **narrowed to the typed
  failure** here (degradation must not hide real pipeline bugs).
- **MT-1.13-03 (remote vision provider: config + cost logging)** —
  `apps/attachments/description_remote.py`:
  `RemoteVisionDescriptionProvider` (`anthropic-vision`) speaks the
  Anthropic Messages shape — `x-api-key` + `anthropic-version`
  headers, base64 normalized PNG block + captioning prompt (P10
  wording inside the prompt: image text is data to describe, never
  instructions), `max_tokens` bound 1024 (documented choice) — over
  stdlib `urllib` (no new dependency; recorded). Configuration:
  `ORCHESTRATOR_DESCRIPTION_REMOTE_{BASE_URL,MODEL,API_KEY,TIMEOUT_
  SECONDS}` (defaults: empty/empty/empty/30 s — enabling is an OQ-07
  deployment decision; nothing vendor-hardcoded beyond the Section 9.5
  "Anthropic-compatible" shape). **Startup fail-fast** (Section 9.10):
  `apps.core.settings.base` gained the pure
  `missing_description_remote_settings(...)` predicate plus the
  import-time raise when the remote provider is selected without its
  required values; the provider re-validates at the point of use with
  the same offending env names. **Cost logging** (Section 9.5;
  Section 17; NFR-10): every invocation emits a structured record —
  `description_provider/model/duration_ms/usage_present/input_tokens/
  output_tokens` + `attachment_id` — and a response without usage
  logs the *absence* explicitly, never fabricated zeros (OQ-07 budget
  discipline). **Failure logging**: transport errors, non-2xx and
  malformed outputs log structured records (status code / exception
  type name, duration, transient flag) and raise the typed signal;
  response bodies and the API key never reach a log record (asserted).
  Tests: `tests/attachments/test_remote_provider.py` (9 — stubbed
  transport, request shape, caption parsing, selector construction,
  missing-config fail-fast ×2, cost fields, usage absence, failure
  record, malformed shapes, credential-free logging, nothing stored on
  failure). No live calls in CI.
- **MT-1.13-04 (permanent per-attachment caching)** —
  `apps/attachments/caption.py::generate_caption`: the cache is the
  attachment row's own `layout_caption` column (Section 7.2 derived
  field — **no migration needed**; the MT's "isolated migration"
  target is satisfied by WP-1.11's model, recorded reading).
  Read-through: a stored caption short-circuits the provider (zero
  calls, zero failure risk — "produced once" is testable across
  retries/reprocessing). Write-once: a compare-and-set
  (`filter(layout_caption="").update(...)`) so concurrent attempts
  may each call the provider once (documented residual race — no
  single-flight lock claimed, per the MT risk note) but only one
  write wins and the loser adopts the stored value. Failures store
  nothing (the retry path stays free); the disabled provider's `""`
  stores nothing — G-14 caches descriptions, not absence, so
  disabled-then-enabled generates normally. "Permanently" = no TTL and
  no eviction API exists (asserted); attachment deletion removes the
  value with the record (derived-but-cached reading, stated for
  WP-1.14). Tests: `tests/attachments/test_description_cache.py` (6 —
  generate-once, permanence, retry-after-failure, disabled-then-
  enabled, empty-caption-not-cached, CAS adoption).
- **MT-1.13-05 (failure degradation to OCR-only)** —
  the caption step of `pipeline_images.process_image` catches **only**
  `DescriptionProviderError` (narrowed from WP-1.12's blanket except):
  logs one structured warning (`transient` flag + reason, Section 17)
  and continues with `""`, so the attachment reaches `ready` with its
  OCR transcript, an empty description and no `failure_detail`
  (Section 9.5 "failures degrade to OCR-only"; `failed` reasons stay
  meaningful for WP-1.14 consumers). No `attachment.failed` event is
  emitted — degraded runs are not failures (Section 9.6 catalog);
  the ready event still lands. Documented policy: one provider attempt
  per pipeline run, then degrade — the Section 9.9 retry seam never
  counts provider outages, so retry exhaustion cannot land an
  attachment in `failed` for one (asserted over multiple attempts).
  Programming errors still surface (asserted). The cache stores
  nothing on failure, so a later healthy run generates (MT-1.13-04
  contract, cross-tested). Cost logging stays accurate on failed
  attempts (failure record, no usage figures). **Visibility gap
  recorded** (MT-1.13-05 risk note): Section 17 defines no alert for
  repeated provider failures, so the structured log is the only
  signal — no alert rule was invented. Tests:
  `tests/attachments/test_degradation.py` (7 — three failure shapes
  reaching `ready` OCR-only, event assertions, single structured
  warning, retry-exhaustion stance, typed-only degradation, cache-not-
  poisoned follow-up).

Follow-ups (recorded, not done here — ownership elsewhere):
* `schemas/openapi.yaml` regeneration by the sole OpenAPI regenerator
  (backend audit agent) to publish the WP-1.13 settings and the
  WP-1.14 route; the bridge contract test validates the flip once the
  snapshot lands (the stale-flag rule order).
* The Section 9.5 `local model` implementation remains undelivered by
  design (new OQ or plan amendment required before building it).
