import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:orchestrator_mobile/core/api/api_exception.dart';
import 'package:orchestrator_mobile/core/api/orchestrator_client.dart';
import 'package:orchestrator_mobile/core/api/request_headers.dart';
import 'package:orchestrator_mobile/core/config/app_config.dart';
import 'package:orchestrator_mobile/orchestrator_mobile.dart';

/// Serves canned responses and records the request for assertions.
class _FixtureAdapter implements HttpClientAdapter {
  _FixtureAdapter(this._status, this._body,
      {this.contentType = 'application/json'});

  final int _status;
  final String _body;
  final String contentType;

  RequestOptions? lastRequest;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    lastRequest = options;
    return ResponseBody.fromString(
      _body,
      _status,
      headers: <String, List<String>>{
        Headers.contentTypeHeader: <String>[contentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// Typed client behavior (MT-5.5-03): envelope mapping at one point,
/// idempotency support, correlation id generation, and construction from
/// resolved flavor config.
void main() {
  AppConfig devConfig() => AppConfig.resolve(
        flavor: 'dev',
        baseUrl: 'http://10.0.2.2:8000/api/v1',
      );

  LoginRequest loginRequest() => LoginRequest(
        (LoginRequestBuilder b) => b
          ..username = 'owner'
          ..password = 'secret', // pragma: allowlist secret
      );

  OrchestratorClient clientWith(HttpClientAdapter adapter) {
    final OrchestratorClient client =
        OrchestratorClient.fromConfig(devConfig());
    client.dio.httpClientAdapter = adapter;
    return client;
  }

  Future<DioException> captureFailure(Future<Object?> call) async {
    try {
      await call;
      fail('expected a DioException');
    } on DioException catch (e) {
      return e;
    }
  }

  const String canonicalBody = '{"error":{'
      '"code":"TASK_ALREADY_CLAIMED",'
      '"message":"Task PID00007-T004 is held by another worker.",'
      '"retryable":false,'
      '"details":{"task_id":"PID00007-T004","state":"in_progress"},'
      '"correlation_id":"c0a8-4f2e-91d7"'
      '}}';

  group('Section 9.2 error envelope — one mapping point', () {
    test('nested fixture body keeps all five fields intact', () async {
      final _FixtureAdapter adapter = _FixtureAdapter(409, canonicalBody);
      final OrchestratorClient client = clientWith(adapter);

      final DioException failure = await captureFailure(
        client.api.apiV1AuthLoginCreate(loginRequest: loginRequest()),
      );
      final OrchestratorApiException mapped =
          OrchestratorApiException.of(failure);

      expect(mapped.code, CodeEnum.TASK_ALREADY_CLAIMED);
      expect(mapped.codeName, 'TASK_ALREADY_CLAIMED');
      expect(mapped.message, 'Task PID00007-T004 is held by another worker.');
      expect(mapped.retryable, isFalse);
      expect(mapped.details, <String, Object?>{
        'task_id': 'PID00007-T004',
        'state': 'in_progress',
      });
      expect(mapped.correlationId, 'c0a8-4f2e-91d7');
      expect(mapped.statusCode, 409);
    });

    test('top-level five-field body (OpenAPI schema shape) maps too', () async {
      const String topLevelBody = '{'
          '"code":"VALIDATION_ERROR",'
          '"message":"Bad input.",'
          '"retryable":true,'
          '"details":null,'
          '"correlation_id":"aaaa-bbbb-cccc"'
          '}';
      final _FixtureAdapter adapter = _FixtureAdapter(400, topLevelBody);
      final OrchestratorClient client = clientWith(adapter);

      final DioException failure = await captureFailure(
        client.api.apiV1AuthLoginCreate(loginRequest: loginRequest()),
      );
      final OrchestratorApiException mapped =
          OrchestratorApiException.of(failure);

      expect(mapped.code, CodeEnum.VALIDATION_ERROR);
      expect(mapped.retryable, isTrue);
      expect(mapped.correlationId, 'aaaa-bbbb-cccc');
      expect(mapped.statusCode, 400);
    });

    test('non-envelope body never invents a catalog code', () async {
      final _FixtureAdapter adapter = _FixtureAdapter(
        502,
        '<html><body>Bad Gateway</body></html>',
        contentType: 'text/html',
      );
      final OrchestratorClient client = clientWith(adapter);

      final DioException failure = await captureFailure(
        client.api.apiV1AuthLoginCreate(loginRequest: loginRequest()),
      );
      final OrchestratorApiException mapped =
          OrchestratorApiException.of(failure);

      expect(mapped.code, isNull);
      expect(mapped.statusCode, 502);
      expect(mapped.retryable, isFalse);
    });
  });

  group('idempotency key support (Section 9.2, NFR-12)', () {
    test('mutating call can carry Idempotency-Key via headers', () async {
      final _FixtureAdapter adapter = _FixtureAdapter(400, canonicalBody);
      final OrchestratorClient client = clientWith(adapter);

      await captureFailure(
        client.api.apiV1AuthLoginCreate(
          loginRequest: loginRequest(),
          headers: idempotencyHeaders('mutation-key-0001'),
        ),
      );

      final Map<String, dynamic> sent = adapter.lastRequest!.headers;
      final String? key = sent.entries
          .where((MapEntry<String, dynamic> e) =>
              e.key.toLowerCase() == idempotencyKeyHeader.toLowerCase())
          .map((MapEntry<String, dynamic> e) => e.value.toString())
          .firstOrNull;
      expect(key, 'mutation-key-0001');
    });

    test('no key is injected when the mutation layer does not opt in',
        () async {
      final _FixtureAdapter adapter = _FixtureAdapter(400, canonicalBody);
      final OrchestratorClient client = clientWith(adapter);

      await captureFailure(
        client.api.apiV1AuthLoginCreate(loginRequest: loginRequest()),
      );

      final bool present = adapter.lastRequest!.headers.keys.any(
        (String k) => k.toLowerCase() == idempotencyKeyHeader.toLowerCase(),
      );
      expect(present, isFalse);
    });
  });

  group('correlation id (headers.md)', () {
    test('generated when absent, in the example shape', () async {
      final _FixtureAdapter adapter = _FixtureAdapter(
        200,
        '{"token":"opaque-session-token",'
        '"expires_at":"2026-10-12T12:00:00Z",'
        '"user":{"id":1,"username":"owner"}}',
      );
      final OrchestratorClient client = clientWith(adapter);

      await client.api.apiV1AuthLoginCreate(loginRequest: loginRequest());

      final Map<String, dynamic> sent = adapter.lastRequest!.headers;
      final String? value = sent.entries
          .where((MapEntry<String, dynamic> e) =>
              e.key.toLowerCase() == correlationIdHeader.toLowerCase())
          .map((MapEntry<String, dynamic> e) => e.value.toString())
          .firstOrNull;
      expect(value, isNotNull);
      expect(
          RegExp(r'^[0-9a-f]{4}(-[0-9a-f]{4}){2}$').hasMatch(value!), isTrue);
    });

    test('an explicitly supplied value is honored', () async {
      final _FixtureAdapter adapter = _FixtureAdapter(400, canonicalBody);
      final OrchestratorClient client = clientWith(adapter);

      await captureFailure(
        client.api.apiV1AuthLoginCreate(
          loginRequest: loginRequest(),
          headers: <String, String>{correlationIdHeader: 'feed-beef-cafe'},
        ),
      );

      final String? value = adapter.lastRequest!.headers.entries
          .where((MapEntry<String, dynamic> e) =>
              e.key.toLowerCase() == correlationIdHeader.toLowerCase())
          .map((MapEntry<String, dynamic> e) => e.value.toString())
          .firstOrNull;
      expect(value, 'feed-beef-cafe');
    });
  });

  group('construction from resolved flavor config', () {
    test('dev config provides the base URL — no committed endpoint', () {
      final ProviderContainer container = ProviderContainer(
        overrides: [appConfigProvider.overrideWithValue(devConfig())],
      );
      addTearDown(container.dispose);

      final OrchestratorClient client = container.read(apiClientProvider);
      expect(client.dio.options.baseUrl, 'http://10.0.2.2:8000');
      expect(client.dio.options.baseUrl.contains('/api/v1'), isFalse,
          reason: 'operation paths already carry the /api/v1 prefix');
    });

    test('prod config derived from the tunnel hostname provides the URL', () {
      final AppConfig prod = AppConfig.resolve(
        flavor: 'prod',
        baseUrl: '',
        tunnelHostname: 'orchestrator.example.com',
      );
      final ProviderContainer container = ProviderContainer(
        overrides: [appConfigProvider.overrideWithValue(prod)],
      );
      addTearDown(container.dispose);

      expect(
        container.read(apiClientProvider).dio.options.baseUrl,
        'https://orchestrator.example.com',
      );
    });
  });
}
