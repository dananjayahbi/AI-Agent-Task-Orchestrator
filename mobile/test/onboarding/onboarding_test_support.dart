import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_api.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_progress_store.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../security/security_test_support.dart';

/// Scriptable [OnboardingApi] fake: no network, no generated client.
class FakeOnboardingApi implements OnboardingApi {
  FakeOnboardingApi({
    this.reachable = true,
    this.loginResult,
    this.deviceToken = 'device-token-value', // pragma: allowlist secret
  });

  bool reachable;
  OwnerLoginResult? loginResult;
  String deviceToken;

  /// Thrown by login/register when set (before any scripted result).
  OrchestratorApiException? loginError;
  OrchestratorApiException? registerError;

  int reachabilityCalls = 0;
  int loginCalls = 0;
  int registerCalls = 0;
  String? lastIdempotencyKey;
  String? lastOwnerSessionToken;

  @override
  Future<void> checkServerReachable(String baseUrl) async {
    reachabilityCalls += 1;
    if (!reachable) {
      throw OrchestratorApiException.unparsed(
        statusCode: 503,
        message: 'connection refused',
        retryable: true,
      );
    }
  }

  @override
  Future<OwnerLoginResult> login({
    required String baseUrl,
    required String username,
    required String password,
  }) async {
    loginCalls += 1;
    final OrchestratorApiException? error = loginError;
    if (error != null) {
      throw error;
    }
    final OwnerLoginResult? scripted = loginResult;
    if (scripted == null) {
      throw StateError('FakeOnboardingApi.loginResult not set');
    }
    return scripted;
  }

  @override
  Future<String> registerDevice({
    required String baseUrl,
    required String ownerSessionToken,
    required String idempotencyKey,
  }) async {
    registerCalls += 1;
    lastOwnerSessionToken = ownerSessionToken;
    lastIdempotencyKey = idempotencyKey;
    final OrchestratorApiException? error = registerError;
    if (error != null) {
      throw error;
    }
    return deviceToken;
  }
}

/// In-memory [OnboardingProgressStore] for resume tests.
class InMemoryOnboardingProgressStore implements OnboardingProgressStore {
  int? step;
  String? serverUrl;
  bool completed = false;

  @override
  Future<int?> readStep() async => step;

  @override
  Future<void> writeStep(int stepIndex) async => step = stepIndex;

  @override
  Future<String?> readServerUrl() async => serverUrl;

  @override
  Future<void> writeServerUrl(String url) async => serverUrl = url;

  @override
  Future<bool> readCompleted() async => completed;

  @override
  Future<void> writeCompleted(bool value) async => completed = value;
}

/// A catalog-shaped AUTH_REQUIRED exception (login failure mapping tests).
OrchestratorApiException authRequiredException() =>
    const OrchestratorApiException(
      statusCode: 401,
      code: CodeEnum.AUTH_REQUIRED,
      message: 'Authentication credentials were not provided.',
      retryable: false,
      details: null,
      correlationId: null,
    );

/// Provider overrides wiring the onboarding flow to fakes plus the
/// MT-5.5-04 security seams.
List<Override> onboardingOverrides({
  required FakeOnboardingApi api,
  required InMemoryOnboardingProgressStore progress,
  InMemorySecureTokenStore? secureStore,
  FakeBiometricAuthenticator? authenticator,
}) {
  return <Override>[
    onboardingApiProvider.overrideWithValue(api),
    onboardingProgressStoreProvider.overrideWithValue(progress),
    secureTokenStoreProvider
        .overrideWithValue(secureStore ?? InMemorySecureTokenStore()),
    biometricAuthProvider
        .overrideWithValue(authenticator ?? FakeBiometricAuthenticator()),
  ];
}

/// Well-formed OwnerLoginResult for fakes (session token is a test secret).
OwnerLoginResult ownerLogin({String username = 'owner'}) => OwnerLoginResult(
      username: username,
      sessionToken: 'owner-session-token', // pragma: allowlist secret
    );
