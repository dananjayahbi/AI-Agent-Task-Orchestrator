# WP-4.5 — Task creation/edit modal and attachment uploader: changelog

## Unreleased

- **MT-4.5-01 — task form modal with field validation (done).**
  `web/components/task/task-form-modal.tsx`: one controlled surface over
  the shared `TaskFormValues` schema (Section 13.3); create via
  `POST /projects/{pid}/tasks` (T1 lands in `draft`), edit via
  `PATCH /tasks/{id}` with the `version` the client saw (Section 8.2);
  catalog errors map to friendly copy, `VALIDATION_ERROR` details map to
  field-level feedback; Radix Dialog keyboard/focus management plus an
  explicit discard confirmation on unsaved close. Entry points on the
  board: "New task" button and a per-card "Edit" (board.tsx,
  board-column.tsx, task-card.tsx). Tests:
  `web/tests/task/task-form-modal.test.tsx` (7).
- **MT-4.5-02 — markdown editor with preview (done).** Dependency
  decision (MT risk note): **no new npm dependency** —
  `web/lib/forms/markdown.ts` is a small block/inline tokenizer and
  `markdown-preview.tsx` renders the AST as React elements. No
  `dangerouslySetInnerHTML`, no `href`/`src` attributes: links render as
  inert text, images as labelled placeholders (nothing fetches remote
  resources), raw HTML/scripts stay literal — safe by construction (P10;
  Section 12.1). Round-trip fidelity is the textarea contract: save
  exactly what was typed (tested byte-identical). Tests:
  `web/tests/task/markdown-editor.test.tsx` (5).
- **MT-4.5-03 — criteria + target-scope editors (done).**
  `web/lib/forms/glob-rules.ts` mirrors WP-1.4's
  `validate_target_scope_globs` line-for-line (≤ 64 globs, ≤ 500 chars,
  no backslash/NUL, no absolute paths, no `..` segments) — one fixture
  set in the tests pins the mirror; **not** mirrored: the policy-list
  validator's `**`-segment syntax pass (the task validator performs no
  syntax check, so a client check would invent a rule the server
  accepts). Criteria mirror the backend's `ListField(child=CharField())`
  stance: the list is optional, blank rows are blocked (WP-1.4's
  T2-required-fields reads only the title — flagged as OQ below for the
  publish reading). Editors: `criteria-editor.tsx`, `scope-editor.tsx`
  (the scope panel always displays the saved-set mirror — R2/RISK-04
  context; nothing pre-filled). Per-index server details map onto rows
  (`listFieldErrorsFromDetails`). Tests:
  `web/tests/task/criteria-scope-editors.test.tsx` (6).
- **MT-4.5-04 — dependencies picker (done).**
  `web/lib/queries/task-choices.ts` + `dependencies-picker.tsx`:
  project-scoped choices (the query address is the bound project's list
  endpoint — zero-bleed is structural, Section 12.1), lazily paged
  (25/page, "Load more") — no eager full-project fetch (Section 13.4);
  client-side search over loaded pages; self and duplicate exclusion;
  each selected dependency shows its live state (T2/T4 visibility);
  `DEPENDENCY_UNMET` and other catalog codes map to friendly copy.
  **Cycle handling:** WP-1.4 validates existence, self and cycles
  server-side and rolls the whole write back (`TaskCreate.depends_on`
  contract text) — the client keeps only the obvious self-guard; no
  client cycle detection (server rejects; recorded per MT risk note).
  Tests: `web/tests/task/dependencies-picker.test.tsx` (5).
