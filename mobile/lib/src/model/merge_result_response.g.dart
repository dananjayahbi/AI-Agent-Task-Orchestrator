// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_result_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeResultResponse extends MergeResultResponse {
  @override
  final QueueTaskState task;
  @override
  final ResultEnum result;
  @override
  final String? sha;

  factory _$MergeResultResponse(
          [void Function(MergeResultResponseBuilder)? updates]) =>
      (MergeResultResponseBuilder()..update(updates))._build();

  _$MergeResultResponse._({required this.task, required this.result, this.sha})
      : super._();
  @override
  MergeResultResponse rebuild(
          void Function(MergeResultResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeResultResponseBuilder toBuilder() =>
      MergeResultResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeResultResponse &&
        task == other.task &&
        result == other.result &&
        sha == other.sha;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jc(_$hash, result.hashCode);
    _$hash = $jc(_$hash, sha.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'MergeResultResponse')
          ..add('task', task)
          ..add('result', result)
          ..add('sha', sha))
        .toString();
  }
}

class MergeResultResponseBuilder
    implements Builder<MergeResultResponse, MergeResultResponseBuilder> {
  _$MergeResultResponse? _$v;

  QueueTaskStateBuilder? _task;
  QueueTaskStateBuilder get task => _$this._task ??= QueueTaskStateBuilder();
  set task(QueueTaskStateBuilder? task) => _$this._task = task;

  ResultEnum? _result;
  ResultEnum? get result => _$this._result;
  set result(ResultEnum? result) => _$this._result = result;

  String? _sha;
  String? get sha => _$this._sha;
  set sha(String? sha) => _$this._sha = sha;

  MergeResultResponseBuilder() {
    MergeResultResponse._defaults(this);
  }

  MergeResultResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _task = $v.task.toBuilder();
      _result = $v.result;
      _sha = $v.sha;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeResultResponse other) {
    _$v = other as _$MergeResultResponse;
  }

  @override
  void update(void Function(MergeResultResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeResultResponse build() => _build();

  _$MergeResultResponse _build() {
    _$MergeResultResponse _$result;
    try {
      _$result = _$v ??
          _$MergeResultResponse._(
            task: task.build(),
            result: BuiltValueNullFieldError.checkNotNull(
                result, r'MergeResultResponse', 'result'),
            sha: sha,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'task';
        task.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'MergeResultResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
