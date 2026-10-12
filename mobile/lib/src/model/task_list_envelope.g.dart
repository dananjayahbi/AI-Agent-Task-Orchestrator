// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task_list_envelope.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$TaskListEnvelope extends TaskListEnvelope {
  @override
  final BuiltList<Task> results;
  @override
  final String? nextCursor;

  factory _$TaskListEnvelope(
          [void Function(TaskListEnvelopeBuilder)? updates]) =>
      (TaskListEnvelopeBuilder()..update(updates))._build();

  _$TaskListEnvelope._({required this.results, this.nextCursor}) : super._();
  @override
  TaskListEnvelope rebuild(void Function(TaskListEnvelopeBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  TaskListEnvelopeBuilder toBuilder() =>
      TaskListEnvelopeBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is TaskListEnvelope &&
        results == other.results &&
        nextCursor == other.nextCursor;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, results.hashCode);
    _$hash = $jc(_$hash, nextCursor.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'TaskListEnvelope')
          ..add('results', results)
          ..add('nextCursor', nextCursor))
        .toString();
  }
}

class TaskListEnvelopeBuilder
    implements Builder<TaskListEnvelope, TaskListEnvelopeBuilder> {
  _$TaskListEnvelope? _$v;

  ListBuilder<Task>? _results;
  ListBuilder<Task> get results => _$this._results ??= ListBuilder<Task>();
  set results(ListBuilder<Task>? results) => _$this._results = results;

  String? _nextCursor;
  String? get nextCursor => _$this._nextCursor;
  set nextCursor(String? nextCursor) => _$this._nextCursor = nextCursor;

  TaskListEnvelopeBuilder() {
    TaskListEnvelope._defaults(this);
  }

  TaskListEnvelopeBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _results = $v.results.toBuilder();
      _nextCursor = $v.nextCursor;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(TaskListEnvelope other) {
    _$v = other as _$TaskListEnvelope;
  }

  @override
  void update(void Function(TaskListEnvelopeBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  TaskListEnvelope build() => _build();

  _$TaskListEnvelope _build() {
    _$TaskListEnvelope _$result;
    try {
      _$result = _$v ??
          _$TaskListEnvelope._(
            results: results.build(),
            nextCursor: nextCursor,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'results';
        results.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'TaskListEnvelope', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
