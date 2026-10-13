// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'dashboard_summary.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$DashboardSummary extends DashboardSummary {
  @override
  final BuiltList<ProjectDashboardCard> projects;

  factory _$DashboardSummary(
          [void Function(DashboardSummaryBuilder)? updates]) =>
      (DashboardSummaryBuilder()..update(updates))._build();

  _$DashboardSummary._({required this.projects}) : super._();
  @override
  DashboardSummary rebuild(void Function(DashboardSummaryBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  DashboardSummaryBuilder toBuilder() =>
      DashboardSummaryBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is DashboardSummary && projects == other.projects;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, projects.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'DashboardSummary')
          ..add('projects', projects))
        .toString();
  }
}

class DashboardSummaryBuilder
    implements Builder<DashboardSummary, DashboardSummaryBuilder> {
  _$DashboardSummary? _$v;

  ListBuilder<ProjectDashboardCard>? _projects;
  ListBuilder<ProjectDashboardCard> get projects =>
      _$this._projects ??= ListBuilder<ProjectDashboardCard>();
  set projects(ListBuilder<ProjectDashboardCard>? projects) =>
      _$this._projects = projects;

  DashboardSummaryBuilder() {
    DashboardSummary._defaults(this);
  }

  DashboardSummaryBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _projects = $v.projects.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(DashboardSummary other) {
    _$v = other as _$DashboardSummary;
  }

  @override
  void update(void Function(DashboardSummaryBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  DashboardSummary build() => _build();

  _$DashboardSummary _build() {
    _$DashboardSummary _$result;
    try {
      _$result = _$v ??
          _$DashboardSummary._(
            projects: projects.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'projects';
        projects.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'DashboardSummary', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
