import 'package:built_value/serializer.dart' show FullType;
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';

/// One per-event-type switch as the UI layer sees it (MT-5.9-03) — a thin
/// value over the MT-5.4-05 wire pair so widgets never touch built_value.
class NotificationPreferenceItem {
  const NotificationPreferenceItem({
    required this.eventType,
    required this.enabled,
  });

  /// The backend's canonical wire key (`in_human_review`, `merge_failure`,
  /// `retry_exhaustion`, `completion_digest`) — the closed set the API
  /// defines; the screen renders exactly the types it is given.
  final String eventType;
  final bool enabled;

  NotificationPreferenceItem copyWith({bool? enabled}) =>
      NotificationPreferenceItem(
        eventType: eventType,
        enabled: enabled ?? this.enabled,
      );

  @override
  bool operator ==(Object other) =>
      other is NotificationPreferenceItem &&
      other.eventType == eventType &&
      other.enabled == enabled;

  @override
  int get hashCode => Object.hash(eventType, enabled);
}

/// Repository behind the toggles (Section 14.1) — one generated-client
/// operation per verb over the MT-5.4-05 endpoint (NFR-11: no hand-written
/// request layer, no raw URLs).
abstract class NotificationPreferencesRepository {
  /// `GET /notifications/preferences` — the full closed set.
  Future<List<NotificationPreferenceItem>> fetchPreferences();

  /// `PUT /notifications/preferences` — one pair in, the full set back.
  Future<List<NotificationPreferenceItem>> updatePreference({
    required String eventType,
    required bool enabled,
  });
}

/// The canonical wire spelling of a preference key (Section 20.5: the
/// generated enum's Dart name is never what the backend defines — the
/// serializer knows the wire value, same as the audit log's event types).
String _wireName(EventTypeEnum value) {
  final Object? wire = serializers.serialize(
    value,
    specifiedType: const FullType(EventTypeEnum),
  );
  return wire is String ? wire : value.name;
}

/// The generated enum for one backend wire key (closed set — the toggle
/// list *is* the GET response, so only known keys reach here).
EventTypeEnum _eventTypeFromWire(String wire) {
  for (final EventTypeEnum value in EventTypeEnum.values) {
    if (_wireName(value) == wire) {
      return value;
    }
  }
  throw OrchestratorApiException.unparsed(
    message: 'Unknown preference event type: $wire',
    retryable: false,
  );
}

List<NotificationPreferenceItem> _mapItems(
  Iterable<NotificationPreference> rows,
) =>
    rows
        .map(
          (NotificationPreference row) => NotificationPreferenceItem(
            eventType: _wireName(row.eventType),
            enabled: row.enabled,
          ),
        )
        .toList(growable: false);

