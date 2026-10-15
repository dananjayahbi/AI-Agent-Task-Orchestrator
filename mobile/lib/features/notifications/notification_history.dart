import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'push_payload.dart';

/// Local alert receipts — the history half of the Notifications area
/// (Section 14.1 "History of alerts"; MT-5.9-02 records, MT-5.9-03 renders).
///
/// **Storage reading (recorded for the WP changelog, per MT-5.9-03's risk
/// note):** the plan never says where "history of alerts" lives; a
/// server-side notification inbox does not exist in Section 9.2, so the
/// consistent reading is *locally recorded receipts* of what the app
/// presented (the in-app banner — MT-5.9-02 — and a system-notification
/// tap). Offline the list still reads (Section 14.2's read-only cache
/// posture); nothing is ever queued or re-sent from here.

/// Where a receipt was recorded — the two presentation channels.
enum NotificationOrigin {
  /// The in-app banner (MT-5.9-02, foreground path).
  banner,

  /// The OS notification was tapped (cold/warm start path, MT-5.9-01).
  systemNotification,
}

/// One recorded alert: the MT-5.4-02 payload it showed, its origin and when.
class NotificationReceipt {
  const NotificationReceipt({
    required this.payload,
    required this.origin,
    required this.recordedAt,
  });

  final PushTapPayload payload;
  final NotificationOrigin origin;
  final DateTime recordedAt;

  /// The MT-5.4-03 tuple — at most one receipt per alert (banner and tap
  /// for the same event collapse onto this key).
  String get dedupeKey => payload.dedupeKey;

  Map<String, Object?> toJson() => <String, Object?>{
        'event_type': payload.eventType,
        'project_id': payload.projectId,
        'task_id': payload.taskId,
        'task_version': payload.taskVersion,
        'title': payload.title,
        'origin': origin.name,
        'recorded_at': recordedAt.toIso8601String(),
      };

  /// Rebuilds one row; a row that no longer matches the payload contract
  /// throws (the JSON is ours — [FormatException] lets the store report an
  /// unreadable cache honestly rather than render half a receipt).
  factory NotificationReceipt.fromJson(Map<String, Object?> json) {
    final PushTapPayload? payload = PushTapPayload.tryParse(<String, String>{
      'event_type': json['event_type'] as String,
      'project_id': json['project_id'] as String,
      'task_id': json['task_id'] as String,
      'task_version': (json['task_version'] as Object).toString(),
      'title': json['title'] as String,
    });
    if (payload == null) {
      throw const FormatException(
          'Stored receipt does not match the payload contract.');
    }
    return NotificationReceipt(
      payload: payload,
      origin: NotificationOrigin.values.byName(json['origin'] as String),
      recordedAt: DateTime.parse(json['recorded_at'] as String),
    );
  }
}

/// Persistence seam for the receipts (app-wiring pattern: `main()` supplies
/// the SharedPreferences store, tests supply an in-memory one).
abstract class NotificationHistoryStore {
  /// Stored receipts, **newest first** (the screen's declared order).
  Future<List<NotificationReceipt>> load();

  Future<void> save(List<NotificationReceipt> receipts);
}

/// SharedPreferences-backed store (documented choice: plain local cache,
/// never secrets — Section 12.4's secure-storage rule covers credentials).
class SharedPreferencesNotificationHistoryStore
    implements NotificationHistoryStore {
  SharedPreferencesNotificationHistoryStore(this._prefs);

  final SharedPreferences _prefs;

  static const String storageKey = 'orchestrator.notification.history.v1';

  /// Bounded local history (MT-5.9-03 renders this; cap recorded in the
  /// WP changelog) — oldest rows fall off the end first.
  static const int maxReceipts = 200;

  static Future<SharedPreferencesNotificationHistoryStore> open() async =>
      SharedPreferencesNotificationHistoryStore(
        await SharedPreferences.getInstance(),
      );

  @override
  Future<List<NotificationReceipt>> load() async {
    final String? raw = _prefs.getString(storageKey);
    if (raw == null || raw.isEmpty) {
      return const <NotificationReceipt>[];
    }
    try {
      final Object? decoded = jsonDecode(raw);
      if (decoded is! List<Object?>) {
        throw const FormatException('history payload is not a list');
      }
      return decoded
          .map(
            (Object? row) =>
                NotificationReceipt.fromJson((row as Map<String, Object?>)),
          )
          .toList(growable: false);
    } on FormatException {
      // A corrupted local cache is discarded, never rendered and never a
      // dead-end error state (it is a cache — Section 14.2): the next save
      // overwrites it with fresh, valid rows.
      return const <NotificationReceipt>[];
    }
  }

  @override
  Future<void> save(List<NotificationReceipt> receipts) async {
    await _prefs.setString(
      storageKey,
      jsonEncode(
          <Object?>[for (final NotificationReceipt r in receipts) r.toJson()]),
    );
  }
}

