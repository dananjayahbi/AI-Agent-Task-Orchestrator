// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_register_response.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$DeviceRegisterResponse extends DeviceRegisterResponse {
  @override
  final int id;
  @override
  final PlatformEnum platform;
  @override
  final bool biometricBound;
  @override
  final DateTime expiresAt;
  @override
  final String token;

  factory _$DeviceRegisterResponse(
          [void Function(DeviceRegisterResponseBuilder)? updates]) =>
      (DeviceRegisterResponseBuilder()..update(updates))._build();

  _$DeviceRegisterResponse._(
      {required this.id,
      required this.platform,
      required this.biometricBound,
      required this.expiresAt,
      required this.token})
      : super._();
  @override
  DeviceRegisterResponse rebuild(
          void Function(DeviceRegisterResponseBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  DeviceRegisterResponseBuilder toBuilder() =>
      DeviceRegisterResponseBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is DeviceRegisterResponse &&
        id == other.id &&
        platform == other.platform &&
        biometricBound == other.biometricBound &&
        expiresAt == other.expiresAt &&
        token == other.token;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, id.hashCode);
    _$hash = $jc(_$hash, platform.hashCode);
    _$hash = $jc(_$hash, biometricBound.hashCode);
    _$hash = $jc(_$hash, expiresAt.hashCode);
    _$hash = $jc(_$hash, token.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'DeviceRegisterResponse')
          ..add('id', id)
          ..add('platform', platform)
          ..add('biometricBound', biometricBound)
          ..add('expiresAt', expiresAt)
          ..add('token', token))
        .toString();
  }
}

class DeviceRegisterResponseBuilder
    implements Builder<DeviceRegisterResponse, DeviceRegisterResponseBuilder> {
  _$DeviceRegisterResponse? _$v;

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

  DateTime? _expiresAt;
  DateTime? get expiresAt => _$this._expiresAt;
  set expiresAt(DateTime? expiresAt) => _$this._expiresAt = expiresAt;

  String? _token;
  String? get token => _$this._token;
  set token(String? token) => _$this._token = token;

  DeviceRegisterResponseBuilder() {
    DeviceRegisterResponse._defaults(this);
  }

  DeviceRegisterResponseBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _id = $v.id;
      _platform = $v.platform;
      _biometricBound = $v.biometricBound;
      _expiresAt = $v.expiresAt;
      _token = $v.token;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(DeviceRegisterResponse other) {
    _$v = other as _$DeviceRegisterResponse;
  }

  @override
  void update(void Function(DeviceRegisterResponseBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  DeviceRegisterResponse build() => _build();

  _$DeviceRegisterResponse _build() {
    final _$result = _$v ??
        _$DeviceRegisterResponse._(
          id: BuiltValueNullFieldError.checkNotNull(
              id, r'DeviceRegisterResponse', 'id'),
          platform: BuiltValueNullFieldError.checkNotNull(
              platform, r'DeviceRegisterResponse', 'platform'),
          biometricBound: BuiltValueNullFieldError.checkNotNull(
              biometricBound, r'DeviceRegisterResponse', 'biometricBound'),
          expiresAt: BuiltValueNullFieldError.checkNotNull(
              expiresAt, r'DeviceRegisterResponse', 'expiresAt'),
          token: BuiltValueNullFieldError.checkNotNull(
              token, r'DeviceRegisterResponse', 'token'),
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
