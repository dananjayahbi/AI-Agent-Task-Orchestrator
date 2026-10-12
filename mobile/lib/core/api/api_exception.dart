import 'package:built_value/json_object.dart';
import 'package:dio/dio.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// The Section 9.2 error envelope as seen by the app: exactly the five
/// documented fields, produced at the single client-level mapping point
/// (`ErrorMappingInterceptor`). Screens map [code] to friendly messages later
/// (Section 13.3); they never parse [message].
class OrchestratorApiException implements Exception {
  const OrchestratorApiException({
    this.statusCode,
    required this.code,
    required this.message,
    required this.retryable,
    required this.details,
    required this.correlationId,
  });

  /// Builds from the generated [ErrorEnvelope] — all five fields present.
  factory OrchestratorApiException.fromEnvelope(
    ErrorEnvelope envelope, {
    int? statusCode,
  }) {
    return OrchestratorApiException(
      statusCode: statusCode,
      code: envelope.code,
      message: envelope.message,
      retryable: envelope.retryable,
      details: envelope.details == null
          ? null
          : <String, Object?>{
              for (final MapEntry<String, JsonObject?> entry
                  in envelope.details!.entries)
                entry.key: entry.value?.value,
            },
      correlationId: envelope.correlationId,
    );
  }

  /// Fallback for failures without a parseable envelope (empty body, proxy
  /// error page, transport failure). Catalog fields stay null/false rather
  /// than invented (Section 20.4 item 5: no invented codes).
  factory OrchestratorApiException.unparsed({
    int? statusCode,
    required String message,
    required bool retryable,
  }) {
    return OrchestratorApiException(
      statusCode: statusCode,
      code: null,
      message: message,
      retryable: retryable,
      details: null,
      correlationId: null,
    );
  }

  /// Convenience accessor for a caught [DioException]: returns the mapped
  /// exception or a transport-level fallback.
  static OrchestratorApiException of(DioException error) {
    final Object? mapped = error.error;
    if (mapped is OrchestratorApiException) {
      return mapped;
    }
    final String rawMessage = error.message ?? 'Unexpected error response.';
    return OrchestratorApiException.unparsed(
      statusCode: error.response?.statusCode,
      message: rawMessage.isEmpty ? 'Unexpected error response.' : rawMessage,
      retryable: error.type == DioExceptionType.connectionTimeout ||
          error.type == DioExceptionType.sendTimeout ||
          error.type == DioExceptionType.receiveTimeout ||
          error.type == DioExceptionType.connectionError,
    );
  }

  /// HTTP status of the failing response, when one arrived.
  final int? statusCode;

  /// The canonical catalog code (one of the 19 Section 9.2 codes); null only
  /// when the body was not an envelope.
  final CodeEnum? code;

  /// Human-readable sentence from the server; never parsed (error-envelope.md
  /// rule 2).
  final String message;

  /// Whether a retry can succeed (error-envelope.md rule 3).
  final bool retryable;

  /// Structured context for this occurrence (Section 9.2 example:
  /// `task_id`, `state`).
  final Map<String, Object?>? details;

  /// Correlation id for this exchange (headers.md).
  final String? correlationId;

  /// Wire spelling of [code], e.g. `TASK_ALREADY_CLAIMED`.
  String? get codeName => code?.name;

  @override
  String toString() => 'OrchestratorApiException(${codeName ?? 'no-code'}, '
      'HTTP $statusCode, correlationId: $correlationId): $message';
}
