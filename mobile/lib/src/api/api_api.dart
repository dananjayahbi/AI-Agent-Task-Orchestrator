// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:built_value/serializer.dart';
import 'package:dio/dio.dart';

import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/api_util.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_request.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_response.dart';
import 'package:orchestrator_mobile/src/model/device_register_request.dart';
import 'package:orchestrator_mobile/src/model/device_register_response.dart';
import 'package:orchestrator_mobile/src/model/error_envelope.dart';
import 'package:orchestrator_mobile/src/model/login_request.dart';
import 'package:orchestrator_mobile/src/model/orchestrator_manifest.dart';
import 'package:orchestrator_mobile/src/model/owner_session.dart';
import 'package:orchestrator_mobile/src/model/patched_project_policy.dart';
import 'package:orchestrator_mobile/src/model/patched_project_update.dart';
import 'package:orchestrator_mobile/src/model/patched_task_update.dart';
import 'package:orchestrator_mobile/src/model/project.dart';
import 'package:orchestrator_mobile/src/model/project_create.dart';
import 'package:orchestrator_mobile/src/model/project_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/project_policy.dart';
import 'package:orchestrator_mobile/src/model/refreshed.dart';
import 'package:orchestrator_mobile/src/model/revoked.dart';
import 'package:orchestrator_mobile/src/model/task.dart';
import 'package:orchestrator_mobile/src/model/task_create.dart';
import 'package:orchestrator_mobile/src/model/task_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/token_list_envelope.dart';

class ApiApi {
  final Dio _dio;

  final Serializers _serializers;

  const ApiApi(this._dio, this._serializers);

