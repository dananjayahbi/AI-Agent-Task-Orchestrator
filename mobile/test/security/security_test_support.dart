import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';

/// Sample secret used only by in-memory test doubles — never logged, never
/// committed to production storage (Section 20.4 item 3).
const String testDeviceToken =
    'device-secret-token-value'; // pragma: allowlist secret

/// In-memory secure store: models the store seam for tests and lets them
/// observe that writes happen ONLY through [SecureTokenStore].
class InMemorySecureTokenStore implements SecureTokenStore {
  final Map<String, String> _values = <String, String>{};
  int writeCount = 0;

  @override
  Future<void> write(String key, String value) async {
    writeCount += 1;
    _values[key] = value;
  }

  @override
  Future<String?> read(String key) async => _values[key];

  @override
  Future<void> delete(String key) async {
    _values.remove(key);
  }
}

/// Store that always fails — models a broken/unavailable Keychain.
class ThrowingSecureTokenStore implements SecureTokenStore {
  @override
  Future<void> write(String key, String value) =>
      throw StateError('secure storage unavailable');

  @override
  Future<String?> read(String key) =>
      throw StateError('secure storage unavailable');

  @override
  Future<void> delete(String key) =>
      throw StateError('secure storage unavailable');
}

/// Scriptable biometric authenticator: no platform channels involved.
class FakeBiometricAuthenticator implements BiometricAuthenticator {
  FakeBiometricAuthenticator({
    this.availabilityResult = BiometricAvailability.available,
    this.authenticateResult = true,
  });

  BiometricAvailability availabilityResult;
  bool authenticateResult;
  int authenticateCalls = 0;

  @override
  Future<BiometricAvailability> availability() async => availabilityResult;

  @override
  Future<bool> authenticate({required String reason}) async {
    authenticateCalls += 1;
    return authenticateResult;
  }
}

/// Container with the security seams overridden by fakes.
ProviderContainer createSecurityTestContainer({
  required SecureTokenStore store,
  required FakeBiometricAuthenticator authenticator,
  Duration lockTimeout = const Duration(minutes: 5),
}) {
  final ProviderContainer container = ProviderContainer(
    overrides: <Override>[
      secureTokenStoreProvider.overrideWithValue(store),
      biometricAuthProvider.overrideWithValue(authenticator),
      lockTimeoutProvider.overrideWithValue(lockTimeout),
    ],
  );
  addTearDown(container.dispose);
  return container;
}
