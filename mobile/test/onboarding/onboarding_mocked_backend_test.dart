import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/config/app_config.dart';
import 'package:orchestrator_mobile/core/security/auth_gate.dart';
import 'package:orchestrator_mobile/core/security/biometric_authenticator.dart';
import 'package:orchestrator_mobile/core/security/secure_token_store.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_api.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_flow.dart';
import 'package:orchestrator_mobile/features/onboarding/onboarding_progress_store.dart';

import '../security/security_test_support.dart';
import 'onboarding_test_support.dart';

const String ownerSessionToken =
    'owner-session-token'; // pragma: allowlist secret
const String integrationDeviceToken =
    'device-token-integration'; // pragma: allowlist secret

/// Routes canned responses by path+method, like a scripted backend.
class MockBackendAdapter implements HttpClientAdapter {
  MockBackendAdapter({String? loginBody, this.deviceStatus = 201})
      : loginBody = loginBody ?? _defaultLoginBody();

  /// Pre-parsed so tests can mutate the body per scenario.
  String loginBody;
  int loginStatus = 200;
  int deviceStatus;

  static String _defaultLoginBody() => jsonEncode(<String, Object?>{
        'token': ownerSessionToken,
        'expires_at': '2031-01-01T00:00:00Z',
        'user': <String, Object?>{'id': 1, 'username': 'owner'},
      });

  /// Models a dead host: every request fails like a connection error.
  bool failAll = false;

  final List<String> requests = <String>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (failAll) {
      throw DioException(
        requestOptions: options,
        type: DioExceptionType.connectionError,
        error: 'connection refused',
      );
    }
    requests.add('${options.method} ${options.path}');
    final String path = options.path;
    if (path.endsWith('/health/live')) {
      return _json(200, <String, Object?>{'status': 'ok'});
    }
    if (path.endsWith('/auth/login')) {
      return ResponseBody.fromString(
        loginBody,
        loginStatus,
        headers: _jsonHeaders(),
      );
    }
    if (path.endsWith('/devices')) {
      if (deviceStatus == 201) {
        return _json(201, <String, Object?>{
          'id': 7,
          'platform': 'android',
          'biometric_bound': false,
          'expires_at': '2031-01-01T00:00:00Z',
          'token': integrationDeviceToken,
        });
      }
      return _json(deviceStatus, <String, Object?>{
        'error': <String, Object?>{
          'code': 'AUTH_REQUIRED',
          'message': 'Authentication credentials were not provided.',
          'retryable': false,
          'details': null,
          'correlation_id': 'c0a8-1111',
        },
      });
    }
    return _json(404, <String, Object?>{
      'error': <String, Object?>{
        'code': 'SERVER_ERROR',
        'message': 'Unexpected path $path',
        'retryable': true,
        'details': null,
        'correlation_id': 'c0a8-ffff',
      },
    });
  }

  ResponseBody _json(int status, Map<String, Object?> body) =>
      ResponseBody.fromString(
        jsonEncode(body),
        status,
        headers: _jsonHeaders(),
      );

  Map<String, List<String>> _jsonHeaders() => <String, List<String>>{
        Headers.contentTypeHeader: <String>['application/json'],
      };

  @override
  void close({bool force = false}) {}
}

