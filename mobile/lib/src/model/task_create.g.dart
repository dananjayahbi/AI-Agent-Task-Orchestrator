// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'task_create.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$TaskCreate extends TaskCreate {
  @override
  final String title;
  @override
  final String? description;
  @override
  final BuiltList<String>? acceptanceCriteria;
  @override
  final BuiltList<String>? targetScope;
  @override
  final String? testCommand;
  @override
  final PriorityEnum? priority;

  factory _$TaskCreate([void Function(TaskCreateBuilder)? updates]) =>
      (TaskCreateBuilder()..update(updates))._build();

  _$TaskCreate._(
      {required this.title,
      this.description,
      this.acceptanceCriteria,
      this.targetScope,
      this.testCommand,
      this.priority})
      : super._();
  @override
  TaskCreate rebuild(void Function(TaskCreateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  TaskCreateBuilder toBuilder() => TaskCreateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is TaskCreate &&
        title == other.title &&
        description == other.description &&
        acceptanceCriteria == other.acceptanceCriteria &&
        targetScope == other.targetScope &&
        testCommand == other.testCommand &&
        priority == other.priority;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, title.hashCode);
    _$hash = $jc(_$hash, description.hashCode);
    _$hash = $jc(_$hash, acceptanceCriteria.hashCode);
    _$hash = $jc(_$hash, targetScope.hashCode);
    _$hash = $jc(_$hash, testCommand.hashCode);
    _$hash = $jc(_$hash, priority.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'TaskCreate')
          ..add('title', title)
          ..add('description', description)
          ..add('acceptanceCriteria', acceptanceCriteria)
          ..add('targetScope', targetScope)
          ..add('testCommand', testCommand)
          ..add('priority', priority))
        .toString();
  }
}

class TaskCreateBuilder implements Builder<TaskCreate, TaskCreateBuilder> {
  _$TaskCreate? _$v;

  String? _title;
  String? get title => _$this._title;
  set title(String? title) => _$this._title = title;

  String? _description;
  String? get description => _$this._description;
  set description(String? description) => _$this._description = description;

  ListBuilder<String>? _acceptanceCriteria;
  ListBuilder<String> get acceptanceCriteria =>
      _$this._acceptanceCriteria ??= ListBuilder<String>();
  set acceptanceCriteria(ListBuilder<String>? acceptanceCriteria) =>
      _$this._acceptanceCriteria = acceptanceCriteria;

  ListBuilder<String>? _targetScope;
  ListBuilder<String> get targetScope =>
      _$this._targetScope ??= ListBuilder<String>();
  set targetScope(ListBuilder<String>? targetScope) =>
      _$this._targetScope = targetScope;

  String? _testCommand;
  String? get testCommand => _$this._testCommand;
  set testCommand(String? testCommand) => _$this._testCommand = testCommand;

  PriorityEnum? _priority;
  PriorityEnum? get priority => _$this._priority;
  set priority(PriorityEnum? priority) => _$this._priority = priority;

  TaskCreateBuilder() {
    TaskCreate._defaults(this);
  }

  TaskCreateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _title = $v.title;
      _description = $v.description;
      _acceptanceCriteria = $v.acceptanceCriteria?.toBuilder();
      _targetScope = $v.targetScope?.toBuilder();
      _testCommand = $v.testCommand;
      _priority = $v.priority;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(TaskCreate other) {
    _$v = other as _$TaskCreate;
  }

  @override
  void update(void Function(TaskCreateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  TaskCreate build() => _build();

  _$TaskCreate _build() {
    _$TaskCreate _$result;
    try {
      _$result = _$v ??
          _$TaskCreate._(
            title: BuiltValueNullFieldError.checkNotNull(
                title, r'TaskCreate', 'title'),
            description: description,
            acceptanceCriteria: _acceptanceCriteria?.build(),
            targetScope: _targetScope?.build(),
            testCommand: testCommand,
            priority: priority,
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'acceptanceCriteria';
        _acceptanceCriteria?.build();
        _$failedField = 'targetScope';
        _targetScope?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'TaskCreate', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
