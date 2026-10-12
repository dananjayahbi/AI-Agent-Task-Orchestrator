// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'package:dio/dio.dart';

abstract class AuthInterceptor extends Interceptor {
  /// Get auth information on given route for the given type.
  /// Can return an empty list if type is not present on auth data or
  /// if route doesn't need authentication.
  List<Map<String, String>> getAuthInfo(
      RequestOptions route, bool Function(Map<String, String> secure) handles) {
    if (route.extra.containsKey('secure')) {
      final auth = route.extra['secure'] as List<Map<String, String>>;
      return auth.where((secure) => handles(secure)).toList();
    }
    return [];
  }
}
