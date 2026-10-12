import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/api/auth_token_interceptor.dart';
import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';

import 'security_test_support.dart';

const String secretToken = testDeviceToken;

Future<AuthGateNotifier> openGate(ProviderContainer container) async {
  final AuthGateNotifier gate = container.read(authGateProvider.notifier);
  await gate.initialized;
  return gate;
}

void main() {
  group('cold start (Section 14.2)', () {
    test('stored credential means the app starts LOCKED, token not released',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final FakeBiometricAuthenticator authenticator =
          FakeBiometricAuthenticator();
      final ProviderContainer container = createSecurityTestContainer(
          store: store, authenticator: authenticator);

      final AuthGateNotifier gate = await openGate(container);

      expect(gate.state.status, GateStatus.locked);
      expect(container.read(authGateProvider).status, GateStatus.locked);
      // No biometric success yet — nothing may be released.
      expect(gate.releaseToken(), isNull);
      expect(authenticator.authenticateCalls, 0);
    });

    test('no stored credential lands in noCredential (onboarding territory)',
        () async {
      final ProviderContainer container = createSecurityTestContainer(
        store: InMemorySecureTokenStore(),
        authenticator: FakeBiometricAuthenticator(),
      );

      final AuthGateNotifier gate = await openGate(container);

      expect(gate.state.status, GateStatus.noCredential);
      expect(gate.releaseToken(), isNull);
      expect(await gate.unlock(), isFalse);
    });

    test('unreadable storage is an honest storageError, never a bypass',
        () async {
      final ProviderContainer container = createSecurityTestContainer(
        store: ThrowingSecureTokenStore(),
        authenticator: FakeBiometricAuthenticator(),
      );

      final AuthGateNotifier gate = await openGate(container);

      expect(gate.state.status, GateStatus.storageError);
      expect(gate.releaseToken(), isNull);
    });
  });

  group('unlock releases the token (Section 12.2)', () {
    test('successful biometric unlocks and releases; lock stops releasing',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final FakeBiometricAuthenticator authenticator =
          FakeBiometricAuthenticator();
      final ProviderContainer container = createSecurityTestContainer(
          store: store, authenticator: authenticator);

      final AuthGateNotifier gate = await openGate(container);

      expect(await gate.unlock(), isTrue);
      expect(container.read(authGateProvider).status, GateStatus.unlocked);
      expect(gate.releaseToken(), secretToken);

      gate.lock();
      expect(container.read(authGateProvider).status, GateStatus.locked);
      expect(gate.releaseToken(), isNull);
    });

    test('failed biometric stays locked and flags the failure honestly',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final FakeBiometricAuthenticator authenticator =
          FakeBiometricAuthenticator(authenticateResult: false);
      final ProviderContainer container = createSecurityTestContainer(
          store: store, authenticator: authenticator);

      final AuthGateNotifier gate = await openGate(container);

      expect(await gate.unlock(), isFalse);
      expect(container.read(authGateProvider).status, GateStatus.locked);
      expect(container.read(authGateProvider).lastUnlockFailed, isTrue);
      expect(gate.releaseToken(), isNull);
    });

    test('the token exists in the store seam only — never in gate state',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
      );

      final AuthGateNotifier gate = await openGate(container);
      await gate.unlock();

      // Exactly one prior write (the store call) — the gate itself never
      // writes the token anywhere else (MT-5.5-04 acceptance item 1).
      expect(store.writeCount, 1);
      // State carries no token material at all.
      expect(container.read(authGateProvider).toString(),
          isNot(contains(secretToken)));
    });
  });

  group('inactivity timeout re-locks (Section 14.2)', () {
    test('unlock then silence re-locks and stops releasing the token',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
        lockTimeout: const Duration(milliseconds: 40),
      );

      final AuthGateNotifier gate = await openGate(container);
      expect(await gate.unlock(), isTrue);
      expect(gate.releaseToken(), secretToken);

      await Future<void>.delayed(const Duration(milliseconds: 120));

      expect(container.read(authGateProvider).status, GateStatus.locked);
      expect(gate.releaseToken(), isNull);
    });

    test('user activity extends the unlocked window', () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
        lockTimeout: const Duration(milliseconds: 80),
      );

      final AuthGateNotifier gate = await openGate(container);
      await gate.unlock();

      // Keep tapping before the timeout expires.
      for (int i = 0; i < 3; i += 1) {
        await Future<void>.delayed(const Duration(milliseconds: 40));
        gate.noteActivity();
      }

      expect(container.read(authGateProvider).status, GateStatus.unlocked);
      expect(gate.releaseToken(), secretToken);
    });
  });

  group('honest no-biometrics handling (Section 14.2)', () {
    test('enrollmentRequired surfaces in state so the UI can guide, not skip',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final FakeBiometricAuthenticator authenticator =
          FakeBiometricAuthenticator(
        availabilityResult: BiometricAvailability.enrollmentRequired,
        authenticateResult: false, // user cannot pass the prompt yet
      );
      final ProviderContainer container = createSecurityTestContainer(
          store: store, authenticator: authenticator);

      final AuthGateNotifier gate = await openGate(container);

      expect(gate.state.availability, BiometricAvailability.enrollmentRequired);
      // The prompt is still attempted (OS passcode fallback may apply) but a
      // failure never unlocks.
      expect(await gate.unlock(), isFalse);
      expect(gate.releaseToken(), isNull);
    });

    test('unsupported devices never unlock — documented limitation, no bypass',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final FakeBiometricAuthenticator authenticator =
          FakeBiometricAuthenticator(
        availabilityResult: BiometricAvailability.unsupported,
      );
      final ProviderContainer container = createSecurityTestContainer(
          store: store, authenticator: authenticator);

      final AuthGateNotifier gate = await openGate(container);

      expect(gate.state.availability, BiometricAvailability.unsupported);
      expect(await gate.unlock(), isFalse);
      expect(authenticator.authenticateCalls, 0);
      expect(gate.releaseToken(), isNull);
    });
  });

  group('device registration handoff (MT-5.5-06 seam)', () {
    test('storeToken persists via the store and stays locked until unlock',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
      );

      final AuthGateNotifier gate = await openGate(container);
      expect(container.read(authGateProvider).status, GateStatus.noCredential);

      await gate.storeToken(secretToken);

      expect(store.writeCount, 1);
      expect(await store.read(deviceTokenStorageKey), secretToken);
      expect(container.read(authGateProvider).status, GateStatus.locked);
      expect(gate.releaseToken(), isNull);
      expect(await gate.unlock(), isTrue);
      expect(gate.releaseToken(), secretToken);
    });

    test('discardCredential deletes the stored token (revocation recovery)',
        () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
      );

      final AuthGateNotifier gate = await openGate(container);
      await gate.storeToken(secretToken);
      await gate.unlock();
      expect(gate.releaseToken(), secretToken);

      await gate.discardCredential();

      expect(await store.read(deviceTokenStorageKey), isNull);
      expect(container.read(authGateProvider).status, GateStatus.noCredential);
      expect(gate.releaseToken(), isNull);
    });
  });

  group('interceptor wiring (release only through the gate)', () {
    test('no header while locked; bearer header only after unlock', () async {
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      await store.write(deviceTokenStorageKey, secretToken);
      final ProviderContainer container = createSecurityTestContainer(
        store: store,
        authenticator: FakeBiometricAuthenticator(),
      );
      final AuthGateNotifier gate = await openGate(container);

      final AuthTokenInterceptor interceptor = AuthTokenInterceptor(
        releaseToken: gate.releaseToken,
        discardCredential: gate.discardCredential,
      );

      RequestOptions lockedOptions = RequestOptions(path: '/api/v1/projects');
      interceptor.onRequest(
        lockedOptions,
        RequestInterceptorHandler(),
      );
      expect(lockedOptions.headers.containsKey('Authorization'), isFalse);

      await gate.unlock();
      RequestOptions unlockedOptions = RequestOptions(path: '/api/v1/projects');
      interceptor.onRequest(
        unlockedOptions,
        RequestInterceptorHandler(),
      );
      expect(unlockedOptions.headers['Authorization'], 'Bearer $secretToken');
      expect(
        unlockedOptions.extra[deviceTokenInjectedExtra],
        isTrue,
      );
    });
  });
}
