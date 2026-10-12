// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'claim_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ClaimRequest extends ClaimRequest {
  @override
  final String sessionId;
  @override
  final String workerAgentId;

  factory _$ClaimRequest([void Function(ClaimRequestBuilder)? updates]) =>
      (ClaimRequestBuilder()..update(updates))._build();

  _$ClaimRequest._({required this.sessionId, required this.workerAgentId})
      : super._();
  @override
  ClaimRequest rebuild(void Function(ClaimRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ClaimRequestBuilder toBuilder() => ClaimRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ClaimRequest &&
        sessionId == other.sessionId &&
        workerAgentId == other.workerAgentId;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, workerAgentId.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ClaimRequest')
          ..add('sessionId', sessionId)
          ..add('workerAgentId', workerAgentId))
        .toString();
  }
}

class ClaimRequestBuilder
    implements Builder<ClaimRequest, ClaimRequestBuilder> {
  _$ClaimRequest? _$v;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  String? _workerAgentId;
  String? get workerAgentId => _$this._workerAgentId;
  set workerAgentId(String? workerAgentId) =>
      _$this._workerAgentId = workerAgentId;

  ClaimRequestBuilder() {
    ClaimRequest._defaults(this);
  }

  ClaimRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _sessionId = $v.sessionId;
      _workerAgentId = $v.workerAgentId;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ClaimRequest other) {
    _$v = other as _$ClaimRequest;
  }

  @override
  void update(void Function(ClaimRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ClaimRequest build() => _build();

  _$ClaimRequest _build() {
    final _$result = _$v ??
        _$ClaimRequest._(
          sessionId: BuiltValueNullFieldError.checkNotNull(
              sessionId, r'ClaimRequest', 'sessionId'),
          workerAgentId: BuiltValueNullFieldError.checkNotNull(
              workerAgentId, r'ClaimRequest', 'workerAgentId'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
