import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_flow.dart';

import '../security/security_test_support.dart';
import 'onboarding_test_support.dart';

/// Flow controller behavior (MT-5.5-06): step order, resumable state,
/// friendly non-leaky errors, and the device-token handoff straight into
/// the gate's secure storage — never into app state (Section 12.2/12.4).
void main() {
  ProviderContainer createContainer({
    required FakeOnboardingApi api,
    required InMemoryOnboardingProgressStore progress,
    InMemorySecureTokenStore? store,
    FakeBiometricAuthenticator? authenticator,
  }) {
    final ProviderContainer container = ProviderContainer(
      overrides: onboardingOverrides(
        api: api,
        progress: progress,
        secureStore: store,
        authenticator: authenticator,
      ),
    );
    addTearDown(container.dispose);
    return container;
  }

  Future<void> settle(ProviderContainer container) async {
    // First read constructs the notifier (scheduling the restore
    // microtask), then let that microtask run before asserting.
    container.read(onboardingFlowProvider);
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
  }

  group('server URL step', () {
    test('starts at the URL step with the config default pre-filled', () async {
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: InMemoryOnboardingProgressStore(),
      );
      await settle(container);

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.serverUrl);
      expect(state.serverUrl, '');
    });

    test('rejects malformed URLs locally without touching the API', () async {
      final FakeOnboardingApi api = FakeOnboardingApi();
      final ProviderContainer container = createContainer(
        api: api,
        progress: InMemoryOnboardingProgressStore(),
      );
      await settle(container);

      await container
          .read(onboardingFlowProvider.notifier)
          .confirmServerUrl('not a url');

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.serverUrl);
      expect(state.errorMessage, contains('full address'));
      expect(api.reachabilityCalls, 0);
    });

    test('unreachable server shows the friendly transport message', () async {
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(reachable: false),
        progress: InMemoryOnboardingProgressStore(),
      );
      await settle(container);

      await container
          .read(onboardingFlowProvider.notifier)
          .confirmServerUrl('http://10.0.2.2:8000/api/v1');

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.serverUrl);
      expect(state.errorMessage, contains('Could not reach the server'));
      expect(state.errorMessage, isNot(contains('connection refused')),
          reason: 'raw transport text must not reach the UI');
    });

    test('reachable URL is persisted and advances to login', () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore();
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: progress,
      );
      await settle(container);

      await container
          .read(onboardingFlowProvider.notifier)
          .confirmServerUrl('http://10.0.2.2:8000/api/v1');

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.login);
      expect(progress.serverUrl, 'http://10.0.2.2:8000/api/v1');
      expect(progress.step, OnboardingStep.login.index);
    });
  });

  group('login step', () {
    Future<ProviderContainer> containerAtLogin({
      required FakeOnboardingApi api,
      InMemoryOnboardingProgressStore? progress,
    }) async {
      final ProviderContainer container = createContainer(
        api: api,
        progress: progress ?? InMemoryOnboardingProgressStore(),
      );
      await settle(container);
      await container
          .read(onboardingFlowProvider.notifier)
          .confirmServerUrl('http://10.0.2.2:8000/api/v1');
      return container;
    }

    test('empty credentials are rejected locally', () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin();
      final ProviderContainer container = await containerAtLogin(api: api);

      await container
          .read(onboardingFlowProvider.notifier)
          .login(username: '  ', password: '');

      expect(container.read(onboardingFlowProvider).errorMessage,
          contains('username and password'));
      expect(api.loginCalls, 0);
    });

    test('AUTH_REQUIRED maps to friendly copy without echoing credentials',
        () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginError = authRequiredException();
      final ProviderContainer container = await containerAtLogin(api: api);

      await container.read(onboardingFlowProvider.notifier).login(
            username: 'owner',
            password: 'hunter2', // pragma: allowlist secret
          );

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.login);
      expect(state.errorMessage, 'Username or password is not correct.');
      expect(state.errorMessage, isNot(contains('hunter2')));
      expect(state.errorMessage,
          isNot(contains('Authentication credentials were not provided.')),
          reason: 'raw server message must not reach the UI (Section 12.4)');
    });

    test(
        'successful login advances to registration without the session '
        'token in state', () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin(username: 'alice');
      final ProviderContainer container = await containerAtLogin(api: api);

      await container.read(onboardingFlowProvider.notifier).login(
            username: 'alice',
            password: 'pw', // pragma: allowlist secret
          );

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.deviceRegistration);
      expect(state.signedInAs, 'alice');
      expect(state.toString(), isNot(contains('owner-session-token')),
          reason: 'session token must never enter state (Section 12.4)');
    });

    test('back from login returns to the URL step', () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin();
      final ProviderContainer container = await containerAtLogin(api: api);

      container.read(onboardingFlowProvider.notifier).backToServerUrl();

      expect(container.read(onboardingFlowProvider).step,
          OnboardingStep.serverUrl);
    });
  });

  group('device registration step', () {
    Future<ProviderContainer> containerAtRegistration({
      required FakeOnboardingApi api,
      InMemoryOnboardingProgressStore? progress,
      InMemorySecureTokenStore? store,
    }) async {
      final ProviderContainer container = createContainer(
        api: api,
        progress: progress ?? InMemoryOnboardingProgressStore(),
        store: store,
      );
      await settle(container);
      final OnboardingFlowNotifier flow =
          container.read(onboardingFlowProvider.notifier);
      await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
      await flow.login(
          username: 'owner', password: 'pw'); // pragma: allowlist secret
      return container;
    }

    test('device token goes straight to secure storage and never into state',
        () async {
      const String deviceToken = 'device-token-123'; // pragma: allowlist secret
      final InMemorySecureTokenStore store = InMemorySecureTokenStore();
      final FakeOnboardingApi api = FakeOnboardingApi(deviceToken: deviceToken)
        ..loginResult = ownerLogin();
      final ProviderContainer container = await containerAtRegistration(
        api: api,
        store: store,
      );

      await container.read(onboardingFlowProvider.notifier).registerDevice();

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.biometricEnrollment);
      expect(state.deviceRegistered, isTrue);
      expect(await store.read(deviceTokenStorageKey), deviceToken,
          reason: 'the response token must land in secure storage');
      expect(state.toString(), isNot(contains(deviceToken)),
          reason: 'the device token must never enter app state');
      // The gate landed locked (MT-5.5-04 storeToken contract).
      expect(container.read(authGateProvider).status, GateStatus.locked);
    });

    test(
        'registration reuses one idempotency key across retries of an '
        'attempt, and a new login starts a new key', () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin()
        ..registerError = OrchestratorApiException.unparsed(
          statusCode: 503,
          message: 'network blip',
          retryable: true,
        );
      final ProviderContainer container =
          await containerAtRegistration(api: api);
      final OnboardingFlowNotifier flow =
          container.read(onboardingFlowProvider.notifier);

      // First attempt fails (network) — the session survives for a retry.
      await flow.registerDevice();
      expect(container.read(onboardingFlowProvider).step,
          OnboardingStep.deviceRegistration);
      final String? firstKey = api.lastIdempotencyKey;
      expect(firstKey, isNotNull);

      // Retry of the same logical attempt reuses the key (NFR-12 dedupe).
      api.registerError = null;
      await flow.registerDevice();
      expect(api.lastIdempotencyKey, firstKey);
      expect(api.registerCalls, 2);

      // A fresh login starts a new logical attempt with a fresh key.
      flow.notifyCredentialRejected();
      await flow.login(
          username: 'owner', password: 'pw'); // pragma: allowlist secret
      await flow.registerDevice();
      expect(api.lastIdempotencyKey, isNot(firstKey));
    });

    test('failed registration keeps the user on the step with friendly copy',
        () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin()
        ..registerError = authRequiredException();
      final ProviderContainer container =
          await containerAtRegistration(api: api);

      await container.read(onboardingFlowProvider.notifier).registerDevice();

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.deviceRegistration);
      expect(state.deviceRegistered, isFalse);
      expect(state.errorMessage, isNotEmpty);
    });

    test('registering without a session returns to login honestly', () async {
      final FakeOnboardingApi api = FakeOnboardingApi()
        ..loginResult = ownerLogin();
      final ProviderContainer container =
          await containerAtRegistration(api: api);
      final OnboardingFlowNotifier flow =
          container.read(onboardingFlowProvider.notifier);

      // Simulate a restart that dropped the in-memory session.
      flow.notifyCredentialRejected();
      await flow.registerDevice();

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.login);
      expect(api.registerCalls, 0);
    });
  });

  group('biometric enrollment step', () {
    test('finish claims completion, persists it, and clears onboarding',
        () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore();
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi()..loginResult = ownerLogin(),
        progress: progress,
      );
      await settle(container);
      final OnboardingFlowNotifier flow =
          container.read(onboardingFlowProvider.notifier);
      await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
      await flow.login(
          username: 'owner', password: 'pw'); // pragma: allowlist secret

      expect(container.read(onboardingRequiredProvider), isFalse,
          reason: 'flag only appears via main() seeding or rejection');

      await flow.finish();

      expect(container.read(onboardingFlowProvider).completed, isTrue);
      expect(progress.completed, isTrue);
      expect(container.read(onboardingRequiredProvider), isFalse);
    });

    test('credential rejection re-enters onboarding at login', () async {
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi()..loginResult = ownerLogin(),
        progress: InMemoryOnboardingProgressStore(),
      );
      await settle(container);
      final OnboardingFlowNotifier flow =
          container.read(onboardingFlowProvider.notifier);
      await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
      await flow.login(
          username: 'owner', password: 'pw'); // pragma: allowlist secret
      await flow.registerDevice();

      container.read(onboardingRequiredProvider.notifier).state = true;
      flow.notifyCredentialRejected();

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.login);
      expect(state.completed, isFalse);
      expect(state.deviceRegistered, isFalse);
    });
  });

  group('resume (resumable flow)', () {
    test('URL step resumes at the URL step with the saved URL', () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore()
            ..step = OnboardingStep.serverUrl.index
            ..serverUrl = 'http://saved:9000/api/v1';
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: progress,
      );
      await settle(container);

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.serverUrl);
      expect(state.serverUrl, 'http://saved:9000/api/v1');
    });

    test('registration step resumes at login (session was in memory)',
        () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore()
            ..step = OnboardingStep.deviceRegistration.index
            ..serverUrl = 'http://saved:9000/api/v1';
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: progress,
      );
      await settle(container);

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.login);
      expect(state.serverUrl, 'http://saved:9000/api/v1');
    });

    test('enrollment step resumes there — the device token is already stored',
        () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore()
            ..step = OnboardingStep.biometricEnrollment.index
            ..serverUrl = 'http://saved:9000/api/v1';
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: progress,
      );
      await settle(container);

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.step, OnboardingStep.biometricEnrollment);
      expect(state.deviceRegistered, isTrue);
    });

    test(
        'completed onboarding resumes at login only if the credential is '
        'gone (re-entry)', () async {
      final InMemoryOnboardingProgressStore progress =
          InMemoryOnboardingProgressStore()
            ..step = OnboardingStep.biometricEnrollment.index
            ..serverUrl = 'http://saved:9000/api/v1'
            ..completed = true;
      final ProviderContainer container = createContainer(
        api: FakeOnboardingApi(),
        progress: progress,
      );
      await settle(container);

      final OnboardingState state = container.read(onboardingFlowProvider);
      expect(state.completed, isTrue);
      expect(state.step, OnboardingStep.login);
    });
  });
}
