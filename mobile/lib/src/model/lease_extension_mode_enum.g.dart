// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'lease_extension_mode_enum.dart';

// **************************************************************************
// BuiltValueGenerator
// **************************************************************************

const LeaseExtensionModeEnum _$checkpointOnly =
    const LeaseExtensionModeEnum._('checkpointOnly');
const LeaseExtensionModeEnum _$checkpointAndLiveness =
    const LeaseExtensionModeEnum._('checkpointAndLiveness');

LeaseExtensionModeEnum _$valueOf(String name) {
  switch (name) {
    case 'checkpointOnly':
      return _$checkpointOnly;
    case 'checkpointAndLiveness':
      return _$checkpointAndLiveness;
    default:
      throw ArgumentError(name);
  }
}

final BuiltSet<LeaseExtensionModeEnum> _$values =
    BuiltSet<LeaseExtensionModeEnum>(const <LeaseExtensionModeEnum>[
  _$checkpointOnly,
  _$checkpointAndLiveness,
]);

class _$LeaseExtensionModeEnumMeta {
  const _$LeaseExtensionModeEnumMeta();
  LeaseExtensionModeEnum get checkpointOnly => _$checkpointOnly;
  LeaseExtensionModeEnum get checkpointAndLiveness => _$checkpointAndLiveness;
  LeaseExtensionModeEnum valueOf(String name) => _$valueOf(name);
  BuiltSet<LeaseExtensionModeEnum> get values => _$values;
}

mixin _$LeaseExtensionModeEnumMixin {
  // ignore: non_constant_identifier_names
  _$LeaseExtensionModeEnumMeta get LeaseExtensionModeEnum =>
      const _$LeaseExtensionModeEnumMeta();
}

Serializer<LeaseExtensionModeEnum> _$leaseExtensionModeEnumSerializer =
    _$LeaseExtensionModeEnumSerializer();

class _$LeaseExtensionModeEnumSerializer
    implements PrimitiveSerializer<LeaseExtensionModeEnum> {
  static const Map<String, Object> _toWire = const <String, Object>{
    'checkpointOnly': 'checkpoint_only',
    'checkpointAndLiveness': 'checkpoint_and_liveness',
  };
  static const Map<Object, String> _fromWire = const <Object, String>{
    'checkpoint_only': 'checkpointOnly',
    'checkpoint_and_liveness': 'checkpointAndLiveness',
  };

  @override
  final Iterable<Type> types = const <Type>[LeaseExtensionModeEnum];
  @override
  final String wireName = 'LeaseExtensionModeEnum';

  @override
  Object serialize(Serializers serializers, LeaseExtensionModeEnum object,
          {FullType specifiedType = FullType.unspecified}) =>
      _toWire[object.name] ?? object.name;

  @override
  LeaseExtensionModeEnum deserialize(Serializers serializers, Object serialized,
          {FullType specifiedType = FullType.unspecified}) =>
      LeaseExtensionModeEnum.valueOf(
          _fromWire[serialized] ?? (serialized is String ? serialized : ''));
}

// ignore_for_file: constant_identifier_names, deprecated_member_use_from_same_package, no_leading_underscores_for_local_identifiers, type=lint, unnecessary_brace_in_string_interps, unnecessary_this, unused_import, use_function_type_syntax_for_parameters, use_super_parameters
