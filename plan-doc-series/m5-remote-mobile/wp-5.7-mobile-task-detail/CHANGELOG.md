# WP-5.7 Mobile Task Detail — Changelog

One entry per micro-task, in ID order. Owner scope: `mobile/**` + this
changelog only.

## MT-5.7-01 — Task detail screen (done)

Full `TaskDetailScreen` behind the board's task-detail routes, with all
Section 14.1 areas: summary (title/state/priority/worker chip,
`latest_feedback`, inert-markdown description), acceptance criteria,
a fixed-height (360 px) checkpoint-stream region, resolutions
(summaries only), and the attachments section (entry points for
MT-5.7-03). Loading / catalog-only error+retry / honest no-task state
(no id → never a fabricated task) / Section 14.2 offline-stale banner.

Decisions:
- **Board-cache summary fallback (recorded):** a failed live load falls
  back to the cached board row (id → project derived from the
  `{PID}-T{index}` id format) with a visible stale banner; resolutions
  are live-only in v1 — the cached summary never pretends to be fresh.
- `task.updated|transitioned|claimed|released` events trigger one
  targeted row refetch (deduped in flight) through the shared
  `core/realtime/` SseClient — consumed, never forked.
- Route takes the task id via `settings.arguments` (board push);
  deep-link-by-id remains WP-5.9's job.

## MT-5.7-02 — Live checkpoint feed (done)

`CheckpointFeedNotifier` + `CheckpointFeedView`: foreground live append
via the shared SseClient, background/resume replay with exactly-once
checkpoint ids (dedupe by `checkpoint_id`, server-timestamp ordering —
P7), history/event reconciliation (events buffered during the initial
history load, merged deduped, documented order), cursor "load older",
and the Section 14.2 polling fallback with a visible degraded indicator
(honest "periodic updates" labeling — never "Live" while polling).

Decisions:
- **Polling interval: 30 s** (`checkpointPollInterval`), test-overridable
  via the notifier's `pollInterval` field; active only while the shared
  client reports `SseConnectionStatus.polling`.
- Unknown/malformed event payloads are skipped (Section 20.4 item 6) —
  no crash, no invented rows.

## MT-5.7-03 — Attachment viewing (done)

`AttachmentViewerScreen` (image pinch-zoom via auth-aware base64 fetch,
OCR transcript + layout caption, document pages with Section 9.5
pagination — one page per call, no hidden prefetch), the attachments
list section with processing badges, live row refresh on
`attachment.processing|ready|failed`, the P10 untrusted-content banner
on every text-derived pane (the server's own banner prefix is never
stripped), and catalog-only error copy (ATTACHMENT_NOT_READY /
ATTACHMENT_UNSUPPORTED_FORMAT; anything else falls back to the generic
read messages — no invented codes, raw server text never shown).

Decisions:
- **Explicit formats only** — `image_base64` / `text_ocr` / `markdown`;
  the app never requests `auto` (capability guessing risk note).
- **flutter_markdown, inert:** `MarkdownBody` with no extensions and no
  tap/link handlers (P10) — markdown is data; raw HTML renders as text.
- **OQ-07 default:** the Description pane only appears when the server
  sent a `short_description` — the client never fabricates one.
- A failed content fetch shows the banner plus an honest no-content
  state; the tab count never shifts (the row stays visible).
- Memory-only viewer state (Section 12.4) — no attachment text is
  persisted off-device.

## Cross-cutting

- Generated client regenerated (review-endpoint churn from the backend
  audit landed in `schemas/openapi.yaml`); `check` in sync.
- Final battery: `flutter analyze` clean, `dart format --set-exit-if-changed`
  exit 0, `flutter test` 199/199 green.
