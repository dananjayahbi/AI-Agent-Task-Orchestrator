// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'merge_start_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$MergeStartResponse extends MergeStartResponse {
  @override
  final QueueTaskState task;

  factory _$MergeStartResponse(
          [void Function(MergeStartResponseBuilder)? updates]) =>
      (MergeStartResponseBuilder()..update(updates))._build();

  _$MergeStartResponse._({required this.task}) : super._();
  @override
  MergeStartResponse rebuild(
          void Function(MergeStartResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  MergeStartResponseBuilder toBuilder() =>
      MergeStartResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is MergeStartResponse && task == other.task;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, task.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'MergeStartResponse')
          ..add('task', task))
        .toString();
  }
}

class MergeStartResponseBuilder
    implements Builder<MergeStartResponse, MergeStartResponseBuilder> {
  _$MergeStartResponse? _$v;

  QueueTaskStateBuilder? _task;
  QueueTaskStateBuilder get task => _$this._task ??= QueueTaskStateBuilder();
  set task(QueueTaskStateBuilder? task) => _$this._task = task;

  MergeStartResponseBuilder() {
    MergeStartResponse._defaults(this);
  }

  MergeStartResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _task = $v.task.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(MergeStartResponse other) {
    _$v = other as _$MergeStartResponse;
  }

  @override
  void update(void Function(MergeStartResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  MergeStartResponse build() => _build();

  _$MergeStartResponse _build() {
    _$MergeStartResponse _$result;
    try {
      _$result = _$v ??
          _$MergeStartResponse._(
            task: task.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'task';
        task.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'MergeStartResponse', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
