// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'release_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ReleaseRequest extends ReleaseRequest {
  @override
  final String? sessionId;
  @override
  final int? leaseGeneration;
  @override
  final String? reason;
  @override
  final int? version;

  factory _$ReleaseRequest([void Function(ReleaseRequestBuilder)? updates]) =>
      (ReleaseRequestBuilder()..update(updates))._build();

  _$ReleaseRequest._(
      {this.sessionId, this.leaseGeneration, this.reason, this.version})
      : super._();
  @override
  ReleaseRequest rebuild(void Function(ReleaseRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ReleaseRequestBuilder toBuilder() => ReleaseRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ReleaseRequest &&
        sessionId == other.sessionId &&
        leaseGeneration == other.leaseGeneration &&
        reason == other.reason &&
        version == other.version;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, sessionId.hashCode);
    _$hash = $jc(_$hash, leaseGeneration.hashCode);
    _$hash = $jc(_$hash, reason.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ReleaseRequest')
          ..add('sessionId', sessionId)
          ..add('leaseGeneration', leaseGeneration)
          ..add('reason', reason)
          ..add('version', version))
        .toString();
  }
}

class ReleaseRequestBuilder
    implements Builder<ReleaseRequest, ReleaseRequestBuilder> {
  _$ReleaseRequest? _$v;

  String? _sessionId;
  String? get sessionId => _$this._sessionId;
  set sessionId(String? sessionId) => _$this._sessionId = sessionId;

  int? _leaseGeneration;
  int? get leaseGeneration => _$this._leaseGeneration;
  set leaseGeneration(int? leaseGeneration) =>
      _$this._leaseGeneration = leaseGeneration;

  String? _reason;
  String? get reason => _$this._reason;
  set reason(String? reason) => _$this._reason = reason;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  ReleaseRequestBuilder() {
    ReleaseRequest._defaults(this);
  }

  ReleaseRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _sessionId = $v.sessionId;
      _leaseGeneration = $v.leaseGeneration;
      _reason = $v.reason;
      _version = $v.version;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ReleaseRequest other) {
    _$v = other as _$ReleaseRequest;
  }

  @override
  void update(void Function(ReleaseRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ReleaseRequest build() => _build();

  _$ReleaseRequest _build() {
    final _$result = _$v ??
        _$ReleaseRequest._(
          sessionId: sessionId,
          leaseGeneration: leaseGeneration,
          reason: reason,
          version: version,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
