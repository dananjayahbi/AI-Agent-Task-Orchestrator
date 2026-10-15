// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ops_overview.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$OpsOverview extends OpsOverview {
  @override
  final String schemaVersion;
  @override
  final String generatedAt;
  @override
  final BuiltMap<String, JsonObject?> metrics;
  @override
  final BuiltList<AlertState> alerts;
  @override
  final OpsHealth health;

  factory _$OpsOverview([void Function(OpsOverviewBuilder)? updates]) =>
      (OpsOverviewBuilder()..update(updates))._build();

  _$OpsOverview._(
      {required this.schemaVersion,
      required this.generatedAt,
      required this.metrics,
      required this.alerts,
      required this.health})
      : super._();
  @override
  OpsOverview rebuild(void Function(OpsOverviewBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  OpsOverviewBuilder toBuilder() => OpsOverviewBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is OpsOverview &&
        schemaVersion == other.schemaVersion &&
        generatedAt == other.generatedAt &&
        metrics == other.metrics &&
        alerts == other.alerts &&
        health == other.health;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, schemaVersion.hashCode);
    _$hash = $jc(_$hash, generatedAt.hashCode);
    _$hash = $jc(_$hash, metrics.hashCode);
    _$hash = $jc(_$hash, alerts.hashCode);
    _$hash = $jc(_$hash, health.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'OpsOverview')
          ..add('schemaVersion', schemaVersion)
          ..add('generatedAt', generatedAt)
          ..add('metrics', metrics)
          ..add('alerts', alerts)
          ..add('health', health))
        .toString();
  }
}

class OpsOverviewBuilder implements Builder<OpsOverview, OpsOverviewBuilder> {
  _$OpsOverview? _$v;

  String? _schemaVersion;
  String? get schemaVersion => _$this._schemaVersion;
  set schemaVersion(String? schemaVersion) =>
      _$this._schemaVersion = schemaVersion;

  String? _generatedAt;
  String? get generatedAt => _$this._generatedAt;
  set generatedAt(String? generatedAt) => _$this._generatedAt = generatedAt;

  MapBuilder<String, JsonObject?>? _metrics;
  MapBuilder<String, JsonObject?> get metrics =>
      _$this._metrics ??= MapBuilder<String, JsonObject?>();
  set metrics(MapBuilder<String, JsonObject?>? metrics) =>
      _$this._metrics = metrics;

  ListBuilder<AlertState>? _alerts;
  ListBuilder<AlertState> get alerts =>
      _$this._alerts ??= ListBuilder<AlertState>();
  set alerts(ListBuilder<AlertState>? alerts) => _$this._alerts = alerts;

  OpsHealthBuilder? _health;
  OpsHealthBuilder get health => _$this._health ??= OpsHealthBuilder();
  set health(OpsHealthBuilder? health) => _$this._health = health;

  OpsOverviewBuilder() {
    OpsOverview._defaults(this);
  }

  OpsOverviewBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _schemaVersion = $v.schemaVersion;
      _generatedAt = $v.generatedAt;
      _metrics = $v.metrics.toBuilder();
      _alerts = $v.alerts.toBuilder();
      _health = $v.health.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(OpsOverview other) {
    _$v = other as _$OpsOverview;
  }

  @override
  void update(void Function(OpsOverviewBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  OpsOverview build() => _build();

  _$OpsOverview _build() {
    _$OpsOverview _$result;
    try {
      _$result = _$v ??
          _$OpsOverview._(
            schemaVersion: BuiltValueNullFieldError.checkNotNull(
                schemaVersion, r'OpsOverview', 'schemaVersion'),
            generatedAt: BuiltValueNullFieldError.checkNotNull(
                generatedAt, r'OpsOverview', 'generatedAt'),
            metrics: metrics.build(),
            alerts: alerts.build(),
            health: health.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'metrics';
        metrics.build();
        _$failedField = 'alerts';
        alerts.build();
        _$failedField = 'health';
        health.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'OpsOverview', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
