import 'dart:io';

import 'package:dio/dio.dart' show DioException, HttpClientAdapter, Response;
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../../core/api/api_exception.dart';
import '../../core/api/orchestrator_client.dart';
import '../../core/config/app_config.dart';

/// Onboarding backend seam (MT-5.5-06): reachability probe, Owner login and
/// device registration against the *entered* server URL — which may differ
/// from the flavor default (tunnel hostname, Section 15.1).
///
/// The session token and the returned device token travel through this seam
/// as plain return values but are never stored here, never logged, and the
/// implementation never echoes them (Section 12.4). Tests replace this seam
/// with a scripted fake; the generated-client implementation is the only
/// place real calls are made (NFR-11).
abstract class OnboardingApi {
  /// `GET /health/live` against [baseUrl] — the documented ops liveness
  /// endpoint (Section 9.2). Success means "an Orchestrator server answered
  /// here"; it does not claim backing services are ready.
  Future<void> checkServerReachable(String baseUrl);

  /// `POST /auth/login` — returns the owner session token (plaintext
  /// bearer transport, Section 15.4). Never logged.
  Future<OwnerLoginResult> login({
    required String baseUrl,
    required String username,
    required String password,
  });

  /// `POST /devices` with the owner session as bearer — returns the
  /// device-bound token (shown exactly once, WP-5.3 release contract).
  /// [idempotencyKey] keeps retries of one registration attempt deduped
  /// (Section 9.2, NFR-12).
  Future<String> registerDevice({
    required String baseUrl,
    required String ownerSessionToken,
    required String idempotencyKey,
  });
}

/// Login outcome. The [sessionToken] is a credential: it must never be
/// logged, printed, or placed in widget state (Section 12.4).
class OwnerLoginResult {
  const OwnerLoginResult({required this.username, required this.sessionToken});

  final String username;
  final String sessionToken;
}

/// Placeholder push token until WP-5.4 registers APNs/FCM: the backend
/// requires a non-blank `push_token` row field (accounts serializer); the
/// value is stored sensitive-at-rest and never returned. Recorded as a
/// WP-5.5 follow-up in the changelog.
const String pendingPushToken = 'pending-wp-5.4'; // pragma: allowlist secret

/// Generated-client implementation: one [OrchestratorClient] per server
/// URL, rebuilt when the URL changes (onboarding may correct it mid-flow).
///
/// [adapter] is a test seam: the mocked-backend integration test injects a
/// scripted [HttpClientAdapter] at this single construction point instead
/// of reaching into the private client (NFR-11 — still the generated
/// client doing the talking).
class GeneratedOnboardingApi implements OnboardingApi {
  GeneratedOnboardingApi(this._appConfig, {HttpClientAdapter? adapter})
      : _adapter = adapter;

  final AppConfig _appConfig;
  final HttpClientAdapter? _adapter;

  OrchestratorClient? _client;
  String? _clientBaseUrl;

  OrchestratorClient _clientFor(String baseUrl) {
    if (_client == null || _clientBaseUrl != baseUrl) {
      // Bare client: no gate token injection — onboarding predates the
      // device credential (ADR-006 layering).
      _client = OrchestratorClient.fromConfig(
        AppConfig(flavor: _appConfig.flavor, apiBaseUrl: baseUrl),
      );
      final HttpClientAdapter? adapter = _adapter;
      if (adapter != null) {
        _client!.dio.httpClientAdapter = adapter;
      }
      _clientBaseUrl = baseUrl;
    }
    return _client!;
  }

  @override
  Future<void> checkServerReachable(String baseUrl) async {
    await _clientFor(baseUrl).health.healthLiveRetrieve();
  }

  @override
  Future<OwnerLoginResult> login({
    required String baseUrl,
    required String username,
    required String password,
  }) async {
    try {
      final Response<OwnerSession> response =
          await _clientFor(baseUrl).api.apiV1AuthLoginCreate(
                loginRequest: LoginRequest(
                  (LoginRequestBuilder b) => b
                    ..username = username
                    ..password = password, // pragma: allowlist secret
                ),
              );
      final OwnerSession session = response.data!;
      // The token leaves this method and nowhere else — no state, no log.
      return OwnerLoginResult(
        username: session.user.username,
        sessionToken: session.token,
      );
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }

  @override
  Future<String> registerDevice({
    required String baseUrl,
    required String ownerSessionToken,
    required String idempotencyKey,
  }) async {
    try {
      final Response<DeviceRegisterResponse> response =
          await _clientFor(baseUrl).api.apiV1DevicesCreate(
        deviceRegisterRequest: DeviceRegisterRequest(
          (DeviceRegisterRequestBuilder b) => b
            ..platform =
                Platform.isIOS ? PlatformEnum.ios : PlatformEnum.android
            ..pushToken = pendingPushToken
            ..biometricBound = false,
        ),
        idempotencyKey: idempotencyKey,
        headers: <String, dynamic>{
          'Authorization': 'Bearer $ownerSessionToken',
        },
      );
      // Device token: response → return value → gate storage. It never
      // enters app state or a widget (release contract; MT risk note).
      return response.data!.token;
    } on DioException catch (error) {
      throw OrchestratorApiException.of(error);
    }
  }
}

/// The onboarding backend seam for the app; tests override it.
final Provider<OnboardingApi> onboardingApiProvider = Provider<OnboardingApi>(
  (ref) => GeneratedOnboardingApi(ref.watch(appConfigProvider)),
);
