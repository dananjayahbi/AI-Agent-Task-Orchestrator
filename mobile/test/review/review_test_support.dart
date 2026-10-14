import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/features/review/dictation_service.dart';
import 'package:orchestrator_mobile/features/review/review_repository.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../board/board_test_support.dart';
import '../task_detail/task_detail_test_support.dart';

export '../board/board_test_support.dart' show makeTask;

/// The suite's canonical task under review.
const String reviewTaskId = 'PID00001-T001';

/// A well-formed [Task] escalated to review (Section 8.4 reason kept
/// canonical on the row).
Task makeReviewTask({
  String id = reviewTaskId,
  StateEnum state = StateEnum.inHumanReview,
  int version = 7,
  String? reviewReason = 'test_failure',
  String mergeStatus = 'none',
}) =>
    makeTask(
      id: id,
      state: state,
      version: version,
      mergeStatus: mergeStatus,
      title: 'Review me',
    ).rebuild(
      (TaskBuilder b) => b..reviewReason = reviewReason,
    );

/// A well-formed [Resolution] with authoritative Section 9.7 stats.
Resolution makeReviewResolution({
  String id = 'res-1',
  String taskId = reviewTaskId,
  int attemptNumber = 2,
  String branchName = 'feat/PID00001-2',
  String executionSummary = 'Ran the suite; 2 files touched.',
  List<String> changedFiles = const <String>['src/a.dart', 'src/b.dart'],
  Map<String, Object?>? diffSummary,
}) =>
    Resolution(
      (ResolutionBuilder b) => b
        ..id = id
        ..taskId = taskId
        ..attemptNumber = attemptNumber
        ..branchName = branchName
        ..commitSha = 'deadbeefcafe'
        ..executionSummary = executionSummary
        ..changedFiles.replace(changedFiles)
        ..diffSummary = JsonObject(
          diffSummary ??
              <String, Object?>{
                'files': changedFiles.length,
                'insertions': 42,
                'deletions': 7,
              },
        )
        ..requiresHumanAttention = false
        ..riskJustification = ''
        ..submittedBySession = 'session-1'
        ..submittedAt = DateTime.utc(2026, 10, 11),
    );

/// The Section 9.4 persisted rule-result rows — the exact shape WP-3.4
/// writes (`{rule, passed, review_reason}`).
List<Map<String, Object?>> ruleResultsJson({
  List<String> failing = const <String>['R2', 'R5'],
}) {
  const Map<String, String> reasons = <String, String>{
    'R1': 'test_failure',
    'R2': 'scope_violation',
    'R3': 'critical_path_changed',
    'R4': 'migration_detected',
    'R5': 'sensitive_config_changed',
    'R6': 'diff_over_threshold',
    'R7': 'low_confidence',
    'R8': 'auditor_flagged',
    'R9': 'policy_forced_review',
  };
  return <Map<String, Object?>>[
    for (final String rule in reasons.keys)
      <String, Object?>{
        'rule': rule,
        'passed': !failing.contains(rule),
        'review_reason': failing.contains(rule) ? reasons[rule] : null,
      },
  ];
}

