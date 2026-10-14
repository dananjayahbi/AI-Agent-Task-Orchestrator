// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_result_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeResultRequest extends MergeResultRequest {
  @override
  final ResultEnum result;
  @override
  final String? sha;
  @override
  final String? details;
  @override
  final int? version;

  factory _$MergeResultRequest(
          [void Function(MergeResultRequestBuilder)? updates]) =>
      (MergeResultRequestBuilder()..update(updates))._build();

  _$MergeResultRequest._(
      {required this.result, this.sha, this.details, this.version})
      : super._();
  @override
  MergeResultRequest rebuild(
          void Function(MergeResultRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeResultRequestBuilder toBuilder() =>
      MergeResultRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeResultRequest &&
        result == other.result &&
        sha == other.sha &&
        details == other.details &&
        version == other.version;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, result.hashCode);
    _$hash = $jc(_$hash, sha.hashCode);
    _$hash = $jc(_$hash, details.hashCode);
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'MergeResultRequest')
          ..add('result', result)
          ..add('sha', sha)
          ..add('details', details)
          ..add('version', version))
        .toString();
  }
}

class MergeResultRequestBuilder
    implements Builder<MergeResultRequest, MergeResultRequestBuilder> {
  _$MergeResultRequest? _$v;

  ResultEnum? _result;
  ResultEnum? get result => _$this._result;
  set result(ResultEnum? result) => _$this._result = result;

  String? _sha;
  String? get sha => _$this._sha;
  set sha(String? sha) => _$this._sha = sha;

  String? _details;
  String? get details => _$this._details;
  set details(String? details) => _$this._details = details;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

  MergeResultRequestBuilder() {
    MergeResultRequest._defaults(this);
  }

  MergeResultRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _result = $v.result;
      _sha = $v.sha;
      _details = $v.details;
      _version = $v.version;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeResultRequest other) {
    _$v = other as _$MergeResultRequest;
  }

  @override
  void update(void Function(MergeResultRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeResultRequest build() => _build();

  _$MergeResultRequest _build() {
    final _$result = _$v ??
        _$MergeResultRequest._(
          result: BuiltValueNullFieldError.checkNotNull(
              result, r'MergeResultRequest', 'result'),
          sha: sha,
          details: details,
          version: version,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
