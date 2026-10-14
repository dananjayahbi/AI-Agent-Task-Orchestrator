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
import 'package:orchestrator_mobile/src/model/attachment.dart';
import 'package:orchestrator_mobile/src/model/attachment_content.dart';
import 'package:orchestrator_mobile/src/model/attachment_delete.dart';
import 'package:orchestrator_mobile/src/model/attachment_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/audit_report_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/audit_verdict_request.dart';
import 'package:orchestrator_mobile/src/model/audit_verdict_response.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_create.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/checkpoint_write_response.dart';
import 'package:orchestrator_mobile/src/model/claim_request.dart';
import 'package:orchestrator_mobile/src/model/claim_response.dart';
import 'package:orchestrator_mobile/src/model/dashboard_summary.dart';
import 'package:orchestrator_mobile/src/model/device_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/device_register_request.dart';
import 'package:orchestrator_mobile/src/model/device_register_response.dart';
import 'package:orchestrator_mobile/src/model/error_envelope.dart';
import 'package:orchestrator_mobile/src/model/event_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/login_request.dart';
import 'package:orchestrator_mobile/src/model/merge_queue_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/merge_result_request.dart';
import 'package:orchestrator_mobile/src/model/merge_result_response.dart';
import 'package:orchestrator_mobile/src/model/merge_start_request.dart';
import 'package:orchestrator_mobile/src/model/merge_start_response.dart';
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
import 'package:orchestrator_mobile/src/model/resolution_list_envelope.dart';
import 'package:orchestrator_mobile/src/model/resolution_patch.dart';
import 'package:orchestrator_mobile/src/model/resolution_submit.dart';
import 'package:orchestrator_mobile/src/model/resolution_write_response.dart';
import 'package:orchestrator_mobile/src/model/review_decision_request.dart';
import 'package:orchestrator_mobile/src/model/review_decision_response.dart';
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
  /// Atomically claim one task (Section 9.2 Agent-work row; caller: Agent — the token&#39;s scopes pick the Section 12.2 cell: coder for &#x60;pending&#x60; (T4), auditor for &#x60;to_be_audited&#x60; (T11)). One transaction takes the row with &#x60;FOR UPDATE SKIP LOCKED&#x60;, re-validates the declared &#x60;role&#x60; against the state plus the T4/T11 guards (project status, dependencies, &#x60;max_concurrent_tasks&#x60; for coders; auditor independence (&#x60;AUDITOR_SAME_AS_CODER&#x60;, G-20) and audit-lease availability for auditors), sets the Section 8.6 lease (policy duration, &#x60;lease_generation&#x60; + 1) and bumps &#x60;attempt_number&#x60; on coder claims only (FR-LEA-01/02; ADR-012 fencing; MT-3.3-01). 200 returns task details, the lease record (role &#x60;coder&#x60;|&#x60;auditor&#x60;) and the Section 10.6 rules block. Errors: TASK_ALREADY_CLAIMED, TASK_NOT_FOUND, TASK_STATE_CONFLICT, AUDITOR_SAME_AS_CODER, DEPENDENCY_UNMET, CONCURRENCY_LIMIT_REACHED (409); ROLE_NOT_PERMITTED, AUTH_FORBIDDEN_PROJECT (403) — all per the documented mapping. &#x60;Idempotency-Key&#x60; replays a retried claim without leasing twice (NFR-12).
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
  /// Create a project. The &#x60;PID&#x60; id is assigned server-side from the Section 7.3 database sequence — no client-supplied id is accepted (an &#x60;id&#x60; key is rejected as unknown). The default Project Policy (Section 7.2 defaults) is created as a pair (Section 7.1). Optional &#x60;policy_preset&#x60; (WP-3.1) seeds the new policy&#39;s three glob fields from a framework preset (django | nextjs | flutter); omitted &#x3D; stock Section 7.2 defaults. Caller: Owner only.
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
  /// Create a task (Section 9.2 Tasks row; Section 12.2 *Create draft tasks* caller: Owner, Decomposer agent role, Device — MT-3.8-01). T1&#39;s model-level step: the id is allocated server-side (&#x60;{PID}-T{index}&#x60;, Section 7.3), &#x60;state&#x60; starts at &#x60;draft&#x60;, &#x60;version&#x60; starts at 1 (FR-TSK-06), &#x60;audit_required&#x60; copies the project policy, and &#x60;target_scope&#x60; globs are validated against Section 12.3. Accepts the FR-TSK-02 field set only — &#x60;state&#x60;, &#x60;version&#x60;, &#x60;id&#x60;, lease/merge fields are rejected as unknown. Agents of every other role answer ROLE_NOT_PERMITTED (403). &#x60;Idempotency-Key&#x60; replays a retry without duplicating the task (ADR-012).
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

  /// deleteAttachment
  /// Delete one attachment (Section 9.2; caller: Owner only). Resolved conservatively against Section 16.3: on a completed or archived task the call answers 409 TASK_STATE_CONFLICT — the retention job owns those bytes (archive plus the configurable grace period, Section 12.4; OQ-10 default 30 days). On any earlier state the record is soft-deleted (&#x60;deleted_at&#x60; stamped) and the stored object is removed only when no other de-duplicated record shares its content key. &#x60;Idempotency-Key&#x60; replays a retried DELETE&#39;s response (ADR-012).
  ///
  /// Parameters:
  /// * [id]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same upload replays the original response instead of storing a second copy; reusing it with a different upload is an open point (headers.md) and executes normally.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AttachmentDelete] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AttachmentDelete>> deleteAttachment({
    required String id,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/attachments/{id}'.replaceAll(
        '{' r'id' '}',
        encodeQueryParameter(_serializers, id, const FullType(String))
            .toString());
    final _options = Options(
      method: r'DELETE',
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

    AttachmentDelete? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AttachmentDelete),
            ) as AttachmentDelete;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AttachmentDelete>(
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

  /// getResolutionPatch
  /// The stored unified patch for one resolution (Section 9.2 Submission row; caller: Agent / Owner). One response shape covers both Section 9.7 paths: patches up to the 5 MB inclusive cap serve their body (&#x60;diff_too_large&#x60; false), oversize patches serve the stats-and-file-list-only marker (&#x60;diff_too_large&#x60; true, &#x60;marker&#x60; &#x3D; \&quot;diff too large\&quot;) — a degraded path, never an error. sha256/size_bytes are the server-computed values from Section 7.2. The route embeds no PID, so the addressed project is checked against the token after role admission (ADR-004 zero-bleed): a foreign-project agent answers AUTH_FORBIDDEN_PROJECT (403); unknown resolution ids answer VALIDATION_ERROR (400) via the documented generic-NotFound mapping (no new codes).
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
  /// Returns a [Future] containing a [Response] with a [ResolutionPatch] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ResolutionPatch>> getResolutionPatch({
    required String id,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/resolutions/{id}/patch'.replaceAll(
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

    ResolutionPatch? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ResolutionPatch),
            ) as ResolutionPatch;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ResolutionPatch>(
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

  /// listAuditReports
  /// One task&#39;s Audit Reports, newest first (Section 9.2 Audit row; caller: Auditor / Owner — the review panel and mobile review sheet read surface, MT-3.3-04). Cursor pagination per pagination.md: &#x60;page_size&#x60; (default 25, maximum 100), the opaque &#x60;cursor&#x60; from the previous page&#39;s &#x60;next_cursor&#x60;, stable (created_at, id) ordering so inserts during paging never shift or duplicate rows. Reports accumulate per resolution across T12 audit retries (recorded reading). Empty tasks return an empty page. Coder agents and devices answer ROLE_NOT_PERMITTED (403), cross-project agent tokens AUTH_FORBIDDEN_PROJECT (403), unknown tasks TASK_NOT_FOUND (404).
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
  /// Returns a [Future] containing a [Response] with a [AuditReportListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AuditReportListEnvelope>> listAuditReports({
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
    final _path = r'/api/v1/tasks/{id}/audit-reports'.replaceAll(
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

    AuditReportListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AuditReportListEnvelope),
            ) as AuditReportListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AuditReportListEnvelope>(
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

  /// listMergePending
  /// Tasks awaiting a merge (Section 9.2 Merge queue row; caller: Merge Executor, Owner read-only — §12.2). The queue is every live task with &#x60;merge_status &#x3D; pending&#x60; in a carrier state (&#x60;in_human_review&#x60; from T15&#39;s approve, &#x60;to_be_audited&#x60; from the engine-approved T10/T13 branches — Section 8.1&#39;s sub-status, never a seventh state). Cursor pagination per pagination.md: &#x60;page_size&#x60; (default 25, maximum 100, clamped), the opaque &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60;, FIFO by task id so polling is stable. An agent token sees only its own project&#39;s queue (ADR-004 zero-bleed); the Owner sees every project. Coder/auditor/decomposer agents and devices answer ROLE_NOT_PERMITTED (403); anonymous AUTH_REQUIRED (401).
  ///
  /// Parameters:
  /// * [cursor] - Opaque cursor from the previous page's next_cursor; FIFO by task id so polling is stable (pagination.md rule 1).
  /// * [pageSize] - Items per page (default 25, maximum 100; values above the maximum are clamped — pagination.md documented defaults).
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [MergeQueueListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<MergeQueueListEnvelope>> listMergePending({
    String? cursor,
    int? pageSize,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/merge/pending';
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

    MergeQueueListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(MergeQueueListEnvelope),
            ) as MergeQueueListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<MergeQueueListEnvelope>(
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

  /// listResolutions
  /// One task&#39;s resolutions, newest first (Section 9.2 Submission row; caller: Agent / Owner — the FR-AUD-01 input the auditor flow reads). Cursor pagination per pagination.md: &#x60;page_size&#x60; (default 25, maximum 100), the opaque &#x60;cursor&#x60; from the previous page&#39;s &#x60;next_cursor&#x60;, stable (submitted_at, id) ordering so inserts during paging never shift or duplicate rows. Empty tasks return an empty page. Cross-project agent tokens answer AUTH_FORBIDDEN_PROJECT (403); unknown tasks TASK_NOT_FOUND (404).
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
  /// Returns a [Future] containing a [Response] with a [ResolutionListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ResolutionListEnvelope>> listResolutions({
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
    final _path = r'/api/v1/tasks/{id}/resolutions'.replaceAll(
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

    ResolutionListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ResolutionListEnvelope),
            ) as ResolutionListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ResolutionListEnvelope>(
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

  /// listTaskAttachments
  /// List one task&#39;s attachment descriptors (Section 9.2; caller: Owner or the project&#39;s agent token). Newest first (&#x60;created_at&#x60;, then id — stable, deterministic, pagination.md rule 2). Descriptors carry &#x60;id&#x60;, &#x60;filename&#x60;, &#x60;size&#x60;, &#x60;processing_status&#x60; plus FR-ATT-03&#39;s &#x60;token_count&#x60; and &#x60;short_description&#x60;, which are null until the WP-1.12 pipeline produces them. Pagination is cursor-based: pass &#x60;cursor&#x60; from the previous &#x60;next_cursor&#x60; *for this task only* (rule 1); &#x60;page_size&#x60; defaults to 25, clamped to 100. Soft-deleted attachments are excluded. Cross-project agent tokens answer AUTH_FORBIDDEN_PROJECT (403).
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
  /// Returns a [Future] containing a [Response] with a [AttachmentListEnvelope] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AttachmentListEnvelope>> listTaskAttachments({
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
    final _path = r'/api/v1/tasks/{id}/attachments'.replaceAll(
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

    AttachmentListEnvelope? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AttachmentListEnvelope),
            ) as AttachmentListEnvelope;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AttachmentListEnvelope>(
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
  /// List the project&#39;s offerable work (Section 9.2 Agent-work row; caller: Agent). &#x60;role&#x3D;coder&#x60; (default) lists &#x60;pending&#x60; tasks whose dependencies are completed; &#x60;role&#x3D;auditor&#x60; lists &#x60;to_be_audited&#x60; — never a mixed or wrong-state listing (MT-3.3-01; the matching T11 claim takes the auditor half). Archived tasks are hidden (T19), a non-active project returns an empty list (FR-PRJ-04), order is FR-TSK-05 canonical (priority, then oldest first), cursor-paginated. This read is deliberately non-locking: the locking select-and-claim twin is the claim-next service (Section 9.3).
  ///
  /// Parameters:
  /// * [pid]
  /// * [cursor] - Opaque cursor from the previous next_cursor; valid only with the same role/priority (pagination.md rule 1).
  /// * [pageSize] - Items per page (default 25, maximum 100; values above are clamped).
  /// * [priority] - FR-TSK-05 priority filter (single value).  * `urgent` - urgent * `high` - high * `medium` - medium * `low` - low
  /// * [role] - Which offer list to read: coder → pending (default); auditor → to_be_audited (T11's audit claim takes it — MT-3.3-01).  * `coder` - coder * `auditor` - auditor
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

  /// reportMergeResult
  /// Report one merge outcome (Section 9.2 Merge queue row; caller: Merge Executor — §12.2). &#x60;succeeded&#x60; dispatches T17 → &#x60;completed&#x60; + &#x60;merge_status &#x3D; merged&#x60; (ADR-008: completed only when the result is reported), carrying the required &#x60;sha&#x60; in the payload, the history note and the &#x60;merge.succeeded&#x60; event data (Section 7.2 has no sha column — the three carriers are the contract). &#x60;conflict&#x60;/&#x60;failed&#x60; dispatch T18 → &#x60;in_human_review&#x60; with &#x60;review_reason &#x3D; merge_conflict&#x60; (Section 8.4) and the Section 9.8 push, emitting &#x60;merge.failed&#x60;. Exactly one row applies: a repeat report on an exited task answers TASK_STATE_CONFLICT (409). &#x60;Idempotency-Key&#x60; replays a retried report with no second transition. Rejections: VALIDATION_ERROR (400), ROLE_NOT_PERMITTED / AUTH_FORBIDDEN_PROJECT (403), TASK_NOT_FOUND (404), TASK_STATE_CONFLICT / VERSION_CONFLICT (409), RATE_LIMITED (429).
  ///
  /// Parameters:
  /// * [task]
  /// * [mergeResultRequest]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second claim or applying a second merge result.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [MergeResultResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<MergeResultResponse>> reportMergeResult({
    required String task,
    required MergeResultRequest mergeResultRequest,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/merge/{task}/result'.replaceAll(
        '{' r'task' '}',
        encodeQueryParameter(_serializers, task, const FullType(String))
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
      const _type = FullType(MergeResultRequest);
      _bodyData =
          _serializers.serialize(mergeResultRequest, specifiedType: _type);
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

    MergeResultResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(MergeResultResponse),
            ) as MergeResultResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<MergeResultResponse>(
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

  /// retrieveAttachment
  /// Read one attachment descriptor by id (Section 9.2; caller: Owner or an agent token scoped to the attachment&#39;s project). &#x60;token_count&#x60; and &#x60;short_description&#x60; are null until the WP-1.12 pipeline fills them (FR-ATT-03/07). Foreign agent tokens answer AUTH_FORBIDDEN_PROJECT (403); unknown or malformed ids answer VALIDATION_ERROR (400 — the catalog has no attachment not-found code; recorded mapping).
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
  /// Returns a [Future] containing a [Response] with a [Attachment] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Attachment>> retrieveAttachment({
    required String id,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/attachments/{id}'.replaceAll(
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

    Attachment? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Attachment),
            ) as Attachment;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Attachment>(
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

  /// retrieveAttachmentContent
  /// Retrieve one attachment&#39;s content (Section 9.2; caller: Owner or an agent token scoped to the attachment&#39;s project). The &#x60;format&#x60; parameter follows the Section 9.5 retrieval table: &#x60;auto&#x60; (default) is text-safe — documents resolve to paginated &#x60;markdown&#x60;, images to &#x60;text_ocr&#x60; (OCR transcript plus layout description); &#x60;image_base64&#x60; serves the normalized image and answers ATTACHMENT_UNSUPPORTED_FORMAT (415) for non-images; &#x60;markdown&#x60; and &#x60;text_ocr&#x60; answer 415 where the attachment has no such representation. &#x60;page&#x60; is one-based (the pagination.md content exception): paginated responses carry &#x60;page_number&#x60;, &#x60;total_pages&#x60; and the page&#39;s token count so an agent can budget context; non-paginated responses omit them. Every delivered text value is prefixed with the untrusted-content banner (P10). Attachments not &#x60;ready&#x60; answer 409 ATTACHMENT_NOT_READY (&#x60;failed&#x60; includes the stored reason). Unknown &#x60;format&#x60;/&#x60;page&#x60; values and unknown query parameters answer VALIDATION_ERROR (400).
  ///
  /// Parameters:
  /// * [id]
  /// * [format] - Section 9.5 retrieval table: auto (default; text-safe — documents resolve to markdown, images to text_ocr), image_base64, text_ocr, markdown. Unknown values answer VALIDATION_ERROR.  * `auto` - auto * `image_base64` - image_base64 * `text_ocr` - text_ocr * `markdown` - markdown
  /// * [page] - One-based page for paginated formats (markdown; auto on documents — Section 9.5 pagination clause, the pagination.md content exception). Defaults to 1; out-of-range and non-integer values answer VALIDATION_ERROR. Ignored by the non-paginated formats.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AttachmentContent] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AttachmentContent>> retrieveAttachmentContent({
    required String id,
    String? format = 'auto',
    int? page = 1,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/attachments/{id}/content'.replaceAll(
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
      if (format != null)
        r'format':
            encodeQueryParameter(_serializers, format, const FullType(String)),
      if (page != null)
        r'page': encodeQueryParameter(_serializers, page, const FullType(int)),
    };

    final _response = await _dio.request<Object>(
      _path,
      options: _options,
      queryParameters: _queryParameters,
      cancelToken: cancelToken,
      onSendProgress: onSendProgress,
      onReceiveProgress: onReceiveProgress,
    );

    AttachmentContent? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AttachmentContent),
            ) as AttachmentContent;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AttachmentContent>(
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

  /// retrieveDashboardSummary
  /// Per-project Overview cards for the Home / Overview surfaces (Section 14.1; FR-MOB-01). Every registered project appears once, ordered by project id. &#x60;state_counts&#x60; carries all six canonical G-01 states (ADR-010), zero-filled, over the project&#39;s non-archived tasks (T19 default visibility). &#x60;velocity&#x60; counts the project&#39;s completions in the trailing 7-day window on the server clock (conservative documented default — the plan states no definition; this payload is authoritative and clients never recompute it). &#x60;active_agents&#x60; counts AgentSession rows with &#x60;ended_at&#x60; null. Single-resource GET — no pagination (pagination.md). Caller: Owner only (Section 9.2); agents and devices answer ROLE_NOT_PERMITTED, anonymous callers AUTH_REQUIRED.
  ///
  /// Parameters:
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [DashboardSummary] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<DashboardSummary>> retrieveDashboardSummary({
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/dashboard/summary';
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

    DashboardSummary? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(DashboardSummary),
            ) as DashboardSummary;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<DashboardSummary>(
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

  /// startMerge
  /// Claim one pending task for merging (Section 9.2 Merge queue row; caller: Merge Executor — §12.2). One transaction: verify the task is live, in a carrier state and still &#x60;merge_status &#x3D; pending&#x60; (anything else answers TASK_STATE_CONFLICT, 409 — a second executor&#39;s claim or an exited task changes nothing), optional &#x60;version&#x60; CAS (VERSION_CONFLICT, 409), then set &#x60;merging&#x60;, increment &#x60;version&#x60; and write the &#x60;merge.started&#x60; event (Section 9.6) — published after commit. Not a dispatch: Section 8.2 has no start row (recorded reading). &#x60;Idempotency-Key&#x60; replays a retried claim with no second event. Rejections: VALIDATION_ERROR (400), ROLE_NOT_PERMITTED / AUTH_FORBIDDEN_PROJECT (403), TASK_NOT_FOUND (404), TASK_STATE_CONFLICT / VERSION_CONFLICT (409), RATE_LIMITED (429).
  ///
  /// Parameters:
  /// * [task]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second claim or applying a second merge result.
  /// * [mergeStartRequest]
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [MergeStartResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<MergeStartResponse>> startMerge({
    required String task,
    String? idempotencyKey,
    MergeStartRequest? mergeStartRequest,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/merge/{task}/start'.replaceAll(
        '{' r'task' '}',
        encodeQueryParameter(_serializers, task, const FullType(String))
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
      const _type = FullType(MergeStartRequest);
      _bodyData = mergeStartRequest == null
          ? null
          : _serializers.serialize(mergeStartRequest, specifiedType: _type);
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

    MergeStartResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(MergeStartResponse),
            ) as MergeStartResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<MergeStartResponse>(
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

  /// submitAuditVerdict
  /// Store the auditor&#39;s proposal and delegate the outcome to the Policy Engine seam (Section 9.2 Audit row; caller: Auditor, current lease owner — §12.2). One transaction: verify the fencing pair (&#x60;session_id&#x60; + &#x60;lease_generation&#x60;) against the locked &#x60;to_be_audited&#x60; row, re-prove independence (&#x60;AUDITOR_SAME_AS_CODER&#x60;, G-20), persist the Audit Report (§7.2: evidence verbatim, confidence 1-5, proposed verdict), then dispatch exactly one row: T14 &#x60;audit_verdict_escalated&#x60; → &#x60;in_human_review&#x60; with an enumerated §8.4 reason (the fail-closed default until MT-3.4-07 installs the engine) or T13 &#x60;audit_verdict_pass&#x60; → &#x60;merge_status &#x3D; pending&#x60; (engine approval only — invariant 8.3.4: this endpoint never approves). 201 returns the report, the post-transition task identity, the trigger and the decision. &#x60;Idempotency-Key&#x60; replays a retried verdict with no second report and no second transition. Rejections: VALIDATION_ERROR (400), LEASE_NOT_OWNED (403), ROLE_NOT_PERMITTED (403), TASK_STATE_CONFLICT / LEASE_EXPIRED / AUDITOR_SAME_AS_CODER (409), TASK_NOT_FOUND (404).
  ///
  /// Parameters:
  /// * [id]
  /// * [auditVerdictRequest]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second Audit Report or firing a second transition.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [AuditVerdictResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<AuditVerdictResponse>> submitAuditVerdict({
    required String id,
    required AuditVerdictRequest auditVerdictRequest,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/audit-verdict'.replaceAll(
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
      const _type = FullType(AuditVerdictRequest);
      _bodyData =
          _serializers.serialize(auditVerdictRequest, specifiedType: _type);
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

    AuditVerdictResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(AuditVerdictResponse),
            ) as AuditVerdictResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<AuditVerdictResponse>(
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

  /// submitResolution
  /// Store the lease-owner agent&#39;s submission and fire exactly one Section 8.2 row (Section 9.2 Submission row; caller: Agent, lease owner — §12.2). One transaction: verify the fencing pair (&#x60;session_id&#x60; + &#x60;lease_generation&#x60;) against the locked row, parse the uploaded unified patch into the authoritative &#x60;changed_files&#x60;/&#x60;diff_summary&#x60; (bridge claims are provisional and replaced — Section 9.7), store the Task Resolution (one per attempt, Section 7.2) and its patch artifact (5 MB cap with the Section 9.7 stats-only degraded path), evaluate scope against &#x60;target_scope&#x60; through the single shared glob matcher (Section 12.3), then dispatch: out-of-scope → T8 &#x60;in_human_review&#x60; + &#x60;scope_violation&#x60;, self-flag → T8 + &#x60;self_flagged&#x60; (scope wins when both hold), clean + &#x60;audit_required&#x60; → T7 &#x60;to_be_audited&#x60;, &#x60;audit_required&#x60; false → the T10 policy seam (fail-closed escalate; approve only via the Policy Engine — Section 8.5). &#x60;Idempotency-Key&#x60; replays a retried submission with no second row and no second transition (NFR-12). Rejections: LEASE_NOT_OWNED (403), LEASE_EXPIRED/TASK_STATE_CONFLICT/SCOPE_VIOLATION (409), TASK_NOT_FOUND (404), AUTH_FORBIDDEN_PROJECT (403).
  ///
  /// Parameters:
  /// * [id]
  /// * [resolutionSubmit]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second resolution or firing a second transition.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ResolutionWriteResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ResolutionWriteResponse>> submitResolution({
    required String id,
    required ResolutionSubmit resolutionSubmit,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/resolution'.replaceAll(
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
      const _type = FullType(ResolutionSubmit);
      _bodyData =
          _serializers.serialize(resolutionSubmit, specifiedType: _type);
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

    ResolutionWriteResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ResolutionWriteResponse),
            ) as ResolutionWriteResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ResolutionWriteResponse>(
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

  /// submitReviewDecision
  /// Record one human review decision (Section 9.2 Review row; caller: Owner / Device — §12.2). &#x60;decision&#x60; is one of the three plan values; &#x60;version&#x60; is the optimistic-lock token (a stale value answers VERSION_CONFLICT, 409). **approve** (T15) requires the &#x60;resolution_id&#x60; the reviewer saw (Section 14.2 approve safety): the server compares it to the task&#39;s current-attempt resolution under the row lock and rejects an outdated binding with VERSION_CONFLICT and zero side effects (MT-3.6-04); a pass sets &#x60;merge_status &#x3D; pending&#x60; (the Section 8.1 sub-status WP-3.7&#39;s queue picks up) and records the decision. **request_changes** (T16) requires a &#x60;note&#x60; (VALIDATION_ERROR otherwise) which becomes the task&#39;s &#x60;latest_feedback&#x60; for the next coder, preserves &#x60;attempt_number&#x60; and returns the task to &#x60;pending&#x60;; **reassign** (T16) also returns to &#x60;pending&#x60; and clears the worker. Each decision writes the Transition row, the &#x60;review.decided&#x60; event (§9.6) and the Section 7.2 Review Decision record in one transaction (§8.2 rule 2). &#x60;Idempotency-Key&#x60; replays a retried decision without a second record or a second transition. Rejections: VALIDATION_ERROR (400), ROLE_NOT_PERMITTED / AUTH_FORBIDDEN_PROJECT (403), TASK_NOT_FOUND (404), TASK_STATE_CONFLICT / VERSION_CONFLICT (409).
  ///
  /// Parameters:
  /// * [id]
  /// * [reviewDecisionRequest]
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same request replays the original outcome instead of storing a second Audit Report or firing a second transition.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [ReviewDecisionResponse] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<ReviewDecisionResponse>> submitReviewDecision({
    required String id,
    required ReviewDecisionRequest reviewDecisionRequest,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/review'.replaceAll(
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
      const _type = FullType(ReviewDecisionRequest);
      _bodyData =
          _serializers.serialize(reviewDecisionRequest, specifiedType: _type);
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

    ReviewDecisionResponse? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(ReviewDecisionResponse),
            ) as ReviewDecisionResponse;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<ReviewDecisionResponse>(
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

  /// uploadAttachment
  /// Upload one attachment (Section 9.2; caller: Owner only — agents read, never upload). The multipart body carries the file part &#x60;file&#x60;; limits and the allowlist are Section 9.5&#39;s (25 MB per file, 10 per task, 100 MB total — configurable defaults), the MIME type is **sniffed from the content**, never taken from the extension or the declared type, and a mismatch is rejected (415 ATTACHMENT_UNSUPPORTED_FORMAT; oversize/over-count/over-total answer 400 VALIDATION_ERROR). Identical bytes already attached to the task de-duplicate onto the existing record (200 instead of 201 — one record, one stored object). The response is the FR-ATT-03 descriptor with processing_status &#x60;uploaded&#x60; (FR-ATT-07); &#x60;token_count&#x60; and &#x60;short_description&#x60; are null until the WP-1.12 pipeline fills them. &#x60;Idempotency-Key&#x60; replays a retried upload without duplicating (ADR-012). The pipeline enqueue hook hands the job to the Celery worker after commit (Section 9.9 \&quot;on upload\&quot;; MT-1.12-01 — the unit layer keeps a documented no-op seam).
  ///
  /// Parameters:
  /// * [id]
  /// * [id2] - Server-generated row identity (Section 7.2).
  /// * [taskId] - The owning task (Section 7.2).
  /// * [filename] - Client filename, path components stripped.
  /// * [mimeType] - The sniffed content type (Section 9.5 — never the declared one).
  /// * [size] - Stored size in bytes (Section 7.2 ``size_bytes``).
  /// * [isImage] - Whether the sniffed type is an image — drives the pipeline split (9.5).
  /// * [processingStatus] - FR-ATT-07 enum: uploaded | processing | ready | failed.
  /// * [failureReason] - Human-readable reason when processing_status is failed (FR-ATT-07 visible; Section 9.5 stage 5; null otherwise).
  /// * [tokenCount] - FR-ATT-03 token count — null until the WP-1.12 pipeline computes it.
  /// * [shortDescription] - FR-ATT-03 short description — null until the WP-1.12 pipeline produces it.
  /// * [createdAt] - Server upload time (P7).
  /// * [idempotencyKey] - Caller-derived key making retries safe (ADR-012; NFR-12). Reusing the key with the same upload replays the original response instead of storing a second copy; reusing it with a different upload is an open point (headers.md) and executes normally.
  /// * [cancelToken] - A [CancelToken] that can be used to cancel the operation
  /// * [headers] - Can be used to add additional headers to the request
  /// * [extras] - Can be used to add flags to the request
  /// * [validateStatus] - A [ValidateStatus] callback that can be used to determine request success based on the HTTP status of the response
  /// * [onSendProgress] - A [ProgressCallback] that can be used to get the send progress
  /// * [onReceiveProgress] - A [ProgressCallback] that can be used to get the receive progress
  ///
  /// Returns a [Future] containing a [Response] with a [Attachment] as data
  /// Throws [DioException] if API call or serialization fails
  Future<Response<Attachment>> uploadAttachment({
    required String id,
    required String id2,
    required String taskId,
    required String filename,
    required String mimeType,
    required int size,
    required bool isImage,
    required String processingStatus,
    String? failureReason,
    int? tokenCount,
    String? shortDescription,
    required DateTime createdAt,
    String? idempotencyKey,
    CancelToken? cancelToken,
    Map<String, dynamic>? headers,
    Map<String, dynamic>? extra,
    ValidateStatus? validateStatus,
    ProgressCallback? onSendProgress,
    ProgressCallback? onReceiveProgress,
  }) async {
    final _path = r'/api/v1/tasks/{id}/attachments'.replaceAll(
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
      contentType: 'multipart/form-data',
      validateStatus: validateStatus,
    );

    dynamic _bodyData;

    try {
      _bodyData = FormData.fromMap(<String, dynamic>{
        r'id': encodeFormParameter(_serializers, id2, const FullType(String)),
        r'task_id':
            encodeFormParameter(_serializers, taskId, const FullType(String)),
        r'filename':
            encodeFormParameter(_serializers, filename, const FullType(String)),
        r'mime_type':
            encodeFormParameter(_serializers, mimeType, const FullType(String)),
        r'size': encodeFormParameter(_serializers, size, const FullType(int)),
        r'is_image':
            encodeFormParameter(_serializers, isImage, const FullType(bool)),
        r'processing_status': encodeFormParameter(
            _serializers, processingStatus, const FullType(String)),
        r'failure_reason': encodeFormParameter(
            _serializers, failureReason, const FullType(String)),
        r'token_count':
            encodeFormParameter(_serializers, tokenCount, const FullType(int)),
        r'short_description': encodeFormParameter(
            _serializers, shortDescription, const FullType(String)),
        r'created_at': encodeFormParameter(
            _serializers, createdAt, const FullType(DateTime)),
      });
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

    Attachment? _responseData;

    try {
      final rawResponse = _response.data;
      _responseData = rawResponse == null
          ? null
          : _serializers.deserialize(
              rawResponse,
              specifiedType: const FullType(Attachment),
            ) as Attachment;
    } catch (error, stackTrace) {
      throw DioException(
        requestOptions: _response.requestOptions,
        response: _response,
        type: DioExceptionType.unknown,
        error: error,
        stackTrace: stackTrace,
      );
    }

    return Response<Attachment>(
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
