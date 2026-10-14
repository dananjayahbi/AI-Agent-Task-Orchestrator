import 'dart:math';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/read_error_messages.dart';
import 'review_repository.dart';

/// Screen state of the review sheet (Section 20.3: loading, ready,
/// error and the Section 14.2 offline state are separate, testable
/// values).
enum ReviewStatus { loading, ready, error, offline }

/// What the last submitted decision produced — the Section 8.2 outcome
/// the sheet echoes back (T15 merge-pending, T16 back to pending).
class ReviewOutcome {
  const ReviewOutcome({required this.decision, required this.task});

  final DecisionEnum decision;

  /// Post-transition task identity from the response (Section 7.2).
  final VerdictTaskState task;

  bool get mergePending =>
      decision == DecisionEnum.approve && task.mergeStatus == 'pending';
}

/// Everything the sheet renders: the task row, the resolution under
/// review (pinned at load — Section 14.2 approve safety), the audit
/// report for that resolution (nullable: Section 8.5 / pre-audit
/// escalations degrade honestly), the submission flow flags and the
/// last informational notice.
class ReviewState {
  const ReviewState({
    required this.status,
    this.task,
    this.resolutions = const <Resolution>[],
    this.report,
    this.notice,
    this.outcome,
    this.error,
    this.isSubmitting = false,
  });

  const ReviewState.loading() : this(status: ReviewStatus.loading);

  const ReviewState.error(OrchestratorApiException error)
      : this(status: ReviewStatus.error, error: error);

  const ReviewState.offline({OrchestratorApiException? error})
      : this(status: ReviewStatus.offline, error: error);

  final ReviewStatus status;
  final Task? task;
  final List<Resolution> resolutions;

  /// Newest submission first — the sheet pins the first row and binds
  /// the approve decision to it (Section 14.2).
  Resolution? get pinnedResolution =>
      resolutions.isEmpty ? null : resolutions.first;

  /// The audit report for the pinned resolution; null when none exists
  /// (missing-report degradation, MT-5.8-02 — never a fabricated one).
  final AuditReport? report;

  /// True when the app cannot reach the server (transport-level
  /// failure) — mutations are disabled outright (Section 14.2: clear
  /// offline state, nothing queued).
  bool get offline => status == ReviewStatus.offline;

  /// The action bar is live only in the ready state with a load pin in
  /// place and no submission in flight.
  bool get actionsEnabled =>
      status == ReviewStatus.ready && !isSubmitting && task != null;

  final OrchestratorApiException? error;
  final String? notice;
  final ReviewOutcome? outcome;
  final bool isSubmitting;

  ReviewState _copyWith({
    ReviewStatus? status,
    Task? task,
    List<Resolution>? resolutions,
    AuditReport? report,
    bool clearReport = false,
    String? notice,
    bool clearNotice = false,
    ReviewOutcome? outcome,
    OrchestratorApiException? error,
    bool clearError = false,
    bool? isSubmitting,
  }) {
    return ReviewState(
      status: status ?? this.status,
      task: task ?? this.task,
      resolutions: resolutions ?? this.resolutions,
      report: clearReport ? null : (report ?? this.report),
      notice: clearNotice ? null : (notice ?? this.notice),
      outcome: outcome ?? this.outcome,
      error: clearError ? null : (error ?? this.error),
      isSubmitting: isSubmitting ?? this.isSubmitting,
    );
  }

  /// Ready transition that keeps notices and the outcome across a
  /// refresh (used after decisions).
  ReviewState copyWithReady({
    required Task task,
    required List<Resolution> resolutions,
    required AuditReport? report,
    String? notice,
    bool clearNotice = false,
    ReviewOutcome? outcome,
    bool isSubmitting = false,
    OrchestratorApiException? error,
    bool clearError = true,
  }) {
    return ReviewState(
      status: ReviewStatus.ready,
      task: task,
      resolutions: resolutions,
      report: report,
      notice: clearNotice ? null : (notice ?? this.notice),
      outcome: outcome ?? this.outcome,
      error: clearError ? null : error,
      isSubmitting: isSubmitting,
    );
  }

  ReviewState submitting(bool value) => _copyWith(isSubmitting: value);

  ReviewState withNotice(String message) =>
      _copyWith(notice: message, clearError: true);

  ReviewState clearedNotice() => _copyWith(clearNotice: true);
}

