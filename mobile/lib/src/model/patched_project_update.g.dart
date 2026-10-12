// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'patched_project_update.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$PatchedProjectUpdate extends PatchedProjectUpdate {
  @override
  final String? name;
  @override
  final String? repoPath;
  @override
  final String? defaultBranch;
  @override
  final String? systemPromptRules;
  @override
  final ActiveStatusEnum? activeStatus;

  factory _$PatchedProjectUpdate(
          [void Function(PatchedProjectUpdateBuilder)? updates]) =>
      (PatchedProjectUpdateBuilder()..update(updates))._build();

  _$PatchedProjectUpdate._(
      {this.name,
      this.repoPath,
      this.defaultBranch,
      this.systemPromptRules,
      this.activeStatus})
      : super._();
  @override
  PatchedProjectUpdate rebuild(
          void Function(PatchedProjectUpdateBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  PatchedProjectUpdateBuilder toBuilder() =>
      PatchedProjectUpdateBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is PatchedProjectUpdate &&
        name == other.name &&
        repoPath == other.repoPath &&
        defaultBranch == other.defaultBranch &&
        systemPromptRules == other.systemPromptRules &&
        activeStatus == other.activeStatus;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, name.hashCode);
    _$hash = $jc(_$hash, repoPath.hashCode);
    _$hash = $jc(_$hash, defaultBranch.hashCode);
    _$hash = $jc(_$hash, systemPromptRules.hashCode);
    _$hash = $jc(_$hash, activeStatus.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'PatchedProjectUpdate')
          ..add('name', name)
          ..add('repoPath', repoPath)
          ..add('defaultBranch', defaultBranch)
          ..add('systemPromptRules', systemPromptRules)
          ..add('activeStatus', activeStatus))
        .toString();
  }
}

class PatchedProjectUpdateBuilder
    implements Builder<PatchedProjectUpdate, PatchedProjectUpdateBuilder> {
  _$PatchedProjectUpdate? _$v;

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

  ActiveStatusEnum? _activeStatus;
  ActiveStatusEnum? get activeStatus => _$this._activeStatus;
  set activeStatus(ActiveStatusEnum? activeStatus) =>
      _$this._activeStatus = activeStatus;

  PatchedProjectUpdateBuilder() {
    PatchedProjectUpdate._defaults(this);
  }

  PatchedProjectUpdateBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _name = $v.name;
      _repoPath = $v.repoPath;
      _defaultBranch = $v.defaultBranch;
      _systemPromptRules = $v.systemPromptRules;
      _activeStatus = $v.activeStatus;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(PatchedProjectUpdate other) {
    _$v = other as _$PatchedProjectUpdate;
  }

  @override
  void update(void Function(PatchedProjectUpdateBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  PatchedProjectUpdate build() => _build();

  _$PatchedProjectUpdate _build() {
    final _$result = _$v ??
        _$PatchedProjectUpdate._(
          name: name,
          repoPath: repoPath,
          defaultBranch: defaultBranch,
          systemPromptRules: systemPromptRules,
          activeStatus: activeStatus,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
