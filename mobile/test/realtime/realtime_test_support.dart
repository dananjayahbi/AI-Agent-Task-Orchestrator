import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'package:orchestrator_mobile/core/realtime/event_history_source.dart';
import 'package:orchestrator_mobile/core/realtime/last_event_id_store.dart';
import 'package:orchestrator_mobile/core/realtime/orchestrator_event.dart';
import 'package:orchestrator_mobile/core/realtime/sse_client.dart';
import 'package:orchestrator_mobile/core/realtime/sse_transport.dart';

/// Test double for [LastEventIdStore] — plain memory, records writes.
class InMemoryLastEventIdStore implements LastEventIdStore {
  InMemoryLastEventIdStore([this.value]);

  int? value;
  final List<int> writes = <int>[];

  @override
  Future<int?> read() async => value;

  @override
  Future<void> write(int id) async {
    value = id;
    writes.add(id);
  }
}

/// Scripted [SseTransport]: each open consumes the next scripted result —
/// either an error to throw or a live controller the test feeds bytes into.
class FakeSseTransport implements SseTransport {
  final List<Object?> script = <Object?>[];
  final List<Map<String, String>> openedHeaders = <Map<String, String>>[];
  final List<Map<String, String>> openedQuery = <Map<String, String>>[];
  final List<String> openedPaths = <String>[];
  final List<StreamController<Uint8List>> opened =
      <StreamController<Uint8List>>[];

  /// Every open attempt, successful or not (errors do not reach [opened]).
  int attemptCount = 0;

  /// Queues a live connection; the test writes SSE bytes via
  /// [emitTo]/[emitRawTo].
  void queueStream() => script.add(null);

  /// Queues a failure for the next open.
  void queueError(Object error) => script.add(error);

  int get openCount => opened.length;

  StreamController<Uint8List> controllerAt(int index) => opened[index];

  /// Emits an SSE frame for [envelope] on connection [index].
  void emitTo(int index, Map<String, dynamic> envelope) {
    final String id = envelope['id'].toString();
    final String data = jsonEncode(envelope);
    emitRawTo(index, 'id: $id\ndata: $data\n\n');
  }

  /// Emits a heartbeat comment on connection [index].
  void emitHeartbeatTo(int index) => emitRawTo(index, ': heartbeat\n\n');

  void emitRawTo(int index, String text) {
    opened[index].add(Uint8List.fromList(utf8.encode(text)));
  }

  void closeAt(int index) {
    opened[index].close();
  }

  @override
  Future<SseConnection> open({
    required String path,
    Map<String, String> query = const <String, String>{},
    Map<String, String> headers = const <String, String>{},
  }) async {
    attemptCount++;
    if (script.isEmpty) {
      throw StateError('FakeSseTransport: no scripted connection left.');
    }
    final Object? next = script.removeAt(0);
    if (next != null) {
      throw next;
    }
    openedPaths.add(path);
    openedQuery.add(query);
    openedHeaders.add(headers);
    final StreamController<Uint8List> controller =
        StreamController<Uint8List>();
    opened.add(controller);
    return SseConnection(controller.stream, controller.close);
  }
}

/// Scripted [EventHistorySource]: pages consumed in order per fetch; every
/// call's parameters are recorded for assertions.
class FakeEventHistorySource implements EventHistorySource {
  final List<EventHistoryPage> pages = <EventHistoryPage>[];
  final List<Map<String, Object?>> calls = <Map<String, Object?>>[];
  Object? nextError;

  @override
  Future<EventHistoryPage> fetch({
    String? cursor,
    int pageSize = 100,
    String? project,
    String? task,
  }) async {
    calls.add(<String, Object?>{
      'cursor': cursor,
      'pageSize': pageSize,
      'project': project,
      'task': task,
    });
    if (nextError != null) {
      final Object error = nextError!;
      nextError = null;
      throw error;
    }
    if (pages.isEmpty) {
      return const EventHistoryPage(
          events: <OrchestratorEvent>[], nextCursor: null);
    }
    return pages.removeAt(0);
  }
}

/// A well-formed Section 9.6 envelope (the plan's example shape).
Map<String, dynamic> envelopeJson({
  required int id,
  String type = 'task.transitioned',
  String? projectId = 'PID00001',
  String? taskId = 'T-00042',
  String occurredAt = '2026-10-11T12:45:02Z',
  String actorType = 'agent',
  String actorRef = 'agent-1',
  Map<String, dynamic>? data = const <String, dynamic>{'to': 'in_progress'},
}) {
  return <String, dynamic>{
    'id': id,
    'type': type,
    'project_id': projectId,
    'task_id': taskId,
    'occurred_at': occurredAt,
    'actor': <String, dynamic>{'type': actorType, 'ref': actorRef},
    'data': data,
  };
}

/// Backoff config with millisecond-scale delays so tests run fast while
/// exercising the real loop.
SseBackoffConfig fastBackoff({
  int maxStreamFailures = 3,
  Duration pollInterval = const Duration(milliseconds: 5),
}) {
  return SseBackoffConfig(
    initial: const Duration(milliseconds: 2),
    max: const Duration(milliseconds: 8),
    factor: 2,
    jitter: 0,
    maxStreamFailures: maxStreamFailures,
    pollInterval: pollInterval,
  );
}

/// A 401 [DioException] carrying a (minimal) response — the shape
/// [SseClient] treats as an auth failure.
DioException unauthorizedException() {
  final RequestOptions options = RequestOptions(path: SseClient.streamPath);
  return DioException(
    requestOptions: options,
    response: Response<dynamic>(
      requestOptions: options,
      statusCode: 401,
    ),
    type: DioExceptionType.badResponse,
  );
}

/// Polls [condition] until true or [timeout] — the client's loop is driven
/// by real (millisecond) timers, so tests wait for observable state.
Future<void> waitFor(
  bool Function() condition, {
  Duration timeout = const Duration(seconds: 2),
  String? reason,
}) async {
  final DateTime deadline = DateTime.now().add(timeout);
  while (!condition()) {
    if (DateTime.now().isAfter(deadline)) {
      throw StateError('waitFor timed out${reason == null ? '' : ': $reason'}');
    }
    await Future<void>.delayed(const Duration(milliseconds: 2));
  }
}