/// Pick the audit report that belongs to [resolutionId] from a
/// newest-first list; null when the escalation has no report for the
/// resolution under review (Section 8.5 coder-evidence path).
AuditReport? reportForResolution(
  List<AuditReport> reports,
  String resolutionId,
) {
  for (final AuditReport report in reports) {
    if (report.resolutionId == resolutionId) {
      return report;
    }
  }
  return null;
}

/// Wire spelling of a decision (Section 20.5: canonical values on
/// display — `request_changes`, never the Dart camelCase name).
String decisionWireName(DecisionEnum decision) {
  if (decision == DecisionEnum.requestChanges) {
    return 'request_changes';
  }
  return decision.name;
}

/// Friendly, catalog-only copy for a failed decision submission
/// (Section 20.4 item 5 — codes map to messages; raw server text never
/// shown). Falls back to the shared read messages for codes shared
/// with the read paths.
String friendlyDecisionErrorMessage(OrchestratorApiException error) {
  switch (error.code) {
    case CodeEnum.VERSION_CONFLICT:
      return 'The submission changed while you were reviewing — the sheet '
          'has refreshed. Confirm again against the new resolution.';
    case CodeEnum.TASK_STATE_CONFLICT:
      return 'The task is no longer awaiting review — nothing was changed.';
    case CodeEnum.ROLE_NOT_PERMITTED:
      return 'This account cannot record review decisions.';
    case CodeEnum.AUTH_FORBIDDEN_PROJECT:
      return 'This account cannot review that project.';
    case CodeEnum.AUTH_REQUIRED:
      return 'Your session has expired — unlock to sign in again.';
    case CodeEnum.VALIDATION_ERROR:
      return 'The server rejected the decision — check the note and try again.';
    case CodeEnum.RATE_LIMITED:
      return 'Too many requests — wait a moment and try again.';
    case CodeEnum.SERVER_ERROR:
      return 'The server had a problem — try again in a moment.';
    default:
      if (error.code == null && error.retryable) {
        return 'Could not reach the server — nothing was queued. Try again '
            'when you are back online.';
      }
      if (error.code == null) {
        return 'Something went wrong — try again.';
      }
      return friendlyReadErrorMessage(error);
  }
}

/// Review sheet state holder (MT-5.8-01) — one notifier per task id
/// (Riverpod family, the single established state-management pattern).
///
/// Deliberately *not* SSE-subscribed (recorded decision): the sheet is
/// an action surface, so its data is pinned at load and every decision
/// outcome is re-read from the server response/reload — a background
/// change is caught by the backend's stale-resolution guard (WP-3.6),
/// which is the acceptance path of MT-5.8-04.
class ReviewNotifier extends AutoDisposeFamilyNotifier<ReviewState, String> {
  ReviewNotifier();

  late String _taskId;
  final Random _random = Random();
  int _loadToken = 0;

  @override
  ReviewState build(String taskId) {
    _taskId = taskId;
    Future<void>.microtask(load);
    return const ReviewState.loading();
  }

  /// Loads task, resolutions and audit reports (network-first).
  ///
  /// A transport-level failure with nothing loaded is the Section 14.2
  /// offline state; a catalog failure is the error state; a failure
  /// over an already-ready state keeps the data and posts a notice
  /// (never replacing a good sheet with a transient error).
  Future<void> load() async {
    final String taskId = _taskId;
    final int token = ++_loadToken;
    final ReviewState previous = state;
    try {
      final ReviewRepository repository = ref.read(reviewRepositoryProvider);
      final List<Object> results = await Future.wait<Object>(<Future<Object>>[
        repository.fetchTask(taskId),
        repository.fetchResolutions(taskId),
        repository.fetchAuditReports(taskId),
      ]);
      if (token != _loadToken) {
        return; // Superseded — drop silently.
      }
      final Task task = results[0] as Task;
      final List<Resolution> resolutions = results[1] as List<Resolution>;
      final List<AuditReport> reports = results[2] as List<AuditReport>;
      final AuditReport? pinned = resolutions.isEmpty
          ? null
          : reportForResolution(reports, resolutions.first.id);
      state = previous.status == ReviewStatus.ready
          ? previous.copyWithReady(
              task: task,
              resolutions: resolutions,
              report: pinned,
            )
          : ReviewState(
              status: ReviewStatus.ready,
              task: task,
              resolutions: resolutions,
              report: pinned,
              outcome: previous.outcome,
            );
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      if (error.code == null && error.retryable) {
        state = previous.status == ReviewStatus.ready
            ? previous.withNotice(friendlyDecisionErrorMessage(error))
            : ReviewState.offline(error: error);
      } else {
        state = previous.status == ReviewStatus.ready
            ? previous.withNotice(friendlyDecisionErrorMessage(error))
            : ReviewState.error(error);
      }
    }
  }

