import 'dart:math';

/// Header names from
/// [docs/plan/conventions/headers.md](../../../../../docs/plan/conventions/headers.md)
/// (parent plan Sections 9.2, 17; ADR-012) — one vocabulary everywhere.
const String correlationIdHeader = 'X-Correlation-ID';

const String idempotencyKeyHeader = 'Idempotency-Key';

/// Headers for one logical mutating request: the caller (the app's mutation
/// layer) supplies a stable idempotency key so retries of the same operation
/// dedupe server-side (Section 9.2, NFR-12). Pass to the generated API
/// methods via their `headers` parameter.
Map<String, String> idempotencyHeaders(String idempotencyKey) =>
    <String, String>{idempotencyKeyHeader: idempotencyKey};

/// Generates an opaque correlation id in the plan's example shape
/// (`c0a8-4f2e-91d7`, Section 9.2). Diagnostic data only: never parsed,
/// never identity (headers.md "Honoring/Scrubbing").
String newCorrelationId() {
  final Random random = Random.secure();
  String group() => random.nextInt(0x10000).toRadixString(16).padLeft(4, '0');
  return '${group()}-${group()}-${group()}';
}
