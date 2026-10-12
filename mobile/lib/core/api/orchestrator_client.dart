import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import '../config/app_config.dart';
import '../security/auth_gate.dart';
import 'auth_token_interceptor.dart';
import 'correlation_id_interceptor.dart';
import 'error_mapping_interceptor.dart';

/// Application-facing wrapper around the generated client (MT-5.5-03).
///
/// * The base URL comes from [AppConfig] — the single source of the endpoint
///   for every consumer; no endpoint is hard-coded in app source
///   (Section 20.4 item 3). The generated `basePath` default is always
///   overridden here.
/// * Non-2xx responses surface through [ErrorMappingInterceptor] — one
///   mapping point for the Section 9.2 envelope.
/// * [CorrelationIdInterceptor] generates `X-Correlation-ID` per exchange
///   (headers.md); mutating calls add `Idempotency-Key` via
///   `idempotencyHeaders(...)` from the mutation layer.
///
/// Authentication seams for later slices: the generated bearer auth
/// interceptor is registered and waits for MT-5.5-04's token gate
/// (`generated.setBearerAuth`); SSE (MT-5.5-05) is transport, not this
/// client.
class OrchestratorClient {
  OrchestratorClient._(this._generated);

  /// Builds the client for [config]'s resolved origin
  /// (`scheme://host[:port]` — operation paths already carry `/api/v1`).
  ///
  /// [releaseToken] / [discardCredential] wire MT-5.5-04's biometric gate:
  /// the device token is attached to outbound requests only while the gate
  /// is unlocked (Section 12.2/14.2). Both are optional so tests and
  /// pre-auth flows (onboarding) can construct a bare client.
  factory OrchestratorClient.fromConfig(
    AppConfig config, {
    String? Function()? releaseToken,
    Future<void> Function()? discardCredential,
  }) {
    final OrchestratorMobile generated = OrchestratorMobile(
      basePathOverride: config.apiOrigin.toString(),
    );
    generated.dio.interceptors.add(
      ErrorMappingInterceptor(generated.serializers),
    );
    generated.dio.interceptors.add(CorrelationIdInterceptor());
    if (releaseToken != null && discardCredential != null) {
      generated.dio.interceptors.add(
        AuthTokenInterceptor(
          releaseToken: releaseToken,
          discardCredential: discardCredential,
        ),
      );
    }
    return OrchestratorClient._(generated);
  }

  final OrchestratorMobile _generated;

  /// The configured [Dio] instance — for transport-level seams only
  /// (tests inject a fake adapter; MT-5.5-04 adds the auth interceptor).
  Dio get dio => _generated.dio;

  late final ApiApi api = _generated.getApiApi();

  late final HealthApi health = _generated.getHealthApi();
}

/// Single source of the API client for every consumer, constructed from the
/// resolved flavor configuration (MT-5.5-02/03) and wired to the biometric
/// gate (MT-5.5-04): while the gate is locked the client sends no
/// `Authorization` header (Section 14.2).
final Provider<OrchestratorClient> apiClientProvider =
    Provider<OrchestratorClient>(
  (ref) {
    final AuthGateNotifier gate = ref.read(authGateProvider.notifier);
    return OrchestratorClient.fromConfig(
      ref.watch(appConfigProvider),
      releaseToken: gate.releaseToken,
      discardCredential: gate.discardCredential,
    );
  },
);
