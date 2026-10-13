// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'project_dashboard_card.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$ProjectDashboardCard extends ProjectDashboardCard {
  @override
  final String projectId;
  @override
  final String name;
  @override
  final StateCounts stateCounts;
  @override
  final int velocity;
  @override
  final int activeAgents;

  factory _$ProjectDashboardCard(
          [void Function(ProjectDashboardCardBuilder)? updates]) =>
      (ProjectDashboardCardBuilder()..update(updates))._build();

  _$ProjectDashboardCard._(
      {required this.projectId,
      required this.name,
      required this.stateCounts,
      required this.velocity,
      required this.activeAgents})
      : super._();
  @override
  ProjectDashboardCard rebuild(
          void Function(ProjectDashboardCardBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  ProjectDashboardCardBuilder toBuilder() =>
      ProjectDashboardCardBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is ProjectDashboardCard &&
        projectId == other.projectId &&
        name == other.name &&
        stateCounts == other.stateCounts &&
        velocity == other.velocity &&
        activeAgents == other.activeAgents;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, projectId.hashCode);
    _$hash = $jc(_$hash, name.hashCode);
    _$hash = $jc(_$hash, stateCounts.hashCode);
    _$hash = $jc(_$hash, velocity.hashCode);
    _$hash = $jc(_$hash, activeAgents.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'ProjectDashboardCard')
          ..add('projectId', projectId)
          ..add('name', name)
          ..add('stateCounts', stateCounts)
          ..add('velocity', velocity)
          ..add('activeAgents', activeAgents))
        .toString();
  }
}

class ProjectDashboardCardBuilder
    implements Builder<ProjectDashboardCard, ProjectDashboardCardBuilder> {
  _$ProjectDashboardCard? _$v;

  String? _projectId;
  String? get projectId => _$this._projectId;
  set projectId(String? projectId) => _$this._projectId = projectId;

  String? _name;
  String? get name => _$this._name;
  set name(String? name) => _$this._name = name;

  StateCountsBuilder? _stateCounts;
  StateCountsBuilder get stateCounts =>
      _$this._stateCounts ??= StateCountsBuilder();
  set stateCounts(StateCountsBuilder? stateCounts) =>
      _$this._stateCounts = stateCounts;

  int? _velocity;
  int? get velocity => _$this._velocity;
  set velocity(int? velocity) => _$this._velocity = velocity;

  int? _activeAgents;
  int? get activeAgents => _$this._activeAgents;
  set activeAgents(int? activeAgents) => _$this._activeAgents = activeAgents;

  ProjectDashboardCardBuilder() {
    ProjectDashboardCard._defaults(this);
  }

  ProjectDashboardCardBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _projectId = $v.projectId;
      _name = $v.name;
      _stateCounts = $v.stateCounts.toBuilder();
      _velocity = $v.velocity;
      _activeAgents = $v.activeAgents;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(ProjectDashboardCard other) {
    _$v = other as _$ProjectDashboardCard;
  }

  @override
  void update(void Function(ProjectDashboardCardBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  ProjectDashboardCard build() => _build();

  _$ProjectDashboardCard _build() {
    _$ProjectDashboardCard _$result;
    try {
      _$result = _$v ??
          _$ProjectDashboardCard._(
            projectId: BuiltValueNullFieldError.checkNotNull(
                projectId, r'ProjectDashboardCard', 'projectId'),
            name: BuiltValueNullFieldError.checkNotNull(
                name, r'ProjectDashboardCard', 'name'),
            stateCounts: stateCounts.build(),
            velocity: BuiltValueNullFieldError.checkNotNull(
                velocity, r'ProjectDashboardCard', 'velocity'),
            activeAgents: BuiltValueNullFieldError.checkNotNull(
                activeAgents, r'ProjectDashboardCard', 'activeAgents'),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'stateCounts';
        stateCounts.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'ProjectDashboardCard', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
