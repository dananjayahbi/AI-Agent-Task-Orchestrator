import 'package:dio/dio.dart';

import 'request_headers.dart';

/// Generates `X-Correlation-ID` for every request that does not already
/// carry one (headers.md "Generation/Honoring": when the header is present,
/// the supplied value is honored).
class CorrelationIdInterceptor extends Interceptor {
  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    if (!options.headers.containsKey(correlationIdHeader)) {
      options.headers[correlationIdHeader] = newCorrelationId();
    }
    handler.next(options);
  }
}
