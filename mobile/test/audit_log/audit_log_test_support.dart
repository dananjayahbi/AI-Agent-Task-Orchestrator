import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/offline/json_cache.dart';
import 'package:orchestrator_mobile/core/realtime/realtime_providers.dart';
import 'package:orchestrator_mobile/features/audit_log/audit_log_repository.dart';
import 'package:orchestrator_mobile/features/task_detail/attachment_providers.dart';
import 'package:orchestrator_mobile/features/task_detail/task_detail_repository.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../board/board_test_support.dart' show buildTestSseClient;
import '../dashboard/dashboard_test_support.dart';
import '../realtime/realtime_test_support.dart';
import '../task_detail/task_detail_test_support.dart';

/// One scripted page: events plus the cursor to continue from.
class ScriptedPage {
  const ScriptedPage(this.events, [this.nextCursor]);

  final List<EventEnvelope> events;
  final String? nextCursor;
}

/// A recorded `GET /events` call — the wiring assertions read these.
class RecordedFetch {
  const RecordedFetch({
    this.project,
    this.task,
    this.cursor,
    required this.pageSize,
  });

  final String? project;
  final String? task;
  final String? cursor;
  final int pageSize;
}

/// Scripted [AuditLogRepository]: pages consumed in order, every call
/// recorded (filters, cursor chaining), plus scripted failures.
///
/// Read-only by construction (the interface has no mutating method) —
/// [operations] exists so the widget test can assert, end to end, that
/// exercising the screen records nothing but `fetchEvents`.
class FakeAuditLogRepository implements AuditLogRepository {
  FakeAuditLogRepository({List<ScriptedPage>? pages})
      : pages = pages ?? <ScriptedPage>[const ScriptedPage(<EventEnvelope>[])];

  final List<ScriptedPage> pages;
  final List<RecordedFetch> calls = <RecordedFetch>[];
  final List<String> operations = <String>[];

  Object? nextError;

  /// When set, the next fetch parks until released (loading states).
  Completer<void>? gate;

  int _next = 0;

  @override
  Future<AuditLogPage> fetchEvents({
    String? project,
    String? task,
    String? cursor,
    int pageSize = 100,
  }) async {
    operations.add('fetchEvents');
    calls.add(RecordedFetch(
      project: project,
      task: task,
      cursor: cursor,
      pageSize: pageSize,
    ));
    final Completer<void>? held = gate;
    if (held != null) {
      gate = null;
      await held.future;
    }
    final Object? error = nextError;
    if (error != null) {
      nextError = null;
      throw error;
    }
    final ScriptedPage page =
        pages[_next < pages.length ? _next : pages.length - 1];
    _next += 1;
    return AuditLogPage(events: page.events, nextCursor: page.nextCursor);
  }
}

/// A well-formed generated [EventEnvelope] fixture (Section 9.6 — the
/// seven envelope keys exactly).
EventEnvelope makeEvent({
  required int id,
  EventEnvelopeTypeEnum type = EventEnvelopeTypeEnum.taskPeriodTransitioned,
  String projectId = 'PID00001',
  String? taskId = 'PID00001-T001',
  String occurredAt = '2026-10-11T12:45:02Z',
  EventActorTypeEnum actorType = EventActorTypeEnum.owner,
  String actorRef = 'alice',
  Map<String, Object?>? data,
}) =>
    EventEnvelope(
      (EventEnvelopeBuilder b) => b
        ..id = id
        ..type = type
        ..projectId = projectId
        ..taskId = taskId
        ..occurredAt = occurredAt
        ..actor.replace(
          EventActor(
            (EventActorBuilder ab) => ab
              ..type = actorType
              ..ref = actorRef,
          ),
        )
        ..data = JsonObject(data ?? <String, Object?>{}),
    );

/// Transport-level failure (no catalog code, retryable).
OrchestratorApiException offlineError() => OrchestratorApiException.unparsed(
      message: 'connection lost',
      retryable: true,
    );

/// Overrides for audit log tests: the fake history plus every seam the
/// task-detail push needs (row navigation is the only navigation).
List<Override> auditLogOverrides({
  required FakeAuditLogRepository repository,
  FakeTaskDetailRepository? taskDetail,
}) =>
    <Override>[
      auditLogRepositoryProvider.overrideWithValue(repository),
      taskDetailRepositoryProvider.overrideWithValue(
        taskDetail ?? FakeTaskDetailRepository(),
      ),
      attachmentRepositoryProvider.overrideWithValue(
        FakeAttachmentRepository(),
      ),
      jsonCacheProvider.overrideWithValue(InMemoryJsonCache()),
      sseClientProvider.overrideWithValue(
        buildTestSseClient(transport: FakeSseTransport()),
      ),
    ];