/// Mocked-backend integration (MT-5.5-06 acceptance item 5): the full
/// four-step flow through the *generated client* — health probe, login,
/// device registration, enrollment — against canned Section 9.2/12.2
/// responses (NFR-11: one typed client, not ad-hoc HTTP).
void main() {
  ProviderContainer createContainer({
    required MockBackendAdapter backend,
    InMemorySecureTokenStore? store,
    FakeBiometricAuthenticator? authenticator,
    InMemoryOnboardingProgressStore? progress,
  }) {
    const AppConfig devConfig = AppConfig(
      flavor: AppFlavor.dev,
      apiBaseUrl: 'http://10.0.2.2:8000/api/v1',
    );
    final ProviderContainer container = ProviderContainer(
      overrides: <Override>[
        // Flavor default URL — the backend adapter answers for any host.
        appConfigProvider.overrideWithValue(devConfig),
        // Real generated-client implementation, scripted at the adapter
        // seam: the flow exercises the same code production runs.
        onboardingApiProvider.overrideWithValue(
            GeneratedOnboardingApi(devConfig, adapter: backend)),
        onboardingProgressStoreProvider
            .overrideWithValue(progress ?? InMemoryOnboardingProgressStore()),
        secureTokenStoreProvider
            .overrideWithValue(store ?? InMemorySecureTokenStore()),
        biometricAuthProvider
            .overrideWithValue(authenticator ?? FakeBiometricAuthenticator()),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  Future<void> settle(ProviderContainer container) async {
    container.read(onboardingFlowProvider);
    await Future<void>.delayed(Duration.zero);
    await Future<void>.delayed(Duration.zero);
  }

  test(
      'full flow: health probe → login → registration → enrollment, with the '
      'device token landing only in secure storage', () async {
    final MockBackendAdapter backend = MockBackendAdapter();
    final InMemorySecureTokenStore store = InMemorySecureTokenStore();
    final ProviderContainer container =
        createContainer(backend: backend, store: store);
    await settle(container);
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);

    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');
    expect(container.read(onboardingFlowProvider).step, OnboardingStep.login);

    await flow.login(
        username: 'owner', password: 'pw'); // pragma: allowlist secret
    final OnboardingState afterLogin = container.read(onboardingFlowProvider);
    expect(afterLogin.step, OnboardingStep.deviceRegistration);
    expect(afterLogin.toString(), isNot(contains(ownerSessionToken)),
        reason: 'owner session token must not enter state');

    await flow.registerDevice();
    final OnboardingState afterRegister =
        container.read(onboardingFlowProvider);
    expect(afterRegister.step, OnboardingStep.biometricEnrollment);
    expect(afterRegister.toString(), isNot(contains(integrationDeviceToken)),
        reason: 'device token must not enter state');
    expect(await store.read(deviceTokenStorageKey), integrationDeviceToken);
    expect(container.read(authGateProvider).status, GateStatus.locked);

    await flow.finish();
    expect(container.read(onboardingFlowProvider).completed, isTrue);

    // The generated client made exactly the three documented calls
    // (Section 9.2) — no hidden extras. (The health operation's path is
    // relative to the configured base URL, which already carries
    // /api/v1; the auth operations embed the prefix themselves.)
    expect(backend.requests, <String>[
      'GET /health/live',
      'POST /api/v1/auth/login',
      'POST /api/v1/devices',
    ]);
  });

  test('login failure surfaces the catalog code mapped to friendly copy',
      () async {
    final MockBackendAdapter backend = MockBackendAdapter()
      ..loginStatus = 401
      ..loginBody = jsonEncode(<String, Object?>{
        'error': <String, Object?>{
          'code': 'AUTH_REQUIRED',
          'message': 'Authentication credentials were not provided.',
          'retryable': false,
          'details': null,
          'correlation_id': 'c0a8-2222',
        },
      });
    final ProviderContainer container = createContainer(backend: backend);
    await settle(container);
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);
    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');

    await flow.login(
        username: 'owner', password: 'wrong'); // pragma: allowlist secret

    final OnboardingState state = container.read(onboardingFlowProvider);
    expect(state.step, OnboardingStep.login);
    expect(state.errorMessage, 'Username or password is not correct.');
    expect(state.errorMessage, isNot(contains('wrong')));
    expect(state.errorMessage,
        isNot(contains('Authentication credentials were not provided.')));
  });

  test(
      'unreachable server (transport failure) keeps the user on the URL '
      'step with friendly copy', () async {
    final MockBackendAdapter deadBackend = MockBackendAdapter()..failAll = true;
    final ProviderContainer container = createContainer(backend: deadBackend);
    await settle(container);
    final OnboardingFlowNotifier flow =
        container.read(onboardingFlowProvider.notifier);

    await flow.confirmServerUrl('http://10.0.2.2:8000/api/v1');

    final OnboardingState state = container.read(onboardingFlowProvider);
    expect(state.step, OnboardingStep.serverUrl);
    expect(state.errorMessage, contains('Could not reach the server'));
    expect(state.errorMessage, isNot(contains('SocketException')));
  });
}
