// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'health_live.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$HealthLive extends HealthLive {
  @override
  final String status;

  factory _$HealthLive([void Function(HealthLiveBuilder)? updates]) =>
      (HealthLiveBuilder()..update(updates))._build();

  _$HealthLive._({required this.status}) : super._();
  @override
  HealthLive rebuild(void Function(HealthLiveBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  HealthLiveBuilder toBuilder() => HealthLiveBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is HealthLive && status == other.status;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, status.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'HealthLive')..add('status', status))
        .toString();
  }
}

class HealthLiveBuilder implements Builder<HealthLive, HealthLiveBuilder> {
  _$HealthLive? _$v;

  String? _status;
  String? get status => _$this._status;
  set status(String? status) => _$this._status = status;

  HealthLiveBuilder() {
    HealthLive._defaults(this);
  }

  HealthLiveBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _status = $v.status;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(HealthLive other) {
    _$v = other as _$HealthLive;
  }

  @override
  void update(void Function(HealthLiveBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  HealthLive build() => _build();

  _$HealthLive _build() {
    final _$result = _$v ??
        _$HealthLive._(
          status: BuiltValueNullFieldError.checkNotNull(
              status, r'HealthLive', 'status'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
