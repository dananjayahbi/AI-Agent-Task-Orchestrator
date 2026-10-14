# WP-5.8 Mobile Review Action Sheet — Changelog

One entry per micro-task, in ID order. Owner scope: `mobile/**` + this
changelog only.

## Unreleased

**MT-5.8-01 — Review sheet layout (done).**
`ReviewScreen` behind the `/review` route (id-addressed like task
detail — the WP-5.9 deep-link contract), rendering the Section 14.1
order: escalation reason (canonical Section 8.4 string + friendly
label), rule-results region, execution summary, auditor notes, evidence,
diff region, and a fixed bottom action bar with the three actions
(approve / request changes / reassign) above the safe area. Data loads
through the generated client via a repository seam
(`review_repository.dart`) with loading / catalog-error+retry /
**offline** / ready states; the offline state disables every action
with the Section 14.2 clear copy and queues nothing. Entry point: an
"Open review sheet" affordance on `in_human_review` board cards
(direct navigation by task id; push deep links remain WP-5.9).

Decisions (recorded per the MT risk notes):
- **Screen, not bottom sheet:** the sheet is a named route area that
  must survive id-based deep links and hold an action bar on small
  screens; system back is the only dismissal — the sole draft state
  lives in the dialogs (discard safety = MT-5.8-05).
- **Notifications-shell entry** is not wired: that area is still the
  MT-5.9-03 placeholder (deferred with WP-5.9); the board entry plus
  the id-addressed route satisfy the acceptance contract.
- **No SSE subscription in the sheet notifier** (unlike task detail):
  the sheet pins its data at load and re-reads outcomes from server
  responses/reloads — staleness is caught by the backend's
  stale-resolution guard (WP-3.6), which is MT-5.8-04's acceptance
  path.
- Offline = transport-level failure with nothing loaded (no
  connectivity plugin in v1); catalog failures are the error state;
  a failed refresh over ready data keeps the data and posts a notice.

Test evidence: `cd mobile; flutter test test\review\review_sheet_layout_test.dart`
→ 8/8 green (regions+action bar, loading, error, offline (no queued
decisions), missing-report degradation, no-id state, id-addressed
route, board handoff by id). `flutter analyze` → no issues.

**MT-5.8-02 — Rule results and evidence display (done).**
`RuleResultsView` + `EvidenceView`: every Section 9.4 R1–R9 outcome
read verbatim from `policy_rule_results` (stable `{rule, passed,
review_reason}` rows — zero client-side evaluation), failing rules
first with each failing rule's Section 8.4 reason (canonical + friendly),
the passing block collapsed behind one disclosure (all nine rows on a
full-pass report — Section 9.4 persists every rule, so all are shown),
and the persisted `policy_engine_version` on the card header for
traceability. Evidence renders the Section 10.5 shape: commands with
`label`/`command`/`exit_code`/`summary` (own horizontal scroll),
`lint_clean`, acceptance-criteria results, confidence (1–5), proposed
verdict, policy decision (null → "not yet evaluated"), auditor notes;
unknown evidence keys land in a collapsed disclosure (key + truncated
JSON, never guessed). Missing report (Section 8.5 / pre-audit path)
degrades to reason + execution summary with an explicit "no audit
report" line — no fabricated pass table; null/empty `policy_rule_results`
reads as "not recorded".

Test evidence: `cd mobile; flutter test test\review\rule_results_test.dart`
→ 5/5 green (failing R2/R5 rows + reasons + collapse order + engine
version, full nine-row pass table, evidence shape, missing-report
degradation, unknown-key collapse). `flutter analyze` → no issues.

**MT-5.8-03 — Lazy per-file diff renderer with highlighting (done).**
`DiffRegionView` + `diff_parser.dart` (a faithful Dart port of the web
parser's semantics — same marker, same stats-only representation, so
the two viewers of one Section 9.7 patch cannot drift): fetch-once
patch through the repository, interpreted exactly like the server's
representation (`diff_too_large`/null body → the shared **"diff too
large"** marker with the backend's `diff_summary`/`changed_files`
stats and file list — never recomputed; empty body → distinct empty
state; unparseable prose → rendered as-is). Parsed patches render in a
fixed-height region with `ListView.builder` (**lazy per file, zero
cache extent** — a shrink-wrap would pre-build everything, which is
what Section 14.2 forbids), per-file monospace body with its own
horizontal scroll, add/del/context tinting, next/previous file
navigation with a "File i of n" label, a **400-line per-file cap** with
"Show more" chunks (single lines truncate at **2,000 chars** with a
continuation ellipsis — both thresholds recorded here), and minimal
keyword highlighting by extension (dart/kt/java/js/ts/py/go/rs/sh +
comment-line tint; plain fallback for anything else — grammars stay a
dependency decision, per the MT risk note). A re-pinned resolution
resets the region's per-patch UI state instead of inheriting it.

Test evidence: `cd mobile; flutter test test\review\diff_renderer_test.dart`
→ 9/9 green (marker+authoritative stats+file list, lazy build of only
the visible file, per-file cap + Show more, 5,000-line capped+fast
(<4 s bar), horizontal-scroll containment, highlighting with plain
fallback, empty state, opaque state, payload interpretation). This is
a Dart-only widget battery; fixture patches follow the web suite's
discipline. `flutter analyze` → no issues.

