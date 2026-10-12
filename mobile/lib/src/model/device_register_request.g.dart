// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'device_register_request.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

class _$DeviceRegisterRequest extends DeviceRegisterRequest {
  @override
  final PlatformEnum platform;
  @override
  final String pushToken;
  @override
  final bool? biometricBound;

  factory _$DeviceRegisterRequest(
          [void Function(DeviceRegisterRequestBuilder)? updates]) =>
      (DeviceRegisterRequestBuilder()..update(updates))._build();

  _$DeviceRegisterRequest._(
      {required this.platform, required this.pushToken, this.biometricBound})
      : super._();
  @override
  DeviceRegisterRequest rebuild(
          void Function(DeviceRegisterRequestBuilder) updates) =>
      (toBuilder()..update(updates)).build();

  @override
  DeviceRegisterRequestBuilder toBuilder() =>
      DeviceRegisterRequestBuilder()..replace(this);

  @override
  bool operator ==(Object other) {
    if (identical(other, this)) return true;
    return other is DeviceRegisterRequest &&
        platform == other.platform &&
        pushToken == other.pushToken &&
        biometricBound == other.biometricBound;
  }

  @override
  int get hashCode {
    var _$hash = 0;
    _$hash = $jc(_$hash, platform.hashCode);
    _$hash = $jc(_$hash, pushToken.hashCode);
    _$hash = $jc(_$hash, biometricBound.hashCode);
    _$hash = $jf(_$hash);
    return _$hash;
  }

  @override
  String toString() {
    return (newBuiltValueToStringHelper(r'DeviceRegisterRequest')
          ..add('platform', platform)
          ..add('pushToken', pushToken)
          ..add('biometricBound', biometricBound))
        .toString();
  }
}

class DeviceRegisterRequestBuilder
    implements Builder<DeviceRegisterRequest, DeviceRegisterRequestBuilder> {
  _$DeviceRegisterRequest? _$v;

  PlatformEnum? _platform;
  PlatformEnum? get platform => _$this._platform;
  set platform(PlatformEnum? platform) => _$this._platform = platform;

  String? _pushToken;
  String? get pushToken => _$this._pushToken;
  set pushToken(String? pushToken) => _$this._pushToken = pushToken;

  bool? _biometricBound;
  bool? get biometricBound => _$this._biometricBound;
  set biometricBound(bool? biometricBound) =>
      _$this._biometricBound = biometricBound;

  DeviceRegisterRequestBuilder() {
    DeviceRegisterRequest._defaults(this);
  }

  DeviceRegisterRequestBuilder get _$this {
    final $v = _$v;
    if ($v != null) {
      _platform = $v.platform;
      _pushToken = $v.pushToken;
      _biometricBound = $v.biometricBound;
      _$v = null;
    }
    return this;
  }

  @override
  void replace(DeviceRegisterRequest other) {
    _$v = other as _$DeviceRegisterRequest;
  }

  @override
  void update(void Function(DeviceRegisterRequestBuilder)? updates) {
    if (updates != null) updates(this);
  }

  @override
  DeviceRegisterRequest build() => _build();

  _$DeviceRegisterRequest _build() {
    final _$result = _$v ??
        _$DeviceRegisterRequest._(
          platform: BuiltValueNullFieldError.checkNotNull(
              platform, r'DeviceRegisterRequest', 'platform'),
          pushToken: BuiltValueNullFieldError.checkNotNull(
              pushToken, r'DeviceRegisterRequest', 'pushToken'),
          biometricBound: biometricBound,
        );
    replace(_$result);
    return _$result;
  }
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
