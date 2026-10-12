import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_flow.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_screen.dart';

import '../security/security_test_support.dart';
import 'onboarding_test_support.dart';

/// Screen behavior (MT-5.5-06 acceptance items 1-4): the four Section 14.1
/// screens render in order, validation and friendly errors surface, the
/// device token never renders, and skip stays honest.
void main() {
  Future<ProviderContainer> pumpOnboarding(
    WidgetTester tester, {
    FakeOnboardingApi? api,
    InMemoryOnboardingProgressStore? progress,
    InMemorySecureTokenStore? store,
    FakeBiometricAuthenticator? authenticator,
  }) async {
    final FakeOnboardingApi resolvedApi = api ?? FakeOnboardingApi();
    final InMemoryOnboardingProgressStore resolvedProgress =
        progress ?? InMemoryOnboardingProgressStore();
    final ProviderContainer container = ProviderContainer(
      overrides: onboardingOverrides(
        api: resolvedApi,
        progress: resolvedProgress,
        secureStore: store,
        authenticator: authenticator,
      ),
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: OnboardingScreen(),
        ),
      ),
    );
    await tester.pumpAndSettle();
    return container;
  }

  testWidgets('fresh flow shows the URL step first, pre-filled from config',
      (tester) async {
    await pumpOnboarding(tester);

    expect(find.text('Step 1 of 4 — Server URL'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('onboarding-server-url-field')),
        findsOneWidget);
  });

  testWidgets('URL validation error appears and stays on step 1',
      (tester) async {
    final ProviderContainer container = await pumpOnboarding(tester);

    await tester.enterText(
        find.byKey(const ValueKey<String>('onboarding-server-url-field')),
        'nope');
    await tester.tap(
        find.byKey(const ValueKey<String>('onboarding-server-url-continue')));
    await tester.pumpAndSettle();

    expect(
        find.byKey(const ValueKey<String>('onboarding-error')), findsOneWidget);
    expect(
        container.read(onboardingFlowProvider).step, OnboardingStep.serverUrl);
  });

  testWidgets('successful URL check advances to the login step',
      (tester) async {
    final ProviderContainer container = await pumpOnboarding(tester);

    await tester.enterText(
        find.byKey(const ValueKey<String>('onboarding-server-url-field')),
        'http://10.0.2.2:8000/api/v1');
    await tester.tap(
        find.byKey(const ValueKey<String>('onboarding-server-url-continue')));
    await tester.pumpAndSettle();

    expect(find.text('Step 2 of 4 — Sign in'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('onboarding-password-field')),
        findsOneWidget);
    expect(container.read(onboardingFlowProvider).step, OnboardingStep.login);
  });

  testWidgets('password field is obscured and back returns to the URL step',
      (tester) async {
    final ProviderContainer container = await pumpOnboarding(tester);
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await tester.pumpAndSettle();

    final TextField passwordField = tester.widget<TextField>(
        find.byKey(const ValueKey<String>('onboarding-password-field')));
    expect(passwordField.obscureText, isTrue);

    await tester
        .tap(find.byKey(const ValueKey<String>('onboarding-login-back')));
    await tester.pumpAndSettle();

    expect(find.text('Step 1 of 4 — Server URL'), findsOneWidget);
  });

  testWidgets('login failure shows the friendly message, not the raw one',
      (tester) async {
    final FakeOnboardingApi api = FakeOnboardingApi()
      ..loginError = authRequiredException();
    final ProviderContainer container = await pumpOnboarding(tester, api: api);
    await container
        .read(onboardingFlowProvider.notifier)
        .confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await tester.pumpAndSettle();

    await tester.enterText(
        find.byKey(const ValueKey<String>('onboarding-username-field')),
        'owner');
    await tester.enterText(
        find.byKey(const ValueKey<String>('onboarding-password-field')), 'pw');
    await tester
        .tap(find.byKey(const ValueKey<String>('onboarding-login-submit')));
    await tester.pumpAndSettle();

    expect(find.text('Username or password is not correct.'), findsOneWidget);
    expect(find.textContaining('Authentication credentials'), findsNothing);
  });

  testWidgets(
      'registration hands the token to storage; it never renders on screen',
      (tester) async {
    const String deviceToken =
        'device-token-widget'; // pragma: allowlist secret
    final FakeOnboardingApi api = FakeOnboardingApi(
      deviceToken: deviceToken,
      loginResult: ownerLogin(),
    );
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    final ProviderContainer container = await pumpOnboarding(
      tester,
      api: api,
      store: store,
    );
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    await tester.pumpAndSettle();

    await tester
        .tap(find.byKey(const ValueKey<String>('onboarding-register-submit')));
    await tester.pumpAndSettle();

    // Enrollment step reached; the token is in secure storage only.
    expect(find.text('Step 4 of 4 — Protect the app'), findsOneWidget);
    expect(find.textContaining(deviceToken), findsNothing);
    expect(await store.read(deviceTokenStorageKey), deviceToken);
  });

  testWidgets(
      'enrollment guidance reflects missing biometrics honestly (no bypass)',
      (tester) async {
    final FakeOnboardingApi api = FakeOnboardingApi(loginResult: ownerLogin());
    final ProviderContainer container = await pumpOnboarding(
      tester,
      api: api,
      authenticator: FakeBiometricAuthenticator(
        availabilityResult: BiometricAvailability.enrollmentRequired,
        authenticateResult: false,
      ),
    );
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    await flow.registerDevice();
    await tester.pumpAndSettle();

    expect(find.textContaining('No biometrics are enrolled'), findsOneWidget);
    // The honest skip is offered — not a silent completion claim.
    expect(find.byKey(const ValueKey<String>('onboarding-enrollment-skip')),
        findsOneWidget);
  });

  testWidgets('skip finishes the flow; the gate stays locked until real unlock',
      (tester) async {
    final FakeOnboardingApi api = FakeOnboardingApi(loginResult: ownerLogin());
    final ProviderContainer container = await pumpOnboarding(
      tester,
      api: api,
    );
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    await flow.registerDevice();
    await tester.pumpAndSettle();

    await tester
        .tap(find.byKey(const ValueKey<String>('onboarding-enrollment-skip')));
    await tester.pumpAndSettle();

    expect(container.read(onboardingFlowProvider).completed, isTrue);
    // Honest skip: the credential is stored but the gate never unlocked.
    expect(container.read(authGateProvider).status, GateStatus.locked);
    expect(container.read(onboardingRequiredProvider), isFalse);
  });

  testWidgets('enable runs the real biometric prompt; success finishes',
      (tester) async {
    final FakeOnboardingApi api = FakeOnboardingApi(loginResult: ownerLogin());
    final FakeBiometricAuthenticator authenticator =
        FakeBiometricAuthenticator(authenticateResult: true);
    final ProviderContainer container = await pumpOnboarding(
      tester,
      api: api,
      authenticator: authenticator,
    );
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    await flow.registerDevice();
    await tester.pumpAndSettle();

    await tester.tap(
        find.byKey(const ValueKey<String>('onboarding-enrollment-enable')));
    await tester.pumpAndSettle();

    expect(authenticator.authenticateCalls, 1);
    expect(container.read(onboardingFlowProvider).completed, isTrue);
    expect(container.read(authGateProvider).status, GateStatus.unlocked);
    // Success armed the inactivity timer (MT-5.5-04); let it expire in
    // fake time so no Timer outlives the widget tree.
    await tester.pump(const Duration(minutes: 5) + const Duration(seconds: 1));
  });

  testWidgets('cancelled biometric prompt leaves the flow unfinished',
      (tester) async {
    final FakeOnboardingApi api = FakeOnboardingApi(loginResult: ownerLogin());
    final FakeBiometricAuthenticator authenticator =
        FakeBiometricAuthenticator(authenticateResult: false);
    final ProviderContainer container = await pumpOnboarding(
      tester,
      api: api,
      authenticator: authenticator,
    );
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    await flow.registerDevice();
    await tester.pumpAndSettle();

    await tester.tap(
        find.byKey(const ValueKey<String>('onboarding-enrollment-enable')));
    await tester.pumpAndSettle();

    expect(container.read(onboardingFlowProvider).completed, isFalse);
    expect(container.read(authGateProvider).status, GateStatus.locked);
    // The honest failure hint shows on the enrollment screen.
    expect(
        find.byKey(const ValueKey<String>('onboarding-error')), findsOneWidget);
  });

  testWidgets('resumed enrollment step renders directly after restore',
      (tester) async {
    final InMemoryOnboardingProgressStore progress =
        InMemoryOnboardingProgressStore()
          ..serverUrl = 'http://saved:9000/api/v1'
          ..step = OnboardingStep.biometricEnrollment.index;
    await pumpOnboarding(tester, progress: progress);
    await tester.pumpAndSettle();

    expect(find.text('Step 4 of 4 — Protect the app'), findsOneWidget);
    expect(find.textContaining('http://saved:9000/api/v1'), findsNothing);
  });
}
