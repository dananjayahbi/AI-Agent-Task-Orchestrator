// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_create.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ProjectCreate extends ProjectCreate {
  @override
  final String name;
  @override
  final String repoPath;
  @override
  final String defaultBranch;
  @override
  final String? systemPromptRules;

  factory _$ProjectCreate([void Function(ProjectCreateBuilder)? updates]) =>
      (ProjectCreateBuilder()..update(updates))._build();

  _$ProjectCreate._(
      {required this.name,
      required this.repoPath,
      required this.defaultBranch,
      this.systemPromptRules})
      : super._();
  @override
  ProjectCreate rebuild(void Function(ProjectCreateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ProjectCreateBuilder toBuilder() => ProjectCreateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ProjectCreate &&
        name == other.name &&
        repoPath == other.repoPath &&
        defaultBranch == other.defaultBranch &&
        systemPromptRules == other.systemPromptRules;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, name.hashCode);
    _$hash = $jc(_$hash, repoPath.hashCode);
    _$hash = $jc(_$hash, defaultBranch.hashCode);
    _$hash = $jc(_$hash, systemPromptRules.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ProjectCreate')
          ..add('name', name)
          ..add('repoPath', repoPath)
          ..add('defaultBranch', defaultBranch)
          ..add('systemPromptRules', systemPromptRules))
        .toString();
  }
}

class ProjectCreateBuilder
    implements Builder<ProjectCreate, ProjectCreateBuilder> {
  _$ProjectCreate? _$v;

  String? _name;
  String? get name => _$this._name;
  set name(String? name) => _$this._name = name;

  String? _repoPath;
  String? get repoPath => _$this._repoPath;
  set repoPath(String? repoPath) => _$this._repoPath = repoPath;

  String? _defaultBranch;
  String? get defaultBranch => _$this._defaultBranch;
  set defaultBranch(String? defaultBranch) =>
      _$this._defaultBranch = defaultBranch;

  String? _systemPromptRules;
  String? get systemPromptRules => _$this._systemPromptRules;
  set systemPromptRules(String? systemPromptRules) =>
      _$this._systemPromptRules = systemPromptRules;

  ProjectCreateBuilder() {
    ProjectCreate._defaults(this);
  }

  ProjectCreateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _name = $v.name;
      _repoPath = $v.repoPath;
      _defaultBranch = $v.defaultBranch;
      _systemPromptRules = $v.systemPromptRules;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ProjectCreate other) {
    _$v = other as _$ProjectCreate;
  }

  @override
  void update(void Function(ProjectCreateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ProjectCreate build() => _build();

  _$ProjectCreate _build() {
    final _$result = _$v ??
        _$ProjectCreate._(
          name: BuiltValueNullFieldError.checkNotNull(
              name, r'ProjectCreate', 'name'),
          repoPath: BuiltValueNullFieldError.checkNotNull(
              repoPath, r'ProjectCreate', 'repoPath'),
          defaultBranch: BuiltValueNullFieldError.checkNotNull(
              defaultBranch, r'ProjectCreate', 'defaultBranch'),
          systemPromptRules: systemPromptRules,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
