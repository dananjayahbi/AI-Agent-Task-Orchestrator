import 'package:built_value/serializer.dart';
import 'package:dio/dio.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

import 'api_exception.dart';

/// The single client-level mapping point for non-2xx responses (MT-5.5-03,
/// Section 9.2): every failing response is deserialized into the five-field
/// envelope and surfaced as an [OrchestratorApiException] attached to the
/// [DioException.error] slot, so screens have exactly one place to read
/// catalog codes from (Section 13.3's mobile equivalent).
///
/// Both documented renderings are accepted at this one point: the canonical
/// nested body `{"error": {…}}` (Section 9.2 — what the OpenAPI
/// `ErrorEnvelope` schema declares since the schema owner reconciled the
/// shape) and a top-level five-field body (legacy rendering, tolerated
/// defensively by wrapping it before deserialization).
class ErrorMappingInterceptor extends Interceptor {
  ErrorMappingInterceptor(this._serializers);

  final Serializers _serializers;

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    handler.next(err.copyWith(error: mapError(err)));
  }

  /// The one mapping point. Exposed for direct unit testing.
  OrchestratorApiException mapError(DioException err) {
    final int? statusCode = err.response?.statusCode;
    final Object? body = err.response?.data;

    if (body is Map) {
      // Canonical rendering already nests under `error`; anything else is
      // wrapped so one deserializer handles both shapes.
      final Map<String, dynamic> wire = body['error'] is Map
          ? Map<String, dynamic>.from(body)
          : <String, dynamic>{'error': Map<String, dynamic>.from(body)};
      try {
        final Object? decoded = _serializers.deserialize(
          wire,
          specifiedType: const FullType(ErrorEnvelope),
        );
        if (decoded is ErrorEnvelope) {
          return OrchestratorApiException.fromEnvelope(
            decoded,
            statusCode: statusCode,
          );
        }
      } catch (_) {
        // Fall through: body was not a valid envelope (bad code, missing
        // field). Never invent a catalog code for it.
      }
    }

    final String rawMessage = err.message ?? 'Unexpected error response.';
    return OrchestratorApiException.unparsed(
      statusCode: statusCode,
      message: rawMessage.isEmpty ? 'Unexpected error response.' : rawMessage,
      retryable: err.type == DioExceptionType.connectionTimeout ||
          err.type == DioExceptionType.sendTimeout ||
          err.type == DioExceptionType.receiveTimeout ||
          err.type == DioExceptionType.connectionError,
    );
  }
}
