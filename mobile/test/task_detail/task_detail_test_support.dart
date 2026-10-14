import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/features/task_detail/attachment_providers.dart';
import 'package:orchestrator_mobile/features/task_detail/checkpoint_feed_providers.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_repository.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';

/// A valid 1×1 transparent PNG — decoded by `Image.memory` without
/// codec errors (raw junk bytes would async-throw in the image
/// resource service and fail the test harness).
const String validPngBase64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQAB'
    'h6FO1AAAAABJRU5ErkJggg==';

/// A well-formed generated [Checkpoint] fixture (Section 7.2 fields).
Checkpoint makeCheckpoint({
  required String id,
  String taskId = 'PID00001-T1',
  String message = 'Working…',
  int? percent = 40,
  String kind = 'progress',
  DateTime? timestamp,
  Map<String, dynamic>? tokenUsage,
  int attemptNumber = 1,
}) =>
    Checkpoint(
      (CheckpointBuilder b) => b
        ..id = id
        ..taskId = taskId
        ..attemptNumber = attemptNumber
        ..sessionId = 'session-1'
        ..timestamp = timestamp ?? DateTime.utc(2026, 10, 11, 12, 45, 2)
        ..message = message
        ..percent = percent
        ..kind = kind
        ..tokenUsage = tokenUsage == null ? null : JsonObject(tokenUsage),
    );

/// A well-formed generated [Resolution] fixture.
Resolution makeResolution({
  required String id,
  String taskId = 'PID00001-T1',
  int attemptNumber = 1,
  String branchName = 'feat/PID00001-1',
  String executionSummary = 'Ran the tests.',
  bool requiresHumanAttention = false,
}) =>
    Resolution(
      (ResolutionBuilder b) => b
        ..id = id
        ..taskId = taskId
        ..attemptNumber = attemptNumber
        ..branchName = branchName
        ..commitSha = 'deadbeef'
        ..executionSummary = executionSummary
        ..changedFiles.replace(const <String>['src/a.dart'])
        ..requiresHumanAttention = requiresHumanAttention
        ..riskJustification = ''
        ..submittedBySession = 'session-1'
        ..submittedAt = DateTime.utc(2026, 10, 11),
    );

/// A well-formed generated [Attachment] fixture (Section 7.2 fields).
Attachment makeAttachment({
  required String id,
  String taskId = 'PID00001-T1',
  String filename = 'shot.png',
  String mimeType = 'image/png',
  int size = 2048,
  bool isImage = true,
  String processingStatus = 'ready',
  String? failureReason,
  String? shortDescription,
}) =>
    Attachment(
      (AttachmentBuilder b) => b
        ..id = id
        ..taskId = taskId
        ..filename = filename
        ..mimeType = mimeType
        ..size = size
        ..isImage = isImage
        ..processingStatus = processingStatus
        ..failureReason = failureReason
        ..shortDescription = shortDescription
        ..createdAt = DateTime.utc(2026, 10, 11),
    );

/// A well-formed generated [AttachmentContent] fixture (Section 9.5).
AttachmentContent makeContent({
  required String attachmentId,
  required String format,
  String? content,
  String? description,
  String? imageBase64,
  int? pageNumber,
  int? totalPages,
  int? tokenCount,
}) =>
    AttachmentContent(
      (AttachmentContentBuilder b) => b
        ..attachmentId = attachmentId
        ..format = format
        ..content = content
        ..description = description
        ..imageBase64 = imageBase64
        ..mediaType = imageBase64 == null ? null : 'image/png'
        ..pageNumber = pageNumber
        ..totalPages = totalPages
        ..tokenCount = tokenCount,
    );

/// A catalog [OrchestratorApiException] for scripted failures —
/// envelope-shaped, exactly as ErrorMappingInterceptor produces.
OrchestratorApiException apiError(CodeEnum code, {int? statusCode}) =>
    OrchestratorApiException(
      statusCode: statusCode,
      code: code,
      message: 'scripted',
      retryable: false,
      details: null,
      correlationId: 'test',
    );

/// A release-on-demand async gate for scripting in-flight fetches.
class ScriptedGate {
  final Completer<void> _completer = Completer<void>();
  int waits = 0;

  /// When true, the gate has been released (later waits return promptly).
  bool get isOpen => _completer.isCompleted;

  Future<void> wait() {
    waits += 1;
    return _completer.future;
  }

  void release() => _completer.complete();
}

/// Scripted [TaskDetailRepository]: per-id rows plus scripted checkpoint
/// pages and one-shot errors.
class FakeTaskDetailRepository implements TaskDetailRepository {
  final Map<String, Task> tasks = <String, Task>{};

  /// Rows served by later `fetchTask` calls once a test promotes a task
  /// here (simulates the server row changing between fetches).
  final Map<String, Task> updatedTasks = <String, Task>{};

  final Map<String, List<Resolution>> resolutions =
      <String, List<Resolution>>{};
  final Map<String, List<Attachment>> attachments =
      <String, List<Attachment>>{};

  /// Checkpoint pages served in order per task id; when a task's script
  /// is exhausted the last page repeats (stable for polling tests).
  final Map<String, List<CheckpointPage>> checkpointPages =
      <String, List<CheckpointPage>>{};

  Object? nextTaskError;
  Object? nextCheckpointError;
  int taskCalls = 0;
  final List<String> checkpointCalls = <String>[];

  /// When set, [fetchCheckpoints] parks until released (drives the
  /// history/replay reconciliation window).
  ScriptedGate? checkpointGate;

  /// When set, [fetchTask] parks until completed (drives loading states).
  Completer<void>? held;

