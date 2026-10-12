import 'dart:convert';

import 'package:dio/dio.dart';

import 'orchestrator_event.dart';

/// One cursor page of `GET /events` (history; Section 9.2 Events row,
/// pagination.md envelope: `results` + `next_cursor`).
class EventHistoryPage {
  const EventHistoryPage({required this.events, required this.nextCursor});

  final List<OrchestratorEvent> events;

  /// Opaque cursor for the next page; null = end of list.
  final String? nextCursor;
}

/// History seam for the polling fallback (Section 14.2: "fall back to
/// polling … fetches event history (GET /events) and emits the same typed
/// events").
abstract class EventHistorySource {
  /// Fetches one page after [cursor] (null = first page), filtered like the
  /// stream (Section 9.6 filter names).
  Future<EventHistoryPage> fetch({
    String? cursor,
    int pageSize = 100,
    String? project,
    String? task,
  });

  /// Encodes [lastId] into the server's opaque cursor shape
  /// (`apps/core/pagination.py: encode_cursor` — urlsafe base64 of the
  /// stringified id, padding stripped). Clients are told cursors are
  /// opaque, but the polling fallback has no server-side "after id" param
  /// on `GET /events`; re-encoding our own resume id round-trips exactly
  /// through `decode_cursor`. Recorded as a WP-5.5 decision + follow-up OQ
  /// (an `after_id`-style param would remove the need).
  static String cursorForId(int lastId) {
    final String padded = base64Url.encode(utf8.encode('$lastId'));
    return padded.replaceAll('=', '');
  }
}

/// Dio-backed history source. Uses the same interceptors as the API client
/// (device token from the gate, Section 9.2 error mapping) — the typed
/// generated client does not cover `GET /events` yet: the committed
/// `schemas/openapi.yaml` snapshot predates WP-1.10, whose views declare
/// the endpoint only in code. Reported as a contract follow-up (NFR-11);
/// the hand-written half here is parsing, not endpoint models.
class DioEventHistorySource implements EventHistorySource {
  DioEventHistorySource(this._dio);

  final Dio _dio;

  @override
  Future<EventHistoryPage> fetch({
    String? cursor,
    int pageSize = 100,
    String? project,
    String? task,
  }) async {
    final Response<Map<String, dynamic>> response =
        await _dio.get<Map<String, dynamic>>(
      '/api/v1/events',
      queryParameters: <String, dynamic>{
        if (cursor != null) 'cursor': cursor,
        'page_size': pageSize,
        if (project != null) 'project': project,
        if (task != null) 'task': task,
      },
    );
    final Map<String, dynamic> body =
        response.data ?? const <String, dynamic>{};
    final Object? results = body['results'];
    final List<OrchestratorEvent> events = <OrchestratorEvent>[];
    if (results is List) {
      for (final Object? item in results) {
        if (item is! Map) {
          continue;
        }
        final OrchestratorEvent? event =
            OrchestratorEvent.tryParse(Map<String, dynamic>.from(item));
        if (event == null) {
          // Malformed item: skipped with a warning at the call site — a
          // bad row never crashes the poll (MT-5.5-05 acceptance item 1).
          continue;
        }
        events.add(event);
      }
    }
    final Object? nextCursor = body['next_cursor'];
    return EventHistoryPage(
      events: events,
      nextCursor:
          nextCursor is String && nextCursor.isNotEmpty ? nextCursor : null,
    );
  }
}
