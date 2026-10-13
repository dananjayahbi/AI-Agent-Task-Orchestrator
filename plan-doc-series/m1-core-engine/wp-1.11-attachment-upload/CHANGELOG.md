# WP-1.11 — Attachment storage and upload API: changelog

Short note per completed micro-task (parent plan Section 20.4, item 7).

## Unreleased

- **MT-1.11-01 (storage abstraction)** —
  `apps/attachments/storage.py`: one `StorageBackend` protocol with two
  implementations selected **by configuration only** (Section 16.3) —
  `LocalStorageBackend` (default, rooted at `MEDIA_ROOT`) and
  `S3StorageBackend` (the reserved seam: the configuration half builds
  from the Section 9.10 group and then refuses with the recorded
  WP-6.2 marker — never a silent local fallback; the client lands with
  WP-6.2). Keys are **content-addressed**: `content_key(sha256)` is a
  pure function of the digest, so identical bytes produce the same key
  from either backend (Sections 9.5, 16.3). Recorded readings: the key
  *format* is `objects/<aa>/<full-hex>` — a two-level fan-out so the
  local volume never holds one flat directory of millions of entries
  (the plan fixes "content-hash keys", not the layout; the format is
  an implementation detail behind `content_key`, never parsed by
  callers); the local backend treats keys as untrusted and refuses
  every escaping shape (traversal/absolute/separator — Section 12.3;
  uploads are never stored outside the configured root); writes are
  atomic (temp file in the destination directory + `os.replace`, and a
  failed write leaves no scratch behind); `get_storage()` fails fast on
  an unknown selector (Section 9.10). Public contract unchanged — no
  schema diff (item 4: N/A noted). The S3 contract half is exercised
  through its configuration path only — no boto fixture exists, so the
  client half stays the explicit `NotImplementedError` marker (MT
  acceptance: "skipped with an explicit marker").