- **MT-4.5-05 — attachment uploader with progress and processing status
  (done).** `web/lib/attachments/limits.ts` mirrors the Section 9.5
  limits/allowlist (25 MB/file, 10/task, 100 MB total; PNG/JPEG/WebP/
  PDF/DOCX/Markdown/plain text) as instant client pre-checks — the
  server stays the authority (sniffing, WP-1.11).
  `attachment-dropzone.tsx`: drag-and-drop + picker, multipart upload
  through the generated client (`FormData` `file` part — NFR-11); a file
  awaiting a not-yet-created draft queues locally and uploads only after
  create succeeds (cancelled create → zero orphaned uploads, tested).
  Status (`uploaded → processing → ready|failed`) arrives **exclusively**
  from `attachment.processing|ready|failed` stream events patched into
  the `taskAttachments` cache by WP-4.3's single SSE sink
  (`patchAttachmentCaches` in board-live.ts) — the tests assert no
  polling (one list load, transitions only from events). `failed` rows
  show the pipeline's human-readable reason (FR-ATT-07) and support
  removal via `DELETE /attachments/{id}`. Server rejections map to
  canonical copy (`VALIDATION_ERROR`, `ATTACHMENT_UNSUPPORTED_FORMAT`).
  **Recorded choice:** per-file upload _progress_ is phase-based
  (queued → "Uploading…" in-flight → server-confirmed) because the
  fetch-based generated client exposes no byte-level upload hook and
  NFR-11 forbids a hand-written XHR path. Test-harness note:
  `tests/helpers/api.tsx` no longer attempts `request.clone().json()`
  for non-JSON bodies (it stalled on multipart). Tests:
  `web/tests/task/attachment-uploader.test.tsx` (6).
- **MT-4.5-06 — publish action gated on attachment readiness (done).**
  `web/lib/task/publish-gate.ts` (pure T2 mirror: title, attachments
  ready/override, completed dependencies — the WP-1.5 recorded reading
  of "dependencies exist"; unsaved edits block publish) +
  `publish-action.tsx` in the modal for saved drafts. The three-
  attachment WP-4.5 acceptance is tested: blocked until the last
  `attachment.ready` event; `failed` blocks with its reason; the
  explicit override checkbox appears only for attachment blockers, is
  never pre-selected, and sends `override: true`. **Transition seam:**
  `POST /tasks/{id}/transition` is still absent from
  `schemas/openapi.yaml`, so `publish-seam.ts` fixes the request shape
  (`{taskId, version, override}`) and an unwired consumer shows an
  explicit "not available yet" notice (WP-4.4 precedent — never a
  silent no-op); tests mock the consumer. `VERSION_CONFLICT` /
  `TASK_STATE_CONFLICT` map to the catalog's refresh guidance.
  Tests: `web/tests/task/publish-gating.test.tsx` (8).

### Open questions recorded by this WP

- **OQ: T2 override flag.** The backend's T2 guard
  (`transitions_owner._guard_publish`) passes attachment readiness
  vacuously and defines **no override flag**; FR-ATT-07 requires an
  explicit override path. The client sends `override: boolean` in the
  transition seam — the backend needs a matching flag (or a documented
  refusal of overridden publishes) before the override can be more than
  UX. Until then the server is the authority and may accept a publish
  the client gated.
- **OQ: `POST /tasks/{id}/transition` endpoint.** Still missing from
  `schemas/openapi.yaml`; the publish action's seam consumer cannot be
  wired through the typed client (NFR-11) until it lands. Regenerate the
  client (`npm run generate:api`) and bind `publish-seam.ts` when it
  does.
- **OQ (from MT-4.5-03): criteria required-for-publish?** The plan does
  not say; WP-1.4's T2 implementation requires only a non-blank title.
  The client mirrors that (criteria optional) — revisit if the server
  tightens the guard.

### Notes

- **Typed-client regen (concurrent backend churn).** During the final
  battery, `schemas/openapi.yaml` had moved under this WP (backend
  agents adding `audit_retry_count` + embedded `attachments` on `Task`).
  Ran the documented `npm run generate:api`; the regenerated client is
  part of this WP's diff and the `makeTask` test fixture was updated
  for the two new required `Task` fields. `POST /tasks/{id}/transition`
  is still absent from the schema after the regen (OQ above stands).
- **Convergence gate:** client regenerated again after the WP-3.3
  nullable-enum schema fix (SPECTACULAR hook, new schema SHA `5C57C958…`);
  web lint/typecheck/format/build green, 197/197 tests green.