/// A well-formed [AuditReport] fixture (Section 7.2 fields).
AuditReport makeAuditReport({
  String id = 'report-1',
  String taskId = reviewTaskId,
  String resolutionId = 'res-1',
  int confidence = 2,
  String auditorNotes = 'Tests fail on the touched module.',
  ProposedVerdictEnum proposedVerdict = ProposedVerdictEnum.fail,
  PolicyDecisionEnum? policyDecision = PolicyDecisionEnum.escalate,
  String? engineVersion = '1.0.0',
  List<Map<String, Object?>>? ruleResults,
  Map<String, Object?>? evidence,
}) =>
    AuditReport(
      (AuditReportBuilder b) => b
        ..id = id
        ..taskId = taskId
        ..resolutionId = resolutionId
        ..auditorSessionId = 'aud-1'
        ..evidence = JsonObject(
          evidence ??
              <String, Object?>{
                'commands': <Object?>[
                  <String, Object?>{
                    'label': 'flutter test',
                    'command': 'flutter test',
                    'exit_code': 1,
                    'summary': '12 failed',
                  },
                ],
                'lint_clean': true,
                'acceptance_criteria_results': <Object?>[
                  <String, Object?>{
                    'criterion': 'covers the bug',
                    'met': false
                  },
                ],
              },
        )
        ..confidence = confidence
        ..auditorNotes = auditorNotes
        ..proposedVerdict = proposedVerdict
        ..policyDecision = policyDecision
        ..policyRuleResults =
            ruleResults == null ? null : JsonObject(ruleResults)
        ..policyEngineVersion = engineVersion
        ..createdAt = DateTime.utc(2026, 10, 11, 9),
    );

/// A well-formed [ResolutionPatch] fixture (Section 9.7 both paths).
ResolutionPatch makePatch({
  String resolutionId = 'res-1',
  String? patchBody,
  bool tooLarge = false,
  String? marker,
}) =>
    ResolutionPatch(
      (ResolutionPatchBuilder b) => b
        ..resolutionId = resolutionId
        ..kind = 'patch'
        ..sha256 = '0' * 64
        ..sizeBytes = patchBody?.length ?? 0
        ..diffTooLarge = tooLarge
        ..patch_ = patchBody
        ..marker = marker,
    );

/// The frozen review response for a scripted decision.
ReviewDecisionResponse makeReviewResponse({
  required DecisionEnum decision,
  String taskId = reviewTaskId,
  String? resolutionId = 'res-1',
  String state = 'pending',
  String mergeStatus = 'none',
  int version = 8,
}) =>
    ReviewDecisionResponse(
      (ReviewDecisionResponseBuilder b) => b
        ..decision.replace(
          ReviewDecisionRecord(
            (ReviewDecisionRecordBuilder rb) => rb
              ..id = 'decision-1'
              ..taskId = taskId
              ..resolutionId = resolutionId
              ..decision = decision
              ..note = ''
              ..decidedBy = 'owner'
              ..decidedVia = DecidedViaEnum.mobile
              ..decidedAt = DateTime.utc(2026, 10, 11, 10),
          ),
        )
        ..task.replace(
          VerdictTaskState(
            (VerdictTaskStateBuilder tb) => tb
              ..id = taskId
              ..state = state
              ..version = version
              ..reviewReason = null
              ..mergeStatus = mergeStatus,
          ),
        ),
    );

/// Scripted [ReviewRepository]: fixture rows, scripted errors, and a
/// recorded decision log for payload assertions.
class FakeReviewRepository implements ReviewRepository {
  final Map<String, Task> tasks = <String, Task>{};
  final Map<String, List<Resolution>> resolutions =
      <String, List<Resolution>>{};
  final Map<String, List<AuditReport>> reports = <String, List<AuditReport>>{};
  final Map<String, ResolutionPatch> patches = <String, ResolutionPatch>{};

  /// When set, the next read parks until released (drives loading
  /// states).
  Completer<void>? gate;

  Object? nextTaskError;
  Object? nextResolutionError;
  Object? nextReportError;
  Object? nextPatchError;
  Object? nextDecisionError;

  /// When set, the next decision submission parks until released
  /// (drives double-submit tests).
  Completer<void>? decisionGate;

  /// Response served by [submitDecision] when no error is scripted.
  ReviewDecisionResponse decisionResponse;

  final List<ReviewDecisionRequest> decisionCalls = <ReviewDecisionRequest>[];
  final List<String> idempotencyKeys = <String>[];
  int patchCalls = 0;

  FakeReviewRepository({ReviewDecisionResponse? decisionResponse})
      : decisionResponse = decisionResponse ??
            makeReviewResponse(decision: DecisionEnum.approve);