/// App-wiring seam: `main()` opens the SharedPreferences store and
/// overrides this; tests override with an in-memory store.
final Provider<NotificationHistoryStore> notificationHistoryStoreProvider =
    Provider<NotificationHistoryStore>(
  (Ref ref) => throw UnimplementedError(
    'Override notificationHistoryStoreProvider with a concrete store '
    '(SharedPreferencesNotificationHistoryStore in app wiring).',
  ),
);

/// Section 20.3 states for the history list.
enum NotificationHistoryStatus { loading, ready, error }

class NotificationHistoryState {
  const NotificationHistoryState.loading()
      : status = NotificationHistoryStatus.loading,
        receipts = const <NotificationReceipt>[],
        error = null;

  const NotificationHistoryState.ready(this.receipts)
      : status = NotificationHistoryStatus.ready,
        error = null;

  const NotificationHistoryState.error(Object this.error)
      : status = NotificationHistoryStatus.error,
        receipts = const <NotificationReceipt>[];

  final NotificationHistoryStatus status;

  /// Newest first (the Section 14.1 reverse-chronological presentation).
  final List<NotificationReceipt> receipts;

  /// The store failure behind [NotificationHistoryStatus.error].
  final Object? error;

  bool get isEmpty =>
      status == NotificationHistoryStatus.ready && receipts.isEmpty;
}

/// Holds the receipts: lazy load on first read (the screen's opening),
/// append-only recording from the MT-5.9-02 paths.
class NotificationHistoryNotifier extends Notifier<NotificationHistoryState> {
  @override
  NotificationHistoryState build() => const NotificationHistoryState.loading();

  bool _loaded = false;

  /// Loads once (the screen's opening path); failures surface as the honest
  /// error state with a retry ([ensureLoaded] may run again).
  Future<void> ensureLoaded() async {
    if (_loaded) {
      return;
    }
    state = const NotificationHistoryState.loading();
    try {
      final List<NotificationReceipt> rows =
          await ref.read(notificationHistoryStoreProvider).load();
      _loaded = true;
      state = NotificationHistoryState.ready(rows);
    } catch (error) {
      state = NotificationHistoryState.error(error);
    }
  }

  /// Records one presented alert (MT-5.9-02) — newest first, deduped on the
  /// MT-5.4-03 tuple, capped at [SharedPreferencesNotificationHistoryStore.maxReceipts].
  ///
  /// Recording never fails the presenting path: an unreadable cache is
  /// discarded (see the store) and a failed write keeps the in-memory copy
  /// for this session — the receipt must not break banner/tap handling.
  Future<void> record(
    PushTapPayload payload, {
    required NotificationOrigin origin,
  }) async {
    if (!_loaded) {
      try {
        final List<NotificationReceipt> rows =
            await ref.read(notificationHistoryStoreProvider).load();
        _loaded = true;
        state = NotificationHistoryState.ready(rows);
      } catch (_) {
        _loaded = true;
        state = const NotificationHistoryState.ready(<NotificationReceipt>[]);
      }
    }
    if (state.receipts
        .any((NotificationReceipt r) => r.dedupeKey == payload.dedupeKey)) {
      return; // One receipt per alert — banner and tap collapse.
    }
    final NotificationReceipt receipt = NotificationReceipt(
      payload: payload,
      origin: origin,
      recordedAt: DateTime.now(),
    );
    final List<NotificationReceipt> next = <NotificationReceipt>[
      receipt,
      ...state.receipts,
    ];
    state = NotificationHistoryState.ready(
      next.length > SharedPreferencesNotificationHistoryStore.maxReceipts
          ? next.sublist(
              0,
              SharedPreferencesNotificationHistoryStore.maxReceipts,
            )
          : next,
    );
    try {
      await ref.read(notificationHistoryStoreProvider).save(state.receipts);
    } catch (_) {
      // Best-effort write — the in-memory list stands for this session.
    }
  }
}

final NotifierProvider<NotificationHistoryNotifier, NotificationHistoryState>
    notificationHistoryProvider =
    NotifierProvider<NotificationHistoryNotifier, NotificationHistoryState>(
  NotificationHistoryNotifier.new,
);
