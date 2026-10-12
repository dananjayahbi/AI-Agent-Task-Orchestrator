import 'dart:async';

import 'package:dio/dio.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'api_exception.dart';

/// Extra flag marking a request that carried the gate-released device token
/// (set by [AuthTokenInterceptor.onRequest], read in its error path).
const String deviceTokenInjectedExtra = 'device_token_injected';

/// The token injection point (MT-5.5-04; Sections 12.2/14.2, ADR-006).
///
/// * **Release only after unlock:** the device token is fetched from the
///   gate on every request; while the gate is locked the request goes out
///   with no `Authorization` header at all, so a locked app can never carry
///   authenticated data (Section 14.2).
/// * **AUTH_REQUIRED recovery:** when a request that carried the device
///   token is rejected with 401 (invalid/expired/revoked credential —
///   Section 9.2 catalog code, enforced per-request by WP-5.3), the gate is
///   asked to discard the stored token and return the app to the
///   unlock/onboarding flow (release contract, "Rejection and recovery") —
///   never a silent fallback.
///
/// The token value is never logged or echoed; this interceptor only places
/// it into the request header (Section 12.4, Section 20.4 item 3). Function
/// seams instead of a Riverpod [Ref] keep the interceptor unit-testable.
class AuthTokenInterceptor extends Interceptor {
  AuthTokenInterceptor({
    required String? Function() releaseToken,
    required Future<void> Function() discardCredential,
  })  : _releaseToken = releaseToken,
        _discardCredential = discardCredential;

  final String? Function() _releaseToken;
  final Future<void> Function() _discardCredential;

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    final String? token = _releaseToken();
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
      options.extra[deviceTokenInjectedExtra] = true;
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (err.requestOptions.extra[deviceTokenInjectedExtra] == true &&
        err.response?.statusCode == 401) {
      // Fire-and-forget: the gate transition is independent of the response
      // chain, and the mapped exception must still reach the caller.
      unawaited(_discardCredential());
    }
    handler.next(err);
  }

  /// True when [err] surfaced the Section 9.2 `AUTH_REQUIRED` code — exposed
  /// for callers that want code-level (not just 401-level) checks.
  static bool isAuthRequired(DioException err) {
    final Object? error = err.error;
    return error is OrchestratorApiException &&
        error.code == CodeEnum.AUTH_REQUIRED;
  }
}