  /// Clears the informational notice (dismiss affordance).
  void dismissNotice() {
    state = state.clearedNotice();
  }

  /// Posted when an open confirmation is invalidated by a refresh (the
  /// stricter Section 14.2 reading — MT-5.8-04 risk note): the user
  /// must confirm again against the resolution now pinned.
  void noteStaleConfirmation() {
    state = state.withNotice(
      'The submission changed while your confirmation was open — confirm '
      'again against the new resolution.',
    );
  }

  /// Approve-and-merge bound to the [resolutionId] the reviewer saw
  /// (Section 14.2; T15). [version] is the task version the sheet
  /// rendered (optimistic lock).
  Future<void> approve({
    required String resolutionId,
    required int version,
  }) {
    return _submit(
      request: ReviewDecisionRequest(
        (ReviewDecisionRequestBuilder b) => b
          ..decision = DecisionEnum.approve
          ..resolutionId = resolutionId
          ..version = version
          ..note = '',
      ),
    );
  }

  /// Request changes with a mandatory note (T16 guard — the dialog
  /// enforces non-empty; the server re-checks).
  Future<void> requestChanges({
    required String note,
    required int version,
  }) {
    return _submit(
      request: ReviewDecisionRequest(
        (ReviewDecisionRequestBuilder b) => b
          ..decision = DecisionEnum.requestChanges
          ..note = note
          ..version = version,
      ),
    );
  }

  /// Reassign: returns the task to `pending`, clears the worker; the
  /// note is optional and becomes `latest_feedback` when provided
  /// (Section 11.5; T16).
  Future<void> reassign({required String note, required int version}) {
    return _submit(
      request: ReviewDecisionRequest(
        (ReviewDecisionRequestBuilder builder) => builder
          ..decision = DecisionEnum.reassign
          ..note = note
          ..version = version,
      ),
    );
  }

  Future<void> _submit({required ReviewDecisionRequest request}) async {
    if (state.isSubmitting || state.status != ReviewStatus.ready) {
      return; // Double-submit guard (P6/ADR-012 on the wire).
    }
    final ReviewState current = state;
    state = current.submitting(true).clearedNotice();
    final DecisionEnum decision = request.decision;
    try {
      final ReviewDecisionResponse response =
          await ref.read(reviewRepositoryProvider).submitDecision(
                taskId: _taskId,
                request: request,
                idempotencyKey: _newIdempotencyKey(decision),
              );
      final String notice;
      if (decision == DecisionEnum.approve) {
        notice =
            'Approved — merge pending (the merge executor takes it from here).';
      } else if (decision == DecisionEnum.requestChanges) {
        notice =
            'Changes requested — the task returned to pending with your note.';
      } else {
        notice =
            'Reassigned — the task returned to pending and the worker was cleared.';
      }
      // Re-read the row so the sheet shows the server's post-transition
      // state (never a locally invented one), keeping the outcome.
      state = state.submitting(false);
      await load();
      state = state.copyWithOutcome(
        ReviewOutcome(decision: decision, task: response.task),
        notice: notice,
      );
    } on OrchestratorApiException catch (error) {
      state = state.submitting(false);
      final bool stale = error.code == CodeEnum.VERSION_CONFLICT ||
          error.code == CodeEnum.TASK_STATE_CONFLICT;
      state = state.withNotice(friendlyDecisionErrorMessage(error));
      if (stale) {
        // Refresh to the new resolution / state so a fresh confirmation
        // is required (MT-5.8-04 acceptance).
        await load();
      }
    }
  }

  String _newIdempotencyKey(DecisionEnum decision) {
    final int suffix = _random.nextInt(1 << 32);
    return 'mobile-${decision.name}-${DateTime.now().microsecondsSinceEpoch}-$suffix';
  }
}

extension on ReviewState {
  ReviewState copyWithOutcome(ReviewOutcome outcome, {required String notice}) {
    return ReviewState(
      status: status,
      task: task,
      resolutions: resolutions,
      report: report,
      notice: notice,
      outcome: outcome,
      error: error,
      isSubmitting: false,
    );
  }
}

/// One review sheet per task id.
final AutoDisposeNotifierProviderFamily<ReviewNotifier, ReviewState, String>
    reviewProvider =
    AutoDisposeNotifierProviderFamily<ReviewNotifier, ReviewState, String>(
  ReviewNotifier.new,
);
