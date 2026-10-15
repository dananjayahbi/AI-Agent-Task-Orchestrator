# WP-5.4 — Push notifications (FCM): changelog

## Unreleased

**MT-5.4-01 — Configure FCM credentials and the worker-side sender (done).**

Section 9.8's "dispatch via FCM from the worker" foundation (ADR-003;
NFR-03):

* **Config contract (Section 9.10).** New settings group in
  `apps/core/settings/base.py`: `ORCHESTRATOR_PUSH_ENABLED` (default
  **false** — a stack with no FCM project runs clean, the MT's risk
  note), `ORCHESTRATOR_FCM_PROJECT_ID`, `ORCHESTRATOR_FCM_CREDENTIALS_JSON`,
  `ORCHESTRATOR_PUSH_RETRY_MAX_ATTEMPTS` (3), and
  `ORCHESTRATOR_PUSH_RETRY_BACKOFF_SECONDS` (1 s). Pure validators
  `missing_fcm_settings` / `fcm_credentials_wellformed` back a fail-fast
  startup check scoped to *enabled* push: missing names and weak
  credentials (Section 16.2 — must parse as a JSON object with a
  non-empty `private_key`) raise `ImproperlyConfigured` naming the
  variable, never the value. `.env.example` and configuration.md carry
  names/placeholders only (Section 20.4 item 3); retry values flagged
  for owner confirmation.