- **MT-1.11-02 (upload validation)** —
  `apps/attachments/validation.py`: the endpoint-independent stage that
  runs **before any bytes are stored** — per-file size cap, per-task
  count and total caps (all configurable through the new `ATTACHMENT_`
  Section 9.10 group with the exact Section 9.5 defaults: 25 MB / 10 /
  100 MB), MIME validation by **pure-Python content sniffing** (magic
  bytes; no native dependency) against the Section 9.5 allowlist
  verbatim (none added, none dropped — traceability test asserts it).
  Recorded readings: **DOCX is verified structurally** — the zip
  container must hold `word/document.xml`, never zip magic alone (the
  MT's risk note); Markdown and plain text share one sniffable "text"
  family (no magic number exists — strict UTF-8 with no NULs/binary
  controls) and the declared type refines within that family; a
  declared type that contradicts the sniffed content is rejected
  (415 `ATTACHMENT_UNSUPPORTED_FORMAT`); `application/octet-stream`
  (the multipart default for a type-less part) is treated as *no
  declaration*, never a claim — the sniffed content decides (Section
  9.5's rule, made precise); oversize/over-count/over-total answer 400
  `VALIDATION_ERROR` with the numbers in the envelope `details`; the
  count/total counters are computed **under the task row lock** at
  write time (the concurrency risk note — the service locks, this
  module computes); soft-deleted records (MT-1.11-05) free their
  capacity; de-duplication identity is the sha256, probed per task.
  New settings appended: `ORCHESTRATOR_ATTACHMENT_MAX_FILE_BYTES`
  (26214400), `_MAX_PER_TASK` (10), `_MAX_TOTAL_BYTES` (104857600),
  `_RETENTION_GRACE_DAYS` (30 — OQ-10's default, used not re-decided);
  configuration.md rows and the compose `.env.example` entries follow
  the append-only rule.
- **MT-1.11-03 (multipart upload endpoint)** —
  `POST /tasks/{id}/attachments` (caller **Owner** only — Section 9.2
  gives agents read access; the scope guard runs first, ADR-004):
  multipart `file` part → MT-1.11-02 validation → bytes stored via the
  MT-1.11-01 abstraction under the content key → record created with
  `processing_status = uploaded` (FR-ATT-07) → the **pipeline enqueue
  seam** invoked post-commit (`set_enqueue_seam`/`enqueue_processing`;
  today a documented no-op, MT-1.12-01 wires the worker job — the seam
  is exercised by every upload test). Recorded readings: the whole
  sequence runs in **one transaction with the task row locked**
  (`select_for_update`) so the Section 9.5 counters cannot overshoot;
  a duplicate upload answers **200** with the existing descriptor
  instead of 201 (one record, one object — the de-duplication
  acceptance; the response-shape choice is locked in the OpenAPI
  diff); `Idempotency-Key` replay (headers.md fingerprint = multipart
  textual fields + the file's name/size — files stream, so full-byte
  hashing is the de-dup stage's job, a layered design); the enqueue
  seam runs **post-commit** (a pipeline job never observes a row the
  upload then rolls back); the upload rollback window can leave an
  unreferenced content-addressed object — harmless and self-healing,
  with the Section 9.9 retention sweep as the designed cleanup; uploads
  to completed/archived tasks are **accepted** (Section 9.5/16.3 gate
  *deletion* on completion, not upload — recorded); there is no
  `attachment.uploaded` event-catalog value, so upload emits none
  (the pipeline's `attachment.processing|ready|failed` land with
  WP-1.12); a missing `file` part answers `VALIDATION_ERROR`. The
  25 MB body risk note: Django's `DATA_UPLOAD_MAX_MEMORY_SIZE`
  excludes file uploads from its cap, so the multipart parser spools
  the file without a non-canonical early rejection; the validator is
  the first (canonical) gate, and ASGI/proxy body limits above 25 MB
  are WP-5.1's edge verification, noted here.
- **MT-1.11-04 (descriptor listing)** —
  `GET /tasks/{id}/attachments` + `GET /attachments/{id}`, caller
  Owner or the project's agent token (the Section 9.2 read cell; the
  bridge's `read_task_attachment` activates WP-2.x). Descriptors carry
  the **FR-ATT-03 field shape, locked here**: `id`, `task_id`,
  `filename`, `mime_type`, `size`, `is_image`, `processing_status`,
  plus `token_count` and `short_description` — **null until the
  WP-1.12 pipeline fills them** (the MT's risk note: this shape feeds
  task payloads, the web modal and the mobile views; the OpenAPI diff
  is its lock). Recorded readings: ordering is `(-created_at, -id)` —
  the pagination.md default shape with the UUID primary key as the
  deterministic tiebreak (the MT's "stable (by id)" is the tiebreak
  half; an id-only sort would be stable but not the documented
  default); composite opaque cursor, fetch-one-lookahead
  `next_cursor`; `page_size` clamps to the documented 25/100 defaults;
  the `/attachments/{id}` scope guard resolves the row's task project
  (a UUID carries no PID — ADR-004, never from the body), and unknown
  or malformed ids answer **400 `VALIDATION_ERROR`** — the closed
  catalog has no attachment not-found code, so the recorded generic
  mapping applies (the same asymmetry projects carry, MT-1.3-03);
  soft-deleted rows are invisible on list **and** detail; devices are
  not in the caller cell (`ROLE_NOT_PERMITTED`); the shared views carry
  `AgentEndpointThrottle` for the agent-read cell (WP-1.8's recorded
  shared-route pattern — the owner's write halves ride the same class
  budget; FR-SEC-05 keying is per token, so owner sessions never share
  an agent's budget). `GET /attachments/{id}/content` remains deferred
  (WP-1.14) and stays in the drift guards.
- **MT-1.11-05 (deletion rules + retention hooks)** —
  `DELETE /attachments/{id}` (Owner only) resolves the Section 9.2
  endpoint vs Section 16.3's "never by user action on completed tasks"
  **conservatively**: completed/archived tasks answer **409
  `TASK_STATE_CONFLICT`** (`AttachmentOnImmutableTask`) pointing at the
  retention path; earlier states soft-delete (``deleted_at`` stamped —
  the one documented model addition to the Section 7.2 field list, a
  nullable marker the retention job needs) and remove the stored
  object **only when no other live record shares the content key**
  (reference counting — the MT's sharp edge: naive key deletion would
  corrupt de-duplicated siblings; proven for per-task and cross-task
  sharing, and again inside the purge). `apps/attachments/retention.py`
  provides `purge_archived_attachments` — the hook the Section 9.9
  daily job (WP-1.7's beat wiring; scheduling is out of scope here)
  calls: archived tasks older than the grace period (Section 12.4;
  **OQ-10 default 30 days**, `ORCHESTRATOR_ATTACHMENT_RETENTION_GRACE_DAYS`
  — the documented default is used, never re-decided) have all their
  records hard-deleted (live **and** soft-deleted — the marker is
  bookkeeping that must not accumulate) and their now-orphaned objects
  removed; the boundary is inclusive-at-retain (archive + grace == now
  keeps — pinned-instant test, not a sleep race); the sweep is
  idempotent (a crashed run resumes cleanly). `drop_derived_data`
  proves Section 9.5's "derived data re-creatable" independently: the
  derived columns clear while the original (record, key, bytes) stays
  intact — the standalone hook for future storage-pressure paths.
  Deletion is idempotent at the record level: a soft-deleted row is
  unknown to the API, so no second storage decision can race the
  first. The plan-wide tension (9.2 DELETE vs 16.3 retention) is
  resolved here as the MT directs; product wanting hard delete
  anywhere would be a parent-plan amendment, not an implementation
  choice.
- **Cross-cutting** — `backend/config/urls.py` mounts the app with one
  include line; `TaskAttachment` (Section 7.2, field for field, plus
  the recorded `deleted_at`) lands with migration
  `attachments/0001_initial` and a DB-frozen `processing_status`
  check (the Section 7.4 double-constraint discipline); the
  authorization matrix gains the landed Attachments-row cases
  (upload/list/detail/delete per actor — §12.2 prints no attachments
  capability row, so this follows the WP-1.8/WP-2.x landed-routes
  pattern rather than a PROBES entry) and drops the three deferred
  entries (`/attachments/{id}/content` stays deferred for WP-1.14);
  `tests/test_rate_limiting.py`'s two attachment rows flip to
  `present=True` with the throttle wired (the file's own landing
  instruction). Follow-ups: the bridge catalog's
  `read_task_attachment` tool (WP-2.x), the `content` endpoint
  (WP-1.14), the pipeline worker job (WP-1.12) and the beat wiring of
  the retention hook (WP-1.7 schedule entry, Section 9.9).
- **Finisher verification (post-502)** — all five MTs audited
  acceptance-criterion by criterion against the landed code and suites
  (116 attachment/matrix unit cases green). Gaps filled:
  `tests/integration/test_attachment_upload_postgres.py` adds the
  MT-1.11-02 risk-note concurrent counter races on real Postgres —
  count cap, total-bytes cap and identical-bytes de-duplication
  (Postgres twin; SQLite's
  single-writer cannot prove `select_for_update`, Section 18 split;
  auto-skips on the unit layer); `tests/test_task_model.py`'s
  reverse-relation set gains `attachments` (Section 7.2's Task
  Attachment FK — relation metadata, never a Task column, same reading
  as `transitions`/`checkpoints`); the bridge contract retires the
  stale `attachment_list`/`attachment_get` pending flags and gains
  their response samples (attachment endpoints are in the document
  now); `schemas/openapi.yaml` regenerated once (byte-stable on a
  second run, picks up WP-3.1's `policy_preset` too). Final battery:
  ruff, format --check, mypy, `manage.py check`, `makemigrations
  --check`, 244-case targeted pytest (attachments + matrix + WP-1.4
  suites + rate limiting), bridge contract (13/13) — all green.
