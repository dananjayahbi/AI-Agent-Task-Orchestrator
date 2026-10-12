// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'error_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ErrorEnvelope extends ErrorEnvelope {
  @override
  final CodeEnum code;
  @override
  final String message;
  @override
  final bool retryable;
  @override
  final BuiltMap<String, JsonObject?>? details;
  @override
  final String correlationId;

  factory _$ErrorEnvelope([void Function(ErrorEnvelopeBuilder)? updates]) =>
      (ErrorEnvelopeBuilder()..update(updates))._build();

  _$ErrorEnvelope._(
      {required this.code,
      required this.message,
      required this.retryable,
      this.details,
      required this.correlationId})
      : super._();
  @override
  ErrorEnvelope rebuild(void Function(ErrorEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ErrorEnvelopeBuilder toBuilder() => ErrorEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ErrorEnvelope &&
        code == other.code &&
        message == other.message &&
        retryable == other.retryable &&
        details == other.details &&
        correlationId == other.correlationId;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, code.hashCode);
    _$hash = $jc(_$hash, message.hashCode);
    _$hash = $jc(_$hash, retryable.hashCode);
    _$hash = $jc(_$hash, details.hashCode);
    _$hash = $jc(_$hash, correlationId.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ErrorEnvelope')
          ..add('code', code)
          ..add('message', message)
          ..add('retryable', retryable)
          ..add('details', details)
          ..add('correlationId', correlationId))
        .toString();
  }
}

class ErrorEnvelopeBuilder
    implements Builder<ErrorEnvelope, ErrorEnvelopeBuilder> {
  _$ErrorEnvelope? _$v;

  CodeEnum? _code;
  CodeEnum? get code => _$this._code;
  set code(CodeEnum? code) => _$this._code = code;

  String? _message;
  String? get message => _$this._message;
  set message(String? message) => _$this._message = message;

  bool? _retryable;
  bool? get retryable => _$this._retryable;
  set retryable(bool? retryable) => _$this._retryable = retryable;

  MapBuilder<String, JsonObject?>? _details;
  MapBuilder<String, JsonObject?> get details =>
      _$this._details ??= MapBuilder<String, JsonObject?>();
  set details(MapBuilder<String, JsonObject?>? details) =>
      _$this._details = details;

  String? _correlationId;
  String? get correlationId => _$this._correlationId;
  set correlationId(String? correlationId) =>
      _$this._correlationId = correlationId;

  ErrorEnvelopeBuilder() {
    ErrorEnvelope._defaults(this);
  }

  ErrorEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _code = $v.code;
      _message = $v.message;
      _retryable = $v.retryable;
      _details = $v.details?.toBuilder();
      _correlationId = $v.correlationId;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ErrorEnvelope other) {
    _$v = other as _$ErrorEnvelope;
  }

  @override
  void update(void Function(ErrorEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ErrorEnvelope build() => _build();

  _$ErrorEnvelope _build() {
    _$ErrorEnvelope _$result;
    try {
      _$result = _$v ??
          _$ErrorEnvelope._(
            code: BuiltValueNullFieldError.checkNotNull(
                code, r'ErrorEnvelope', 'code'),
            message: BuiltValueNullFieldError.checkNotNull(
                message, r'ErrorEnvelope', 'message'),
            retryable: BuiltValueNullFieldError.checkNotNull(
                retryable, r'ErrorEnvelope', 'retryable'),
            details: _details?.build(),
            correlationId: BuiltValueNullFieldError.checkNotNull(
                correlationId, r'ErrorEnvelope', 'correlationId'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'details';
        _details?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ErrorEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
