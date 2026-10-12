import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// The one storage key for the device-bound token (Section 12.2). The key
/// name is not a secret; the value always is.
const String deviceTokenStorageKey = 'device_token';

/// Minimal key/value surface the auth gate needs from platform secure storage
/// (iOS Keychain / Android Keystore-backed storage — parent plan Section 14.2,
/// ADR-006). Kept as an interface so tests inject an in-memory fake and the
/// gate logic stays platform-free.
abstract class SecureTokenStore {
  /// Persists [value] under [key]. The value is a secret: implementations
  /// must never log it or write it to plaintext storage (Section 12.4,
  /// Section 20.4 item 3).
  Future<void> write(String key, String value);

  /// Reads the value for [key], or null when absent.
  Future<String?> read(String key);

  /// Deletes the value for [key] (no error when absent).
  Future<void> delete(String key);
}

/// Production store backed by `flutter_secure_storage`: Keychain on iOS,
/// Keystore-backed encrypted storage on Android. This is the only place the
/// device token touches disk, and it is never plaintext
/// (docs/mobile/device-auth-release-contract.md).
class FlutterSecureTokenStore implements SecureTokenStore {
  FlutterSecureTokenStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  @override
  Future<void> write(String key, String value) =>
      _storage.write(key: key, value: value);

  @override
  Future<String?> read(String key) => _storage.read(key: key);

  @override
  Future<void> delete(String key) => _storage.delete(key: key);
}

/// Riverpod provider for the single secure store (Section 14.3: one provider
/// graph). Tests override this with an in-memory fake.
final Provider<SecureTokenStore> secureTokenStoreProvider =
    Provider<SecureTokenStore>(
  (Ref ref) => FlutterSecureTokenStore(),
);