* **Transport pick (recorded per the MT risk note).** `firebase-admin`
  7.x (Google's official Admin SDK, FCM v1) added to
  `backend/pyproject.toml`, imported lazily so the unit suite and
  push-disabled deployments never load it. Kept behind the
  `FcmTransport` protocol — later MTs stay testable without the library.
* **Sender** (`apps/notifications/sender.py`). Per-token retry loop:
  transient failures back off `base × 2^(n-1)` up to the configured
  budget; permanent failures return immediately; the explicit
  `classify_fcm_error` table maps FCM's documented codes to the
  transient/permanent split, marks the invalid-token subset for
  MT-5.4-04's pruning, and treats *unknown* codes as transient —
  ambiguity may cost a bounded retry, never destroy a working device.
* **Dispatch job** (`apps/notifications/dispatch.py`). The Section 9.9
  on-event job: the dispatcher's existing `trigger_review_push` seam
  enqueues `notifications.dispatch_push` via
  `transaction.on_commit` (the worker never sees an uncommitted
  trigger); the Celery task fans out to every *active* device
  (`revoked_at IS NULL`, non-empty token — the ADR-006 lost-phone
  control; **decision recorded**: no project→owner link exists on the
  `Project` model and the product is single-owner, so fan-out is all
  active devices) and invokes the sender per device. Installed from
  `NotificationsConfig.ready()` via `ensure_push_dispatch_wired()`,
  gated off in the unit layer (no broker; hermetic suite) and when
  push is disabled. All triggers active from the start, as the MT
  fixes; MT-5.4-05 inserts its preference filter downstream of the
  seam.
* **Tests** (`backend/tests/test_fcm_sender.py`, 18): config defaults,
  pure validators, real `manage.py check` boot cases (missing/weak
  refuse naming the variable without echoing the value; complete
  config boots), sender success/transient-retry-with-schedule/
  permanent-once/exhaustion, classification table incl. unknown-code
  ambiguity, transport seam override, post-commit enqueue from a real
  T9 escalation dispatch, device fan-out with revoked/empty-token
  exclusion, and both `ensure_push_dispatch_wired` gates.

**MT-5.4-02 — Define minimal push payloads (ids and short title only) (done).**

Section 9.8's payload-minimization contract, as an allowlist builder:

* `apps/notifications/payloads.py`. `build_push_payload(trigger,
  title=...)` copies exactly the five named fields — event type,
  `project_id`, `task_id`, `task_version` (the state version
  MT-5.4-03's dedupe reads) and the short title — into an all-string
  FCM data map. **Allowlist, never blocklist** (the MT's risk note):
  nothing unlisted is read, so WP-3.9 rule details, feedback, notes,
  evidence, diffs or any future event growth cannot leak; the
  dispatcher's `reason_code` rides the trigger and is deliberately not
  forwarded. Widening the set is a plan change against Section 9.8.
* Truncation policy: the title truncates to a 64-char **prefix** of
  the user's own text — display shortening, never substitution, no
  appended marker. `payload_within_size_limit` sanity-checks the
  serialized payload against a documented 4 KB bound (FCM v1's data
  ceiling) — real outputs are orders of magnitude below it.
* The dispatch job now fetches the task's short title server-side and
  routes every send through the builder (`task_short_title` yields an
  empty banner line for a deleted task rather than crashing — the ids
  still deep-link in-app, Section 14.2).
* **Tests** (`backend/tests/test_push_payload.py`, 9): exact field-set
  per trigger type, routing-id round-trip, exclusion of every
  sensitive field *and its content* even when the trigger carries it,
  reason-code exclusion, prefix-only truncation, size sanity vs the
  bound.

**MT-5.4-03 — Implement dedupe keys (event type, task id, state version) (done).**

Section 9.8's "per-device dedupe key … prevents duplicates on
retries" (ADR-012 posture):

* `apps/notifications/models.py` + migration `0001_initial`.
  `PushDedupeRecord` is unique on `(device, event type, task id,
  state version)` — the constraint *is* the mechanism:
  `apps/notifications/dedupe.py::claim_dedupe` is an insert-first
  atomic claim (own savepoint; `IntegrityError` = lost race = suppress
  the send), so two concurrent workers cannot both send (Section 18
  posture). Keyed on **state version**, not event row id (the MT's
  risk note): queue redeliveries replay different event rows; a later
  escalation (same task/type, newer version) notifies again.
* Wired into the dispatch job between device selection and the sender
  — retried jobs, re-delivered events and mid-dispatch worker restarts
  yield one push per device per key. **Record-before-send** recorded
  decision: a crash between claim and send may lose that device's one
  push; the inverse would *duplicate* on redelivery, and Section 9.8's
  stated goal is duplicate suppression (MT-5.4-04's delivery rows are
  the visibility story for the lost-push corner).
* **Tests** (`backend/tests/test_push_dedupe.py`, 10): claim wins
  once, per-device independence (never a global key), version-change
  re-notify, raw unique-constraint race, through-the-job retry/
  redelivery/restart suppression, fan-out independence with a
  pre-claimed device, exhausted-send redelivery stays suppressed,
  retention anchor.
* **Retention (recorded choice, flagged for owner confirmation — the
  MT risk note):** dedupe records persist **90 days** on
  `created_at` (`prune_dedupe_records` is the cleanup entry point,
  for WP-6.4's ops cadence) — orders of magnitude past MT-5.4-01's
  seconds-long backoff and any realistic redelivery window.

**MT-5.4-04 — Implement delivery tracking and invalid-token pruning (done).**

Section 9.8's "Delivery status tracked; invalid push tokens are
pruned" and Section 17's observability rows:

* `PushDeliveryRecord` (same migration): device, the MT-5.4-03 event
  key, outcome (`accepted`/`transient_failure`/`permanent_failure`),
  attempts, FCM error code, invalid-token flag, `created_at` — **no
  payload content** (Section 12.4: tracking is not a leak channel).
* `apps/notifications/tracking.py`: `record_delivery` (the job
  records every send), `prune_invalid_token` (blanks **only**
  `push_token` on the sender's definitive `invalid_token` verdict —
  never `revoked_at`/auth/registration state, which stay WP-5.3's;
  idempotent; the dispatch query then skips the device forever),
  `push_success_stats` (Section 17's accepted/total/failure-counts
  query — the WP-6.4 metric/alert seam), and the retention entry
  points.
* Ambiguity never prunes (the sender's unknown-code → transient rule,
  retested here end-to-end); non-token permanents (e.g.
  `THIRD_PARTY_AUTH_ERROR`) record once and keep the token; pruning
  cannot resurrect a suppressed send (dedupe rows untouched).
* **Tests** (`backend/tests/test_push_delivery_tracking.py`, 10):
  accepted/transient/permanent recording with attempt evidence,
  payload-free rows, prune-and-skip without errors, token-only
  mutation (device stays active, credential survives), ambiguous-code
  no-prune, dedupe interplay across prune + re-register, stats query
  and window filter, retention pruning for both tables.
* **Retention (recorded choice, flagged for owner confirmation):**
  delivery records persist **90 days** on `created_at`
  (`prune_delivery_records`) — operational, not audit data.

**MT-5.4-05 — Per-event-type notification preferences (done).**

Section 9.8's preference set as storage, endpoint and dispatch
consultation (OQ-13's decided default honored: per-event toggles only,
digest off):

* **Dependency ruling (recorded explicitly, per the batch-11
  interpretation brief):** this MT's "WP-5.9 (toggle UI consumer)"
  dependency names the **consumer only** — the MT's own Scope says
  "this task is storage, endpoint and dispatch consultation" and puts
  the toggle UIs (web account settings and the mobile Notifications
  screen) out of scope. The backend half therefore ships **before**
  MT-5.9-03 consumes it (built and tested in the same batch, backend
  first), not after the consumer exists. MT-5.9-03's changelog records
  the consuming side.
* **Model** (`NotificationPreference`, migration
  `0002_notificationpreference`): one row per Section 9.8 type,
  unique on `event_type` — `in_human_review`, `merge_failure`,
  `retry_exhaustion`, `completion_digest` (the closed
  `PREFERENCE_EVENT_TYPES` the API and MT-5.9-03's toggle list share).
  **Account-level, no owner/foreign-key scoping** (the MT's storage-
  granularity risk note): the same single-owner reading as MT-5.4-01's
  fan-out — one record both named surfaces (Section 13.1 web settings,
  Section 14.1 mobile toggles) read and write. Defaults where rows are
  created: escalations **on** (FR-MOB-04 out of the box), digest
  **off** (OQ-13). No mandatory-escalation carve-out is hard-coded
  (the MT's risk note): the policy question stays open, defaults on.
* **Trigger → preference-key ruling (recorded):** every push arrives
  through the one `in_human_review`-entry seam, so each trigger
  resolves to exactly **one** key — reason `retry_exhausted` (T9) →
  `retry_exhaustion`; a merge-failure row (T18: event
  `merge.failed`/`merge_failed`) → `merge_failure`; every other entry
  (T8/T10/T14, …) → the `in_human_review` umbrella; unknown → the
  umbrella, never the digest. `completion_digest` is stored and
  exposed but never consulted — no trigger can select it until the
  digest itself is built (OQ-13 keeps it off).
* **Endpoint** `GET/PUT /api/v1/notifications/preferences`
  (`apps/notifications/{views,serializers,urls}.py`): the read
  materializes the full closed set (clients never guess a default);
  the PUT accepts a partial list and answers with the full current
  set; strict input (`StrictSerializerMixin` + duplicate/empty
  rejection → `VALIDATION_ERROR`, Section 9.2 discipline). Operation
  ids `retrieve_notification_preferences` /
  `update_notification_preferences`.
* **Authorization (the MT's "confirm against the matrix and record the
  choice"):** the Section 12.2 matrix has no preferences row and
  Section 9.2 no notifications row, so the guard is its own named
  class `HasNotificationPreferencesAccess` (the `IsOwnerSession`
  precedent for non-row guards) granting **Owner and Device** — the
  two actors the plan hands these surfaces — and denying every agent
  (push stays the owner's surface, like the events row). Both verbs
  covered; anonymous → `AUTH_REQUIRED`. The Section 9.2 contract test
  carries the two operations as **documented plan gaps** with PROOF
  pointers (its established GAPS mechanism).
* **Dispatch consultation** (`dispatch.py`): the gate runs after
  trigger selection and **before dedupe/send** (the MT's Scope
  ordering) — a disabled type produces **zero FCM attempts, zero
  dedupe claims and zero tracking rows** (the Section 17
  success-rate metric cannot be skewed), counts as `suppressed` in
  the job summary, and the payload/title fetch is skipped entirely.
  Nothing is stored anywhere, so re-enabling notifies only events
  dispatched afterwards (no retro-fire by construction); the
  recorded nuance, pinned by a test: because the key was never
  claimed, a *re-dispatch* of the same never-delivered trigger after
  re-enabling delivers once — re-enabling itself fires nothing.
* **Contracts:** OpenAPI snapshot regenerated (`manage.py
  spectacular`, schema diff = the two operations + three components)
  and kept; the mobile client was regenerated from it (MT-5.9-03
  consumes the generated operations, NFR-11).
* **Tests** (`backend/tests/test_notification_preferences.py`, 19):
  OQ-13 defaults + materialization; idempotent reads; PUT round trip
  (persist + full-set answer); unknown type / unknown fields /
  duplicates / empty list all refuse with `VALIDATION_ERROR`; the
  Owner+Device+denied-agent+anonymous authorization matrix on both
  verbs; the trigger→key mapping table (incl. unknown → umbrella,
  never digest); disabled type → zero transport calls, zero dedupe
  rows, zero delivery rows, both devices counted suppressed;
  per-type isolation (umbrella off, merge/retry still send; retry
  toggle governs only the retry trigger); re-enable notifies future
  events only; the ordering pin; digest never selectable by dispatch.
  Lint/type clean (`ruff check`, `ruff format --check`, full
  `mypy .` → Success, 419 files); full backend suite
  (`uv run pytest tests/ -q --ignore=tests/integration`) →
  **1616 passed, 4 skipped** (1597 baseline + 19 new).