/// Generated-client implementation (NFR-11; the MT-5.4-05 contract).
class GeneratedNotificationPreferencesRepository
    implements NotificationPreferencesRepository {
  GeneratedNotificationPreferencesRepository(this._client);

  final OrchestratorClient _client;

  @override
  Future<List<NotificationPreferenceItem>> fetchPreferences() async {
    try {
      final Response<NotificationPreferencesResponse> response =
          await _client.api.retrieveNotificationPreferences();
      final NotificationPreferencesResponse? body = response.data;
      if (body == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Preferences response carried no body.',
          retryable: true,
        );
      }
      return _mapItems(body.preferences);
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<List<NotificationPreferenceItem>> updatePreference({
    required String eventType,
    required bool enabled,
  }) async {
    try {
      final Response<NotificationPreferencesResponse> response =
          await _client.api.updateNotificationPreferences(
        notificationPreferencesRequest: NotificationPreferencesRequest(
          (NotificationPreferencesRequestBuilder builder) => builder
            ..preferences.replace(<NotificationPreference>[
              NotificationPreference(
                (NotificationPreferenceBuilder builder) => builder
                  ..eventType = _eventTypeFromWire(eventType)
                  ..enabled = enabled,
              ),
            ]),
        ),
      );
      final NotificationPreferencesResponse? body = response.data;
      if (body == null) {
        throw OrchestratorApiException.unparsed(
          message: 'Preferences response carried no body.',
          retryable: true,
        );
      }
      return _mapItems(body.preferences);
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The repository seam — tests override it (one seam, the review-sheet
/// pattern).
final Provider<NotificationPreferencesRepository>
    notificationPreferencesRepositoryProvider =
    Provider<NotificationPreferencesRepository>(
  (Ref ref) => GeneratedNotificationPreferencesRepository(
    ref.watch(apiClientProvider),
  ),
);

enum NotificationPreferencesStatus { loading, ready, error, offline }

class NotificationPreferencesState {
  const NotificationPreferencesState({
    required this.status,
    this.items = const <NotificationPreferenceItem>[],
    this.error,
    this.saveError,
    this.isSaving = false,
  });

  const NotificationPreferencesState.loading()
      : this(status: NotificationPreferencesStatus.loading);

  final NotificationPreferencesStatus status;

  /// The backend's set, in the API's order — toggles render from this.
  final List<NotificationPreferenceItem> items;

  /// Load failure (initial fetch or retry).
  final OrchestratorApiException? error;

  /// A failed save the user must see (restored values + this message).
  final OrchestratorApiException? saveError;

  /// One save in flight — switches lock meanwhile (no request races).
  final bool isSaving;

  bool get togglesEnabled =>
      status == NotificationPreferencesStatus.ready && !isSaving;

  /// Transport-level failure (Section 14.2 offline reading — no catalog
  /// code and retryable, the client-wide convention).
  static bool isTransportError(OrchestratorApiException error) =>
      error.code == null && error.retryable;
}

/// Loads the MT-5.4-05 set and applies toggle changes (optimistic value,
/// restore + surfaced error on failure — the AC; Section 14.2: a failed
/// mutation is never queued).
class NotificationPreferencesNotifier
    extends Notifier<NotificationPreferencesState> {
  @override
  NotificationPreferencesState build() =>
      const NotificationPreferencesState.loading();

  int _loadToken = 0;

  Future<void> load() async {
    final int token = ++_loadToken;
    final NotificationPreferencesState previous = state;
    state = NotificationPreferencesState(
      status: NotificationPreferencesStatus.loading,
      items: previous.items,
    );
    try {
      final List<NotificationPreferenceItem> items = await ref
          .read(notificationPreferencesRepositoryProvider)
          .fetchPreferences();
      if (token != _loadToken) {
        return; // Superseded — drop silently.
      }
      state = NotificationPreferencesState(
        status: NotificationPreferencesStatus.ready,
        items: items,
      );
    } on OrchestratorApiException catch (error) {
      if (token != _loadToken) {
        return;
      }
      state = NotificationPreferencesState(
        status: NotificationPreferencesState.isTransportError(error)
            ? NotificationPreferencesStatus.offline
            : NotificationPreferencesStatus.error,
        error: error,
      );
    }
  }

  /// One toggle: optimistic update, one PUT, restore + notice on failure.
  Future<void> setEnabled(String eventType, bool enabled) async {
    if (!state.togglesEnabled) {
      return; // One save at a time; the switch row is disabled meanwhile.
    }
    final List<NotificationPreferenceItem> previous = state.items;
    state = NotificationPreferencesState(
      status: NotificationPreferencesStatus.ready,
      items: <NotificationPreferenceItem>[
        for (final NotificationPreferenceItem item in state.items)
          item.eventType == eventType ? item.copyWith(enabled: enabled) : item,
      ],
      isSaving: true,
    );
    try {
      final List<NotificationPreferenceItem> items = await ref
          .read(notificationPreferencesRepositoryProvider)
          .updatePreference(eventType: eventType, enabled: enabled);
      state = NotificationPreferencesState(
        status: NotificationPreferencesStatus.ready,
        items: items,
      );
    } on OrchestratorApiException catch (error) {
      // Section 14.2/AC: restore the prior value and surface why.
      state = NotificationPreferencesState(
        status: NotificationPreferencesStatus.ready,
        items: previous,
        saveError: error,
      );
    }
  }

  /// Clears the save-failure notice (dismiss affordance).
  void dismissSaveError() {
    state = NotificationPreferencesState(
      status: state.status,
      items: state.items,
      error: state.error,
      isSaving: state.isSaving,
    );
  }
}

final NotifierProvider<NotificationPreferencesNotifier,
        NotificationPreferencesState> notificationPreferencesProvider =
    NotifierProvider<NotificationPreferencesNotifier,
        NotificationPreferencesState>(
  NotificationPreferencesNotifier.new,
);