  Future<void> _maybeWait() async {
    final Completer<void>? held = gate;
    if (held != null) {
      gate = null;
      await held.future;
    }
  }

  @override
  Future<Task> fetchTask(String taskId) async {
    await _maybeWait();
    final Object? error = nextTaskError;
    if (error != null) {
      nextTaskError = null;
      throw error;
    }
    final Task? task = tasks[taskId];
    if (task == null) {
      throw apiError(CodeEnum.TASK_NOT_FOUND, statusCode: 404);
    }
    return task;
  }

  @override
  Future<List<Resolution>> fetchResolutions(String taskId) async {
    final Object? error = nextResolutionError;
    if (error != null) {
      nextResolutionError = null;
      throw error;
    }
    return resolutions[taskId] ?? <Resolution>[];
  }

  @override
  Future<List<AuditReport>> fetchAuditReports(String taskId) async {
    final Object? error = nextReportError;
    if (error != null) {
      nextReportError = null;
      throw error;
    }
    return reports[taskId] ?? <AuditReport>[];
  }

  @override
  Future<ResolutionPatch> fetchPatch(String resolutionId) async {
    patchCalls += 1;
    final Object? error = nextPatchError;
    if (error != null) {
      nextPatchError = null;
      throw error;
    }
    final ResolutionPatch? patch = patches[resolutionId];
    if (patch == null) {
      throw apiError(CodeEnum.TASK_NOT_FOUND, statusCode: 404);
    }
    return patch;
  }

  @override
  Future<ReviewDecisionResponse> submitDecision({
    required String taskId,
    required ReviewDecisionRequest request,
    required String idempotencyKey,
  }) async {
    decisionCalls.add(request);
    idempotencyKeys.add(idempotencyKey);
    final Completer<void>? held = decisionGate;
    if (held != null) {
      decisionGate = null;
      await held.future;
    }
    final Object? error = nextDecisionError;
    if (error != null) {
      nextDecisionError = null;
      throw error;
    }
    return decisionResponse;
  }
}

/// Transport-level failure (no catalog code, retryable) — what a dead
/// connection looks like at the client seam.
OrchestratorApiException offlineError() => OrchestratorApiException.unparsed(
      message: 'connection lost',
      retryable: true,
    );

/// Scripted [DictationService]: scripted transcripts, scripted
/// capability/permission failures, recorded stop calls.
class FakeDictationService implements DictationService {
  bool failWithPermission = false;
  bool failWithCapability = false;
  int startCalls = 0;
  int stopCalls = 0;

  void Function(String)? _onText;
  void Function()? _onEnded;

  /// Transcript pushed when a session starts (if any).
  String? transcriptOnStart;

  @override
  Future<void> start({
    required void Function(String text) onText,
    required void Function() onEnded,
  }) async {
    startCalls += 1;
    if (failWithPermission) {
      throw const DictationUnavailableException('permission');
    }
    if (failWithCapability) {
      throw const DictationUnavailableException('capability');
    }
    _onText = onText;
    _onEnded = onEnded;
    final String? scripted = transcriptOnStart;
    if (scripted != null) {
      onText(scripted);
    }
  }

  @override
  Future<void> stop() async {
    stopCalls += 1;
    final void Function()? ended = _onEnded;
    _onEnded = null;
    ended?.call();
  }

  /// Emits another transcript chunk mid-session (partial result).
  void emit(String text) => _onText?.call(text);

  /// Ends the session from the platform side (timeout).
  void platformEnded() {
    final void Function()? ended = _onEnded;
    _onEnded = null;
    ended?.call();
  }
}

/// Provider overrides for review-sheet tests — the fake repository
/// covers the sheet, its dialogs and the diff region (one seam).
List<Override> reviewOverrides({
  required FakeReviewRepository repository,
  FakeDictationService? dictation,
}) =>
    <Override>[
      reviewRepositoryProvider.overrideWithValue(repository),
      if (dictation != null)
        dictationServiceProvider.overrideWithValue(dictation),
    ];
