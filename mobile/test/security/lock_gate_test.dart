import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/lock_gate.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';

import 'security_test_support.dart';

/// Lock state blocks the app shell (MT-5.5-04 acceptance item 4): while the
/// gate is locked, no authenticated content is rendered underneath — the
/// lock view with honest per-state messaging takes its place.
void main() {
  const Widget shellProbe =
      Text('SECRET SHELL DATA', textDirection: TextDirection.ltr);

  Future<void> pumpGateWithOverrides(
    WidgetTester tester, {
    required SecureTokenStore store,
    required BiometricAuthenticator authenticator,
    required List<Override> extra,
  }) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureTokenStoreProvider.overrideWithValue(store),
          biometricAuthProvider.overrideWithValue(authenticator),
          ...extra,
        ],
        child: const MaterialApp(
          home: LockGate(child: shellProbe),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  Future<void> pumpGate(
    WidgetTester tester, {
    required SecureTokenStore store,
    required BiometricAuthenticator authenticator,
  }) async {
    await pumpGateWithOverrides(
      tester,
      store: store,
      authenticator: authenticator,
      extra: const <Override>[],
    );
  }

  testWidgets(
      'cold start with a stored token shows the lock view, not the shell',
      (tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await pumpGate(
      tester,
      store: store,
      authenticator: FakeBiometricAuthenticator(),
    );

    expect(find.text('Orchestrator is locked'), findsOneWidget);
    expect(find.text('SECRET SHELL DATA'), findsNothing);
    expect(find.text('Unlock'), findsOneWidget);
  });

  testWidgets(
      'no stored credential passes the shell through when no onboarding '
      'is pending', (tester) async {
    await pumpGate(
      tester,
      store: InMemorySecureTokenStore(),
      authenticator: FakeBiometricAuthenticator(),
    );

    expect(find.text('SECRET SHELL DATA'), findsOneWidget);
    expect(find.text('Orchestrator is locked'), findsNothing);
  });

  testWidgets(
      'pending onboarding replaces the no-credential shell with the '
      'onboarding flow (MT-5.5-06)', (tester) async {
    await pumpGateWithOverrides(
      tester,
      store: InMemorySecureTokenStore(),
      authenticator: FakeBiometricAuthenticator(),
      extra: <Override>[
        onboardingRequiredProvider.overrideWith((ref) => true),
      ],
    );

    expect(find.text('SECRET SHELL DATA'), findsNothing);
    expect(find.text('Onboarding'), findsOneWidget);
    expect(find.byKey(const ValueKey<String>('onboarding-server-url-field')),
        findsOneWidget);
  });

  testWidgets(
      'pending onboarding under a locked gate shows the enrollment step, '
      'not the lock view', (tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await pumpGateWithOverrides(
      tester,
      store: store,
      authenticator: FakeBiometricAuthenticator(),
      extra: <Override>[
        onboardingRequiredProvider.overrideWith((ref) => true),
      ],
    );

    expect(find.text('Orchestrator is locked'), findsNothing);
    // The flow restores to its last persisted step; with none persisted
    // it starts at the URL step — onboarding owns the screen either way.
    expect(find.text('Onboarding'), findsOneWidget);
    expect(find.text('SECRET SHELL DATA'), findsNothing);
  });

  testWidgets('enrollment guidance is shown honestly instead of a bypass',
      (tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await pumpGate(
      tester,
      store: store,
      authenticator: FakeBiometricAuthenticator(
        availabilityResult: BiometricAvailability.enrollmentRequired,
        authenticateResult: false,
      ),
    );

    expect(
      find.textContaining('No biometrics are enrolled'),
      findsOneWidget,
    );
    // The unlock affordance remains (OS passcode fallback may apply), but
    // the shell stays hidden.
    expect(find.text('SECRET SHELL DATA'), findsNothing);
  });

  testWidgets('tapping Unlock runs the gate; success reveals the shell',
      (tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await pumpGate(
      tester,
      store: store,
      authenticator: FakeBiometricAuthenticator(),
    );

    await tester.tap(find.text('Unlock'));
    await tester.pumpAndSettle();

    expect(find.text('SECRET SHELL DATA'), findsOneWidget);
    expect(find.text('Orchestrator is locked'), findsNothing);
  });

  testWidgets('failed unlock keeps the lock view and shows the honest hint',
      (tester) async {
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    await store.write(deviceTokenStorageKey, 'tok'); // pragma: allowlist secret

    await pumpGate(
      tester,
      store: store,
      authenticator: FakeBiometricAuthenticator(authenticateResult: false),
    );

    await tester.tap(find.text('Unlock'));
    await tester.pumpAndSettle();

    expect(find.text('Not recognized. Try again.'), findsOneWidget);
    expect(find.text('SECRET SHELL DATA'), findsNothing);
  });
}
