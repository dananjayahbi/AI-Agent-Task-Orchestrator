import 'dart:async';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// One open SSE connection: the response byte stream plus a close handle.
class SseConnection {
  SseConnection(this.bytes, this._close);

  final Stream<Uint8List> bytes;
  final void Function() _close;

  /// Closes the connection cleanly (app pause, teardown) — the stream
  /// errors out or completes and the caller reconnects later (14.2).
  void close() => _close();
}

/// Transport seam: opens `GET [path]?[query]` as an SSE stream with
/// [headers] (authorization, resume id). A fake implements this for tests
/// (MT-5.5-05: "unit tests with a fake transport").
abstract class SseTransport {
  Future<SseConnection> open({
    required String path,
    Map<String, String> query = const <String, String>{},
    Map<String, String> headers = const <String, String>{},
  });
}

/// Dio-backed transport for `GET /events/stream`.
///
/// Uses a dedicated [Dio] (same interceptors as the API client — auth,
/// error mapping, correlation id) so the gate's 401 discard rule applies to
/// the stream too. The generated client's receive timeout only covers the
/// time to response *headers* in dio 5's IO adapter (the SSE body is a raw
/// streamed response afterwards), so the 15 s heartbeat gap between body
/// chunks is unaffected. Non-2xx responses arrive as [DioException] with
/// the mapped Section 9.2 envelope — the same single mapping point as every
/// call.
class DioSseTransport implements SseTransport {
  DioSseTransport(this._dio);

  final Dio _dio;

  @override
  Future<SseConnection> open({
    required String path,
    Map<String, String> query = const <String, String>{},
    Map<String, String> headers = const <String, String>{},
  }) async {
    final CancelToken cancelToken = CancelToken();
    final Response<Stream<Uint8List>> response =
        await _dio.get<Stream<Uint8List>>(
      path,
      queryParameters: query.isEmpty ? null : query,
      cancelToken: cancelToken,
      options: Options(
        responseType: ResponseType.stream,
        headers: headers,
      ),
    );
    final Stream<Uint8List>? body = response.data;
    if (body == null) {
      cancelToken.cancel();
      throw StateError('SSE response carried no body stream.');
    }
    return SseConnection(
      body,
      () {
        if (!cancelToken.isCancelled) {
          cancelToken.cancel();
        }
      },
    );
  }
}
