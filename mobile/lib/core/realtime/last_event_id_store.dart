import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Persistence for the last *processed* event id (MT-5.5-05).
///
/// "Processed" is defined precisely: the event was parsed, de-duplicated
/// and emitted to the client's event stream — persisted AFTER emission, so
/// a crash can at worst replay the tail event on next start (at-least-once
/// with id de-dup on the consuming side), never skip it (the MT risk note:
/// an id persisted before its event was handled creates gaps).
///
/// The id is **not a secret** (Section 9.6 wire value) — plain preferences
/// are appropriate; the device token never goes anywhere near this store.
abstract class LastEventIdStore {
  Future<int?> read();
  Future<void> write(int id);
}

/// SharedPreferences-backed store (documented choice: non-secret resume
/// marker; Section 12.4's secure-storage rule covers credentials only).
class SharedPreferencesLastEventIdStore implements LastEventIdStore {
  SharedPreferencesLastEventIdStore(this._prefs);

  static const String storageKey = 'sse_last_event_id';

  final SharedPreferences _prefs;

  /// Async constructor — preferences need an async singleton load.
  static Future<SharedPreferencesLastEventIdStore> open() async =>
      SharedPreferencesLastEventIdStore(await SharedPreferences.getInstance());

  @override
  Future<int?> read() async => _prefs.getInt(storageKey);

  @override
  Future<void> write(int id) async => _prefs.setInt(storageKey, id);
}

/// Riverpod provider; tests override with an in-memory store.
final Provider<LastEventIdStore> lastEventIdStoreProvider =
    Provider<LastEventIdStore>(
  (Ref ref) => throw UnimplementedError(
    'Override lastEventIdStoreProvider with a concrete store '
    '(SharedPreferencesLastEventIdStore in app wiring).',
  ),
);