**MT-5.8-04 — Approve-and-merge with resolution-bound confirmation (done).**
`showApproveConfirmDialog`: the confirmation shows exactly Section
14.2's three facts — **task id, branch, diff stats** (backend
`diff_summary`, never computed from the renderer) — plus MT-5.8-02's
failing/passing rule summary. The facts and the resolution id/version
are **captured once when the dialog opens**; the approve request binds
that resolution id and the rendered task version, carries a fresh
`Idempotency-Key` (ADR-012), and a background re-pin invalidates the
open confirmation client-side **before any request leaves** (the
risk note's strict reading — surfaced via `noteStaleConfirmation`).
The backend rejection path (WP-3.6 `VERSION_CONFLICT` /
`TASK_STATE_CONFLICT`) maps from catalog codes to friendly copy,
refreshes the sheet and closes the confirmation so a fresh one is
required; success applies T15: post-transition identity re-read from
the server, the outcome banner shows `merge_status: pending` — never a
premature `completed` (ADR-008). Double-submit is guarded in the
notifier and the dialog; offline/loading states keep the action
disabled with nothing queued.

Decisions: merge completion arrives via events/refresh later (WP-5.9
area); the sheet tolerates re-opening and shows the current
`merge_status` from the row.

Test evidence: `cd mobile; flutter test test\review\approve_flow_test.dart`
→ 5/5 green (confirmation contents incl. rule summary + cancel sends
nothing, payload binding (resolution id + version + idempotency key) →
merge-pending banner, stale rejection surfaced + refreshed, open-dialog
re-pin invalidation with zero requests, double-tap submits once).
`flutter analyze` → no issues.

**MT-5.8-05 — Request changes with dictated note (done).**
`showRequestChangesDialog` + `dictation_service.dart`: a required note
(T16 guard — empty/whitespace-only keeps Send disabled) as first-class
typed input, plus a **dictate** affordance backed by the OS speech
framework (`speech_to_text`, `listenOptions.onDevice: true` so the
recognizer runs on-device where the platform supports it): the running
transcript fills the editable field (read-only while dictating), the
user stops, edits, then sends; **no audio is captured, stored or
uploaded by the app** — text only (Section 14.2). The UI states
"on-device … audio is never uploaded" next to the button. Permission
denial and missing capability both degrade to a clear message with
typed input fully working (no dead end); any platform failure is an
"unavailable" outcome, never a crash. Success shows the T16 outcome
(task back to `pending`, `request_changes` decision recorded with
`decided_via: mobile`), conflicts map from catalog codes, offline keeps
Send disabled with nothing queued, and dismissing with uncommitted text
confirms first (`PopScope` → Keep editing / Discard) — the discard
dialog itself sends nothing.

Recorded readings: on-device = the platform speech framework with no
third-party SDK and no app-side audio path (the plan's own parenthetical);
`dictationServiceProvider` is the test seam (scripted fake).
The dictation capability check is the platform's `initialize`/`listen`
result surfaced as "dictation unavailable" (MT risk note).

Test evidence: `cd mobile; flutter test test\review\request_changes_test.dart`
→ 5/5 green (dictate → edit → send payload incl. version + whitespace
guard, permission-degraded typed fallback, capability-unavailable,
discard confirmation flow (keep/discard, no send), cancel without
confirmation). `flutter analyze` → no issues.

**MT-5.8-06 — Reassign action (done).**
`showReassignDialog`: a confirmation that states the outcome in plain
language (task returns to `pending`, worker cleared, any eligible
agent may claim — Sections 11.5/8.2) with an **optional** note (empty
stays empty; the server sets `latest_feedback` when provided) and
**no assignee picker anywhere** — reassign is free re-claim, nothing
invented (Section 20.5). The payload is explicit (`decision: reassign`,
its own idempotency key) and never ambiguous with `request_changes`
(the two dialogs are covered by separate tests, per the risk note).
Success re-reads the row and shows the T16 outcome banner with the
canonical wire value (`reassign recorded — task is now pending`) plus
the "worker was cleared" notice; `TASK_STATE_CONFLICT` /
`VERSION_CONFLICT` surface catalog-mapped friendly copy with no
outcome recorded. Offline/loading keep the action disabled (Section
14.2, no queued reassigns).

Decision (recorded): confirmation-vs-direct is a parity choice with
the web dialog — the plan mandates confirmation only for approve; the
discard-text guard was NOT added here (the plan attaches it to the
dictated/typed draft of MT-5.8-05 only; reassign's note is optional and
the dialog is a short confirmation).

Test evidence: `cd mobile; flutter test test\review\reassign_test.dart`
→ 4/4 green (confirmation copy + optional note enabled + no assignee
picker + cancel, empty-note payload distinctness, provided-note payload,
conflict → friendly message without outcome). `flutter analyze` → no
issues; full suite: `cd mobile; flutter test` (see final batch report).
