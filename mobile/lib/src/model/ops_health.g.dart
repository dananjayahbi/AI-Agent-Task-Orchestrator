// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'ops_health.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$OpsHealth extends OpsHealth {
  @override
  final bool live;
  @override
  final BuiltMap<String, String> checks;

  factory _$OpsHealth([void Function(OpsHealthBuilder)? updates]) =>
      (OpsHealthBuilder()..update(updates))._build();

  _$OpsHealth._({required this.live, required this.checks}) : super._();
  @override
  OpsHealth rebuild(void Function(OpsHealthBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  OpsHealthBuilder toBuilder() => OpsHealthBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is OpsHealth && live == other.live && checks == other.checks;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, live.hashCode);
    _$hash = $jc(_$hash, checks.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'OpsHealth')
          ..add('live', live)
          ..add('checks', checks))
        .toString();
  }
}

class OpsHealthBuilder implements Builder<OpsHealth, OpsHealthBuilder> {
  _$OpsHealth? _$v;

  bool? _live;
  bool? get live => _$this._live;
  set live(bool? live) => _$this._live = live;

  MapBuilder<String, String>? _checks;
  MapBuilder<String, String> get checks =>
      _$this._checks ??= MapBuilder<String, String>();
  set checks(MapBuilder<String, String>? checks) => _$this._checks = checks;

  OpsHealthBuilder() {
    OpsHealth._defaults(this);
  }

  OpsHealthBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _live = $v.live;
      _checks = $v.checks.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(OpsHealth other) {
    _$v = other as _$OpsHealth;
  }

  @override
  void update(void Function(OpsHealthBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  OpsHealth build() => _build();

  _$OpsHealth _build() {
    _$OpsHealth _$result;
    try {
      _$result = _$v ??
          _$OpsHealth._(
            live: BuiltValueNullFieldError.checkNotNull(
                live, r'OpsHealth', 'live'),
            checks: checks.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'checks';
        checks.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'OpsHealth', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
