import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// One cursor page of `GET /api/v1/events` (Section 9.6 envelope rows;
/// pagination.md: `results` + `next_cursor`).
class AuditLogPage {
  const AuditLogPage({required this.events, this.nextCursor});

  final List<EventEnvelope> events;
  final String? nextCursor;
}

/// Read-only repository behind the audit log viewer (MT-5.9-04).
///
/// The interface admits **no mutating method by construction** — the
/// viewer is read-only (Section 12.5 / FR-SEC-03); this is the
/// structural half of the no-mutation guarantee that the widget test
/// then observes end to end.
abstract class AuditLogRepository {
  /// One page of event history. The endpoint's declared sort is id
  /// **ascending** (Section 9.6 monotonic order), cursor-paginated per
  /// WP-0.5; filters are exactly the API's documented query
  /// parameters — `project` and `task` (Section 9.2; anything the API
  /// does not accept is simply not offered, never faked client-side).
  Future<AuditLogPage> fetchEvents({
    String? project,
    String? task,
    String? cursor,
    int pageSize = 100,
  });
}

/// Generated-client implementation of [AuditLogRepository].
class GeneratedAuditLogRepository implements AuditLogRepository {
  GeneratedAuditLogRepository(this._client);

  final OrchestratorClient _client;

  @override
  Future<AuditLogPage> fetchEvents({
    String? project,
    String? task,
    String? cursor,
    int pageSize = 100,
  }) async {
    try {
      final Response<EventListEnvelope> response =
          await _client.api.apiV1EventsRetrieve(
        cursor: cursor,
        pageSize: pageSize,
        project: project,
        task: task,
      );
      final EventListEnvelope? envelope = response.data;
      if (envelope == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Events response carried no body.',
          retryable: true,
        );
      }
      return AuditLogPage(
        events: envelope.results.toList(),
        nextCursor: envelope.nextCursor,
      );
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The audit log repository for the app; tests override it.
final Provider<AuditLogRepository> auditLogRepositoryProvider =
    Provider<AuditLogRepository>(
  (Ref ref) => GeneratedAuditLogRepository(ref.watch(apiClientProvider)),
);
