# MT-5.8-05 — Implement request-changes with dictated (speech-to-text) note

> **Context-Loss Rule:** If you have lost the context of the parent architecture plan
> `../../../ai_agent_task_orchestrator_architecture_plan.md`, STOP and re-read it (and
> `../../overview.md`) before continuing this document. Never rely on memory of the plan.

| Field | Value |
|---|---|
| ID | MT-5.8-05 |
| Title | Implement request-changes with dictated (speech-to-text) note |
| Parent WP | WP-5.8 — Review action sheet (Milestone M5) |
| Requirements | FR-MOB-05 |
| Priority | M |
| Dependencies | MT-5.8-01 (sheet action bar); WP-3.6 complete (`latest_feedback` flow); MT-5.7-01 (note rendering context on task detail) |
| Parent sections | 14.2 (Voice note), 11.5 (request changes with a note), 8.2 (T16), 7.2 (`latest_feedback`, Review Decision), 19 (WP-5.8), 20.3, 20.4, 20.5 |

## Context
Section 11.5: "request changes with a note (becomes `latest_feedback`, returns to
`pending`)"; Section 8.2 T16 makes the note mandatory ("Note required for request
changes") with side effects `latest_feedback` set, `attempt_number` preserved, worker
cleared. Section 14.2 fixes the mobile differentiator: "dictation uses on-device
speech-to-text and submits the resulting text (no audio upload in v1); user can edit
the text before sending." FR-MOB-05 requires "request changes (text or dictated
note)" — typed text remains a first-class input alongside dictation.

## Inputs / Prerequisites
* Parent plan Section 14.2 — voice-note rules: on-device STT, text-only upload,
  editable before send.
* Parent plan Sections 11.5 and 8.2 T16 — mandatory note, resulting state.
* Parent plan Section 9.2 — `POST /tasks/{id}/review` `request_changes` payload;
  Section 7.2 — `latest_feedback` and Review Decision (`decided_via` `mobile`).
* WP-3.6 — feedback propagation into `get_task_details` (Section 19 WP-3.6
  acceptance: "feedback appears in the next coder's task details").
* Platform capability: on-device speech-to-text available via the OS (Section 14.2
  requires on-device; no third-party service).

## Scope (in)
* The request-changes flow: dialog/sheet section with a required note field, both
  typed input and a **dictate** affordance using on-device speech-to-text;
  transcription lands in the editable text field; the user reviews/edits before
  sending; **no audio is uploaded or stored** (Section 14.2 v1 rule).
* Permission handling: first-use microphone permission prompt with graceful denial
  (dictation unavailable → typed input still works; no dead-end).
* Validation: submit disabled until the note is non-empty (T16 guard); whitespace-only
  counts as empty.
* Submit via the generated client with disable-while-pending; success applies T16 —
  sheet shows the task returned to `pending` with feedback recorded, `decided_via`
  `mobile` (Sections 8.2, 7.2); conflict errors refresh per canonical codes
  (Section 20.4 item 5).
* Offline: disabled with the Section 14.2 clear offline state — no queued notes.
* Discard safety: dismissing with uncommitted dictated/typed text confirms first
  (recorded UX decision).
* Widget/integration tests: dictate → editable text, permission-denied fallback,
  required-note validation, payload contains the note, success state, offline
  disabled, discard confirmation — mocked backend per Section 14.3.
* A WP changelog note.

## Out of scope
* Server-side feedback propagation — WP-3.6.
* Audio capture/upload of any kind — explicitly excluded by Section 14.2 (v1).
* Approve/reassign flows — MT-5.8-04/06.
* Web request-changes dialog — WP-4.8 (MT-4.8-03).
* Push notification of the resulting escalation — Section 9.8 worker.

## Target paths
* `mobile/` (request-changes dialog with dictation in the review sheet)
* `mobile/` tests (widget and integration tests)
* WP changelog entry

## Acceptance criteria
- [ ] Request changes requires a non-empty note before submit (Section 8.2 T16 guard)
  and the note is sent as the feedback that becomes `latest_feedback`
  (Section 11.5).
- [ ] Dictation uses **on-device** speech-to-text, fills an editable text field, and
  uploads no audio — text only (Section 14.2; FR-MOB-05 "text or dictated note").
- [ ] Permission denial degrades to typed input with a clear message
  (Section 20.3 states).
- [ ] Success shows the T16 outcome: task back to `pending`, worker cleared, decision
  recorded `decided_via` `mobile` (Sections 8.2, 7.2) — canonical values only
  (Section 20.5).
- [ ] Offline disables submission with the Section 14.2 clear offline state; nothing
  queued; conflict errors map from catalog codes (Section 20.4 item 5).
- [ ] End-to-end against the real backend: request changes works and the feedback
  reaches the next coder's task details (Section 19 WP-5.8 acceptance; WP-3.6).
- [ ] Tests green in CI; changelog note added (Section 20.4 items 2 and 7).

## Test command
Run the mobile suite filtered to request changes (for example
`flutter test --dart-define=test_filter=request_changes` or the project's
equivalent) for dictate-edit-send, permission fallback, validation, offline and
discard cases; then the WP end-to-end check against the real backend confirms
`latest_feedback` reaches `get_task_details` (Section 19 WP-5.8 acceptance); the
full mobile suite stays green.

## Attachments
* [Section 14.2 — Mobile-specific behaviors (Voice note)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 8.2 — Transition table (T16)](../../../ai_agent_task_orchestrator_architecture_plan.md)
* [Section 19 — WP-5.8 acceptance](../../../ai_agent_task_orchestrator_architecture_plan.md)

## Risk notes
* On-device STT availability/quality varies by platform and locale — treat dictation
  as an enhancement over the required text input; never block the core action on STT
  (RISK-09 scope discipline).
* Transcription may contain sensitive diff context spoken aloud — note in the UI that
  processing is on-device (Section 14.2) and do not log transcribed text.
* Platform speech APIs may require background-audio/permission config — surface
  missing capability as "dictation unavailable" rather than a crash; record the
  capability check in the changelog (Section 14.2 mandates the feature, not a
  specific OS API).
