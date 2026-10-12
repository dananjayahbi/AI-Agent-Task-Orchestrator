// ignore_for_file: constant_identifier_names, no_leading_underscores_for_local_identifiers, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
//
// AUTO-GENERATED FILE, DO NOT MODIFY!
//

import 'dart:async';

import 'package:built_value/json_object.dart';
import 'package:built_value/serializer.dart';
import 'package:dio/dio.dart';

import 'dart:typed_data';
import 'package:built_collection/built_collection.dart';
import 'package:orchestrator_mobile/src/api_util.dart';
import 'package:orchestrator_mobile/src/model/agent_session.dart';
import 'package:orchestrator_mobile/src/model/agent_session_create.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_request.dart';
import 'package:orchestrator_mobile/src/model/agent_token_issue_response.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_create.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_write_response.dart';
import 'package:orchestrator_mobile/src/model/claim_request.dart';
import 'package:orchestrator_mobile/src/model/claim_response.dart';
import 'package:orchestrator_mobile/src/model/device_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/device_register_request.dart';
import 'package:orchestrator_mobile/src/model/device_register_response.dart';
import 'package:orchestrator_mobile/src/model/error_envelope.dart';
import 'package:orchestrator_mobile/src/model/event_list_envelope.dart';
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
import 'package:orchestrator_mobile/src/model/release_request.dart';
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
  /// Register a device after Owner login (Section 9.2 Devices row; Section 12.2). Creates the Device row and its &#x60;kind &#x3D; device&#x60; API Token atomically; the plaintext &#x60;token&#x60; is returned exactly once — store it in platform secure storage (Section 12.2). &#x60;Idempotency-Key&#x60; replays a retried registration instead of duplicating the device (ADR-012).
  ///
  /// Parameters:
  /// * [deviceRegisterRequest]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original 201 outcome — the same device id and token material — instead of registering a second device; reuse with a different request is an open point (headers.md) and executes normally.
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
    String? idempotencyKey,
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

  /// apiV1DevicesRetrieve
  /// List the caller&#39;s registered devices as metadata (no push_token, no token material) — the Section 13.1 account settings surface. Sort: id descending (newest first). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;; &#x60;page_size&#x60; defaults to 25 and is clamped to 100. Revoked devices stay listed with &#x60;revoked_at&#x60; set so settings can show history.
  ///
  /// Parameters:
  /// * [cursor] - Opaque cursor from the previous page's next_cursor.
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [DeviceListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<DeviceListEnvelope>> apiV1DevicesRetrieve({
    String? cursor,
    int? pageSize,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/devices';
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

    DeviceListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(DeviceListEnvelope),
            ) as DeviceListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<DeviceListEnvelope>(
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

  /// apiV1EventsRetrieve
  /// Event history (Section 9.6 envelope per item). Sort: id ascending (chronological — the monotonic SSE id order). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;; &#x60;page_size&#x60; defaults to 25 and is clamped to 100. Filters: &#x60;project&#x60;, &#x60;task&#x60; (Section 9.6 names).
  ///
  /// Parameters:
  /// * [cursor] - Opaque cursor from the previous page's next_cursor.
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults).
  /// * [project] - Only events for this project id (PID + five digits, Section 7.3).
  /// * [task] - Only events for this task id ({PID}-T{index}, Section 7.3).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [EventListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<EventListEnvelope>> apiV1EventsRetrieve({
    String? cursor,
    int? pageSize,
    String? project,
    String? task,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/events';
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
      if (project != null)
        r'project':
            encodeQueryParameter(_serializers, project, const FullType(String)),
      if (task != null)
        r'task':
            encodeQueryParameter(_serializers, task, const FullType(String)),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    EventListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(EventListEnvelope),
            ) as EventListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<EventListEnvelope>(
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

  /// apiV1EventsStreamRetrieve
  /// Server-Sent Events feed of Section 9.6 envelopes (&#x60;id:&#x60; carries the monotonic event id; &#x60;data:&#x60; carries the envelope JSON; comment lines are heartbeats and carry no id). Filters: &#x60;project&#x60;, &#x60;task&#x60;, fixed at connect. Resume: send the last received id as the &#x60;Last-Event-ID&#x60; header (or &#x60;last_event_id&#x60; query parameter) to replay missed events before switching to live. Authentication: owner session or device bearer token — agents never subscribe (Section 12.2).
  ///
  /// Parameters:
  /// * [project] - Only events for this project id (PID + five digits, Section 7.3).
  /// * [task] - Only events for this task id ({PID}-T{index}, Section 7.3).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Uint8List] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Uint8List>> apiV1EventsStreamRetrieve({
    String? project,
    String? task,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/events/stream';
    final _options = Options(
      method: r'GET',
      responseType: ResponseType.bytes,
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
      if (project != null)
        r'project':
            encodeQueryParameter(_serializers, project, const FullType(String)),
      if (task != null)
        r'task':
            encodeQueryParameter(_serializers, task, const FullType(String)),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    Uint8List? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null ? null : rawResponse as Uint8List;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Uint8List>(
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

  /// claimTask
  /// Atomically claim a pending task (Section 9.2 Agent-work row; caller: Agent coder). One transaction takes the row with &#x60;FOR UPDATE SKIP LOCKED&#x60;, re-validates state, project status, dependencies and &#x60;max_concurrent_tasks&#x60; inside the lock, sets the Section 8.6 lease and bumps &#x60;lease_generation&#x60; and &#x60;attempt_number&#x60; (FR-LEA-01/02; ADR-012 fencing). 200 returns task details, the lease record and the Section 10.6 rules block. Errors: TASK_ALREADY_CLAIMED, TASK_NOT_FOUND, TASK_STATE_CONFLICT, DEPENDENCY_UNMET, CONCURRENCY_LIMIT_REACHED, AUTH_FORBIDDEN_PROJECT — all 409/404/403 per the documented mapping. &#x60;Idempotency-Key&#x60; replays a retried claim without leasing twice (NFR-12).
  ///
  /// Parameters:
  /// * [id]
  /// * [claimRequest]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of executing the claim/release again.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ClaimResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ClaimResponse>> claimTask({
    required String id,
    required ClaimRequest claimRequest,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/claim'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
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
      const _type = FullType(ClaimRequest);
      _bodyData = _serializers.serialize(claimRequest, specifiedType: _type);
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

    ClaimResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ClaimResponse),
            ) as ClaimResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ClaimResponse>(
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

  /// createCheckpoint
  /// Store one agent checkpoint and extend the lease (Section 9.2 Progress row; caller: Agent lease holder; Section 6.5 Flow B). One transaction verifies the fencing pair (&#x60;session_id&#x60; + &#x60;lease_generation&#x60;) against the locked row — a stale generation or dead lease answers LEASE_EXPIRED (409, stop and re-claim per Section 10.5), a foreign session LEASE_NOT_OWNED (403) — then stores the row (server timestamp; &#x60;attempt_number&#x60; copied at write time), applies Section 8.6&#39;s min(now + duration, acquired + cap) extension, emits &#x60;task.checkpoint&#x60; in-transaction, and returns the new &#x60;lease_expires_at&#x60; (plus &#x60;capped&#x60;, so the bridge can surface submit-or-release guidance). &#x60;kind&#x60; gates extension (OQ-04 recorded reading): progress/system always, liveness only under the project&#39;s checkpoint_and_liveness mode. &#x60;Idempotency-Key&#x60; replays a retried checkpoint without a duplicate row or a double extension (NFR-12).
  ///
  /// Parameters:
  /// * [id]
  /// * [checkpointCreate]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second checkpoint or double-extending the lease.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [CheckpointWriteResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<CheckpointWriteResponse>> createCheckpoint({
    required String id,
    required CheckpointCreate checkpointCreate,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/checkpoints'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
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
      const _type = FullType(CheckpointCreate);
      _bodyData =
          _serializers.serialize(checkpointCreate, specifiedType: _type);
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

    CheckpointWriteResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(CheckpointWriteResponse),
            ) as CheckpointWriteResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<CheckpointWriteResponse>(
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

  /// endAgentSession
  /// End an agent session (Section 9.2 Sessions row; caller: Bridge). Sets &#x60;ended_at&#x60; exactly once; repeating the call returns the same row unchanged (best-effort shutdown calls must be safe). The session&#39;s project must match the token&#39;s scope (AUTH_FORBIDDEN_PROJECT otherwise); an unknown id answers the standard no-catalog-code mapping (VALIDATION_ERROR, 400). &#x60;Idempotency-Key&#x60; replays a retried end.
  ///
  /// Parameters:
  /// * [id]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of opening a second session.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AgentSession] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AgentSession>> endAgentSession({
    required String id,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/agent-sessions/{id}/end'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
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
      validateStatus: validateStatus,
    );

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    AgentSession? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AgentSession),
            ) as AgentSession;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AgentSession>(
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

  /// listCheckpoints
  /// One task&#39;s checkpoint history, newest first (Section 9.2 Progress row; caller: Agent / Owner). Cursor pagination per WP-0.5-04: &#x60;page_size&#x60; (default 25, maximum 100), the opaque &#x60;cursor&#x60; from the previous page&#39;s &#x60;next_cursor&#x60;, stable (timestamp, id) ordering so inserts during paging never shift or duplicate rows. Empty tasks return an empty page, not an error. Cross-project agent tokens answer AUTH_FORBIDDEN_PROJECT (403); unknown tasks TASK_NOT_FOUND (404). History/backfill only — live updates are the WP-1.10 &#x60;task.checkpoint&#x60; event stream.
  ///
  /// Parameters:
  /// * [id]
  /// * [cursor] - Opaque cursor from the previous page's next_cursor; valid only for this task's listing (pagination.md rule 1).
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults, same per-endpoint choice as the other list routes).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [CheckpointListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<CheckpointListEnvelope>> listCheckpoints({
    required String id,
    String? cursor,
    int? pageSize,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/checkpoints'.replaceAll(
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

    CheckpointListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(CheckpointListEnvelope),
            ) as CheckpointListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<CheckpointListEnvelope>(
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
  /// List registered projects. Sort: project id ascending — PID generation order, i.e. creation order (zero-padded Section 7.3 ids make lexicographic order deterministic; pagination.md rule 2). Pagination: cursor-based — pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;; &#x60;page_size&#x60; defaults to 25, clamped to 100. Caller: Owner only — the list spans every project, so agent tokens are refused here (ROLE_NOT_PERMITTED); an agent reads its own project through &#x60;GET /projects/{pid}&#x60; instead.
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

  /// listWork
  /// List the project&#39;s offerable work (Section 9.2 Agent-work row; caller: Agent). &#x60;role&#x3D;coder&#x60; (default) lists &#x60;pending&#x60; tasks whose dependencies are completed; &#x60;role&#x3D;auditor&#x60; lists &#x60;to_be_audited&#x60; (the audit claim arrives with WP-3.3). Archived tasks are hidden (T19), a non-active project returns an empty list (FR-PRJ-04), order is FR-TSK-05 canonical (priority, then oldest first), cursor-paginated. This read is deliberately non-locking: the locking select-and-claim twin is the claim-next service (Section 9.3).
  ///
  /// Parameters:
  /// * [pid]
  /// * [cursor] - Opaque cursor from the previous next_cursor; valid only with the same role/priority (pagination.md rule 1).
  /// * [pageSize] - Items per page (default 25, maximum 100; values above are clamped).
  /// * [priority] - FR-TSK-05 priority filter (single value).  * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
  /// * [role] - Which offer list to read: coder → pending (default); auditor → to_be_audited (the audit claim itself is WP-3.3's T11).  * `coder` - coder * `auditor` - auditor
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [TaskListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<TaskListEnvelope>> listWork({
    required String pid,
    String? cursor,
    int? pageSize,
    String? priority,
    String? role = 'coder',
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/projects/{pid}/work'.replaceAll(
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
      if (pageSize != null)
        r'page_size':
            encodeQueryParameter(_serializers, pageSize, const FullType(int)),
      if (priority != null)
        r'priority': encodeQueryParameter(
            _serializers, priority, const FullType(String)),
      if (role != null)
        r'role':
            encodeQueryParameter(_serializers, role, const FullType(String)),
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

  /// openAgentSession
  /// Open an agent session (Section 9.2 Sessions row; caller: Bridge). The session id is bridge-issued and unguessable (G-18) and travels in the body; &#x60;project_id&#x60; and &#x60;token_id&#x60; are taken from the authenticated agent token — never from the payload (ADR-004; a body &#x60;project_id&#x60; is rejected as an unknown field). &#x60;capability&#x60; defaults to &#x60;unknown&#x60; (Section 10.4); &#x60;transport&#x60; is one of Section 10.2&#39;s run modes. 201 returns the Section 7.2 row; a duplicate id answers VALIDATION_ERROR; &#x60;Idempotency-Key&#x60; replays a retried open without creating a second row.
  ///
  /// Parameters:
  /// * [agentSessionCreate]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of opening a second session.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AgentSession] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AgentSession>> openAgentSession({
    required AgentSessionCreate agentSessionCreate,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/agent-sessions';
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
      const _type = FullType(AgentSessionCreate);
      _bodyData =
          _serializers.serialize(agentSessionCreate, specifiedType: _type);
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

    AgentSession? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AgentSession),
            ) as AgentSession;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AgentSession>(
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
  /// Partially update a project: &#x60;name&#x60;, &#x60;repo_path&#x60;, &#x60;default_branch&#x60;, &#x60;system_prompt_rules&#x60;, &#x60;active_status&#x60; (transitions among active | paused | archived — FR-PRJ-04; projects are never deleted). Unspecified fields keep their current values. The &#x60;id&#x60; is immutable (Section 7.3/7.4) and is rejected if sent. Caller: Owner only. Emits &#x60;project.updated&#x60; (Section 9.6) inside the update transaction.
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
  /// Partially update the policy — the only supported way to change it (Section 12.5). Validation states exactly what Section 7.2 states: enums (&#x60;lease_extension_mode&#x60;, &#x60;merge_strategy&#x60;), positive durations/retries/thresholds, &#x60;auditor_min_confidence&#x60; 1-5, &#x60;max_concurrent_tasks&#x60; &gt;&#x3D; 0, non-empty branch prefix and glob lists when supplied; unknown fields are rejected, never ignored. Unspecified fields keep their current values. &#x60;branch_prefix&#x60; is the G-09 canonical prefix (default &#x60;feat/{PID}-&#x60;) applied when bridge branch names are derived. Caller: Owner only. Policy edits emit a &#x60;project.updated&#x60; event (Section 9.6) inside the update transaction.
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
  /// Partially update a task (FR-TSK-02 fields; caller: Owner only). The body must carry the &#x60;version&#x60; the client saw (FR-TSK-06): a match applies the change and increments &#x60;version&#x60;; a stale value answers VERSION_CONFLICT (409) so a drag-and-drop client never silently overwrites an agent&#39;s change. &#x60;state&#x60;, lease, merge and archive fields are not client-settable — they are rejected as unknown fields (the state machine of WP-1.5 owns &#x60;state&#x60;). &#x60;Idempotency-Key&#x60; replays a retried PATCH (ADR-012). Refused with TASK_STATE_CONFLICT (409) while the row is &#x60;completed&#x60; (FR-TSK-08 read-only; Section 7.4 rule 3) or archived — both stay fully readable by id and in lists (MT-1.4-06).
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

  /// releaseTask
  /// Voluntarily release a claimed task back to &#x60;pending&#x60; (Section 9.2; Section 8.2 T6 — actors C, O). No &#x60;failure_retry_count&#x60; increment (FR-LEA-06); &#x60;attempt_number&#x60; is preserved. Agent callers must carry &#x60;session_id&#x60; and &#x60;lease_generation&#x60; (ADR-012): a foreign session answers LEASE_NOT_OWNED, a stale generation or dead lease LEASE_EXPIRED. An Owner session applies the documented override without the fencing pair. Optional &#x60;reason&#x60; lands on the Transition note; optional &#x60;version&#x60; enables the FR-TSK-06 stale-version check. 200 returns the updated task.
  ///
  /// Parameters:
  /// * [id]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of executing the claim/release again.
  /// * [releaseRequest]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Task] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Task>> releaseTask({
    required String id,
    String? idempotencyKey,
    ReleaseRequest? releaseRequest,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/release'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
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
      const _type = FullType(ReleaseRequest);
      _bodyData = releaseRequest == null
          ? null
          : _serializers.serialize(releaseRequest, specifiedType: _type);
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
  /// Read one project. Caller: Owner or an agent token scoped to this project (Section 9.2: agents read-only for own project); other agent tokens answer AUTH_FORBIDDEN_PROJECT (403) and devices ROLE_NOT_PERMITTED. A malformed or unknown pid answers VALIDATION_ERROR (400): the catalog has no PROJECT_NOT_FOUND.
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
  /// Download the project manifest (orchestrator.json) as an attachment — the Section 10.3 wire contract: schema_version 1, the allowlisted keys only, &#x60;auto_branch_prefix&#x60; from policy (G-09), &#x60;orchestrator_api&#x60; from server configuration (NFR-06), &#x60;audit_required_default&#x60; from policy. No secret values: safe to commit (FR-SEC-04). Validate against the published schemas/manifest.v1.json. Caller: Owner only — agents read their own project&#39;s manifest from the bridge&#39;s local file (Section 10.3), and endpoint access for them activates in WP-2.x. A malformed or unknown pid answers VALIDATION_ERROR (400).
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
  /// Read the project&#39;s full policy with current values (Section 7.2 field names and documented defaults). Caller: Owner or an agent token scoped to this project (Section 9.2: agents read-only for own project); foreign agent tokens answer AUTH_FORBIDDEN_PROJECT and devices ROLE_NOT_PERMITTED. A malformed or unknown pid answers VALIDATION_ERROR (400).
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
  /// Read one task by id (Section 9.2). Caller: Owner or an agent token scoped to the task&#39;s project — the row the bridge&#39;s &#x60;get_task_details&#x60; tool serves (Section 10.5); foreign agent tokens answer AUTH_FORBIDDEN_PROJECT (403) and devices ROLE_NOT_PERMITTED. Every Section 7.2 field is returned. A malformed id answers VALIDATION_ERROR (400) — the boundary check of Section 7.3; an unknown but well-formed id answers TASK_NOT_FOUND (404). Archived and completed tasks remain readable (MT-1.4-06).
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
