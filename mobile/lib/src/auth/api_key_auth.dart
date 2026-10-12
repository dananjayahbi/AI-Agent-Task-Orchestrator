// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'package:dio/dio.dart';
import 'package:orchestrator_mobile/src/auth/auth.dart';

class ApiKeyAuthInterceptor extends AuthInterceptor {
  final Map<String, String> apiKeys = {};

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final authInfo =
        getAuthInfo(options, (secure) => secure['type'] == 'apiKey');
    for (final info in authInfo) {
      final authName = info['name'] as String;
      final authKeyName = info['keyName'] as String;
      final authWhere = info['where'] as String;
      final apiKey = apiKeys[authName];
      if (apiKey != null) {
        if (authWhere == 'query') {
          options.queryParameters[authKeyName] = apiKey;
        } else {
          options.headers[authKeyName] = apiKey;
        }
      }
    }
    super.onRequest(options, handler);
  }
}
