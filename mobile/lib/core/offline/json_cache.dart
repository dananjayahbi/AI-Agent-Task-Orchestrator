import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Tiny read/write JSON-string cache seam for the Section 14.2 read-only
/// offline rule ("cache of the last overview and board").
///
/// Feature layers (dashboard, board) serialize their own payloads and use
/// this only as a keyed string store — no cache semantics live here. Values
/// are never secrets (Section 12.4's secure-storage rule covers credentials
/// only); the device token never goes near this store.
abstract class JsonCache {
  Future<String?> read(String key);

  Future<void> write(String key, String value);

  Future<void> remove(String key);
}

/// SharedPreferences-backed [JsonCache] for the app wiring.
class SharedPreferencesJsonCache implements JsonCache {
  SharedPreferencesJsonCache(this._prefs);

  final SharedPreferences _prefs;

  /// Async constructor — preferences need an async singleton load.
  static Future<SharedPreferencesJsonCache> open() async =>
      SharedPreferencesJsonCache(await SharedPreferences.getInstance());

  @override
  Future<String?> read(String key) async => _prefs.getString(key);

  @override
  Future<void> write(String key, String value) async =>
      _prefs.setString(key, value);

  @override
  Future<void> remove(String key) async => _prefs.remove(key);
}

/// Riverpod provider; tests override with an in-memory store.
final Provider<JsonCache> jsonCacheProvider = Provider<JsonCache>(
  (Ref ref) => throw UnimplementedError(
    'Override jsonCacheProvider with a concrete cache '
    '(SharedPreferencesJsonCache in app wiring).',
  ),
);
