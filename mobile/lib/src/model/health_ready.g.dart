// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health_ready.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$HealthReady extends HealthReady {
  @override
  final String status;
  @override
  final BuiltMap<String, String> checks;

  factory _$HealthReady([void Function(HealthReadyBuilder)? updates]) =>
      (HealthReadyBuilder()..update(updates))._build();

  _$HealthReady._({required this.status, required this.checks}) : super._();
  @override
  HealthReady rebuild(void Function(HealthReadyBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  HealthReadyBuilder toBuilder() => HealthReadyBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is HealthReady &&
        status == other.status &&
        checks == other.checks;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, status.hashCode);
    _$hash = $jc(_$hash, checks.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'HealthReady')
          ..add('status', status)
          ..add('checks', checks))
        .toString();
  }
}

class HealthReadyBuilder implements Builder<HealthReady, HealthReadyBuilder> {
  _$HealthReady? _$v;

  String? _status;
  String? get status => _$this._status;
  set status(String? status) => _$this._status = status;

  MapBuilder<String, String>? _checks;
  MapBuilder<String, String> get checks =>
      _$this._checks ??= MapBuilder<String, String>();
  set checks(MapBuilder<String, String>? checks) => _$this._checks = checks;

  HealthReadyBuilder() {
    HealthReady._defaults(this);
  }

  HealthReadyBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _status = $v.status;
      _checks = $v.checks.toBuilder();
      _$v = null;
    }
    return this;
  }

  @override
  void replace(HealthReady other) {
    _$v = other as _$HealthReady;
  }

  @override
  void update(void Function(HealthReadyBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  HealthReady build() => _build();

  _$HealthReady _build() {
    _$HealthReady _$result;
    try {
      _$result = _$v ??
          _$HealthReady._(
            status: BuiltValueNullFieldError.checkNotNull(
                status, r'HealthReady', 'status'),
            checks: checks.build(),
          );
    } catch (_) {
      late String _$failedField;
      try {
        _$failedField = 'checks';
        checks.build();
      } catch (e) {
        throw BuiltValueNestedFieldError(
            r'HealthReady', _$failedField, e.toString());
      }
      rethrow;
    }
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
