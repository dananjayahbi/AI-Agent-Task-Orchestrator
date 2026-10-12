// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_summary.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$DeviceSummary extends DeviceSummary {
  @override
  final int id;
  @override
  final PlatformEnum platform;
  @override
  final bool biometricBound;
  @override
  final DateTime? lastSeenAt;
  @override
  final DateTime? revokedAt;
  @override
  final DateTime? expiresAt;

  factory _$DeviceSummary([void Function(DeviceSummaryBuilder)? updates]) =>
      (DeviceSummaryBuilder()..update(updates))._build();

  _$DeviceSummary._(
      {required this.id,
      required this.platform,
      required this.biometricBound,
      this.lastSeenAt,
      this.revokedAt,
      this.expiresAt})
      : super._();
  @override
  DeviceSummary rebuild(void Function(DeviceSummaryBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  DeviceSummaryBuilder toBuilder() => DeviceSummaryBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is DeviceSummary &&
        id == other.id &&
        platform == other.platform &&
        biometricBound == other.biometricBound &&
        lastSeenAt == other.lastSeenAt &&
        revokedAt == other.revokedAt &&
        expiresAt == other.expiresAt;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, platform.hashCode);
    _$hash = $jc(_$hash, biometricBound.hashCode);
    _$hash = $jc(_$hash, lastSeenAt.hashCode);
    _$hash = $jc(_$hash, revokedAt.hashCode);
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'DeviceSummary')
          ..add('id', id)
          ..add('platform', platform)
          ..add('biometricBound', biometricBound)
          ..add('lastSeenAt', lastSeenAt)
          ..add('revokedAt', revokedAt)
          ..add('expiresAt', expiresAt))
        .toString();
  }
}

class DeviceSummaryBuilder
    implements Builder<DeviceSummary, DeviceSummaryBuilder> {
  _$DeviceSummary? _$v;

  int? _id;
  int? get id => _$this._id;
  set id(int? id) => _$this._id = id;

  PlatformEnum? _platform;
  PlatformEnum? get platform => _$this._platform;
  set platform(PlatformEnum? platform) => _$this._platform = platform;

  bool? _biometricBound;
  bool? get biometricBound => _$this._biometricBound;
  set biometricBound(bool? biometricBound) =>
      _$this._biometricBound = biometricBound;

  DateTime? _lastSeenAt;
  DateTime? get lastSeenAt => _$this._lastSeenAt;
  set lastSeenAt(DateTime? lastSeenAt) => _$this._lastSeenAt = lastSeenAt;

  DateTime? _revokedAt;
  DateTime? get revokedAt => _$this._revokedAt;
  set revokedAt(DateTime? revokedAt) => _$this._revokedAt = revokedAt;

  DateTime? _expiresAt;
  DateTime? get expiresAt => _$this._expiresAt;
  set expiresAt(DateTime? expiresAt) => _$this._expiresAt = expiresAt;

  DeviceSummaryBuilder() {
    DeviceSummary._defaults(this);
  }

  DeviceSummaryBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _platform = $v.platform;
      _biometricBound = $v.biometricBound;
      _lastSeenAt = $v.lastSeenAt;
      _revokedAt = $v.revokedAt;
      _expiresAt = $v.expiresAt;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(DeviceSummary other) {
    _$v = other as _$DeviceSummary;
  }

  @override
  void update(void Function(DeviceSummaryBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  DeviceSummary build() => _build();

  _$DeviceSummary _build() {
    final _$result = _$v ??
        _$DeviceSummary._(
          id: BuiltValueNullFieldError.checkNotNull(id, r'DeviceSummary', 'id'),
          platform: BuiltValueNullFieldError.checkNotNull(
              platform, r'DeviceSummary', 'platform'),
          biometricBound: BuiltValueNullFieldError.checkNotNull(
              biometricBound, r'DeviceSummary', 'biometricBound'),
          lastSeenAt: lastSeenAt,
          revokedAt: revokedAt,
          expiresAt: expiresAt,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
