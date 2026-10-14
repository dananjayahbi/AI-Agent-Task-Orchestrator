// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_start_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeStartRequest extends MergeStartRequest {
  @override
  final int? version;

  factory _$MergeStartRequest(
          [void Function(MergeStartRequestBuilder)? updates]) =>
      (MergeStartRequestBuilder()..update(updates))._build();

  _$MergeStartRequest._({this.version}) : super._();
  @override
  MergeStartRequest rebuild(void Function(MergeStartRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeStartRequestBuilder toBuilder() =>
      MergeStartRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeStartRequest && version == other.version;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'MergeStartRequest')
          ..add('version', version))
        .toString();
  }
}

class MergeStartRequestBuilder
    implements Builder<MergeStartRequest, MergeStartRequestBuilder> {
  _$MergeStartRequest? _$v;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  MergeStartRequestBuilder() {
    MergeStartRequest._defaults(this);
  }

  MergeStartRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _version = $v.version;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeStartRequest other) {
    _$v = other as _$MergeStartRequest;
  }

  @override
  void update(void Function(MergeStartRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeStartRequest build() => _build();

  _$MergeStartRequest _build() {
    final _$result = _$v ??
        _$MergeStartRequest._(
          version: version,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
