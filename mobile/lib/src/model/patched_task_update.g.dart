// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'patched_task_update.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$PatchedTaskUpdate extends PatchedTaskUpdate {
  @override
  final int? version;
  @override
  final String? title;
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
  @override
  final BuiltList<String>? dependsOn;

  factory _$PatchedTaskUpdate(
          [void Function(PatchedTaskUpdateBuilder)? updates]) =>
      (PatchedTaskUpdateBuilder()..update(updates))._build();

  _$PatchedTaskUpdate._(
      {this.version,
      this.title,
      this.description,
      this.acceptanceCriteria,
      this.targetScope,
      this.testCommand,
      this.priority,
      this.dependsOn})
      : super._();
  @override
  PatchedTaskUpdate rebuild(void Function(PatchedTaskUpdateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  PatchedTaskUpdateBuilder toBuilder() =>
      PatchedTaskUpdateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is PatchedTaskUpdate &&
        version == other.version &&
        title == other.title &&
        description == other.description &&
        acceptanceCriteria == other.acceptanceCriteria &&
        targetScope == other.targetScope &&
        testCommand == other.testCommand &&
        priority == other.priority &&
        dependsOn == other.dependsOn;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, version.hashCode);
    _$hash = $jc(_$hash, title.hashCode);
    _$hash = $jc(_$hash, description.hashCode);
    _$hash = $jc(_$hash, acceptanceCriteria.hashCode);
    _$hash = $jc(_$hash, targetScope.hashCode);
    _$hash = $jc(_$hash, testCommand.hashCode);
    _$hash = $jc(_$hash, priority.hashCode);
    _$hash = $jc(_$hash, dependsOn.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'PatchedTaskUpdate')
          ..add('version', version)
          ..add('title', title)
          ..add('description', description)
          ..add('acceptanceCriteria', acceptanceCriteria)
          ..add('targetScope', targetScope)
          ..add('testCommand', testCommand)
          ..add('priority', priority)
          ..add('dependsOn', dependsOn))
        .toString();
  }
}

class PatchedTaskUpdateBuilder
    implements Builder<PatchedTaskUpdate, PatchedTaskUpdateBuilder> {
  _$PatchedTaskUpdate? _$v;

  int? _version;
  int? get version => _$this._version;
  set version(int? version) => _$this._version = version;

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

  ListBuilder<String>? _dependsOn;
  ListBuilder<String> get dependsOn =>
      _$this._dependsOn ??= ListBuilder<String>();
  set dependsOn(ListBuilder<String>? dependsOn) =>
      _$this._dependsOn = dependsOn;

  PatchedTaskUpdateBuilder() {
    PatchedTaskUpdate._defaults(this);
  }

  PatchedTaskUpdateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _version = $v.version;
      _title = $v.title;
      _description = $v.description;
      _acceptanceCriteria = $v.acceptanceCriteria?.toBuilder();
      _targetScope = $v.targetScope?.toBuilder();
      _testCommand = $v.testCommand;
      _priority = $v.priority;
      _dependsOn = $v.dependsOn?.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(PatchedTaskUpdate other) {
    _$v = other as _$PatchedTaskUpdate;
  }

  @override
  void update(void Function(PatchedTaskUpdateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  PatchedTaskUpdate build() => _build();

  _$PatchedTaskUpdate _build() {
    _$PatchedTaskUpdate _$result;
    try {
      _$result = _$v ??
          _$PatchedTaskUpdate._(
            version: version,
            title: title,
            description: description,
            acceptanceCriteria: _acceptanceCriteria?.build(),
            targetScope: _targetScope?.build(),
            testCommand: testCommand,
            priority: priority,
            dependsOn: _dependsOn?.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'acceptanceCriteria';
        _acceptanceCriteria?.build();
        _$failedField = 'targetScope';
        _targetScope?.build();

        _$failedField = 'dependsOn';
        _dependsOn?.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'PatchedTaskUpdate', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
