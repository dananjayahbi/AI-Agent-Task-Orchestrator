// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:orchestrator_mobile/src/auth/auth.dart';

class BasicAuthInfo {
  final String username;
  final String password;

  const BasicAuthInfo(this.username, this.password);
}

class BasicAuthInterceptor extends AuthInterceptor {
  final Map<String, BasicAuthInfo> authInfo = {};

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    final metadataAuthInfo = getAuthInfo(
        options,
        (secure) =>
            (secure['type'] == 'http' &&
                secure['scheme']?.toLowerCase() == 'basic') ||
            secure['type'] == 'basic');
    for (final info in metadataAuthInfo) {
      final authName = info['name'] as String;
      final basicAuthInfo = authInfo[authName];
      if (basicAuthInfo != null) {
        final basicAuth =
            'Basic ${base64Encode(utf8.encode('${basicAuthInfo.username}:${basicAuthInfo.password}'))}';
        options.headers['Authorization'] = basicAuth;
        break;
      }
    }
    super.onRequest(options, handler);
  }
}
