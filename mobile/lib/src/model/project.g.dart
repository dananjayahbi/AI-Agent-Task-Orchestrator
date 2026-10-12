// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$Project extends Project {
  @override
  final String id;
  @override
  final String name;
  @override
  final String repoPath;
  @override
  final ActiveStatusEnum activeStatus;
  @override
  final String defaultBranch;
  @override
  final String systemPromptRules;
  @override
  final int agentPolicy;
  @override
  final int taskCounter;
  @override
  final DateTime createdAt;
  @override
  final DateTime updatedAt;

  factory _$Project([void Function(ProjectBuilder)? updates]) =>
      (ProjectBuilder()..update(updates))._build();

  _$Project._(
      {required this.id,
      required this.name,
      required this.repoPath,
      required this.activeStatus,
      required this.defaultBranch,
      required this.systemPromptRules,
      required this.agentPolicy,
      required this.taskCounter,
      required this.createdAt,
      required this.updatedAt})
      : super._();
  @override
  Project rebuild(void Function(ProjectBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ProjectBuilder toBuilder() => ProjectBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is Project &&
        id == other.id &&
        name == other.name &&
        repoPath == other.repoPath &&
        activeStatus == other.activeStatus &&
        defaultBranch == other.defaultBranch &&
        systemPromptRules == other.systemPromptRules &&
        agentPolicy == other.agentPolicy &&
        taskCounter == other.taskCounter &&
        createdAt == other.createdAt &&
        updatedAt == other.updatedAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, name.hashCode);
    _$hash = $jc(_$hash, repoPath.hashCode);
    _$hash = $jc(_$hash, activeStatus.hashCode);
    _$hash = $jc(_$hash, defaultBranch.hashCode);
    _$hash = $jc(_$hash, systemPromptRules.hashCode);
    _$hash = $jc(_$hash, agentPolicy.hashCode);
    _$hash = $jc(_$hash, taskCounter.hashCode);
    _$hash = $jc(_$hash, createdAt.hashCode);
    _$hash = $jc(_$hash, updatedAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'Project')
          ..add('id', id)
          ..add('name', name)
          ..add('repoPath', repoPath)
          ..add('activeStatus', activeStatus)
          ..add('defaultBranch', defaultBranch)
          ..add('systemPromptRules', systemPromptRules)
          ..add('agentPolicy', agentPolicy)
          ..add('taskCounter', taskCounter)
          ..add('createdAt', createdAt)
          ..add('updatedAt', updatedAt))
        .toString();
  }
}

class ProjectBuilder implements Builder<Project, ProjectBuilder> {
  _$Project? _$v;

  String? _id;
  String? get id => _$this._id;
  set id(String? id) => _$this._id = id;

  String? _name;
  String? get name => _$this._name;
  set name(String? name) => _$this._name = name;

  String? _repoPath;
  String? get repoPath => _$this._repoPath;
  set repoPath(String? repoPath) => _$this._repoPath = repoPath;

  ActiveStatusEnum? _activeStatus;
  ActiveStatusEnum? get activeStatus => _$this._activeStatus;
  set activeStatus(ActiveStatusEnum? activeStatus) =>
      _$this._activeStatus = activeStatus;

  String? _defaultBranch;
  String? get defaultBranch => _$this._defaultBranch;
  set defaultBranch(String? defaultBranch) =>
      _$this._defaultBranch = defaultBranch;

  String? _systemPromptRules;
  String? get systemPromptRules => _$this._systemPromptRules;
  set systemPromptRules(String? systemPromptRules) =>
      _$this._systemPromptRules = systemPromptRules;

  int? _agentPolicy;
  int? get agentPolicy => _$this._agentPolicy;
  set agentPolicy(int? agentPolicy) => _$this._agentPolicy = agentPolicy;

  int? _taskCounter;
  int? get taskCounter => _$this._taskCounter;
  set taskCounter(int? taskCounter) => _$this._taskCounter = taskCounter;

  DateTime? _createdAt;
  DateTime? get createdAt => _$this._createdAt;
  set createdAt(DateTime? createdAt) => _$this._createdAt = createdAt;

  DateTime? _updatedAt;
  DateTime? get updatedAt => _$this._updatedAt;
  set updatedAt(DateTime? updatedAt) => _$this._updatedAt = updatedAt;

  ProjectBuilder() {
    Project._defaults(this);
  }

  ProjectBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _name = $v.name;
      _repoPath = $v.repoPath;
      _activeStatus = $v.activeStatus;
      _defaultBranch = $v.defaultBranch;
      _systemPromptRules = $v.systemPromptRules;
      _agentPolicy = $v.agentPolicy;
      _taskCounter = $v.taskCounter;
      _createdAt = $v.createdAt;
      _updatedAt = $v.updatedAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(Project other) {
    _$v = other as _$Project;
  }

  @override
  void update(void Function(ProjectBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  Project build() => _build();

  _$Project _build() {
    final _$result = _$v ??
        _$Project._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'Project', 'id'),
          name: BuiltValueNullFieldError.checkNotNull(name, r'Project', 'name'),
          repoPath: BuiltValueNullFieldError.checkNotNull(
              repoPath, r'Project', 'repoPath'),
          activeStatus: BuiltValueNullFieldError.checkNotNull(
              activeStatus, r'Project', 'activeStatus'),
          defaultBranch: BuiltValueNullFieldError.checkNotNull(
              defaultBranch, r'Project', 'defaultBranch'),
          systemPromptRules: BuiltValueNullFieldError.checkNotNull(
              systemPromptRules, r'Project', 'systemPromptRules'),
          agentPolicy: BuiltValueNullFieldError.checkNotNull(
              agentPolicy, r'Project', 'agentPolicy'),
          taskCounter: BuiltValueNullFieldError.checkNotNull(
              taskCounter, r'Project', 'taskCounter'),
          createdAt: BuiltValueNullFieldError.checkNotNull(
              createdAt, r'Project', 'createdAt'),
          updatedAt: BuiltValueNullFieldError.checkNotNull(
              updatedAt, r'Project', 'updatedAt'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
