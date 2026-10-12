// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'error_envelope_body.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ErrorEnvelopeBody extends ErrorEnvelopeBody {
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

  factory _$ErrorEnvelopeBody(
          [void Function(ErrorEnvelopeBodyBuilder)? updates]) =>
      (ErrorEnvelopeBodyBuilder()..update(updates))._build();

  _$ErrorEnvelopeBody._(
      {required this.code,
      required this.message,
      required this.retryable,
      this.details,
      required this.correlationId})
      : super._();
  @override
  ErrorEnvelopeBody rebuild(void Function(ErrorEnvelopeBodyBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ErrorEnvelopeBodyBuilder toBuilder() =>
      ErrorEnvelopeBodyBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ErrorEnvelopeBody &&
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
    return (newBuiltValueToStringHelper(r'ErrorEnvelopeBody')
          ..add('code', code)
          ..add('message', message)
          ..add('retryable', retryable)
          ..add('details', details)
          ..add('correlationId', correlationId))
        .toString();
  }
}

class ErrorEnvelopeBodyBuilder
    implements Builder<ErrorEnvelopeBody, ErrorEnvelopeBodyBuilder> {
  _$ErrorEnvelopeBody? _$v;

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

  ErrorEnvelopeBodyBuilder() {
    ErrorEnvelopeBody._defaults(this);
  }

  ErrorEnvelopeBodyBuilder get _$this {
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
  void replace(ErrorEnvelopeBody other) {
    _$v = other as _$ErrorEnvelopeBody;
  }

  @override
  void update(void Function(ErrorEnvelopeBodyBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ErrorEnvelopeBody build() => _build();

  _$ErrorEnvelopeBody _build() {
    _$ErrorEnvelopeBody _$result;
    try {
      _$result = _$v ??
          _$ErrorEnvelopeBody._(
            code: BuiltValueNullFieldError.checkNotNull(
                code, r'ErrorEnvelopeBody', 'code'),
            message: BuiltValueNullFieldError.checkNotNull(
                message, r'ErrorEnvelopeBody', 'message'),
            retryable: BuiltValueNullFieldError.checkNotNull(
                retryable, r'ErrorEnvelopeBody', 'retryable'),
            details: _details?.build(),
            correlationId: BuiltValueNullFieldError.checkNotNull(
                correlationId, r'ErrorEnvelopeBody', 'correlationId'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'details';
        _details?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ErrorEnvelopeBody', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