  /// apiV1AuthLoginCreate
  /// Verify credentials, start the session, return the binding once.
  ///
  /// Parameters:
  /// * [loginRequest]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [OwnerSession] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<OwnerSession>> apiV1AuthLoginCreate({
    required LoginRequest loginRequest,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/auth/login';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(LoginRequest);
      _bodyData = _serializers.serialize(loginRequest, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    OwnerSession? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(OwnerSession),
            ) as OwnerSession;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<OwnerSession>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1AuthLogoutCreate
  /// Revoke the caller&#39;s &#x60;&#x60;owner_session&#x60;&#x60; row and flush its session.
  ///
  /// Parameters:
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Revoked] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Revoked>> apiV1AuthLogoutCreate({
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/auth/logout';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Revoked? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Revoked),
            ) as Revoked;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Revoked>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1AuthRefreshCreate
  /// Push expiry forward by the Section 9.10 lifetime; return it.
  ///
  /// Parameters:
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Refreshed] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Refreshed>> apiV1AuthRefreshCreate({
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/auth/refresh';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Refreshed? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Refreshed),
            ) as Refreshed;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Refreshed>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1DevicesCreate
  /// Create Device + device token atomically; plaintext returned once.
  ///
  /// Parameters:
  /// * [deviceRegisterRequest]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [DeviceRegisterResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<DeviceRegisterResponse>> apiV1DevicesCreate({
    required DeviceRegisterRequest deviceRegisterRequest,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/devices';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(DeviceRegisterRequest);
      _bodyData =
          _serializers.serialize(deviceRegisterRequest, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    DeviceRegisterResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(DeviceRegisterResponse),
            ) as DeviceRegisterResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<DeviceRegisterResponse>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1DevicesDestroy
  /// Revoke one of the caller&#39;s devices (immediate on both rows).
  ///
  /// Parameters:
  /// * [id]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Revoked] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Revoked>> apiV1DevicesDestroy({
    required int id,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/devices/{id}'.replaceAll('{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(int)).toString());
    final _options = Options(
      method: r'DELETE',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Revoked? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Revoked),
            ) as Revoked;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Revoked>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1TokensAgentCreate
  /// Issue one agent token; plaintext returned exactly once.
  ///
  /// Parameters:
  /// * [agentTokenIssueRequest]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AgentTokenIssueResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AgentTokenIssueResponse>> apiV1TokensAgentCreate({
    required AgentTokenIssueRequest agentTokenIssueRequest,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tokens/agent';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(AgentTokenIssueRequest);
      _bodyData =
          _serializers.serialize(agentTokenIssueRequest, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    AgentTokenIssueResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AgentTokenIssueResponse),
            ) as AgentTokenIssueResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AgentTokenIssueResponse>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1TokensDestroy
  /// Revoke one of the caller&#39;s tokens (immediate — no cache).
  ///
  /// Parameters:
  /// * [id]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Revoked] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Revoked>> apiV1TokensDestroy({
    required int id,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tokens/{id}'.replaceAll('{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(int)).toString());
    final _options = Options(
      method: r'DELETE',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Revoked? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Revoked),
            ) as Revoked;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Revoked>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// apiV1TokensRetrieve
  /// List the caller&#39;s API tokens as metadata (no hash, no plaintext). Sort: id descending (newest first). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;; &#x60;page_size&#x60; defaults to 25 and is clamped to 100.
  ///
  /// Parameters:
  /// * [cursor] - Opaque cursor from the previous page's next_cursor.
  /// * [kind] - Filter by token kind.  * `owner_session` - owner session * `agent` - agent * `device` - device
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults).
  /// * [projectId] - Filter by project id (agent tokens are project-scoped).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [TokenListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<TokenListEnvelope>> apiV1TokensRetrieve({
    String? cursor,
    String? kind,
    int? pageSize,
    String? projectId,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tokens';
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _queryParameters = <String, dynamic>{
      if (cursor != null)
        r'cursor':
            encodeQueryParameter(_serializers, cursor, const FullType(String)),
      if (kind != null)
        r'kind':
            encodeQueryParameter(_serializers, kind, const FullType(String)),
      if (pageSize != null)
        r'page_size':
            encodeQueryParameter(_serializers, pageSize, const FullType(int)),
      if (projectId != null)
        r'project_id': encodeQueryParameter(
            _serializers, projectId, const FullType(String)),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    TokenListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(TokenListEnvelope),
            ) as TokenListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<TokenListEnvelope>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// createProject
  /// Create a project. The &#x60;PID&#x60; id is assigned server-side from the Section 7.3 database sequence — no client-supplied id is accepted (an &#x60;id&#x60; key is rejected as unknown). The default Project Policy (Section 7.2 defaults) is created as a pair (Section 7.1). Caller: Owner only.
  ///
  /// Parameters:
  /// * [projectCreate]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Project] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Project>> createProject({
    required ProjectCreate projectCreate,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects';
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(ProjectCreate);
      _bodyData = _serializers.serialize(projectCreate, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Project? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Project),
            ) as Project;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Project>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// createTask
  /// Create a task (Section 9.2 Tasks row; caller: Owner only). T1&#39;s model-level step: the id is allocated server-side (&#x60;{PID}-T{index}&#x60;, Section 7.3), &#x60;state&#x60; starts at &#x60;draft&#x60;, &#x60;version&#x60; starts at 1 (FR-TSK-06), &#x60;audit_required&#x60; copies the project policy, and &#x60;target_scope&#x60; globs are validated against Section 12.3. Accepts the FR-TSK-02 field set only — &#x60;state&#x60;, &#x60;version&#x60;, &#x60;id&#x60;, lease/merge fields are rejected as unknown. &#x60;Idempotency-Key&#x60; replays a retry without duplicating the task (ADR-012).
  ///
  /// Parameters:
  /// * [pid]
  /// * [taskCreate]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of re-executing it; reusing it with a different request is an open point (headers.md) and executes normally.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Task] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Task>> createTask({
    required String pid,
    required TaskCreate taskCreate,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/tasks'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'POST',
      headers: <String, dynamic>{
        if (idempotencyKey != null) r'Idempotency-Key': idempotencyKey,
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(TaskCreate);
      _bodyData = _serializers.serialize(taskCreate, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Task? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Task),
            ) as Task;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Task>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// listProjects
  /// List registered projects. Sort: project id ascending — PID generation order, i.e. creation order (zero-padded Section 7.3 ids make lexicographic order deterministic; pagination.md rule 2). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;; &#x60;page_size&#x60; defaults to 25, clamped to 100. Caller: Owner only — agent read-only access for a token&#39;s own project activates in WP-2.x and is denied until then.
  ///
  /// Parameters:
  /// * [cursor] - Opaque cursor from the previous page's next_cursor.
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults, same per-endpoint choice as GET /tokens).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ProjectListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ProjectListEnvelope>> listProjects({
    String? cursor,
    int? pageSize,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects';
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _queryParameters = <String, dynamic>{
      if (cursor != null)
        r'cursor':
            encodeQueryParameter(_serializers, cursor, const FullType(String)),
      if (pageSize != null)
        r'page_size':
            encodeQueryParameter(_serializers, pageSize, const FullType(int)),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    ProjectListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ProjectListEnvelope),
            ) as ProjectListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ProjectListEnvelope>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// listTasks
  /// List one project&#39;s tasks (Section 9.2; caller: Owner only). Default order is FR-TSK-05 canonical: &#x60;urgent &gt; high &gt; medium &gt; low&#x60;, then oldest &#x60;created_at&#x60; first (FIFO), then the task id&#39;s generation order (&#x60;T001&#x60; … &#x60;T999&#x60; &lt; &#x60;T1000&#x60;) — one deterministic sort computed in the database (NFR-09). Filters: repeat &#x60;state&#x60; for canonical values, single &#x60;priority&#x60;; archived tasks are excluded unless &#x60;include_archived&#x3D;true&#x60; (T19 default visibility). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60; *with the same filters* (pagination.md rule 1); &#x60;page_size&#x60; defaults to 25, clamped to 100. Results never cross the path project.
  ///
  /// Parameters:
  /// * [pid]
  /// * [cursor] - Opaque cursor from the previous page's next_cursor; valid only with the same filters it was issued under (pagination.md rule 1).
  /// * [includeArchived] - Include soft-archived tasks; default false — archived tasks are hidden from boards by default (Section 8.2 T19).
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults, same per-endpoint choice as GET /projects).
  /// * [priority] - FR-TSK-05 priority filter (single value).  * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
  /// * [state] - Canonical states to include; repeat for several (?state=draft&state=pending). Unknown values are VALIDATION_ERROR.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [TaskListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<TaskListEnvelope>> listTasks({
    required String pid,
    String? cursor,
    bool? includeArchived = false,
    int? pageSize,
    String? priority,
    BuiltList<String>? state,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/tasks'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _queryParameters = <String, dynamic>{
      if (cursor != null)
        r'cursor':
            encodeQueryParameter(_serializers, cursor, const FullType(String)),
      if (includeArchived != null)
        r'include_archived': encodeQueryParameter(
            _serializers, includeArchived, const FullType(bool)),
      if (pageSize != null)
        r'page_size':
            encodeQueryParameter(_serializers, pageSize, const FullType(int)),
      if (priority != null)
        r'priority': encodeQueryParameter(
            _serializers, priority, const FullType(String)),
      if (state != null)
        r'state': encodeCollectionQueryParameter<String>(
          _serializers,
          state,
          const FullType(BuiltList, [FullType(String)]),
          format: ListFormat.multi,
        ),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    TaskListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(TaskListEnvelope),
            ) as TaskListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<TaskListEnvelope>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// partialUpdateProject
  /// Partially update a project: &#x60;name&#x60;, &#x60;repo_path&#x60;, &#x60;default_branch&#x60;, &#x60;system_prompt_rules&#x60;, &#x60;active_status&#x60; (transitions among active | paused | archived — FR-PRJ-04; projects are never deleted). Unspecified fields keep their current values. The &#x60;id&#x60; is immutable (Section 7.3/7.4) and is rejected if sent. Caller: Owner only. Emits &#x60;project.updated&#x60; once WP-1.9&#39;s event helper exists.
  ///
  /// Parameters:
  /// * [pid]
  /// * [patchedProjectUpdate]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Project] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Project>> partialUpdateProject({
    required String pid,
    PatchedProjectUpdate? patchedProjectUpdate,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'PATCH',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(PatchedProjectUpdate);
      _bodyData = patchedProjectUpdate == null
          ? null
          : _serializers.serialize(patchedProjectUpdate, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Project? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Project),
            ) as Project;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Project>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// partialUpdateProjectPolicy
  /// Partially update the policy — the only supported way to change it (Section 12.5). Validation states exactly what Section 7.2 states: enums (&#x60;lease_extension_mode&#x60;, &#x60;merge_strategy&#x60;), positive durations/retries/thresholds, &#x60;auditor_min_confidence&#x60; 1-5, &#x60;max_concurrent_tasks&#x60; &gt;&#x3D; 0, non-empty branch prefix and glob lists when supplied; unknown fields are rejected, never ignored. Unspecified fields keep their current values. &#x60;branch_prefix&#x60; is the G-09 canonical prefix (default &#x60;feat/{PID}-&#x60;) applied when bridge branch names are derived. Caller: Owner only. Policy edits emit an audit event once WP-1.9&#39;s helper exists.
  ///
  /// Parameters:
  /// * [pid]
  /// * [patchedProjectPolicy]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ProjectPolicy] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ProjectPolicy>> partialUpdateProjectPolicy({
    required String pid,
    PatchedProjectPolicy? patchedProjectPolicy,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/policy'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'PATCH',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(PatchedProjectPolicy);
      _bodyData = patchedProjectPolicy == null
          ? null
          : _serializers.serialize(patchedProjectPolicy, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    ProjectPolicy? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ProjectPolicy),
            ) as ProjectPolicy;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ProjectPolicy>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// partialUpdateTask
  /// Partially update a task (FR-TSK-02 fields; caller: Owner only). The body must carry the &#x60;version&#x60; the client saw (FR-TSK-06): a match applies the change and increments &#x60;version&#x60;; a stale value answers VERSION_CONFLICT (409) so a drag-and-drop client never silently overwrites an agent&#39;s change. &#x60;state&#x60;, lease, merge and archive fields are not client-settable — they are rejected as unknown fields (the state machine of WP-1.5 owns &#x60;state&#x60;). &#x60;Idempotency-Key&#x60; replays a retried PATCH (ADR-012).
  ///
  /// Parameters:
  /// * [id]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of re-executing it; reusing it with a different request is an open point (headers.md) and executes normally.
  /// * [patchedTaskUpdate]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Task] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Task>> partialUpdateTask({
    required String id,
    String? idempotencyKey,
    PatchedTaskUpdate? patchedTaskUpdate,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
            .toString());
    final _options = Options(
      method: r'PATCH',
      headers: <String, dynamic>{
        if (idempotencyKey != null) r'Idempotency-Key': idempotencyKey,
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      contentType: 'application/json',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      const _type = FullType(PatchedTaskUpdate);
      _bodyData = patchedTaskUpdate == null
          ? null
          : _serializers.serialize(patchedTaskUpdate, specifiedType: _type);
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _options.compose(
          _dio.options,
          _path,
        ),
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    final _response = await _dio.request<Object>(
      _path,
      data: _bodyData,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Task? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Task),
            ) as Task;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Task>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// retrieveProject
  /// Read one project. Caller: Owner only — agent read-only access for a token&#39;s own project activates in WP-2.x and is denied until then. A malformed or unknown pid answers VALIDATION_ERROR (400): the catalog has no PROJECT_NOT_FOUND.
  ///
  /// Parameters:
  /// * [pid]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Project] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Project>> retrieveProject({
    required String pid,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Project? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Project),
            ) as Project;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Project>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// retrieveProjectManifest
  /// Download the project manifest (orchestrator.json) as an attachment — the Section 10.3 wire contract: schema_version 1, the allowlisted keys only, &#x60;auto_branch_prefix&#x60; from policy (G-09), &#x60;orchestrator_api&#x60; from server configuration (NFR-06), &#x60;audit_required_default&#x60; from policy. No secrets: safe to commit (FR-SEC-04). Validate against the published schemas/manifest.v1.json. Caller: Owner only — agents read their own project&#39;s manifest from the bridge&#39;s local file (Section 10.3), and endpoint access for them activates in WP-2.x. A malformed or unknown pid answers VALIDATION_ERROR (400).
  ///
  /// Parameters:
  /// * [pid]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [OrchestratorManifest] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<OrchestratorManifest>> retrieveProjectManifest({
    required String pid,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/manifest'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    OrchestratorManifest? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(OrchestratorManifest),
            ) as OrchestratorManifest;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<OrchestratorManifest>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// retrieveProjectPolicy
  /// Read the project&#39;s full policy with current values (Section 7.2 field names and documented defaults). Caller: Owner only — agent access activates in WP-2.x and is denied until then. A malformed or unknown pid answers VALIDATION_ERROR (400).
  ///
  /// Parameters:
  /// * [pid]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ProjectPolicy] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ProjectPolicy>> retrieveProjectPolicy({
    required String pid,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/policy'.replaceAll(
        '{' r'pid' '}',
        encodeQueryParameter(_serializers, pid, const FullType(String))
            .toString());
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    ProjectPolicy? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ProjectPolicy),
            ) as ProjectPolicy;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ProjectPolicy>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }

  /// retrieveTask
  /// Read one task by id (Section 9.2; caller: Owner only). Every Section 7.2 field is returned. A malformed id answers VALIDATION_ERROR (400) — the boundary check of Section 7.3; an unknown but well-formed id answers TASK_NOT_FOUND (404). Archived and completed tasks remain readable (MT-1.4-06).
  ///
  /// Parameters:
  /// * [id]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Task] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Task>> retrieveTask({
    required String id,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
            .toString());
    final _options = Options(
      method: r'GET',
      headers: <String, dynamic>{
        ...?headers,
      },
      extra: <String, dynamic>{
        'secure': <Map<String, String>>[
          {
            'type': 'http',
            'scheme': 'bearer',
            'name': 'bearerAuth',
          },
          {
            'type': 'apiKey',
            'name': 'sessionAuth',
            'keyName': 'sessionid',
            'where': '',
          },
        ],
        ...?extra,
      },
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Task? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Task),
            ) as Task;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Task>(
      data: _responseData,
      headers: _response.headers,
      isRedirect: _response.isRedirect,
      requestOptions: _response.requestOptions,
      redirects: _response.redirects,
      statusCode: _response.statusCode,
      statusMessage: _response.statusMessage,
      extra: _response.extra,
    );
  }
}