  @override
  Future<Task> fetchTask(String taskId) async {
    taskCalls += 1;
    final Completer<void>? gate = held;
    if (gate != null) {
      held = null;
      await gate.future;
    }
    final Object? error = nextTaskError;
    if (error != null) {
      nextTaskError = null;
      throw error;
    }
    final Task? updated = updatedTasks[taskId];
    if (updated != null) {
      return updated;
    }
    final Task? task = tasks[taskId];
    if (task == null) {
      throw apiError(CodeEnum.TASK_NOT_FOUND, statusCode: 404);
    }
    return task;
  }

  @override
  Future<List<Resolution>> fetchResolutions(String taskId) async =>
      resolutions[taskId] ?? <Resolution>[];

  @override
  Future<CheckpointPage> fetchCheckpoints(
    String taskId, {
    String? cursor,
    int pageSize = 25,
  }) async {
    checkpointCalls.add(taskId);
    final ScriptedGate? gate = checkpointGate;
    if (gate != null && !gate.isOpen) {
      await gate.wait();
    }
    final Object? error = nextCheckpointError;
    if (error != null) {
      nextCheckpointError = null;
      throw error;
    }
    final List<CheckpointPage> script = checkpointPages[taskId] ??
        <CheckpointPage>[const CheckpointPage(checkpoints: <Checkpoint>[])];
    if (script.length == 1) {
      return script.single;
    }
    return script.removeAt(0);
  }

  @override
  Future<List<Attachment>> fetchAttachments(String taskId) async =>
      attachments[taskId] ?? <Attachment>[];
}

/// Scripted [AttachmentRepository] for the viewer tests.
class FakeAttachmentRepository implements AttachmentRepository {
  final Map<String, Attachment> rows = <String, Attachment>{};

  /// Content served per `'attachmentId|format|page'` key; the bare
  /// `'attachmentId|format'` key serves any page.
  final Map<String, AttachmentContent> content = <String, AttachmentContent>{};

  Object? nextRowError;
  final Map<String, Object> nextContentErrors = <String, Object>{};
  final List<Map<String, Object?>> contentCalls = <Map<String, Object?>>[];

  @override
  Future<Attachment> fetchAttachment(String attachmentId) async {
    final Object? error = nextRowError;
    if (error != null) {
      nextRowError = null;
      throw error;
    }
    final Attachment? row = rows[attachmentId];
    if (row == null) {
      throw apiError(CodeEnum.ATTACHMENT_NOT_READY, statusCode: 409);
    }
    return row;
  }

  @override
  Future<AttachmentContent> fetchContent(
    String attachmentId, {
    required String format,
    int page = 1,
  }) async {
    contentCalls.add(<String, Object?>{
      'id': attachmentId,
      'format': format,
      'page': page,
    });
    final Object? error = nextContentErrors['$attachmentId|$format|$page'] ??
        nextContentErrors['$attachmentId|$format'];
    if (error != null) {
      nextContentErrors.remove('$attachmentId|$format|$page');
      nextContentErrors.remove('$attachmentId|$format');
      throw error;
    }
    final AttachmentContent? value = content['$attachmentId|$format|$page'] ??
        content['$attachmentId|$format'];
    if (value == null) {
      throw apiError(
        CodeEnum.ATTACHMENT_UNSUPPORTED_FORMAT,
        statusCode: 415,
      );
    }
    return value;
  }
}

/// A [CheckpointFeedNotifier] whose [build] returns a fixed state and
/// whose commands are no-ops — widget-state tests assert rendering only,
/// with no client, timers or fetches involved.
class ScriptedCheckpointFeedNotifier extends CheckpointFeedNotifier {
  ScriptedCheckpointFeedNotifier(this.initial);

  final CheckpointFeedState initial;

  @override
  CheckpointFeedState build(String taskId) => initial;

  @override
  Future<void> load() async {}

  @override
  Future<void> loadOlder() async {}
}

/// A real [SseClient] on scripted fakes — the MT-5.5-05 transport reused
/// verbatim by WP-5.7 (no forked stream client); mirrors the board
/// suite's builder without importing across test-support files.
SseClient buildDetailTestSseClient({
  required FakeSseTransport transport,
  FakeEventHistorySource? history,
  InMemoryLastEventIdStore? store,
  int maxStreamFailures = 3,
  Duration pollInterval = const Duration(milliseconds: 5),
}) =>
    SseClient(
      transport: transport,
      history: history ?? FakeEventHistorySource(),
      idStore: store ?? InMemoryLastEventIdStore(),
      backoff: fastBackoff(
        maxStreamFailures: maxStreamFailures,
        pollInterval: pollInterval,
      ),
      heartbeatTimeout: const Duration(seconds: 30),
      onWarning: (_) {},
    );

/// Overrides for pumping Task-detail-side widgets deterministically —
/// no real HTTP, no real preferences, no real stream.
List<Override> taskDetailOverrides({
  FakeTaskDetailRepository? repository,
  FakeAttachmentRepository? attachments,
  JsonCache? cache,
  SseClient? sseClient,
}) =>
    <Override>[
      taskDetailRepositoryProvider.overrideWithValue(
        repository ?? FakeTaskDetailRepository(),
      ),
      attachmentRepositoryProvider.overrideWithValue(
        attachments ?? FakeAttachmentRepository(),
      ),
      jsonCacheProvider.overrideWithValue(cache ?? InMemoryJsonCache()),
      sseClientProvider.overrideWithValue(
        sseClient ?? buildDetailTestSseClient(transport: FakeSseTransport()),
      ),
    ];
